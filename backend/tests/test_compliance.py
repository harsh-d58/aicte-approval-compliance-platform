"""Unit tests for institutional compliance, evidence submissions, and officer verifications."""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.compliance import (
    CloseConditionRequest,
    CreateConditionRequest,
    ReopenConditionRequest,
    SubmitEvidenceRequest,
    VerifyEvidenceRequest,
    close_compliance_condition,
    create_compliance_condition,
    get_compliance_condition,
    list_compliance_conditions,
    reopen_compliance_condition,
    submit_condition_evidence,
    verify_evidence_submission,
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
        if self.sql.startswith("SELECT event_hash, event_at"):
            return None
        if isinstance(self.fetchone_val, list):
            return self.fetchone_val.pop(0) if self.fetchone_val else None
        return self.fetchone_val

    def fetchall(self):
        if isinstance(self.fetchall_val, list) and self.fetchall_val and isinstance(self.fetchall_val[0], list):
            return self.fetchall_val.pop(0)
        return self.fetchall_val


class MockConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor


class ComplianceRouteTests(TestCase):
    def setUp(self):
        self.inst_id = UUID(int=1)
        self.app_id = UUID(int=2)
        self.cond_id = UUID(int=3)
        self.sub_id = UUID(int=4)
        self.doc_ver_id = UUID(int=5)
        self.caller_id = UUID(int=6)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=99))),
        )
        self.subject = "test-subject"

    def test_closure_requires_verified_compliance(self):
        cur = MockCursor(fetchone_val={"id": self.cond_id, "status": "evidence_submitted", "version": 1})
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                close_compliance_condition(self.cond_id, CloseConditionRequest(reason="Attempt premature closure"), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertFalse(cur.sql.startswith("UPDATE"))

    def test_reopen_requires_closed_condition(self):
        cur = MockCursor(fetchone_val={"id": self.cond_id, "status": "open", "version": 1})
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                reopen_compliance_condition(self.cond_id, ReopenConditionRequest(reason="Attempt invalid reopening"), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_evidence_from_another_institution_is_rejected(self):
        cur = MockCursor(fetchone_val=[
            {"id": self.cond_id, "institution_id": self.inst_id, "application_id": self.app_id, "status": "open", "version": 1},
            {"next_sub_num": 1}, None,
        ])
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                submit_condition_evidence(self.cond_id, SubmitEvidenceRequest(document_version_ids=[self.doc_ver_id]), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("d.institution_id=%s", cur.sql)
        self.assertEqual(cur.params, (self.doc_ver_id, self.inst_id, self.app_id))

    def test_evidence_submitter_cannot_self_verify(self):
        cur = MockCursor(fetchone_val=[
            {"id": self.sub_id, "compliance_condition_id": self.cond_id, "submitted_by": self.caller_id, "status": "submitted"},
            {"id": self.cond_id, "status": "evidence_submitted", "version": 1},
        ])
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                verify_evidence_submission(self.sub_id, VerifyEvidenceRequest(result="accepted", comments="Attempt self verification"), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_superseded_evidence_cannot_be_verified(self):
        cur = MockCursor(fetchone_val=[
            {"id": self.sub_id, "compliance_condition_id": self.cond_id, "submitted_by": UUID(int=50), "status": "submitted"},
            {"id": self.cond_id, "status": "evidence_submitted", "version": 1},
            {"id": UUID(int=51)},
        ])
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                verify_evidence_submission(self.sub_id, VerifyEvidenceRequest(result="accepted", comments="Attempt stale verification"), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 409)

    @patch("backend.app.compliance.write_transaction")
    @patch("backend.app.compliance._user")
    def test_create_condition_success(self, mock_user, mock_tx):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val={
                "id": self.cond_id,
                "institution_id": self.inst_id,
                "application_id": self.app_id,
                "source_approval_id": None,
                "condition_code": "COND-01",
                "description": "Fire safety renewal required",
                "due_at": None,
                "status": "open",
                "verification_role_id": None,
                "created_at": datetime.now(timezone.utc),
                "version": 1,
            }
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur)

        req = CreateConditionRequest(
            institution_id=self.inst_id,
            application_id=self.app_id,
            condition_code="COND-01",
            description="Fire safety renewal required",
        )
        res = create_compliance_condition(req, self.request, self.subject)
        self.assertEqual(res["condition_code"], "COND-01")
        self.assertEqual(res["status"], "open")

    @patch("backend.app.compliance._user")
    def test_create_condition_requires_app_or_approval(self, mock_user):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        req = CreateConditionRequest(
            institution_id=self.inst_id,
            condition_code="COND-01",
            description="No source bound",
        )
        with self.assertRaises(HTTPException) as ctx:
            create_compliance_condition(req, self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("backend.app.compliance._read_connection")
    @patch("backend.app.compliance._user")
    def test_list_conditions(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchall_val=[
                {
                    "id": self.cond_id,
                    "institution_id": self.inst_id,
                    "application_id": self.app_id,
                    "source_approval_id": None,
                    "condition_code": "COND-01",
                    "description": "Fire safety",
                    "due_at": None,
                    "status": "open",
                    "verification_role_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "version": 1,
                }
            ]
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        res = list_compliance_conditions(self.request, self.subject, institution_id=self.inst_id)
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["condition_code"], "COND-01")

    @patch("backend.app.compliance._read_connection")
    @patch("backend.app.compliance._user")
    def test_get_condition_not_found(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(fetchone_val=None)
        mock_conn.return_value = nullcontext(MockConnection(cur))

        with self.assertRaises(HTTPException) as ctx:
            get_compliance_condition(self.cond_id, self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("backend.app.compliance.enqueue", return_value=None)
    @patch("backend.app.compliance.write_transaction")
    @patch("backend.app.compliance._user")
    def test_submit_evidence_success(self, mock_user, mock_tx, mock_enq):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[
                # 1. Condition lookup
                {"id": self.cond_id, "institution_id": self.inst_id, "application_id": self.app_id, "status": "open", "version": 1},
                # 2. Next sub num
                {"next_sub_num": 1},
                # 3. Document version check
                {"id": self.doc_ver_id},
                # 4. Insert submission
                {
                    "id": self.sub_id,
                    "compliance_condition_id": self.cond_id,
                    "submitted_by": self.caller_id,
                    "submitted_at": datetime.now(timezone.utc),
                    "submission_number": 1,
                    "status": "submitted",
                    "created_at": datetime.now(timezone.utc),
                },
            ]
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur)

        req = SubmitEvidenceRequest(
            document_version_ids=[self.doc_ver_id],
            remarks="Fire certificate uploaded",
        )
        res = submit_condition_evidence(self.cond_id, req, self.request, self.subject)
        self.assertEqual(res["submission_number"], 1)
        self.assertEqual(res["status"], "submitted")

    @patch("backend.app.compliance.enqueue", return_value=None)
    @patch("backend.app.compliance.write_transaction")
    @patch("backend.app.compliance._user")
    def test_verify_evidence_accepted(self, mock_user, mock_tx, mock_enq):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[
                # 1. Submission lookup
                {"id": self.sub_id, "compliance_condition_id": self.cond_id, "submitted_by": UUID(int=50), "status": "submitted"},
                # 2. Condition lookup
                {"id": self.cond_id, "status": "evidence_submitted", "version": 1},
                # Latest submission must match the requested version
                {"id": self.sub_id},
                # 3. Insert verification
                {
                    "id": UUID(int=7),
                    "evidence_submission_id": self.sub_id,
                    "reviewer_user_id": self.caller_id,
                    "result": "accepted",
                    "comments": "Certificate valid until 2028",
                    "verified_at": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc),
                },
            ]
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur)

        req = VerifyEvidenceRequest(
            result="accepted",
            comments="Certificate valid until 2028",
        )
        res = verify_evidence_submission(self.sub_id, req, self.request, self.subject)
        self.assertEqual(res["result"], "accepted")
        self.assertEqual(res["comments"], "Certificate valid until 2028")

    @patch("backend.app.compliance.enqueue", return_value=None)
    @patch("backend.app.compliance.write_transaction")
    @patch("backend.app.compliance._user")
    def test_close_and_reopen_condition(self, mock_user, mock_tx, mock_enq):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        now = datetime.now(timezone.utc)
        cur = MockCursor(
            fetchone_val=[
                # Close
                {"id": self.cond_id, "status": "compliant", "version": 2},
                {"id": self.cond_id, "status": "closed", "version": 3, "updated_at": now},
            ]
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur)

        close_req = CloseConditionRequest(reason="Condition fully met and closed")
        res_close = close_compliance_condition(self.cond_id, close_req, self.request, self.subject)
        self.assertEqual(res_close["status"], "closed")

        # Reopen
        cur2 = MockCursor(
            fetchone_val=[
                {"id": self.cond_id, "status": "closed", "version": 3},
                {"id": self.cond_id, "status": "reopened", "version": 4, "updated_at": now},
            ]
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur2)

        reopen_req = ReopenConditionRequest(reason="Audit finding necessitates re-verification")
        res_reopen = reopen_compliance_condition(self.cond_id, reopen_req, self.request, self.subject)
        self.assertEqual(res_reopen["status"], "reopened")
