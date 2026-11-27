"""Event-driven GitHub -> tunnl.gg -> Termux command bridge.

No GitHub polling is performed. A push-triggered Actions workflow sends a
short OIDC-authenticated event; Termux then fetches the command at that exact
commit, executes it, and writes the result back to the user's private mailbox.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .executor import execute
from .oidc import AuthenticationError, GitHubOIDCVerifier, OIDCPolicy
from .protocol import Command, ProtocolError, parse_command
from .state import ReplayState, StateError

LOG = logging.getLogger("android_remote_bridge")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMAND_PATH = "push-bridge/command.json"
RESULT_PATH = "push-bridge/result.json"


class BridgeError(RuntimeError):
    """Raised when a mailbox API operation cannot be completed."""


def _github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    gh = subprocess.run(
        ["gh", "auth", "token", "--hostname", "github.com"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if gh.returncode != 0 or not gh.stdout.strip():
        raise BridgeError("GitHub CLI is not authenticated; run gh auth login")
    return gh.stdout.strip()


def _github_request(
    token: str, method: str, path: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(
        "https://api.github.com" + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ChatGPT-Remote-Hands",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", "replace")
        raise BridgeError(f"GitHub API HTTP {exc.code}: {detail}") from exc


def _get_contents(token: str, repository: str, path: str, ref: str) -> tuple[bytes, str]:
    query = urllib.parse.urlencode({"ref": ref})
    result = _github_request(token, "GET", f"/repos/{repository}/contents/{path}?{query}")
    if result.get("encoding") != "base64" or not isinstance(result.get("content"), str):
        raise BridgeError(f"GitHub did not return base64 file content for {path}")
    return base64.b64decode(result["content"]), result["sha"]


def _put_contents(
    token: str, repository: str, path: str, content: bytes, message: str, branch: str
) -> None:
    sha = None
    try:
        _old, sha = _get_contents(token, repository, path, branch)
    except BridgeError as exc:
        if "HTTP 404" not in str(exc):
            raise
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    _github_request(token, "PUT", f"/repos/{repository}/contents/{path}", payload)


def _publish_result(server: ThreadingHTTPServer, result: dict[str, Any]) -> None:
    config = server.bridge_config  # type: ignore[attr-defined]
    token = _github_token()
    repository = config["repository"]
    branch = config["branch"]
    command_id = result["id"]
    _put_contents(
        token, repository, RESULT_PATH,
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode(),
        "Bridge result " + command_id, branch,
    )
    try:
        raw, sha = _get_contents(token, repository, COMMAND_PATH, branch)
        command_data = json.loads(raw.decode("utf-8"))
        if command_data.get("id") == command_id and command_data.get("status") == "ready":
            command_data["status"] = result["status"]
            command_data["completed_at"] = result["finished_at"]
            _github_request(
                token, "PUT", f"/repos/{repository}/contents/{COMMAND_PATH}",
                {
                    "message": "Acknowledge Bridge command " + command_id,
                    "content": base64.b64encode(
                        (json.dumps(command_data, ensure_ascii=False, indent=2) + "\n").encode()
                    ).decode("ascii"),
                    "sha": sha,
                    "branch": branch,
                },
            )
    except Exception:
        LOG.exception("command acknowledgement failed after result publication")


def _republish_cached(server: ThreadingHTTPServer, result: dict[str, Any]) -> None:
    try:
        _publish_result(server, result)
    except Exception:
        LOG.exception("could not republish cached result %s", result.get("id"))
    finally:
        server.busy_lock.release()  # type: ignore[attr-defined]


def _run_command(server: ThreadingHTTPServer, command: Command, command_hash: str) -> None:
    try:
        result = execute(command)
        server.replay_state.complete(  # type: ignore[attr-defined]
            sequence=command.sequence, command_id=command.command_id, result=result
        )
        server.last_result = result  # type: ignore[attr-defined]
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                _publish_result(server, result)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                LOG.exception("result publication attempt %s failed for %s", attempt + 1, command.command_id)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        if last_error is not None:
            LOG.error("result remains in local replay state; GitHub publication failed")
        else:
            LOG.info("command %s finished: %s exit=%s", command.command_id, result["status"], result["exit_code"])
    except Exception:
        LOG.exception("command worker failed for %s", command.command_id)
    finally:
        server.busy_lock.release()  # type: ignore[attr-defined]


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "ChatGPTRemoteHands/0.3"

    def log_message(self, fmt: str, *args: Any) -> None:
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
            self._reply(200, {"status": "ok", "bridge": "push"})
        else:
            self._reply(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self._reply(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._reply(400, {"error": "invalid_content_length"})
            return
        if length < 1 or length > 8192:
            self._reply(413, {"error": "event_size_invalid"})
            return
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self._reply(401, {"error": "bearer_token_required"})
            return
        try:
            claims = self.server.verifier.verify(auth[7:].strip())  # type: ignore[attr-defined]
        except AuthenticationError:
            self._reply(401, {"error": "authentication_failed"})
            return
        acquired = False
        try:
            event = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(event, dict):
                self._reply(400, {"error": "event_must_be_object"})
                return
            config = self.server.bridge_config  # type: ignore[attr-defined]
            if event.get("repository") != config["repository"] or event.get("ref") != config["ref"]:
                self._reply(403, {"error": "wrong_repository_or_ref"})
                return
            commit = event.get("after", "")
            if not isinstance(commit, str) or not SHA_PATTERN.fullmatch(commit):
                self._reply(400, {"error": "invalid_commit_sha"})
                return
            try:
                age = abs(time.time() - int(event.get("timestamp", 0)))
            except (TypeError, ValueError):
                age = 999999
            if age > 3600:
                self._reply(401, {"error": "stale_event"})
                return
            if not self.server.busy_lock.acquire(blocking=False):  # type: ignore[attr-defined]
                self._reply(409, {"error": "command_in_progress"})
                return
            acquired = True

            token = _github_token()
            raw_command, _sha = _get_contents(
                token, config["repository"], COMMAND_PATH, commit
            )
            command = parse_command(raw_command)
            command_hash = hashlib.sha256(raw_command).hexdigest()
            cached = self.server.replay_state.accept(  # type: ignore[attr-defined]
                sequence=command.sequence,
                jti=claims["jti"],
                command_id=command.command_id,
                command_hash=command_hash,
            )
            if cached is not None:
                threading.Thread(
                    target=_republish_cached, args=(self.server, cached), daemon=True
                ).start()
                acquired = False  # the republish worker now owns the mailbox lock
                self._reply(200, {"status": "duplicate", "id": command.command_id})
                return
            threading.Thread(
                target=_run_command,
                args=(self.server, command, command_hash),
                daemon=True,
            ).start()
            acquired = False  # the worker now owns and releases the mailbox lock
            self._reply(
                202,
                {"status": "accepted", "id": command.command_id, "sequence": command.sequence},
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            if acquired:
                self.server.busy_lock.release()  # type: ignore[attr-defined]
            self._reply(400, {"error": "invalid_event_json"})
        except (ProtocolError, StateError, BridgeError) as exc:
            if acquired:
                self.server.busy_lock.release()  # type: ignore[attr-defined]
            LOG.warning("event rejected: %s", str(exc)[:500])
            self._reply(400, {"error": "event_rejected", "detail": str(exc)[:300]})
        except Exception:
            if acquired:
                self.server.busy_lock.release()  # type: ignore[attr-defined]
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
    if data["audience"] != "termux-push-bridge":
        raise ValueError("config audience must be termux-push-bridge")
    if not REPOSITORY_PATTERN.fullmatch(data["repository"]):
        raise ValueError("config repository must be OWNER/REPOSITORY")
    if data["ref"] != "refs/heads/push-bridge":
        raise ValueError("config ref must be refs/heads/push-bridge")
    port = data.get("port", 18767)
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ValueError("config port must be an integer between 1024 and 65535")
    data["port"] = port
    data["branch"] = "push-bridge"
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Android Remote Bridge event listener")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    state_path = Path(config["state_file"]).expanduser()
    replay_state = ReplayState(state_path)
    server = ThreadingHTTPServer(("127.0.0.1", config["port"]), BridgeHandler)
    server.verifier = GitHubOIDCVerifier(  # type: ignore[attr-defined]
        OIDCPolicy(config["audience"], config["repository"], config["ref"], "push")
    )
    server.replay_state = replay_state  # type: ignore[attr-defined]
    server.bridge_config = config  # type: ignore[attr-defined]
    server.busy_lock = threading.Lock()  # type: ignore[attr-defined]
    server.last_result = None  # type: ignore[attr-defined]
    LOG.info("listening on 127.0.0.1:%s; event-driven push mode, no GitHub polling", config["port"])
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
