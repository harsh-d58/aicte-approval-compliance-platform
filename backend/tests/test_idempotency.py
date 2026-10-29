"""A reused retry key cannot silently change request semantics."""

import unittest
from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.app.idempotency import IdempotencyConflict, IdempotencyExpired, find_result
from backend.app.transactions import request_hash


class Cursor:
    def __init__(self, result):
        self.result = result
        self.params = None

    def execute(self, _sql, params):
        self.params = params

    def fetchone(self):
        return self.result


class IdempotencyTests(unittest.TestCase):
    def test_same_key_and_request_replays_completed_result(self):
        body = {"application_id": "demo", "submit": True}
        cursor = Cursor((request_hash("application.submit", body), 201, {"id": "demo"},
                         datetime.now(timezone.utc) + timedelta(days=1)))
        result = find_result(cursor, actor_id=UUID(int=1), operation="application.submit",
                             raw_key="attempt-1", body=body)
        self.assertEqual(result, (201, {"id": "demo"}))
        self.assertEqual(cursor.params[0], UUID(int=1))
        self.assertNotIn("attempt-1", cursor.params)

    def test_same_key_with_different_request_conflicts(self):
        cursor = Cursor((request_hash("application.submit", {"submit": True}), 201, {},
                         datetime.now(timezone.utc) + timedelta(days=1)))
        with self.assertRaises(IdempotencyConflict):
            find_result(cursor, actor_id=UUID(int=1), operation="application.submit",
                        raw_key="attempt-1", body={"submit": False})

    def test_expired_key_cannot_be_reused_as_a_new_action(self):
        body = {"submit": True}
        cursor = Cursor((request_hash("application.submit", body), 201, {},
                         datetime.now(timezone.utc) - timedelta(seconds=1)))
        with self.assertRaises(IdempotencyExpired):
            find_result(cursor, actor_id=UUID(int=1), operation="application.submit",
                        raw_key="attempt-1", body=body)


if __name__ == "__main__":
    unittest.main()
