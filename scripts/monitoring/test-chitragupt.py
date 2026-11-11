#!/usr/bin/env python3
import json
from pathlib import Path
import tempfile
import unittest
from pydantic import ValidationError
from chitragupt_probe import RegistryReader
from chitragupt_models import RegistrySummary

class BotProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.write("db_users.json", {"123456789": {"name": "PRIVATE PERSON", "username": "PRIVATE_HANDLE", "level": 10}, "-987654321": {"name": "PRIVATE GROUP", "level": 50}})
        self.write("db_chats.json", {"chat_tracking": {"-987654321": {"title": "PRIVATE TITLE", "type": "group"}}})
        self.write("db_rules.json", {"roles": [{"level": 10, "name": "PRIVATE ROLE"}, {"level": 50}]})
    def tearDown(self):
        self.temp.cleanup()
    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data, indent=2) + "\n")
    def collect(self):
        return RegistrySummary.model_validate(RegistryReader(self.root).collect())
    def test_only_aggregates_leave_the_probe(self):
        result = self.collect()
        serialized = result.model_dump_json()
        for private in ("123456789", "987654321", "PRIVATE PERSON", "PRIVATE_HANDLE", "PRIVATE GROUP", "PRIVATE TITLE", "PRIVATE ROLE"):
            self.assertNotIn(private, serialized)
        self.assertEqual(result.user_identities, 1)
        self.assertEqual(result.chat_identities, 1)
        self.assertEqual(result.managed_chats, 1)
    def test_missing_chat_registry_is_unknown_not_zero(self):
        (self.root / "db_chats.json").unlink()
        result = self.collect()
        self.assertIsNone(result.managed_chats)
        self.assertEqual(result.chats_state, "unavailable")
    def test_invalid_user_level_is_rejected(self):
        self.write("db_users.json", {"123456789": {"level": "SECRET VALUE"}})
        with self.assertRaises(ValueError):
            self.collect()
    def test_role_cardinality_is_bounded(self):
        self.write("db_users.json", {str(i + 1): {"level": i} for i in range(65)})
        with self.assertRaises(ValueError):
            self.collect()
    def test_extra_output_fields_are_rejected(self):
        data = self.collect().model_dump()
        data["token"] = "SECRET"
        with self.assertRaises(ValidationError):
            RegistrySummary.model_validate(data)

if __name__ == "__main__":
    unittest.main()
