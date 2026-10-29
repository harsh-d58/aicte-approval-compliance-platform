"""Unit tests for statutory decisions and human authority governance."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.concurrency import StaleVersion
from backend.app.decisions import (
    CreateDecisionRequest,
    list_application_decisions,
    record_statutory_decision,
)
from backend.app.settings import Settings


class MockCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.fetchone_val = fetchone_val
        self.fetchall_val = fetchall_val or []
        self.sql = ""
        self.params = None
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        self.executed.append((sql, params))

    def fetchone(self):
        if isinstance(self.fetchone_val, list):
            return self.fetchone_val.pop(0) if self.fetchone_val else None
        return self.fetchone_val

    def fetchall(self):
        return self.fetchall_val


class MockConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor


class DecisionRouteTests(TestCase):
    def setUp(self):
        self.app_id = UUID(int=1)
        self.decision_id = UUID(int=2)
        self.caller_id = UUID(int=3)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=99))),
        )
        self.caller_row = {
            "id": self.caller_id,
            "display_name": "Executive Committee Chair",
            "email": "chair@example.com",
            "status": "active",
        }

    def test_record_statutory_decision_approval_keeps_application_open_for_conditions(self):
        payload = CreateDecisionRequest(
            decision_type="approval",
            decision_status="approved",
            decision_authority="Executive Committee",
            reason="All statutory norms and infrastructure verified compliant",
            expected_version=3,
        )
        app_row = {"id": self.app_id, "application_number": "APP-2026-ABCD", "status": "under_review"}
        decision_row = {
            "id": self.decision_id,
            "application_id": self.app_id,
            "decision_type": "approval",
            "decision_status": "approved",
            "decision_authority": "Executive Committee",
            "decision_at": "2026-10-29T00:00:00Z",
            "reason": payload.reason,
            "record_document_id": None,
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[app_row, decision_row])

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.decisions.lock_versioned", return_value=None), \
             patch("backend.app.decisions.bump_version", return_value=4), \
             patch("backend.app.decisions.append_event", return_value=None), \
             patch("backend.app.decisions.enqueue", return_value=None):
            res = record_statutory_decision(self.app_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.decision_id)
        self.assertEqual(res["decision_status"], "approved")
        self.assertEqual(res["application_version"], 4)
        status_updates = [params for sql, params in cursor.executed if "SET status = %s, closed_at" in sql]
        self.assertEqual(len(status_updates), 1)
        self.assertEqual(status_updates[0][0], "approved")
        self.assertIsNone(status_updates[0][1])

    def test_record_statutory_decision_stale_version_raises_412(self):
        payload = CreateDecisionRequest(
            decision_type="approval",
            decision_status="approved",
            decision_authority="Executive Committee",
            reason="Version conflict test",
            expected_version=1,
        )
        cursor = MockCursor()

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.decisions.lock_versioned", side_effect=StaleVersion("Stale")):
            with self.assertRaises(HTTPException) as ctx:
                record_statutory_decision(self.app_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 412)

    def test_record_statutory_decision_already_closed_raises_409(self):
        payload = CreateDecisionRequest(
            decision_type="approval",
            decision_status="approved",
            decision_authority="Executive Committee",
            reason="Already approved test",
            expected_version=3,
        )
        app_row = {"id": self.app_id, "application_number": "APP-2026-ABCD", "status": "approved"}
        cursor = MockCursor(fetchone_val=[app_row])

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.decisions.lock_versioned", return_value=None), \
             patch("backend.app.decisions.bump_version", return_value=4):
            with self.assertRaises(HTTPException) as ctx:
                record_statutory_decision(self.app_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_list_application_decisions(self):
        decisions = [
            {
                "id": self.decision_id,
                "application_id": self.app_id,
                "decision_type": "approval",
                "decision_status": "approved",
                "decision_authority": "Executive Committee",
                "decision_at": "2026-10-29T00:00:00Z",
                "reason": "Approved",
                "record_document_id": None,
                "created_at": "2026-10-29T00:00:00Z",
            }
        ]
        cursor = MockCursor(fetchall_val=decisions)

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_application_decisions(self.app_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["decision_type"], "approval")
