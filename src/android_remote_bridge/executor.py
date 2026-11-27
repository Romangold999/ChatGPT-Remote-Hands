"""Execute a user-authorized shell command in the Termux environment."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import Command

MAX_OUTPUT_CHARS = 100_000


def execute(command: Command) -> dict[str, Any]:
    """Run bash -lc with a hard timeout and bounded result output."""
    started = datetime.now(timezone.utc).isoformat()
    status = "error"
    exit_code = 1
    stdout = ""
    stderr = ""
    error = None
    try:
        completed = subprocess.run(
            ["bash", "-lc", command.command],
            cwd=str(Path.home()),
            capture_output=True,
            text=True,
            timeout=command.timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        status = "completed" if exit_code == 0 else "failed"
        stdout = (completed.stdout or "")[-MAX_OUTPUT_CHARS:]
        stderr = (completed.stderr or "")[-MAX_OUTPUT_CHARS:]
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        exit_code = 124
        stdout = str(exc.stdout or "")[-MAX_OUTPUT_CHARS:]
        stderr = str(exc.stderr or "")[-MAX_OUTPUT_CHARS:]
        error = f"Timeout after {command.timeout_seconds} seconds"
    except Exception as exc:
        status = "error"
        error = f"{type(exc).__name__}: {str(exc)[:1000]}"
    finished = datetime.now(timezone.utc).isoformat()
    return {
        "version": 1,
        "id": command.command_id,
        "sequence": command.sequence,
        "status": status,
        "started_at": started,
        "finished_at": finished,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "error": error,
    }
