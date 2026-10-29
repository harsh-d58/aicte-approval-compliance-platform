"""Unit tests for document registry, upload sessions, immutable versioning, and download authorization."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.concurrency import RecordMissing, StaleVersion
from backend.app.documents import (
    AddDocumentVersionRequest,
    CreateUploadSessionRequest,
    RegisterDocumentRequest,
    add_document_version,
    create_upload_session,
    download_document_version,
    get_document_detail,
    get_download_token,
    list_document_types,
    list_document_versions,
    register_document,
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


class DocumentRouteTests(TestCase):
    def setUp(self):
        self.document_id = UUID(int=1)
        self.version_id = UUID(int=2)
        self.institution_id = UUID(int=3)
        self.doc_type_id = UUID(int=4)
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
            "display_name": "Applicant Officer",
            "email": "officer@example.com",
            "status": "active",
        }

    def test_list_document_types(self):
        types = [
            {"id": self.doc_type_id, "document_type_code": "LAND_LEASE", "name": "Land Title", "supports_expiry": True, "metadata_schema": {}, "version": 1},
        ]
        cursor = MockCursor(fetchall_val=types)

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_document_types(self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["document_type_code"], "LAND_LEASE")

    def test_create_upload_session_success(self):
        payload = CreateUploadSessionRequest(
            institution_id=self.institution_id,
            document_type_id=self.doc_type_id,
            file_name="land_title.pdf",
            mime_type="application/pdf",
            max_size_bytes=5 * 1024 * 1024,
        )
        inst_row = {"id": self.institution_id}
        doc_type_row = {"id": self.doc_type_id}
        session_row = {
            "id": UUID(int=10),
            "institution_id": self.institution_id,
            "document_type_id": self.doc_type_id,
            "file_name": "land_title.pdf",
            "mime_type": "application/pdf",
            "max_size_bytes": 5 * 1024 * 1024,
            "status": "created",
            "upload_token": "safe_token_123",
            "expires_at": "2026-10-29T01:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[inst_row, doc_type_row, session_row])

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            res = create_upload_session(payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], UUID(int=10))
        self.assertEqual(res["status"], "created")

    def test_create_upload_session_missing_institution_raises_404(self):
        payload = CreateUploadSessionRequest(
            institution_id=self.institution_id,
            document_type_id=self.doc_type_id,
            file_name="land_title.pdf",
            mime_type="application/pdf",
            max_size_bytes=5 * 1024 * 1024,
        )
        cursor = MockCursor(fetchone_val=[None])

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                create_upload_session(payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 404)

    def test_register_document_success(self):
        payload = RegisterDocumentRequest(
            institution_id=self.institution_id,
            document_type_id=self.doc_type_id,
            document_scope="institution",
            reason="Register land evidence",
        )
        inst_row = {"id": self.institution_id}
        doc_type_row = {"id": self.doc_type_id}
        doc_row = {
            "id": self.document_id,
            "institution_id": self.institution_id,
            "campus_id": None,
            "application_id": None,
            "document_type_id": self.doc_type_id,
            "document_scope": "institution",
            "status": "active",
            "created_at": "2026-10-29T00:00:00Z",
            "version": 1,
        }
        cursor = MockCursor(fetchone_val=[inst_row, doc_type_row, doc_row])

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.documents.append_event", return_value=None), \
             patch("backend.app.documents.enqueue", return_value=None):
            res = register_document(payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.document_id)
        self.assertEqual(res["status"], "active")

    def test_get_document_detail_success(self):
        doc = {
            "id": self.document_id,
            "institution_id": self.institution_id,
            "campus_id": None,
            "application_id": None,
            "document_type_id": self.doc_type_id,
            "document_scope": "institution",
            "status": "active",
            "current_version_id": self.version_id,
            "created_at": "2026-10-29T00:00:00Z",
            "updated_at": "2026-10-29T00:00:00Z",
            "version": 2,
            "document_type_code": "LAND_LEASE",
            "document_type_name": "Land Title",
            "supports_expiry": True,
        }
        cursor = MockCursor(fetchone_val=doc)

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = get_document_detail(self.document_id, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.document_id)
        self.assertEqual(res["document_type_code"], "LAND_LEASE")

    def test_list_document_versions(self):
        versions = [
            {"id": self.version_id, "document_id": self.document_id, "version_number": 1, "file_name": "land.pdf", "verification_status": "pending"},
        ]
        cursor = MockCursor(fetchall_val=versions)

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_document_versions(self.document_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["file_name"], "land.pdf")

    def test_add_document_version_success(self):
        payload = AddDocumentVersionRequest(
            upload_session_id=UUID(int=40),
            file_name="land_title_v1.pdf",
            mime_type="application/pdf",
            size_bytes=102400,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            object_key="documents/inst_1/land_title_v1.pdf",
            issue_date="2026-01-01",
            expiry_date="2036-01-01",
            reason="Initial deed submission",
            expected_version=1,
        )
        max_ver_row = {"next_ver": 1}
        ver_row = {
            "id": self.version_id,
            "document_id": self.document_id,
            "version_number": 1,
            "object_key": payload.object_key,
            "file_name": payload.file_name,
            "mime_type": payload.mime_type,
            "size_bytes": payload.size_bytes,
            "sha256_hash": payload.sha256_hash,
            "uploaded_at": "2026-10-29T00:00:00Z",
            "issue_date": "2026-01-01",
            "expiry_date": "2036-01-01",
            "verification_status": "pending",
            "created_at": "2026-10-29T00:00:00Z",
        }
        parent = {"institution_id": self.institution_id, "document_type_id": self.doc_type_id, "supports_expiry": True}
        session = {**payload.model_dump(), "institution_id": self.institution_id, "document_type_id": self.doc_type_id, "status": "uploaded", "finalized_version_id": None, "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)}
        cursor = MockCursor(fetchone_val=[parent, session, max_ver_row, ver_row])

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.documents.lock_versioned", return_value=None), \
             patch("backend.app.documents.bump_version", return_value=2), \
             patch("backend.app.documents.append_event", return_value=None), \
             patch("backend.app.documents.enqueue", return_value=None):
            res = add_document_version(self.document_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.version_id)
        self.assertEqual(res["version_number"], 1)
        self.assertEqual(res["document_version"], 2)

    def test_add_document_version_expiry_precedes_issue_raises_400(self):
        payload = AddDocumentVersionRequest(
            file_name="bad_dates.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            object_key="documents/bad.pdf",
            issue_date="2026-05-01",
            expiry_date="2026-01-01",
            expected_version=1,
        )
        with patch("backend.app.documents._user", return_value=self.caller_row):
            with self.assertRaises(HTTPException) as ctx:
                add_document_version(self.document_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_download_document_version_success(self):
        version_row = {
            "id": self.version_id,
            "object_key": "safe_doc.pdf",
            "file_name": "safe_doc.pdf",
            "mime_type": "application/pdf",
        }
        cursor = MockCursor(fetchone_val=version_row)

        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents.verify_download_token", return_value=True), \
             patch("backend.app.documents._read_connection", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.documents.retrieve_file", return_value=b"%PDF-1.4 test"):
            response = download_document_version(self.version_id, "valid_token", self.request, str(self.caller_id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.body, b"%PDF-1.4 test")

    def test_download_document_version_invalid_token_raises_403(self):
        with patch("backend.app.documents._user", return_value=self.caller_row), \
             patch("backend.app.documents.verify_download_token", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                download_document_version(self.version_id, "bad_token", self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 403)
