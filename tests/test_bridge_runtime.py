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
from android_remote_bridge.executor import execute
from android_remote_bridge.oidc import AuthenticationError, GitHubOIDCVerifier, OIDCPolicy
from android_remote_bridge.protocol import parse_command
from android_remote_bridge.server import BridgeHandler
from android_remote_bridge.state import ReplayState, StateError
from android_remote_bridge.tunnel import _URL_PATTERN, _tunnel_event

COMMAND_ID = "test-command-001"


def command_envelope(sequence: int = 1) -> bytes:
    return json.dumps({
        "version": 1, "id": COMMAND_ID, "sequence": sequence,
        "status": "ready", "operation": "shell", "approval": "not_required",
        "timeout_seconds": 10, "command": "printf 'push-mode-ok'",
    }).encode()


class StateTests(unittest.TestCase):
    def test_sequence_and_jti_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = ReplayState(path)
            self.assertIsNone(state.accept(sequence=1,jti="token-1",command_id=COMMAND_ID,command_hash="hash-1"))
            result = {"id": COMMAND_ID, "sequence": 1, "status": "completed"}
            state.complete(sequence=1, command_id=COMMAND_ID, result=result)
            self.assertEqual(ReplayState(path).accept(sequence=1,jti="token-2",command_id=COMMAND_ID,command_hash="hash-1"), result)
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=1,jti="token-2",command_id=COMMAND_ID,command_hash="hash-1")
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=1,jti="token-3",command_id=COMMAND_ID,command_hash="different")
            self.assertIsNone(ReplayState(path).accept(sequence=3,jti="token-4",command_id="future",command_hash="hash-3"))

    def test_restart_marks_active_command_interrupted_without_rerunning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = ReplayState(path)
            state.accept(sequence=1, jti="token-before-restart", command_id=COMMAND_ID, command_hash="payload-hash")
            restarted = ReplayState(path)
            cached = restarted.accept(
                sequence=1, jti="token-after-restart", command_id=COMMAND_ID, command_hash="payload-hash"
            )
            self.assertEqual(cached["status"], "interrupted")
            self.assertEqual(cached["exit_code"], 125)
            self.assertIn("NOT rerun", cached["error"])

    def test_corrupt_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("broken", encoding="utf-8")
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=1,jti="x",command_id=COMMAND_ID,command_hash="hash")


class OIDCTests(unittest.TestCase):
    def test_real_rs256_signature_and_push_claims_are_verified(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = int(time.time())
        claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "termux-push-bridge",
            "exp": now + 300,
            "iat": now,
            "jti": "unique-token-id",
            "repository": "owner/private-repo",
            "ref": "refs/heads/main",
            "event_name": "push",
        }
        token = jwt.encode(claims, private_key, algorithm="RS256")
        verifier = GitHubOIDCVerifier(OIDCPolicy("termux-push-bridge", "owner/private-repo", "refs/heads/main"))
        signing_key = type("SigningKey", (), {"key": private_key.public_key()})()
        with patch.object(verifier._jwks, "get_signing_key_from_jwt", return_value=signing_key):
            verified = verifier.verify(token)
        self.assertEqual(verified["jti"], "unique-token-id")

    def test_wrong_event_claim_is_rejected(self):
        verifier = GitHubOIDCVerifier(OIDCPolicy("aud", "owner/repo", "refs/heads/main"))
        claims = {"repository":"owner/repo","ref":"refs/heads/main","event_name":"workflow_dispatch","jti":"id","iat":int(time.time())}
        key = type("SigningKey", (), {"key": "key"})()
        with patch.object(verifier._jwks, "get_signing_key_from_jwt", return_value=key):
            with patch("android_remote_bridge.oidc.jwt.decode", return_value=claims):
                with self.assertRaises(AuthenticationError):
                    verifier.verify("header.payload.signature")


class ExecutorTests(unittest.TestCase):
    def test_executes_shell_and_returns_stdout(self):
        result = execute(parse_command(command_envelope()))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["stdout"], "push-mode-ok")
        self.assertEqual(result["exit_code"], 0)

    def test_nonzero_exit_is_reported(self):
        result = execute(parse_command(command_envelope().replace(b"printf 'push-mode-ok'", b"exit 7")))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 7)


