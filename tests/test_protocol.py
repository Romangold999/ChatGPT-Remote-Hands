import json
import unittest
import uuid

from android_remote_bridge.protocol import (
    MAX_COMMAND_BYTES,
    ProtocolError,
    parse_command,
)


def valid_payload(**overrides):
    data = {
        "version": 1,
        "id": str(uuid.uuid4()),
        "sequence": 1,
        "status": "pending",
        "operation": "bridge.health",
        "arguments": {},
        "approval": False,
        "timeout_seconds": 10,
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


class ParseCommandTests(unittest.TestCase):
    def test_accepts_valid_health_command(self):
        command = parse_command(valid_payload())
        self.assertEqual(command.operation, "bridge.health")
        self.assertEqual(command.sequence, 1)
        self.assertFalse(command.approval)

    def test_accepts_string_payload(self):
        command = parse_command(valid_payload().decode("utf-8"))
        self.assertEqual(command.version, 1)

    def test_rejects_invalid_json(self):
        with self.assertRaises(ProtocolError):
            parse_command(b"{not-json")

    def test_rejects_non_object(self):
        with self.assertRaises(ProtocolError):
            parse_command(b"[]")

    def test_rejects_oversized_payload(self):
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

    def test_rejects_invalid_uuid(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(id="not-a-uuid"))

    def test_rejects_non_positive_sequence(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(sequence=0))

    def test_rejects_arbitrary_shell_operation(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(operation="shell.exec"))

    def test_rejects_arguments_until_operations_define_a_schema(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(arguments={"cmd": "id"}))

    def test_rejects_non_boolean_approval(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(approval="yes"))

    def test_rejects_out_of_range_timeout(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(timeout_seconds=999))

    def test_rejects_non_pending_new_command(self):
        with self.assertRaises(ProtocolError):
            parse_command(valid_payload(status="done"))


if __name__ == "__main__":
    unittest.main()
