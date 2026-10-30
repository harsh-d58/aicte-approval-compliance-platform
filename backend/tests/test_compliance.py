"""Unit tests for institutional compliance, evidence submissions, and officer verifications."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.compliance import (
    CloseConditionRequest,
    CreateConditionRequest,
    UpdateConditionRequest,
    ReopenConditionRequest,
    SubmitEvidenceRequest,
    VerifyEvidenceRequest,
    close_compliance_condition,
    create_compliance_condition,
    update_condition_requirements,
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
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        self.executed.append((sql,params))

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

    def condition_request(self, **changes):
        values={"institution_id":self.inst_id,"application_id":self.app_id,
                "condition_code":"COND-TEST","description":"Submit structural evidence"}
        return CreateConditionRequest(**{**values,**changes})

    def call_create_with_rows(self, payload, rows):
        cursor=MockCursor(fetchone_val=rows)
        with patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
             patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.compliance.enqueue"), patch("backend.app.compliance.append_event"):
            result=create_compliance_condition(payload,self.request,self.subject)
        return result,cursor

    def test_condition_due_dates_require_timezone_and_requirements_are_meaningful(self):
        with self.assertRaises(ValidationError):
            self.condition_request(due_at=datetime(2027,1,1))
        for values in (["   "],["PWD attestation","PWD attestation"],["x"*501]):
            with self.subTest(requirements=values),self.assertRaises(ValidationError):
                self.condition_request(evidence_requirements=values)

    def test_past_condition_deadline_is_rejected_before_insert(self):
        payload=self.condition_request(due_at=datetime.now(timezone.utc)-timedelta(minutes=1))
        with self.assertRaises(HTTPException) as caught:
            self.call_create_with_rows(payload,[{"id":self.app_id,"institution_id":self.inst_id,"status":"under_review","stage_type":"decision"}])
        self.assertEqual(caught.exception.status_code,422)

    def test_condition_cannot_bind_foreign_institution(self):
        with self.assertRaises(HTTPException) as caught:
            self.call_create_with_rows(self.condition_request(),[{
                "id":self.app_id,"institution_id":UUID(int=500),"status":"under_review","stage_type":"decision"}])
        self.assertEqual(caught.exception.status_code,422)

    def test_conditions_cannot_be_created_before_decision_or_after_closure(self):
        for status,stage in [("draft","intake"),("under_review","evc"),("closed","closure"),("rejected","decision")]:
            with self.subTest(status=status,stage=stage),self.assertRaises(HTTPException) as caught:
                self.call_create_with_rows(self.condition_request(),[{
                    "id":self.app_id,"institution_id":self.inst_id,"status":status,"stage_type":stage}])
            self.assertEqual(caught.exception.status_code,409)

    def test_source_approval_must_match_case_and_be_an_approval(self):
        for approval,expected in [
            ({"application_id":UUID(int=100),"decision_status":"approved","decision_type":"approve"},422),
            ({"application_id":self.app_id,"decision_status":"rejected","decision_type":"reject"},409),
            ({"application_id":self.app_id,"decision_status":"approved","decision_type":"close"},409),
        ]:
            with self.subTest(approval=approval),self.assertRaises(HTTPException) as caught:
                self.call_create_with_rows(self.condition_request(source_approval_id=UUID(int=200)),[approval])
            self.assertEqual(caught.exception.status_code,expected)

    def test_source_only_condition_derives_case_and_persists_requirements(self):
        approval_id=UUID(int=200)
        payload=self.condition_request(application_id=None,source_approval_id=approval_id,evidence_requirements=["PWD safety attestation"])
        created={"id":self.cond_id,"institution_id":self.inst_id,"application_id":self.app_id,
                 "source_approval_id":approval_id,"evidence_requirements":payload.evidence_requirements,"status":"open"}
        result,cursor=self.call_create_with_rows(payload,[
            {"application_id":self.app_id,"decision_status":"approved","decision_type":"approval"},
            {"id":self.app_id,"institution_id":self.inst_id,"status":"approved","stage_type":"decision"},created])
        self.assertEqual(result["application_id"],str(self.app_id))
        inserted=next(params for sql,params in cursor.executed if "INSERT INTO public.compliance_conditions" in sql)
        self.assertEqual(inserted[2],self.app_id)
        self.assertEqual(inserted[3],approval_id)
        self.assertEqual(inserted[6].obj,["PWD safety attestation"])
        self.assertTrue(any("FOR UPDATE OF a" in sql for sql,_ in cursor.executed))

    def test_new_condition_on_approved_case_links_existing_approval(self):
        approval_id=UUID(int=201)
        _,cursor=self.call_create_with_rows(self.condition_request(),[
            {"id":self.app_id,"institution_id":self.inst_id,"status":"approved","stage_type":"decision"},
            {"id":approval_id},{"id":self.cond_id,"status":"open"}])
        inserted=next(params for sql,params in cursor.executed if "INSERT INTO public.compliance_conditions" in sql)
        self.assertEqual(inserted[3],approval_id)

    def test_idempotent_bodies_bind_each_compliance_resource(self):
        for operation,ident,payload,key in [
            (submit_condition_evidence,self.cond_id,SubmitEvidenceRequest(document_version_ids=[self.doc_ver_id]),"condition_id"),
            (verify_evidence_submission,self.sub_id,VerifyEvidenceRequest(result="accepted",comments="Verified current evidence"),"submission_id"),
            (close_compliance_condition,self.cond_id,CloseConditionRequest(reason="Verified condition fulfilled"),"condition_id"),
            (reopen_compliance_condition,self.cond_id,ReopenConditionRequest(reason="Audit requires reopening"),"condition_id"),
        ]:
            cursor=MockCursor()
            with self.subTest(operation=operation.__name__), \
                 patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
                 patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cursor))), \
                 patch("backend.app.compliance.find_result",return_value=(200,{"cached":True})) as cached:
                self.assertEqual(operation(ident,payload,self.request,self.subject,idempotency_key="resource-specific-key"),{"cached":True})
                self.assertEqual(cached.call_args.kwargs["body"][key],str(ident))

    def test_draft_condition_requirement_correction_is_versioned_and_audited(self):
        cursor=MockCursor(fetchone_val=[
            {"application_id":self.app_id},
            {"id":self.app_id,"status":"under_review","stage_type":"decision"},
            {"id":self.cond_id,"application_id":self.app_id,"source_approval_id":None,"evidence_requirements":[],"version":1},
            {"id":self.cond_id,"evidence_requirements":["PWD attestation","Geotagged photographs"],"version":2,"updated_at":datetime.now(timezone.utc)}])
        payload=UpdateConditionRequest(evidence_requirements=[" PWD attestation ","Geotagged photographs"],expected_version=1,reason="Restore requirements from the submitted form")
        with patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
             patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.compliance.append_event") as audit,patch("backend.app.compliance.enqueue") as outbox:
            result=update_condition_requirements(self.cond_id,payload,self.request,self.subject)
        self.assertEqual(result["version"],2)
        self.assertEqual(result["evidence_requirements"],["PWD attestation","Geotagged photographs"])
        self.assertEqual(audit.call_args.kwargs["metadata"]["previous_requirements"],[])
        self.assertEqual(audit.call_args.kwargs["metadata"]["new_version"],2)
        self.assertEqual(outbox.call_args.kwargs["event_type"],"CONDITION_REQUIREMENTS_UPDATED")
        locks=[sql for sql,_ in cursor.executed if 'FOR UPDATE' in sql]
        self.assertIn('FOR UPDATE OF a',locks[0])
        self.assertIn('compliance_conditions',locks[1])

    def test_requirement_correction_cannot_change_an_approved_application(self):
        cursor=MockCursor(fetchone_val=[{"application_id":self.app_id},{"id":self.app_id,"status":"approved","stage_type":"decision"}])
        with patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
             patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.compliance.append_event") as audit:
            with self.assertRaises(HTTPException) as caught:
                update_condition_requirements(self.cond_id,UpdateConditionRequest(evidence_requirements=["New requirement"],expected_version=1,reason="Attempt postapproval correction"),self.request,self.subject)
        self.assertEqual(caught.exception.status_code,409)
        audit.assert_not_called()

    def test_requirement_correction_rejects_stale_or_linked_condition(self):
        for linked,version,expected in [(UUID(int=100),1,409),(None,2,412)]:
            cursor=MockCursor(fetchone_val=[{"application_id":self.app_id},
                {"id":self.app_id,"status":"under_review","stage_type":"decision"},
                {"id":self.cond_id,"application_id":self.app_id,"source_approval_id":linked,"evidence_requirements":[],"version":version}])
            with self.subTest(linked=linked,version=version), \
                 patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
                 patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cursor))), \
                 patch("backend.app.compliance.append_event") as audit:
                with self.assertRaises(HTTPException) as caught:
                    update_condition_requirements(self.cond_id,UpdateConditionRequest(evidence_requirements=["Updated requirement"],expected_version=1,reason="Correct prior requirements"),self.request,self.subject)
                self.assertEqual(caught.exception.status_code,expected)
                audit.assert_not_called()

    def test_requirement_correction_replay_binds_resource_and_skips_writes(self):
        cursor=MockCursor()
        with patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
             patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.compliance.find_result",return_value=(200,{"version":2})) as cached:
            result=update_condition_requirements(self.cond_id,UpdateConditionRequest(evidence_requirements=["Requirement"],expected_version=1,reason="Replay original correction"),self.request,self.subject,idempotency_key="correction-key")
        self.assertEqual(result,{"version":2})
        self.assertEqual(cached.call_args.kwargs["body"]["condition_id"],str(self.cond_id))
        self.assertFalse(cursor.executed)

    def test_closure_requires_verified_compliance(self):
        cur = MockCursor(fetchone_val={"id": self.cond_id, "status": "evidence_submitted", "version": 1})
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                close_compliance_condition(self.cond_id, CloseConditionRequest(reason="Attempt premature closure"), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertFalse(cur.sql.startswith("UPDATE"))

    def test_reopen_requires_closed_condition(self):
        cur = MockCursor(fetchone_val=[{"application_id":self.app_id},{"id":self.app_id,"status":"approved"},{"id": self.cond_id, "status": "open", "version": 1}])
        with patch("backend.app.compliance._user", return_value={"id": self.caller_id, "subject": self.subject}), \
             patch("backend.app.compliance.write_transaction", return_value=nullcontext(MockConnection(cur))):
            with self.assertRaises(HTTPException) as ctx:
                reopen_compliance_condition(self.cond_id, ReopenConditionRequest(reason="Attempt invalid reopening"), self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_closed_application_must_reopen_before_its_condition(self):
        cur=MockCursor(fetchone_val=[{"application_id":self.app_id},{"id":self.app_id,"status":"closed"}])
        with patch("backend.app.compliance._user",return_value={"id":self.caller_id,"subject":self.subject}), \
             patch("backend.app.compliance.write_transaction",return_value=nullcontext(MockConnection(cur))), \
             patch("backend.app.compliance.append_event") as audit:
            with self.assertRaises(HTTPException) as caught:
                reopen_compliance_condition(self.cond_id,ReopenConditionRequest(reason="Attempt to reopen condition after case closure"),self.request,self.subject)
        self.assertEqual(caught.exception.status_code,409)
        self.assertEqual(caught.exception.detail,"Reopen the application before reopening this condition")
        self.assertFalse(any(sql.startswith("UPDATE") for sql,_ in cur.executed))
        audit.assert_not_called()

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

    @patch("backend.app.compliance.enqueue", return_value=None)
    @patch("backend.app.compliance.write_transaction")
    @patch("backend.app.compliance._user")
    def test_create_condition_success(self, mock_user, mock_tx, mock_enqueue):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[{"id": self.app_id,"institution_id": self.inst_id,"status":"under_review","stage_type":"decision"}, {
                "id": self.cond_id,
                "institution_id": self.inst_id,
                "application_id": self.app_id,
                "source_approval_id": None,
                "condition_code": "COND-01",
                "description": "Fire safety renewal required",
                "evidence_requirements": ["PWD attestation", "Geotagged photographs"],
                "due_at": None,
                "status": "open",
                "verification_role_id": None,
                "created_at": datetime.now(timezone.utc),
                "version": 1,
            }]
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur)

        req = CreateConditionRequest(
            institution_id=self.inst_id,
            application_id=self.app_id,
            condition_code="COND-01",
            description="Fire safety renewal required",
            evidence_requirements=[" PWD attestation ", "Geotagged photographs"],
        )
        res = create_compliance_condition(req, self.request, self.subject)
        self.assertEqual(res["condition_code"], "COND-01")
        self.assertEqual(res["status"], "open")
        self.assertEqual(res["evidence_requirements"],["PWD attestation","Geotagged photographs"])
        inserted = next(params for sql,params in cur.executed if "INSERT INTO public.compliance_conditions" in sql)
        self.assertEqual(inserted[6].obj,["PWD attestation","Geotagged photographs"])

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
                {"application_id":self.app_id},
                {"id":self.app_id,"status":"approved"},
                {"id": self.cond_id, "status": "closed", "version": 3},
                {"id": self.cond_id, "status": "reopened", "version": 4, "updated_at": now},
            ]
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur2)

        reopen_req = ReopenConditionRequest(reason="Audit finding necessitates re-verification")
        res_reopen = reopen_compliance_condition(self.cond_id, reopen_req, self.request, self.subject)
        self.assertEqual(res_reopen["status"], "reopened")