class LifecycleCLITests(unittest.TestCase):
    def test_status_and_logs_without_running_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({
                "audience": "termux-push-bridge",
                "repository": "owner/private-repo",
                "ref": "refs/heads/main",
                "state_file": str(Path(tmp) / "state" / "replay.json"),
            }), encoding="utf-8")
            self.assertEqual(status(config), {"running": False, "pid": None})
            self.assertIn("No Bridge log", show_logs(config))


class TunnelTests(unittest.TestCase):
    def test_stable_tunnl_url_pattern(self):
        self.assertIsNotNone(_URL_PATTERN.fullmatch("https://brave-fox-7c41e09b.tunnl.gg"))
        self.assertIsNone(_URL_PATTERN.fullmatch("https://blue-river.trycloudflare.com"))

    def test_machine_readable_tunnel_event(self):
        url = "https://brave-fox-7c41e09b.tunnl.gg"
        self.assertEqual(_tunnel_event(json.dumps({"event":"tunnel","url":url})), url)
        self.assertIsNone(_tunnel_event(json.dumps({"event":"request","url":url})))


class WorkflowTemplateTests(unittest.TestCase):
    def test_workflow_only_sends_signed_push_event(self):
        path = Path(__file__).parents[1] / "templates" / "operational-repo" / ".github" / "workflows" / "bridge.yml"
        workflow = path.read_text(encoding="utf-8")
        self.assertIn("audience=termux-push-bridge", workflow)
        self.assertIn('"after": os.environ["GITHUB_SHA"]', workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("BRIDGE_TUNNEL_URL", workflow)
        self.assertNotIn("--data-binary @mailbox/command.json", workflow)
        self.assertIn("mailbox/tunnel-url.txt", workflow)


class ListenerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), BridgeHandler)
        self.server.verifier = type("Verifier", (), {"verify": lambda _self, _token: {"jti":"test-jti"}})()
        self.server.replay_state = ReplayState(Path(self.tmp.name) / "state.json")
        self.server.bridge_config = {"repository":"owner/private-repo","ref":"refs/heads/main","branch":"main"}
        self.server.busy_lock = threading.Lock()
        self.server.last_result = None
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def post(self, body=None):
        event = body or {
            "repository":"owner/private-repo",
            "ref":"refs/heads/main",
            "after":"a" * 40,
            "timestamp":int(time.time()),
        }
        request = urllib.request.Request(
            self.base + "/webhook",
            data=json.dumps(event).encode(),
            headers={"Authorization":"Bearer test-token","Content-Type":"application/json"},
        )
        return urllib.request.urlopen(request, timeout=3)

    def test_health_endpoint(self):
        with urllib.request.urlopen(self.base + "/health", timeout=3) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload, {"status":"ok","bridge":"push"})

    def test_webhook_requires_bearer_token(self):
        request = urllib.request.Request(
            self.base + "/webhook", data=b"{}", headers={"Content-Type":"application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 401)

    def test_webhook_accepts_event_then_executes_mailbox_command(self):
        raw = command_envelope()
        with patch("android_remote_bridge.server._github_token", return_value="test-token"), \
             patch("android_remote_bridge.server._get_contents", return_value=(raw, "blob-sha")), \
             patch("android_remote_bridge.server._publish_result") as publish:
            with self.post() as response:
                payload = json.loads(response.read())
                self.assertEqual(response.status, 202)
            self.assertEqual(payload["status"], "accepted")
            deadline = time.time() + 3
            while time.time() < deadline and self.server.last_result is None:
                time.sleep(0.02)
            self.assertIsNotNone(self.server.last_result)
            self.assertEqual(self.server.last_result["stdout"], "push-mode-ok")
            publish.assert_called_once()

    def test_event_rejects_wrong_repository(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post({"repository":"attacker/repo","ref":"refs/heads/main","after":"a"*40,"timestamp":int(time.time())})
        self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
