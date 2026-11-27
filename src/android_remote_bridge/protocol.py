"""Validation for the event-triggered Termux command mailbox.

GitHub Actions sends only a signed push event. The Android listener then
fetches the command at that exact commit SHA from the user's private repo.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

MAX_COMMAND_BYTES = 64 * 1024
MAX_COMMAND_CHARS = 20_000
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 3600
SUPPORTED_VERSION = 1
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")


class ProtocolError(ValueError):
    """Raised when a mailbox command is malformed."""


@dataclass(frozen=True, slots=True)
class Command:
    version: int
    command_id: str
    sequence: int
    status: str
    operation: str
    approval: str
    command: str
    timeout_seconds: int


def parse_command(payload: bytes | str) -> Command:
    if isinstance(payload, str):
        encoded = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        encoded = payload
    else:
        raise ProtocolError("payload must be bytes or str")
    if len(encoded) > MAX_COMMAND_BYTES:
        raise ProtocolError("command envelope exceeds size limit")
    try:
        data = json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("command must be valid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise ProtocolError("command envelope must be an object")

    required = {"version", "id", "sequence", "status", "operation", "command"}
    allowed = required | {"approval", "timeout_seconds", "created_at"}
    missing = required - set(data)
    unknown = set(data) - allowed
    if missing:
        raise ProtocolError("missing command fields: " + ", ".join(sorted(missing)))
    if unknown:
        raise ProtocolError("unknown command fields: " + ", ".join(sorted(unknown)))

    version = data["version"]
    if type(version) is not int or version != SUPPORTED_VERSION:
        raise ProtocolError("unsupported command version")
    command_id = data["id"]
    if not isinstance(command_id, str) or not _ID_PATTERN.fullmatch(command_id):
        raise ProtocolError("invalid command id")
    sequence = data["sequence"]
    if type(sequence) is not int or sequence < 1:
        raise ProtocolError("sequence must be a positive integer")
    status = data["status"]
    if status != "ready":
        raise ProtocolError("command status must be ready")
    operation = data["operation"]
    if operation != "shell":
        raise ProtocolError("operation must be shell")
    command = data["command"]
    if not isinstance(command, str) or not command.strip():
        raise ProtocolError("command must be a non-empty string")
    if len(command) > MAX_COMMAND_CHARS:
        raise ProtocolError("command text exceeds 20000 characters")
    approval = data.get("approval", "not_required")
    if approval not in ("not_required", "approved"):
        raise ProtocolError("approval must be not_required or approved")
    timeout = data.get("timeout_seconds", 300)
    if type(timeout) is not int or not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
        raise ProtocolError("timeout_seconds must be between 1 and 3600")

    return Command(
        version=version,
        command_id=command_id,
        sequence=sequence,
        status=status,
        operation=operation,
        approval=approval,
        command=command,
        timeout_seconds=timeout,
    )
