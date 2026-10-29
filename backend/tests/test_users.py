"""Unit tests for user listing and role assignment management."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.settings import Settings
from backend.app.authorization import validate_role_grant
from backend.app.users import (
    CreateRoleAssignmentRequest,
    UpdateRoleAssignmentRequest,
    assign_user_role,
    get_user_detail,
    list_users,
    update_user_role_assignment,
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


class UserRouteTests(TestCase):
    def setUp(self):
        self.user_id = UUID(int=1)
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
            "display_name": "Admin User",
            "email": "admin@example.com",
            "status": "active",
            "last_login_at": None,
        }

    def test_grant_requires_system_authority(self):
        cursor = MockCursor(fetchone_val={"id": self.user_id, "status": "active"},
                            fetchall_val=[{"role_code": "DEMO_REGIONAL", "scope_type": "region"}])
        with self.assertRaises(HTTPException) as raised:
            validate_role_grant(cursor, self.caller_id, self.user_id, "DEMO_INSTITUTION",
                                "institution", UUID(int=30), datetime.now(timezone.utc), None)
        self.assertEqual(raised.exception.status_code, 403)

    def test_evaluation_administrator_cannot_grant_production_role(self):
        cursor = MockCursor(fetchone_val={"id": self.user_id, "status": "active"},
                            fetchall_val=[{"role_code": "DEMO_SYSTEM", "scope_type": "global"}])
        with self.assertRaises(HTTPException) as raised:
            validate_role_grant(cursor, self.caller_id, self.user_id, "INSTITUTION_USER",
                                "institution", UUID(int=30), datetime.now(timezone.utc), None)
        self.assertEqual(raised.exception.status_code, 403)

    def test_conflicting_auditor_and_operator_are_rejected(self):
        cursor = MockCursor(fetchone_val={"id": self.user_id, "status": "active"})
        cursor.fetchall = lambda: ([{"role_code": "DEMO_SYSTEM", "scope_type": "global"}]
            if "JOIN public.users" in cursor.sql else [{"role_code": "DEMO_AUDITOR", "scope_type": "global", "scope_id": None}])
        with self.assertRaises(HTTPException) as raised:
            validate_role_grant(cursor, self.caller_id, self.user_id, "DEMO_INSTITUTION",
                                "institution", UUID(int=30), datetime.now(timezone.utc), None)
        self.assertEqual(raised.exception.status_code, 409)

    def test_interval_check_allows_nonoverlapping_grant(self):
        cursor = MockCursor(fetchone_val={"id": self.user_id, "status": "active"})
        cursor.fetchall = lambda: ([{"role_code": "DEMO_SYSTEM", "scope_type": "global"}]
            if "JOIN public.users" in cursor.sql else [])
        start = datetime.now(timezone.utc) + timedelta(days=30)
        end = start + timedelta(days=30)
        validate_role_grant(cursor, self.caller_id, self.user_id, "DEMO_INSTITUTION",
                            "institution", UUID(int=30), start, end)
        self.assertIn("a.valid_until>%s", cursor.sql)
        self.assertIn("a.valid_from<%s", cursor.sql)
        self.assertEqual(cursor.params[-3:], (start, end, end))

    def test_list_users_queries_with_pagination(self):
        user_rows = [
            {"id": self.user_id, "display_name": "Test User", "email": "u@test.com", "status": "active", "last_login_at": None, "active_roles": ["DEMO_VIEWER"]},
        ]
        cursor = MockCursor(fetchall_val=user_rows)
        with patch("backend.app.users._user", return_value=self.caller_row), \
             patch("backend.app.users._read_connection", return_value=nullcontext(MockConnection(cursor))):
            result = list_users(self.request, str(self.caller_id), limit=10)
        self.assertEqual(len(result["data"]), 1)
        self.assertIsNone(result["page"]["next_cursor"])
        self.assertIn("FROM public.users", cursor.sql)

    def test_get_user_detail_returns_user_and_assignments(self):
        target_user = {"id": self.user_id, "display_name": "Target", "email": "t@test.com", "status": "active", "last_login_at": None}
        assignments = [{"id": UUID(int=10), "role_code": "DEMO_VIEWER", "role_name": "Viewer", "scope_type": "institution", "scope_id": UUID(int=20), "valid_from": None, "valid_until": None, "status": "active"}]
        cursor = MockCursor(fetchone_val=target_user, fetchall_val=assignments)
        with patch("backend.app.users._user", return_value=self.caller_row), \
             patch("backend.app.users._read_connection", return_value=nullcontext(MockConnection(cursor))):
            result = get_user_detail(self.user_id, self.request, str(self.caller_id))
        self.assertEqual(result["user"]["id"], self.user_id)
        self.assertEqual(len(result["assignments"]), 1)

    def test_get_user_detail_raises_404_when_user_missing(self):
        cursor = MockCursor(fetchone_val=None)
        with patch("backend.app.users._user", return_value=self.caller_row), \
             patch("backend.app.users._read_connection", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                get_user_detail(self.user_id, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 404)

    def test_assign_role_rejects_global_scope_with_scope_id(self):
        payload = CreateRoleAssignmentRequest(
            role_code="DEMO_INSTITUTION",
            scope_type="global",
            scope_id=UUID(int=99),
            reason="Invalid global scope with scope_id",
        )
        with patch("backend.app.users._user", return_value=self.caller_row):
            with self.assertRaises(HTTPException) as ctx:
                assign_user_role(self.user_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_assign_role_rejects_institution_scope_without_scope_id(self):
        payload = CreateRoleAssignmentRequest(
            role_code="DEMO_ROLE",
            scope_type="institution",
            scope_id=None,
            reason="Invalid institution scope without ID",
        )
        with patch("backend.app.users._user", return_value=self.caller_row):
            with self.assertRaises(HTTPException) as ctx:
                assign_user_role(self.user_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_assign_role_rejects_inverted_dates(self):
        now = datetime.now(timezone.utc)
        payload = CreateRoleAssignmentRequest(
            role_code="DEMO_ROLE",
            scope_type="global",
            scope_id=None,
            valid_from=now + timedelta(days=10),
            valid_until=now + timedelta(days=1),
            reason="Inverted dates",
        )
        with patch("backend.app.users._user", return_value=self.caller_row):
            with self.assertRaises(HTTPException) as ctx:
                assign_user_role(self.user_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_assign_role_detects_conflict_duplicate(self):
        payload = CreateRoleAssignmentRequest(
            role_code="DEMO_INSTITUTION",
            scope_type="institution",
            scope_id=UUID(int=30),
            reason="Duplicate check",
        )
        # Target is locked before authority/scope and interval checks.
        cursor = MockCursor(fetchone_val=[
            {"id": self.user_id, "status": "active"},
            {"id": UUID(int=50), "role_code": "DEMO_INSTITUTION"},
            {"id": self.user_id, "status": "active"},
            {"id": UUID(int=30)},
        ])
        cursor.fetchall = lambda: ([{"role_code": "DEMO_SYSTEM", "scope_type": "global"}]
            if "JOIN public.users" in cursor.sql else [{"role_code": "DEMO_INSTITUTION", "scope_type": "institution", "scope_id": UUID(int=30)}])
        with patch("backend.app.users._user", return_value=self.caller_row), \
             patch("backend.app.users.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                assign_user_role(self.user_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_assign_role_succeeds_with_audit_and_outbox(self):
        payload = CreateRoleAssignmentRequest(
            role_code="DEMO_INSTITUTION",
            scope_type="institution",
            scope_id=UUID(int=30),
            reason="Grant for inspection",
        )
        new_assignment = {
            "id": UUID(int=77),
            "user_id": self.user_id,
            "role_id": UUID(int=50),
            "scope_type": "institution",
            "scope_id": UUID(int=30),
            "valid_from": datetime.now(timezone.utc),
            "valid_until": None,
            "status": "active",
        }
        cursor = MockCursor(fetchone_val=[
            {"id": self.user_id, "status": "active"},
            {"id": UUID(int=50), "role_code": "DEMO_INSTITUTION"},
            {"id": self.user_id, "status": "active"},
            {"id": UUID(int=30)},
            new_assignment,
        ])
        cursor.fetchall = lambda: ([{"role_code": "DEMO_SYSTEM", "scope_type": "global"}]
            if "JOIN public.users" in cursor.sql else [])
        with patch("backend.app.users._user", return_value=self.caller_row), \
             patch("backend.app.users.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.users.append_event") as mock_append, \
             patch("backend.app.users.enqueue") as mock_enqueue:
            result = assign_user_role(self.user_id, payload, self.request, str(self.caller_id))
        self.assertEqual(result["id"], UUID(int=77))
        self.assertEqual(result["status"], "active")
        mock_append.assert_called_once()
        self.assertEqual(mock_append.call_args[1]["action"], "ROLE_ASSIGNED")
        mock_enqueue.assert_called_once()
        self.assertEqual(mock_enqueue.call_args[1]["event_type"], "USER_ROLE_ASSIGNED")

    def test_update_role_assignment_revokes_with_audit_and_outbox(self):
        payload = UpdateRoleAssignmentRequest(
            status="revoked",
            reason="Employee left institution",
        )
        existing_assignment = {
            "id": UUID(int=77),
            "user_id": self.user_id,
            "role_id": UUID(int=50),
            "scope_type": "institution",
            "scope_id": UUID(int=30),
            "valid_from": datetime.now(timezone.utc),
            "valid_until": None,
            "status": "active",
        }
        updated_assignment = {**existing_assignment, "status": "revoked"}
        cursor = MockCursor(fetchone_val=[
            existing_assignment,
            updated_assignment,
        ])
        with patch("backend.app.users._user", return_value=self.caller_row), \
             patch("backend.app.users.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.users.append_event") as mock_append, \
             patch("backend.app.users.enqueue") as mock_enqueue:
            result = update_user_role_assignment(self.user_id, UUID(int=77), payload, self.request, str(self.caller_id))
        self.assertEqual(result["status"], "revoked")
        mock_append.assert_called_once()
        self.assertEqual(mock_append.call_args[1]["action"], "ROLE_REVOKED")
        mock_enqueue.assert_called_once()
        self.assertEqual(mock_enqueue.call_args[1]["event_type"], "USER_ROLE_REVOKED")
