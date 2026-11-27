from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from android_remote_bridge.cli import show_logs, status
from android_remote_bridge.oidc import (
    AuthenticationError,
    GitHubOIDCVerifier,
    OIDCPolicy,
)
from android_remote_bridge.protocol import parse_command
from android_remote_bridge.server import BridgeHandler
from android_remote_bridge.state import ReplayState, StateError
from android_remote_bridge.tunnel import _URL_PATTERN

COMMAND_ID = "123e4567-e89b-12d3-a456-426614174000"


def envelope(sequence: int = 1) -> bytes:
    return json.dumps({
        "version": 1, "id": COMMAND_ID, "sequence": sequence,
        "operation": "bridge.health", "status": "pending",
    }).encode()


class StateTests(unittest.TestCase):
    def test_sequence_and_jti_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = ReplayState(path)
            first = state.accept(
                sequence=1, jti="token-1", command_id=COMMAND_ID, command_hash="hash-1"
            )
            self.assertIsNone(first)
            result = {"id": COMMAND_ID, "sequence": 1, "status": "completed"}
            state.complete(sequence=1, command_id=COMMAND_ID, result=result)
            self.assertEqual(
                ReplayState(path).accept(
                    sequence=1, jti="token-2", command_id=COMMAND_ID, command_hash="hash-1"
                ),
                result,
            )
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=1, jti="token-2", command_id=COMMAND_ID)
            with self.assertRaises(StateError):
                ReplayState(path).accept(
                    sequence=3, jti="token-3", command_id="future-id", command_hash="hash-3"
                )
            self.assertIsNone(
                ReplayState(path).accept(
                    sequence=2, jti="token-3", command_id="next-id", command_hash="hash-2"
                )
            )

    def test_corrupt_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("broken", encoding="utf-8")
            with self.assertRaises(StateError):
                ReplayState(path).accept(
                    sequence=1, jti="x", command_id=COMMAND_ID, command_hash="hash"
                )


class OIDCTests(unittest.TestCase):
    def test_real_rs256_signature_and_claims_are_verified(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        now = int(time.time())
        claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "termux-bridge",
            "exp": now + 300,
            "iat": now,
            "jti": "unique-token-id",
            "repository": "owner/private-repo",
            "ref": "refs/heads/main",
        }
        token = jwt.encode(claims, private_key, algorithm="RS256")
        verifier = GitHubOIDCVerifier(
            OIDCPolicy("termux-bridge", "owner/private-repo", "refs/heads/main")
        )
        signing_key = type("SigningKey", (), {"key": public_key})()
        with patch.object(verifier._jwks, "get_signing_key_from_jwt", return_value=signing_key):
            verified = verifier.verify(token)
        self.assertEqual(verified["jti"], "unique-token-id")

    def test_repository_mismatch_is_rejected(self) -> None:
        verifier = GitHubOIDCVerifier(OIDCPolicy("aud", "owner/repo", "refs/heads/main"))
        claims = {"repository": "other/repo", "ref": "refs/heads/main", "jti": "id", "iat": 1}
        key = type("SigningKey", (), {"key": "key"})()
        with patch.object(verifier._jwks, "get_signing_key_from_jwt", return_value=key):
            with patch("android_remote_bridge.oidc.jwt.decode", return_value=claims):
                with self.assertRaises(AuthenticationError):
                    verifier.verify("header.payload.signature")


class LifecycleCLITests(unittest.TestCase):
    def test_status_and_logs_without_running_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({
                "audience": "termux-bridge",
                "repository": "owner/private-repo",
                "ref": "refs/heads/main",
                "state_file": str(Path(tmp) / "state" / "replay.json"),
            }), encoding="utf-8")
            self.assertEqual(status(config), {"running": False, "pid": None})
            self.assertIn("No Bridge log", show_logs(config))


class TunnelTests(unittest.TestCase):
    def test_quick_tunnel_url_parser(self) -> None:
        match = _URL_PATTERN.search("INF | https://blue-river-123.trycloudflare.com")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "https://blue-river-123.trycloudflare.com")


class ListenerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), BridgeHandler)
        self.server.verifier = type(
            "Verifier", (), {"verify": lambda _self, _token: {"jti": "test-jti"}}
        )()
        self.server.replay_state = ReplayState(Path(self.tmp.name) / "state.json")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def test_health_endpoint(self) -> None:
        with urllib.request.urlopen(self.base + "/health", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["status"], "ok")

    def test_webhook_requires_bearer_token(self) -> None:
        request = urllib.request.Request(
            self.base + "/webhook", data=envelope(), headers={"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 401)

    def test_webhook_executes_only_validated_operation(self) -> None:
        request = urllib.request.Request(
            self.base + "/webhook",
            data=envelope(),
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read())
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["result"]["status"], "completed")
        self.assertEqual(payload["result"]["data"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
