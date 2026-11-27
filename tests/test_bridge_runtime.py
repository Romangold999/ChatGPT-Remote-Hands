from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from android_remote_bridge.executor import execute
from android_remote_bridge.oidc import AuthenticationError, GitHubOIDCVerifier, OIDCPolicy
from android_remote_bridge.protocol import parse_command
from android_remote_bridge.state import ReplayState, StateError

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
            ReplayState(path).accept(sequence=1, jti="token-1")
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=1, jti="token-2")
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=2, jti="token-1")
            ReplayState(path).accept(sequence=2, jti="token-2")

    def test_corrupt_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("broken", encoding="utf-8")
            with self.assertRaises(StateError):
                ReplayState(path).accept(sequence=1, jti="x")


class ExecutorTests(unittest.TestCase):
    def test_health_operation_returns_structured_result(self) -> None:
        result = execute(parse_command(envelope()))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["id"], COMMAND_ID)
        self.assertEqual(result["data"]["status"], "ok")


class OIDCTests(unittest.TestCase):
    def test_repository_claim_is_pinned(self) -> None:
        verifier = GitHubOIDCVerifier(OIDCPolicy("aud", "owner/repo", "refs/heads/main"))
        claims = {"repository": "other/repo", "ref": "refs/heads/main", "jti": "id", "iat": 1}
        key = type("SigningKey", (), {"key": "key"})()
        with patch.object(verifier._jwks, "get_signing_key_from_jwt", return_value=key):
            with patch("android_remote_bridge.oidc.jwt.decode", return_value=claims):
                with self.assertRaises(AuthenticationError):
                    verifier.verify("header.payload.signature")


if __name__ == "__main__":
    unittest.main()
