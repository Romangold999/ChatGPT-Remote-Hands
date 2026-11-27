"""Small, non-shell operation executor."""
from __future__ import annotations

import os
import platform
import time
from datetime import datetime, timezone
from typing import Any

from .protocol import Command


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute(command: Command) -> dict[str, Any]:
    """Execute only built-in operations; never invokes a shell or subprocess."""
    started = _utc_now()
    start_clock = time.monotonic()
    try:
        if command.operation == "bridge.status":
            output = {"status": "running"}
        elif command.operation == "bridge.health":
            output = {"status": "ok", "python": platform.python_version()}
        elif command.operation == "system.info":
            output = {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "pid": os.getpid(),
            }
        else:  # Defense in depth: protocol parser should already reject this.
            raise ValueError("operation is not implemented")
        status, error, exit_code = "completed", None, 0
    except Exception as exc:
        output, status, error, exit_code = {}, "failed", type(exc).__name__, 1
    elapsed = time.monotonic() - start_clock
    if elapsed > command.timeout_seconds:
        output, status, error, exit_code = {}, "failed", "timeout", 124
    return {
        "version": 1,
        "id": command.command_id,
        "sequence": command.sequence,
        "status": status,
        "started_at": started,
        "finished_at": _utc_now(),
        "duration_seconds": round(elapsed, 3),
        "exit_code": exit_code,
        "data": output,
        "error": error,
    }
