"""Loopback-only GitHub Actions webhook listener."""
from __future__ import annotations

import argparse
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .executor import execute
from .oidc import AuthenticationError, GitHubOIDCVerifier, OIDCPolicy
from .protocol import MAX_COMMAND_BYTES, ProtocolError, parse_command
from .state import ReplayState, StateError

LOG = logging.getLogger("android_remote_bridge")


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "AndroidRemoteBridge/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Do not log headers, bearer tokens, request bodies or command payloads.
        LOG.info("request from %s: %s", self.client_address[0], fmt % args)

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._reply(200, {"status": "ok"})
        else:
            self._reply(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self._reply(404, {"error": "not_found"})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._reply(415, {"error": "application_json_required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._reply(400, {"error": "invalid_content_length"})
            return
        if length < 1 or length > MAX_COMMAND_BYTES:
            self._reply(413, {"error": "payload_size_invalid"})
            return
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self._reply(401, {"error": "bearer_token_required"})
            return
        try:
            claims = self.server.verifier.verify(auth[7:].strip())  # type: ignore[attr-defined]
            command = parse_command(self.rfile.read(length))
            cached = self.server.replay_state.accept(  # type: ignore[attr-defined]
                sequence=command.sequence,
                jti=claims["jti"],
                command_id=command.command_id,
            )
            if cached is not None:
                self._reply(200, {"accepted": True, "result": cached, "replayed": True})
                return
            result = execute(command)
            self.server.replay_state.complete(  # type: ignore[attr-defined]
                sequence=command.sequence,
                command_id=command.command_id,
                result=result,
            )
            self.server.last_result = result  # type: ignore[attr-defined]
            self._reply(200, {"accepted": True, "result": result, "replayed": False})
        except AuthenticationError:
            self._reply(401, {"error": "authentication_failed"})
        except (ProtocolError, StateError):
            self._reply(400, {"error": "command_rejected"})
        except Exception:
            LOG.exception("internal bridge error")
            self._reply(500, {"error": "internal_error"})


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"audience", "repository", "ref", "state_file"}
    if not isinstance(data, dict) or required - set(data):
        raise ValueError("config is missing required fields")
    for field in required:
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"config field {field} must be a non-empty string")
    if data["audience"] != "termux-bridge":
        raise ValueError("config audience must match the operational workflow")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", data["repository"]):
        raise ValueError("config repository must be OWNER/REPOSITORY")
    if data["ref"] != "refs/heads/main":
        raise ValueError("config ref must match the operational workflow branch")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Android Remote Bridge local listener")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    state_path = Path(config["state_file"]).expanduser()
    replay_state = ReplayState(state_path)
    server = ThreadingHTTPServer(("127.0.0.1", 18766), BridgeHandler)
    server.verifier = GitHubOIDCVerifier(  # type: ignore[attr-defined]
        OIDCPolicy(config["audience"], config["repository"], config["ref"])
    )
    server.replay_state = replay_state  # type: ignore[attr-defined]
    server.last_result = None  # type: ignore[attr-defined]
    LOG.info("listener bound to 127.0.0.1:18766")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
