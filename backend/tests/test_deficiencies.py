"""Unit tests for deficiency notice creation, response submission, and item resolution."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.deficiencies import (
    CreateDeficiencyItemRequest,
    CreateDeficiencyNoticeRequest,
    ResolveDeficiencyItemRequest,
    SubmitDeficiencyItemResponse,
    SubmitDeficiencyResponseRequest,
    create_deficiency_notice,
    list_deficiency_notices,
    resolve_deficiency_item,
    submit_deficiency_response,
)
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


class DeficiencyRouteTests(TestCase):
    def setUp(self):
        self.app_id = UUID(int=1)
        self.notice_id = UUID(int=2)
        self.item_id = UUID(int=3)
        self.caller_id = UUID(int=4)
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
            "display_name": "Scrutiny Officer",
            "email": "officer@example.com",
            "status": "active",
        }

    def test_create_deficiency_notice_success(self):
        payload = CreateDeficiencyNoticeRequest(
            response_due_days=15,
            items=[
                CreateDeficiencyItemRequest(criterion_code="LAND-01", description="Land title certificate not clear"),
            ],
            reason="Land documentation unclear",
        )
        app_row = {
            "id": self.app_id,
            "status": "under_review",
            "current_stage_instance_id": UUID(int=10),
            "version": 2,
        }
        notice_row = {
            "id": self.notice_id,
            "application_id": self.app_id,
            "stage_instance_id": UUID(int=10),
            "notice_number": "DEF-2026-AAAA",
            "issued_by": self.caller_id,
            "issued_at": "2026-10-29T00:00:00Z",
            "response_due_at": "2026-11-13T00:00:00Z",
            "status": "open",
            "created_at": "2026-10-29T00:00:00Z",
        }
        item_row = {
            "id": self.item_id,
            "deficiency_notice_id": self.notice_id,
            "criterion_code": "LAND-01",
            "description": "Land title certificate not clear",
            "related_document_id": None,
            "resolution_status": "pending",
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[app_row, notice_row, item_row])

        with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
             patch("backend.app.deficiencies.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.deficiencies.append_event", return_value=None), \
             patch("backend.app.deficiencies.enqueue", return_value=None):
            res = create_deficiency_notice(self.app_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.notice_id)
        self.assertEqual(len(res["items"]), 1)
        self.assertEqual(res["items"][0]["criterion_code"], "LAND-01")

    def test_create_deficiency_notice_closed_app_raises_409(self):
        payload = CreateDeficiencyNoticeRequest(
            items=[CreateDeficiencyItemRequest(description="Test gap")],
        )
        app_row = {"id": self.app_id, "status": "approved", "current_stage_instance_id": None}
        cursor = MockCursor(fetchone_val=[app_row])

        with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
             patch("backend.app.deficiencies.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                create_deficiency_notice(self.app_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_list_deficiency_notices(self):
        notices = [
            {"id": self.notice_id, "application_id": self.app_id, "notice_number": "DEF-2026-AAAA", "status": "open"},
        ]
        items = [
            {"id": self.item_id, "deficiency_notice_id": self.notice_id, "description": "Deficiency item 1", "resolution_status": "pending"},
        ]
        cursor = MockCursor(fetchall_val=notices)
        def mock_fetchall():
            if "deficiency_notices" in cursor.sql:
                return notices
            if "deficiency_items" in cursor.sql:
                return items
            return []
        cursor.fetchall = mock_fetchall

        with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
             patch("backend.app.deficiencies._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_deficiency_notices(self.app_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["items"][0]["description"], "Deficiency item 1")

    def test_submit_deficiency_response_success(self):
        doc_id = UUID(int=20)
        payload = SubmitDeficiencyResponseRequest(
            item_responses=[SubmitDeficiencyItemResponse(item_id=self.item_id, related_document_id=doc_id, document_version_id=UUID(int=21), narrative="Registered land certificate attached")],
            reason="Provided registered land certificate",
        )
        notice_row = {"id": self.notice_id, "application_id": self.app_id, "status": "open"}
        updated_item = {
            "id": self.item_id,
            "deficiency_notice_id": self.notice_id,
            "criterion_code": "LAND-01",
            "description": "Land title certificate",
            "related_document_id": doc_id,
            "resolution_status": "submitted",
        }
        cursor = MockCursor(fetchone_val=[notice_row,
            {"id": self.app_id, "status": "deficiency_returned", "institution_id": UUID(int=50)},
            {"id": UUID(int=60), "submission_number": 2},
            {"id": self.item_id, "resolution_status": "pending"},
            {"id": doc_id}, updated_item, {"count": 0}])

        with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
             patch("backend.app.deficiencies.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.deficiencies.append_event", return_value=None), \
             patch("backend.app.deficiencies.enqueue", return_value=None):
            res = submit_deficiency_response(self.notice_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["status"], "responded")
        self.assertEqual(len(res["updated_items"]), 1)
        self.assertEqual(res["updated_items"][0]["resolution_status"], "submitted")

    def test_resolve_deficiency_item_and_notice_resolution(self):
        payload = ResolveDeficiencyItemRequest(resolution_status="accepted", reason="Document verified")
        item_row = {"id": self.item_id, "deficiency_notice_id": self.notice_id, "resolution_status": "submitted"}
        updated_item = {
            "id": self.item_id,
            "deficiency_notice_id": self.notice_id,
            "criterion_code": "LAND-01",
            "description": "Land title certificate",
            "related_document_id": None,
            "resolution_status": "accepted",
        }
        unresolved_count = {"count": 0}  # Notice should resolve
        cursor = MockCursor(fetchone_val=[item_row, updated_item, unresolved_count])

        with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
             patch("backend.app.deficiencies.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.deficiencies.append_event", return_value=None), \
             patch("backend.app.deficiencies.enqueue", return_value=None):
            res = resolve_deficiency_item(self.item_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["item"]["resolution_status"], "accepted")
        self.assertTrue(res["notice_resolved"])

    def test_foreign_or_resolved_response_item_is_rejected(self):
        for current, expected in [(None, 422), ({"id": self.item_id, "resolution_status": "accepted"}, 409)]:
            with self.subTest(current=current):
                payload = SubmitDeficiencyResponseRequest(item_responses=[SubmitDeficiencyItemResponse(
                    item_id=self.item_id, narrative="Correction evidence explained")])
                cursor = MockCursor(fetchone_val=[
                    {"id": self.notice_id, "application_id": self.app_id, "status": "open"},
                    {"id": self.app_id, "status": "deficiency_returned", "institution_id": UUID(int=50)},
                    {"id": UUID(int=60), "submission_number": 2}, current])
                with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
                     patch("backend.app.deficiencies.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
                     patch("backend.app.deficiencies.append_event") as audit:
                    with self.assertRaises(HTTPException) as raised:
                        submit_deficiency_response(self.notice_id, payload, self.request, str(self.caller_id))
                self.assertEqual(raised.exception.status_code, expected)
                audit.assert_not_called()

    def test_partial_response_keeps_notice_open_and_case_returned(self):
        payload = SubmitDeficiencyResponseRequest(item_responses=[SubmitDeficiencyItemResponse(
            item_id=self.item_id, narrative="Corrected first item; second item remains open")])
        cursor = MockCursor(fetchone_val=[
            {"id": self.notice_id, "application_id": self.app_id, "status": "open"},
            {"id": self.app_id, "status": "deficiency_returned", "institution_id": UUID(int=50)},
            {"id": UUID(int=60), "submission_number": 2},
            {"id": self.item_id, "resolution_status": "pending"},
            {"id": self.item_id, "resolution_status": "submitted"}, {"count": 1}])
        statements = []
        execute = cursor.execute
        def remember(sql, params=None):
            statements.append((sql, params))
            execute(sql, params)
        cursor.execute = remember
        with patch("backend.app.deficiencies._user", return_value=self.caller_row), \
             patch("backend.app.deficiencies.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.deficiencies.append_event"), patch("backend.app.deficiencies.enqueue"):
            result = submit_deficiency_response(self.notice_id, payload, self.request, str(self.caller_id))
        self.assertEqual(result["status"], "open")
        self.assertTrue(any("UPDATE public.applications" in sql and params[0] == "deficiency_returned"
                            for sql, params in statements))
        evidence_insert = next(params for sql, params in statements if "INSERT INTO public.deficiency_item_responses" in sql)
        self.assertEqual(evidence_insert[2], payload.item_responses[0].narrative)
