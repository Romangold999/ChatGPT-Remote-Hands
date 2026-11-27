"""Atomic local replay and sequence state."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path


class StateError(ValueError):
    """Raised when a command is a replay or has an invalid sequence."""


class ReplayState:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"last_sequence": 0, "seen_jti": []})

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError("persistent replay state is unreadable; refusing commands") from exc
        if not isinstance(data, dict) or type(data.get("last_sequence")) is not int:
            raise StateError("persistent replay state is invalid")
        if not isinstance(data.get("seen_jti"), list):
            raise StateError("persistent replay state is invalid")
        return data

    def _write(self, data: dict) -> None:
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

    def accept(self, *, sequence: int, jti: str) -> None:
        with self._lock:
            data = self._read()
            seen = data["seen_jti"]
            if jti in seen:
                raise StateError("OIDC token replay detected")
            if sequence != data["last_sequence"] + 1:
                raise StateError("command sequence is not the next expected value")
            seen.append(jti)
            data["seen_jti"] = seen[-10_000:]
            data["last_sequence"] = sequence
            self._write(data)
