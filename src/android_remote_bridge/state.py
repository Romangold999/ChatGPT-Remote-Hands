"""Atomic local replay, sequence and idempotent-result state."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


class StateError(ValueError):
    """Raised when a command is a replay or has an invalid sequence."""


class ReplayState:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({
                "last_sequence": 0,
                "seen_jti": [],
                "last_command_id": None,
                "last_command_hash": None,
                "last_result": None,
            })

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError("persistent replay state is unreadable; refusing commands") from exc
        if not isinstance(data, dict) or type(data.get("last_sequence")) is not int:
            raise StateError("persistent replay state is invalid")
        if not isinstance(data.get("seen_jti"), list):
            raise StateError("persistent replay state is invalid")
        data.setdefault("last_command_id", None)
        data.setdefault("last_command_hash", None)
        data.setdefault("last_result", None)
        return data

    def _write(self, data: dict[str, Any]) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=".bridge-state-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, separators=(",", ":"), sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def accept(
        self, *, sequence: int, jti: str, command_id: str, command_hash: str
    ) -> dict[str, Any] | None:
        """Reserve the next command, or return its cached result on safe retry."""
        with self._lock:
            data = self._read()
            seen = data["seen_jti"]
            if jti in seen:
                raise StateError("OIDC token replay detected")

            if sequence == data["last_sequence"] and command_id == data["last_command_id"]:
                if command_hash != data["last_command_hash"]:
                    raise StateError("same command identity was reused with a different payload")
                cached = data["last_result"]
                if cached is None:
                    raise StateError("command was interrupted before a result was saved")
                seen.append(jti)
                data["seen_jti"] = seen[-10_000:]
                self._write(data)
                return cached

            if sequence != data["last_sequence"] + 1:
                raise StateError("command sequence is not the next expected value")

            seen.append(jti)
            data["seen_jti"] = seen[-10_000:]
            data["last_sequence"] = sequence
            data["last_command_id"] = command_id
            data["last_command_hash"] = command_hash
            data["last_result"] = None
            self._write(data)
            return None

    def complete(self, *, sequence: int, command_id: str, result: dict[str, Any]) -> None:
        """Persist a terminal result before acknowledging the webhook."""
        with self._lock:
            data = self._read()
            if (
                sequence != data["last_sequence"]
                or command_id != data["last_command_id"]
                or data["last_result"] is not None
            ):
                raise StateError("result does not match the active command")
            if result.get("id") != command_id or result.get("sequence") != sequence:
                raise StateError("result identity does not match the active command")
            if result.get("status") not in {"completed", "failed", "timeout", "error", "interrupted"}:
                raise StateError("only terminal results can be persisted")
            data["last_result"] = result
            self._write(data)
