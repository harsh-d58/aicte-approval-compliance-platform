"""Unit tests for application draft intake, editing, submission, and stage transitions."""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.applications import (
    CreateApplicationRequest,
    SubmitApplicationRequest,
    TransitionApplicationRequest,
    UpdateApplicationDraftRequest,
    create_application_draft,
    submit_application,
    transition_application,
    update_application_draft,
)
from backend.app.concurrency import StaleVersion
from backend.app.settings import Settings


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


class ApplicationRouteTests(TestCase):
    def setUp(self):
        self.app_id = UUID(int=1)
        self.institution_id = UUID(int=2)
        self.type_id = UUID(int=3)
        self.wf_id = UUID(int=4)
        self.caller_id = UUID(int=5)
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
            "display_name": "Applicant Rep",
            "email": "rep@example.com",
            "status": "active",
        }

    def test_create_application_draft_success(self):
        payload = CreateApplicationRequest(
            institution_id=self.institution_id,
            application_type_id=self.type_id,
            workflow_definition_id=self.wf_id,
            reason="New application for 2026-27",
        )
        inst_row = {"id": self.institution_id}
        type_row = {"id": self.type_id}
        wf_row = {"id": self.wf_id}
        app_created = {
            "id": self.app_id,
            "application_number": "APP-2026-ABCD",
            "institution_id": self.institution_id,
            "campus_id": None,
            "application_type_id": self.type_id,
            "workflow_definition_id": self.wf_id,
            "status": "draft",
            "created_at": "2026-10-29T00:00:00Z",
            "updated_at": "2026-10-29T00:00:00Z",
            "version": 1,
        }
        cursor = MockCursor(fetchone_val=[inst_row, type_row, wf_row, app_created])

        with patch("backend.app.applications._user", return_value=self.caller_row), \
             patch("backend.app.applications.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.applications.append_event", return_value=None), \
             patch("backend.app.applications.enqueue", return_value=None):
            result = create_application_draft(payload, self.request, str(self.caller_id))

        self.assertEqual(result["id"], self.app_id)
        self.assertEqual(result["status"], "draft")

    def test_create_application_draft_institution_missing_raises_404(self):
        payload = CreateApplicationRequest(
            institution_id=self.institution_id,
            application_type_id=self.type_id,
            workflow_definition_id=self.wf_id,
        )
        cursor = MockCursor(fetchone_val=[None])

        with patch("backend.app.applications._user", return_value=self.caller_row), \
             patch("backend.app.applications.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                create_application_draft(payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 404)

    def test_update_application_draft_success(self):
        campus_id = UUID(int=10)
        payload = UpdateApplicationDraftRequest(campus_id=campus_id, expected_version=1)
        current_app = {"status": "draft"}
        updated_app = {
            "id": self.app_id,
            "application_number": "APP-2026-ABCD",
            "institution_id": self.institution_id,
            "campus_id": campus_id,
            "application_type_id": self.type_id,
            "status": "draft",
            "updated_at": "2026-10-29T00:00:00Z",
            "version": 2,
        }
        cursor = MockCursor(fetchone_val=[current_app, {"id": campus_id}, updated_app])

        with patch("backend.app.applications._user", return_value=self.caller_row), \
             patch("backend.app.applications.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.applications.lock_versioned", return_value=None), \
             patch("backend.app.applications.bump_version", return_value=2), \
             patch("backend.app.applications.append_event", return_value=None), \
             patch("backend.app.applications.enqueue", return_value=None):
            res = update_application_draft(self.app_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["version"], 2)
        self.assertEqual(res["campus_id"], str(campus_id))

    def test_submit_application_success(self):
        payload = SubmitApplicationRequest(expected_version=1)
        app_row = {
            "id": self.app_id,
            "status": "draft",
            "workflow_definition_id": self.wf_id,
            "application_number": "APP-2026-ABCD",
        }
        first_stage = {
            "id": UUID(int=20),
            "stage_code": "INTAKE",
            "stage_name": "Intake",
            "default_sla_days": 7,
        }
        sub_row = {"id": UUID(int=30)}
        stage_inst_row = {"id": UUID(int=40)}
        updated_app = {
            "id": self.app_id,
            "application_number": "APP-2026-ABCD",
            "status": "submitted",
            "current_stage_instance_id": UUID(int=40),
            "submitted_at": "2026-10-29T00:00:00Z",
            "version": 2,
        }
        cursor = MockCursor(fetchone_val=[app_row, first_stage, sub_row, stage_inst_row, updated_app])

        with patch("backend.app.applications._user", return_value=self.caller_row), \
             patch("backend.app.applications.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.applications.lock_versioned", return_value=None), \
             patch("backend.app.applications.bump_version", return_value=2), \
             patch("backend.app.applications.append_event", return_value=None), \
             patch("backend.app.applications.enqueue", return_value=None):
            res = submit_application(self.app_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["status"], "submitted")
        self.assertEqual(res["version"], 2)

    def test_transition_application_success(self):
        to_stage_id = UUID(int=21)
        payload = TransitionApplicationRequest(to_stage_id=to_stage_id, expected_version=2, reason="Move to scrutiny")
        app_row = {
            "id": self.app_id,
            "status": "submitted",
            "current_stage_instance_id": UUID(int=40),
            "workflow_definition_id": self.wf_id,
            "application_number": "APP-2026-ABCD",
            "current_stage_id": UUID(int=20),
        }
        transition_row = {
            "id": UUID(int=50),
            "guard_rule": {"required_status": "submitted"},
            "transition_type": "forward",
            "requires_authorisation": False,
        }
        unresolved_count = {"count": 0}
        target_stage = {
            "id": to_stage_id,
            "stage_code": "SCRUTINY",
            "stage_type": "scrutiny",
            "default_sla_days": 21,
        }
        new_inst_row = {"id": UUID(int=41)}
        updated_app = {
            "id": self.app_id,
            "application_number": "APP-2026-ABCD",
            "status": "under_review",
            "current_stage_instance_id": UUID(int=41),
            "updated_at": "2026-10-29T00:00:00Z",
            "version": 3,
        }
        cursor = MockCursor(
            fetchone_val=[app_row, transition_row, unresolved_count, target_stage, new_inst_row, updated_app],
            fetchall_val=[{"role_code": "SCRUTINY_OFFICER"}],
        )

        with patch("backend.app.applications._user", return_value=self.caller_row), \
             patch("backend.app.applications.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.applications.lock_versioned", return_value=None), \
             patch("backend.app.applications.bump_version", return_value=3), \
             patch("backend.app.applications.append_event", return_value=None), \
             patch("backend.app.applications.enqueue", return_value=None):
            res = transition_application(self.app_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["status"], "under_review")
        self.assertEqual(res["version"], 3)
