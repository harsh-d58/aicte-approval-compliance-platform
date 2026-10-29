"""Unit tests for workflow definitions, stages, transitions, and guard evaluation."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.settings import Settings
from backend.app.workflows import (
    evaluate_guard,
    get_workflow_detail,
    list_application_types,
    list_workflows,
)


class MockCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.fetchone_val = fetchone_val
        self.fetchall_val = fetchall_val or []
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

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


class WorkflowTests(TestCase):
    def setUp(self):
        self.workflow_id = UUID(int=1)
        self.caller_id = UUID(int=2)
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
            "display_name": "Reviewer",
            "email": "reviewer@example.com",
            "status": "active",
        }

    def test_evaluate_guard_empty(self):
        passed, reason = evaluate_guard(None, {})
        self.assertTrue(passed)
        self.assertIsNone(reason)

    def test_evaluate_guard_roles(self):
        rule = {"required_roles": ["SCRUTINY_OFFICER", "ADMIN"]}
        passed, _ = evaluate_guard(rule, {"caller_roles": ["SCRUTINY_OFFICER"]})
        self.assertTrue(passed)

        failed, msg = evaluate_guard(rule, {"caller_roles": ["VIEWER"]})
        self.assertFalse(failed)
        self.assertIn("Transition requires one of roles", msg)

    def test_evaluate_guard_status(self):
        rule = {"required_status": "submitted"}
        passed, _ = evaluate_guard(rule, {"current_status": "submitted"})
        self.assertTrue(passed)

        failed, msg = evaluate_guard(rule, {"current_status": "draft"})
        self.assertFalse(failed)
        self.assertIn("must be in status 'submitted'", msg)

    def test_evaluate_guard_deficiencies(self):
        rule = {"require_all_deficiencies_resolved": True}
        passed, _ = evaluate_guard(rule, {"unresolved_deficiency_count": 0})
        self.assertTrue(passed)

        failed, msg = evaluate_guard(rule, {"unresolved_deficiency_count": 2})
        self.assertFalse(failed)
        self.assertIn("remain unresolved", msg)

    def test_list_application_types(self):
        types = [
            {"id": UUID(int=10), "code": "NEW_INSTITUTION", "name": "New Technical Institution", "status": "active", "version": 1},
        ]
        cursor = MockCursor(fetchall_val=types)

        with patch("backend.app.workflows._user", return_value=self.caller_row), \
             patch("backend.app.workflows._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_application_types(self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["code"], "NEW_INSTITUTION")

    def test_list_workflows(self):
        workflows = [
            {"id": self.workflow_id, "name": "Standard New Institution Approval", "status": "published", "version_number": 1},
        ]
        cursor = MockCursor(fetchall_val=workflows)

        with patch("backend.app.workflows._user", return_value=self.caller_row), \
             patch("backend.app.workflows._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_workflows(self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["name"], "Standard New Institution Approval")

    def test_get_workflow_detail(self):
        wf = {"id": self.workflow_id, "name": "Standard New Institution Approval", "status": "published"}
        stages = [
            {"id": UUID(int=20), "stage_code": "INTAKE", "stage_name": "Intake", "stage_order": 1, "stage_type": "intake", "default_sla_days": 7},
            {"id": UUID(int=21), "stage_code": "SCRUTINY", "stage_name": "Scrutiny", "stage_order": 2, "stage_type": "scrutiny", "default_sla_days": 21},
        ]
        transitions = [
            {"id": UUID(int=30), "from_stage_id": UUID(int=20), "to_stage_id": UUID(int=21), "transition_type": "forward", "guard_rule": None, "requires_authorisation": False},
        ]
        cursor = MockCursor(fetchone_val=wf, fetchall_val=stages)
        # We need fetchone for wf, then fetchall for stages, then fetchall for transitions
        def mock_fetchall():
            if "workflow_stages" in cursor.sql:
                return stages
            if "workflow_transitions" in cursor.sql:
                return transitions
            return []
        cursor.fetchall = mock_fetchall

        with patch("backend.app.workflows._user", return_value=self.caller_row), \
             patch("backend.app.workflows._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = get_workflow_detail(self.workflow_id, self.request, str(self.caller_id))

        self.assertEqual(res["workflow"]["id"], self.workflow_id)
        self.assertEqual(len(res["stages"]), 2)
        self.assertEqual(len(res["transitions"]), 1)

    def test_get_workflow_detail_missing_raises_404(self):
        cursor = MockCursor(fetchone_val=None)

        with patch("backend.app.workflows._user", return_value=self.caller_row), \
             patch("backend.app.workflows._read_connection", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                get_workflow_detail(self.workflow_id, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 404)
