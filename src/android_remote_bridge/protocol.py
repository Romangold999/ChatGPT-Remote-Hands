"""Strict validation for incoming mailbox command envelopes.

This module does not execute commands and does not authenticate network requests.
Callers must verify the transport identity (GitHub OIDC) before accepting an
envelope, then apply replay/sequence state checks before dispatch.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

MAX_COMMAND_BYTES = 16 * 1024
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 60
SUPPORTED_VERSION = 1

# Intentionally small initial allowlist. Adding an operation requires an
# implementation, tests, documentation and a security review.
ALLOWED_OPERATIONS = frozenset(
    {
        "bridge.status",
        "bridge.health",
        "system.info",
    }
)

_ID_PATTERN = re.compile(r"^[a-f0-9-]{36}$")


class ProtocolError(ValueError):
    """Raised when a mailbox command is malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class Command:
    version: int
    command_id: str
    sequence: int
    operation: str
    arguments: dict[str, Any]
    approval: bool
    timeout_seconds: int


def parse_command(payload: bytes | str) -> Command:
    """Parse and validate one UTF-8 JSON command envelope.

    Accepted fields are deliberately explicit. Unknown fields are rejected to
    prevent accidental acceptance of unreviewed protocol extensions.
    """
    if isinstance(payload, str):
        encoded = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        encoded = payload
    else:
        raise ProtocolError("payload must be bytes or str")

    if len(encoded) > MAX_COMMAND_BYTES:
        raise ProtocolError("command payload exceeds size limit")

    try:
        data = json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("payload must be valid UTF-8 JSON") from exc

    if not isinstance(data, dict):
        raise ProtocolError("command envelope must be a JSON object")

    allowed_fields = {
        "version",
        "id",
        "sequence",
        "status",
        "operation",
        "arguments",
        "approval",
        "timeout_seconds",
    }
    unknown = set(data) - allowed_fields
    missing = {"version", "id", "sequence", "operation"} - set(data)
    if unknown:
        raise ProtocolError(f"unknown command fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ProtocolError(f"missing command fields: {', '.join(sorted(missing))}")

    version = data["version"]
    if type(version) is not int or version != SUPPORTED_VERSION:
        raise ProtocolError("unsupported protocol version")

    command_id = data["id"]
    if not isinstance(command_id, str) or not _ID_PATTERN.fullmatch(command_id):
        raise ProtocolError("id must be a canonical UUID")
    try:
        if str(uuid.UUID(command_id)) != command_id:
            raise ProtocolError("id must be a canonical UUID")
    except ValueError as exc:
        raise ProtocolError("id must be a canonical UUID") from exc

    sequence = data["sequence"]
    if type(sequence) is not int or sequence < 1:
        raise ProtocolError("sequence must be a positive integer")

    operation = data["operation"]
    if not isinstance(operation, str) or operation not in ALLOWED_OPERATIONS:
        raise ProtocolError("operation is not in the supported allowlist")

    arguments = data.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ProtocolError("arguments must be a JSON object")
    if arguments:
        raise ProtocolError("this protocol version accepts no arguments for these operations")

    approval = data.get("approval", False)
    if type(approval) is not bool:
        raise ProtocolError("approval must be a boolean")

    timeout = data.get("timeout_seconds", 10)
    if type(timeout) is not int or not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
        raise ProtocolError(
            f"timeout_seconds must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS}"
        )

    status = data.get("status", "pending")
    if status != "pending":
        raise ProtocolError("new commands must have status 'pending'")

    return Command(
        version=version,
        command_id=command_id,
        sequence=sequence,
        operation=operation,
        arguments=arguments,
        approval=approval,
        timeout_seconds=timeout,
    )
