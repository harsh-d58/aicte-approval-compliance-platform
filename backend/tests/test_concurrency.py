"""Version guards reject stale edits before mutation."""

import unittest
from uuid import UUID

from backend.app.concurrency import RecordMissing, StaleVersion, bump_version, lock_versioned


class Cursor:
    def __init__(self, row):
        self.row = row
        self.calls = 0

    def execute(self, *_):
        self.calls += 1

    def fetchone(self):
        return self.row


class ConcurrencyTests(unittest.TestCase):
    def test_lock_requires_exact_version_and_known_table(self):
        cursor = Cursor((4,))
        self.assertEqual(lock_versioned(cursor, table="applications", record_id=UUID(int=1),
                                        expected_version=4), 4)
        with self.assertRaises(StaleVersion):
            lock_versioned(cursor, table="applications", record_id=UUID(int=1),
                           expected_version=3)
        with self.assertRaises(ValueError):
            lock_versioned(cursor, table="audit_events", record_id=UUID(int=1),
                           expected_version=4)
        self.assertEqual(cursor.calls, 2)

    def test_missing_and_competing_edit_fail_closed(self):
        cursor = Cursor(None)
        with self.assertRaises(RecordMissing):
            lock_versioned(cursor, table="applications", record_id=UUID(int=1),
                           expected_version=1)
        with self.assertRaises(StaleVersion):
            bump_version(cursor, table="applications", record_id=UUID(int=1),
                         expected_version=1)

    def test_boolean_version_is_invalid(self):
        cursor = Cursor((1,))
        with self.assertRaises(ValueError):
            lock_versioned(cursor, table="applications", record_id=UUID(int=1),
                           expected_version=True)
        self.assertEqual(cursor.calls, 0)
