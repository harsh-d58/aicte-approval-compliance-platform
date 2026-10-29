"""Unit tests for OCR extraction, automated advisory checks, human review, and renewal cases."""

from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.ocr import (
    CreateRenewalCaseRequest,
    ReviewCheckResultRequest,
    RunOcrCheckRequest,
    create_document_renewal_case,
    get_document_version_checks,
    list_document_renewal_cases,
    review_document_check_result,
    run_ocr_and_checks,
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


class OcrRouteTests(TestCase):
    def setUp(self):
        self.version_id = UUID(int=1)
        self.document_id = UUID(int=2)
        self.check_id = UUID(int=3)
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

    def test_run_ocr_and_checks_success(self):
        payload = RunOcrCheckRequest(engine_name="Tesseract", engine_version="5.3.0")
        version_info = {
            "id": self.version_id,
            "document_id": self.document_id,
            "version_number": 1,
            "file_name": "land_lease_deed.pdf",
            "mime_type": "application/pdf",
            "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "issue_date": date(2025, 1, 1),
            "expiry_date": date(2035, 1, 1),
            "document_type_id": UUID(int=10),
            "document_type_code": "LAND_LEASE",
            "supports_expiry": True,
        }
        extraction_row = {
            "id": UUID(int=20),
            "document_version_id": self.version_id,
            "engine_name": "Tesseract",
            "engine_version": "5.3.0",
            "status": "completed",
            "confidence_summary": {"overall_confidence": 0.94},
            "extracted_fields": {"certificate_number": "CERT-E3B0C442"},
            "completed_at": "2026-10-29T00:00:00Z",
        }
        check_1 = {"id": UUID(int=30), "check_code": "DOC_TYPE_MATCH", "severity": "medium", "result": "pass", "review_status": "pending"}
        check_2 = {"id": UUID(int=31), "check_code": "EXPIRY_CHECK", "severity": "info", "result": "pass", "review_status": "pending"}
        check_3 = {"id": UUID(int=32), "check_code": "MANDATORY_FIELDS", "severity": "high", "result": "pass", "review_status": "pending"}
        check_4 = {"id": UUID(int=33), "check_code": "CONFIDENCE_THRESHOLD", "severity": "low", "result": "pass", "review_status": "pending"}

        cursor = MockCursor(fetchone_val=[version_info, extraction_row, check_1, check_2, check_3, check_4])

        with patch("backend.app.ocr._user", return_value=self.caller_row), \
             patch("backend.app.ocr.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.ocr.append_event", return_value=None), \
             patch("backend.app.ocr.enqueue", return_value=None):
            res = run_ocr_and_checks(self.version_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["extraction"]["status"], "completed")
        self.assertEqual(len(res["checks"]), 4)
        self.assertEqual(res["checks"][0]["check_code"], "DOC_TYPE_MATCH")

    def test_run_ocr_and_checks_missing_version_raises_404(self):
        payload = RunOcrCheckRequest()
        cursor = MockCursor(fetchone_val=[None])

        with patch("backend.app.ocr._user", return_value=self.caller_row), \
             patch("backend.app.ocr.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                run_ocr_and_checks(self.version_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 404)

    def test_get_document_version_checks(self):
        extractions = [
            {"id": UUID(int=20), "document_version_id": self.version_id, "engine_name": "Tesseract", "status": "completed"},
        ]
        checks = [
            {"id": self.check_id, "document_version_id": self.version_id, "check_code": "DOC_TYPE_MATCH", "result": "pass"},
        ]
        cursor = MockCursor(fetchall_val=extractions)
        def mock_fetchall():
            if "document_extractions" in cursor.sql:
                return extractions
            if "document_check_results" in cursor.sql:
                return checks
            return []
        cursor.fetchall = mock_fetchall

        with patch("backend.app.ocr._user", return_value=self.caller_row), \
             patch("backend.app.ocr._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = get_document_version_checks(self.version_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["extractions"]), 1)
        self.assertEqual(len(res["checks"]), 1)
        self.assertEqual(res["checks"][0]["check_code"], "DOC_TYPE_MATCH")

    def test_review_document_check_result_success(self):
        payload = ReviewCheckResultRequest(review_status="accepted", reason="Verified land registration seal")
        check_row = {"id": self.check_id, "document_version_id": self.version_id, "check_code": "EXPIRY_CHECK", "review_status": "pending"}
        updated_row = {
            "id": self.check_id,
            "document_version_id": self.version_id,
            "check_code": "EXPIRY_CHECK",
            "severity": "info",
            "result": "pass",
            "details": {},
            "review_status": "accepted",
            "reviewed_by": self.caller_id,
            "reviewed_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[check_row, updated_row])

        with patch("backend.app.ocr._user", return_value=self.caller_row), \
             patch("backend.app.ocr.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.ocr.append_event", return_value=None), \
             patch("backend.app.ocr.enqueue", return_value=None):
            res = review_document_check_result(self.check_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.check_id)
        self.assertEqual(res["review_status"], "accepted")

    def test_create_document_renewal_case_success(self):
        payload = CreateRenewalCaseRequest(
            document_id=self.document_id,
            renewal_due_days=45,
            reason="Fire safety approval expiring next month",
        )
        doc_row = {"id": self.document_id, "current_version_id": self.version_id, "status": "active"}
        case_row = {
            "id": UUID(int=40),
            "document_id": self.document_id,
            "current_version_id": self.version_id,
            "renewal_due_at": "2026-12-13T00:00:00Z",
            "status": "open",
            "assigned_to": None,
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[doc_row, case_row])

        with patch("backend.app.ocr._user", return_value=self.caller_row), \
             patch("backend.app.ocr.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.ocr.append_event", return_value=None), \
             patch("backend.app.ocr.enqueue", return_value=None):
            res = create_document_renewal_case(payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], UUID(int=40))
        self.assertEqual(res["status"], "open")

    def test_list_document_renewal_cases(self):
        cases = [
            {
                "id": UUID(int=40),
                "document_id": self.document_id,
                "current_version_id": self.version_id,
                "renewal_due_at": "2026-12-13T00:00:00Z",
                "status": "open",
                "assigned_to": None,
                "closed_at": None,
                "created_at": "2026-10-29T00:00:00Z",
                "institution_id": UUID(int=50),
                "document_type_code": "FIRE_SAFETY",
                "document_type_name": "Fire Safety Certificate",
            }
        ]
        cursor = MockCursor(fetchall_val=cases)

        with patch("backend.app.ocr._user", return_value=self.caller_row), \
             patch("backend.app.ocr._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_document_renewal_cases(self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["document_type_code"], "FIRE_SAFETY")
