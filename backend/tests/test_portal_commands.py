"""Failure-boundary tests for normalized supplemental portal actions."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.portal_commands import PortalCommand, execute_command


ACTOR = "11111111-1111-4111-8111-111111111111"
TARGET = "22222222-2222-4222-8222-222222222222"


class Cursor:
    rowcount = 1

    def __init__(self):
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def fetchall(self):
        return [{"role_code": self.role_code}]


class PortalCommandsTests(TestCase):
    def run_command(self, role, payload, collections=None):
        cursor = Cursor()
        cursor.role_code = "DEMO_" + role
        connection = SimpleNamespace(cursor=lambda **_: cursor)

        @contextmanager
        def transaction(*_):
            yield connection

        data = {"users": [{"id": ACTOR, "status": "ACTIVE", "assignments": [{"role": role, "scope": {"type": "GLOBAL", "id": "all"}}]}]}
        data.update(collections or {})
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(database_write_url="unused"))), state=SimpleNamespace(correlation_id=ACTOR))
        with patch("backend.app.portal_commands._user", return_value={"id": ACTOR}), patch("backend.app.portal_commands.write_transaction", transaction), patch("backend.app.portal_commands.snapshot", return_value=data), patch("backend.app.portal_commands.append_event"), patch("backend.app.portal_commands.enqueue"):
            result = execute_command(request, ACTOR, PortalCommand(**payload))
        return result, cursor

    def test_notification_read_only_for_own_recipient(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("INSTITUTION", {"kind": "notification.read", "id": TARGET, "values": {"read": True}}, {"notifications": [{"id": TARGET, "recipientId": TARGET}]})
        self.assertEqual(error.exception.status_code, 403)

    def test_notification_read_persists_payload(self):
        result, cursor = self.run_command("INSTITUTION", {"kind": "notification.read", "id": TARGET, "values": {"read": True}}, {"notifications": [{"id": TARGET, "recipientId": ACTOR}]})
        self.assertEqual(result["id"], TARGET)
        self.assertTrue(any("UPDATE public.notifications" in sql for sql, _ in cursor.statements))

    def test_wrong_role_cannot_cancel_visit(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("INSTITUTION", {"kind": "visit.cancel", "id": TARGET})
        self.assertEqual(error.exception.status_code, 403)

    def test_out_of_scope_visit_is_hidden(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("REGIONAL", {"kind": "visit.cancel", "id": TARGET}, {"visits": []})
        self.assertEqual(error.exception.status_code, 404)

    def test_stale_application_cannot_be_assigned(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("REGIONAL", {"kind": "application.assign", "id": TARGET, "expectedVersion": 1}, {"applications": [{"id": TARGET, "version": 2}]})
        self.assertEqual(error.exception.status_code, 412)

    def test_unknown_action_cannot_report_success(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("SYSTEM", {"kind": "job.process", "id": TARGET})
        self.assertEqual(error.exception.status_code, 422)

    def test_institution_cannot_administer_users(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("INSTITUTION", {"kind": "user.status", "id": TARGET})
        self.assertEqual(error.exception.status_code, 403)

    def test_read_only_viewer_cannot_mutate(self):
        with self.assertRaises(HTTPException) as error:
            self.run_command("INSTITUTION_VIEWER", {"kind": "notification.read", "id": TARGET, "values": {"read": True}}, {"notifications": [{"id": TARGET, "recipientId": ACTOR}]})
        self.assertEqual(error.exception.status_code, 403)
