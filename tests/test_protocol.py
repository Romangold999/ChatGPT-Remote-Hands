import json
import unittest

from android_remote_bridge.protocol import MAX_COMMAND_CHARS, ProtocolError, parse_command


def valid_payload(**overrides):
    data = {
        "version": 1,
        "id": "test-command-001",
        "sequence": 1,
        "status": "ready",
        "operation": "shell",
        "approval": "not_required",
        "timeout_seconds": 30,
        "command": "printf 'hello'",
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


class ParseCommandTests(unittest.TestCase):
    def test_accepts_shell_command(self):
        command = parse_command(valid_payload())
        self.assertEqual(command.operation, "shell")
        self.assertEqual(command.command, "printf 'hello'")
        self.assertEqual(command.sequence, 1)
        self.assertEqual(command.approval, "not_required")

    def test_accepts_string_payload(self):
        self.assertEqual(parse_command(valid_payload().decode()).version, 1)

    def test_rejects_invalid_json(self):
        with self.assertRaises(ProtocolError):
            parse_command(b"{not-json")

    def test_rejects_non_object(self):
        with self.assertRaises(ProtocolError):
            parse_command(b"[]")

    def test_rejects_oversized_envelope(self):
        from android_remote_bridge.protocol import MAX_COMMAND_BYTES
        with self.assertRaises(ProtocolError):
            parse_command(b" " * (MAX_COMMAND_BYTES + 1))

    def test_rejects_unknown_field(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(unreviewed=True))

    def test_rejects_missing_required_field(self):
        data = json.loads(valid_payload())
        del data["sequence"]
        with self.assertRaises(ProtocolError):
            parse_command(json.dumps(data))

    def test_rejects_bool_as_version(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(version=True))

    def test_rejects_invalid_id(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(id="bad id with spaces"))

    def test_rejects_non_positive_sequence(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(sequence=0))

    def test_rejects_non_shell_operation(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(operation="system.info"))

    def test_rejects_empty_command(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(command="  "))

    def test_rejects_command_over_limit(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(command="x" * (MAX_COMMAND_CHARS + 1)))

    def test_rejects_invalid_approval(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(approval=True))

    def test_rejects_out_of_range_timeout(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(timeout_seconds=3601))

    def test_rejects_non_ready_command(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(status="completed"))


if __name__ == "__main__":
    unittest.main()
