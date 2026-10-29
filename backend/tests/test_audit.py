"""Canonical audit hashes detect changes to protected event fields."""

from datetime import datetime, timedelta, timezone
import unittest
from uuid import UUID

from backend.app.audit import event_digest, verify_event


def digest(row):
    return event_digest(event_id=row["id"], actor_id=row["actor_id"], action=row["action"],
                        entity_type=row["entity_type"], entity_id=row["entity_id"],
                        event_at=row["event_at"], correlation_id=row["correlation_id"],
                        reason=row["reason"], metadata=row["metadata"], previous_hash=row["previous_hash"])


class AuditHashTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "id": UUID(int=1), "actor_id": None, "action": "DEMO_TEST",
            "entity_type": "application", "entity_id": UUID(int=2),
            "event_at": datetime(2026, 10, 29, 12, tzinfo=timezone.utc),
            "correlation_id": UUID(int=3), "reason": "test only",
            "metadata": {"new_status": "submitted", "old_status": "draft"},
            "previous_hash": None,
        }

    def test_hash_is_timezone_and_json_order_stable(self):
        original = digest(self.row)
        changed = dict(self.row, event_at=self.row["event_at"].astimezone(timezone(timedelta(hours=5, minutes=30))),
                       metadata={"old_status": "draft", "new_status": "submitted"})
        self.assertEqual(original, digest(changed))
        self.row["event_hash"] = original
        self.assertTrue(verify_event(self.row))
        self.row["metadata"] = {"old_status": "draft", "new_status": "approved"}
        self.assertFalse(verify_event(self.row))

    def test_naive_audit_time_is_rejected(self):
        with self.assertRaises(ValueError):
            digest(dict(self.row, event_at=datetime(2026, 10, 29, 12)))


if __name__ == "__main__":
    unittest.main()
