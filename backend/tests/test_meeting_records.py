"""Unit tests for Meeting-to-Record Assistant, observations, draft generation, and human approval."""

from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.meeting_records import (
    ApproveMeetingRecordRequest,
    CreateObservationRequest,
    GenerateMeetingDraftRequest,
    RequestChangesRequest,
    approve_meeting_record,
    generate_meeting_record_draft,
    get_meeting_record,
    list_committee_observations,
    list_meeting_record_sources,
    record_committee_observation,
    request_meeting_record_changes,
    submit_meeting_record_for_review,
    _advance_evc_to_decision,
    _require_record_reviewer,
)
from backend.app.settings import Settings


class MockCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.fetchone_val = fetchone_val
        self.fetchall_val = fetchall_val or []
        self.sql = ""
        self.params = None
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        self.calls.append((sql,params))

    def fetchone(self):
        if isinstance(self.fetchone_val, list):
            return self.fetchone_val.pop(0) if self.fetchone_val else None
        return self.fetchone_val

    def fetchall(self):
        if self.fetchall_val and isinstance(self.fetchall_val[0],list):
            return self.fetchall_val.pop(0)
        return self.fetchall_val


class MockConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor


class MeetingRecordRouteTests(TestCase):
    def setUp(self):
        review=patch('backend.app.meeting_records._require_record_reviewer')
        self.review=review.start()
        self.addCleanup(review.stop)
        self.visit_id = UUID(int=1)
        self.report_id = UUID(int=2)
        self.version_id = UUID(int=3)
        self.observation_id = UUID(int=4)
        self.caller_id = UUID(int=99)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=999))),
        )
        sections=[{"criterion":"INFRA-01","text":"Good labs","source_id":str(self.observation_id)}]
        self.manifest={"sections":sections,"sources":[{"id":str(self.observation_id)}],
            "content_sha256":hashlib.sha256(json.dumps(sections,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}
        self.caller_row = {
            "id": self.caller_id,
            "display_name": "Committee Convener",
            "email": "convener@example.com",
            "status": "active",
        }

    def test_record_committee_observation_success(self):
        payload = CreateObservationRequest(
            criterion_code="INFRA-01",
            observation_text="Computer center has 120 functioning terminals with licensed OS",
            source_type="site_inspection",
        )
        visit_row = {"id": self.visit_id, "status": "scheduled"}
        obs_row = {
            "id": self.observation_id,
            "evc_visit_id": self.visit_id,
            "criterion_code": "INFRA-01",
            "observation_text": payload.observation_text,
            "source_type": "site_inspection",
            "review_status": "draft",
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[visit_row, obs_row])

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.meeting_records.append_event", return_value=None), \
             patch("backend.app.meeting_records.enqueue", return_value=None):
            res = record_committee_observation(self.visit_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.observation_id)
        self.assertEqual(res["criterion_code"], "INFRA-01")

    def test_list_committee_observations(self):
        observations = [
            {
                "id": self.observation_id,
                "evc_visit_id": self.visit_id,
                "criterion_code": "INFRA-01",
                "observation_text": "Good labs",
                "source_type": "site_inspection",
                "review_status": "draft",
                "created_at": "2026-10-29T00:00:00Z",
                "expert_name": "Dr. Sharma",
            }
        ]
        cursor = MockCursor(fetchall_val=observations)

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_committee_observations(self.visit_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["criterion_code"], "INFRA-01")

    def test_generate_meeting_record_draft_success(self):
        payload = GenerateMeetingDraftRequest(template_version="EVC-2026.1", record_type="minutes")
        visit_row = {"id": self.visit_id, "status": "completed"}
        obs_list = [{"id": self.observation_id, "criterion_code": "INFRA-01", "observation_text": "Good"}]
        report_row = {"id": self.report_id}
        ver_num_row = {"next_ver": 1}
        ver_row = {
            "id": self.version_id,
            "evc_report_id": self.report_id,
            "record_type": "minutes",
            "version_number": 1,
            "content_reference": "reports/report_1/minutes_v1.json",
            "source_manifest": {},
            "approval_status": "draft",
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[visit_row, report_row, ver_num_row, ver_row], fetchall_val=obs_list)

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.meeting_records.append_event", return_value=None), \
             patch("backend.app.meeting_records.enqueue", return_value=None):
            res = generate_meeting_record_draft(self.visit_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["report_id"], self.report_id)
        self.assertEqual(res["record_version"]["version_number"], 1)
        self.assertEqual(res["record_version"]["approval_status"], "draft")
        inserts=[params for sql,params in cursor.calls if 'INSERT INTO public.meeting_record_versions' in sql]
        persisted=inserts[0][5].obj
        self.assertEqual(persisted['sections'][0]['text'],'Good')
        self.assertEqual(persisted['sections'][0]['source_id'],str(self.observation_id))
        self.assertTrue(inserts[0][4].startswith('urn:meeting-record-version:'))
        source_query=next(sql for sql,_ in cursor.calls if 'FROM public.evc_observations' in sql)
        self.assertIn("review_status='submitted'",source_query)

    def test_get_meeting_record_success(self):
        report = {
            "id": self.report_id,
            "evc_visit_id": self.visit_id,
            "report_status": "draft",
            "template_version": "EVC-2026.1",
            "current_version_id": self.version_id,
            "approved_by": None,
            "approved_at": None,
            "created_at": "2026-10-29T00:00:00Z",
            "record_type": "minutes",
            "version_number": 1,
            "content_reference": "reports/report_1/minutes_v1.json",
            "source_manifest": {},
            "approval_status": "draft",
        }
        cursor = MockCursor(fetchone_val=report)

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = get_meeting_record(self.report_id, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.report_id)
        self.assertEqual(res["approval_status"], "draft")

    def test_approve_meeting_record_success(self):
        payload = ApproveMeetingRecordRequest(reason="Formal convener approval")
        report_row = {"id": self.report_id, "current_version_id": self.version_id, "report_status": "pending_approval", "approval_status":"pending_approval", "record_type":"minutes", "source_manifest":self.manifest}
        approved_version = {
            "id": self.version_id,
            "approval_status": "approved",
            "approved_by": self.caller_id,
            "approved_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[report_row, approved_version])

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.meeting_records.append_event", return_value=None), \
             patch("backend.app.meeting_records.enqueue", return_value=None):
            res = approve_meeting_record(self.report_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["approval_status"], "approved")
        self.assertFalse(any('UPDATE public.applications' in sql for sql,_ in cursor.calls))

    def test_foreign_or_draft_source_selection_is_rejected(self):
        cursor=MockCursor(fetchone_val={'id':self.visit_id,'status':'completed'},fetchall_val=[])
        with patch('backend.app.meeting_records._user',return_value=self.caller_row), \
             patch('backend.app.meeting_records.write_transaction',return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as caught:
                generate_meeting_record_draft(self.visit_id,GenerateMeetingDraftRequest(source_ids=[self.observation_id]),self.request,str(self.caller_id))
        self.assertEqual(caught.exception.status_code,422)
        self.assertFalse(any('INSERT' in sql for sql,_ in cursor.calls))

    def test_draft_cannot_be_approved_before_review(self):
        cursor=MockCursor(fetchone_val={'approval_status':'draft'})
        with patch('backend.app.meeting_records._user',return_value=self.caller_row), \
             patch('backend.app.meeting_records.write_transaction',return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as caught:
                approve_meeting_record(self.report_id,ApproveMeetingRecordRequest(),self.request,str(self.caller_id))
        self.assertEqual(caught.exception.status_code,409)

    def test_expert_member_cannot_issue_convener_approval(self):
        cursor=MockCursor(fetchall_val=[{'role_code':'EVC_EXPERT'}],fetchone_val={'authorised':False})
        with self.assertRaises(HTTPException) as caught:
            _require_record_reviewer(cursor,{'evc_visit_id':self.visit_id},self.caller_id)
        self.assertEqual(caught.exception.status_code,403)

    def test_changed_persisted_sections_cannot_be_approved(self):
        self.manifest['sections'][0]['text']='Changed after generation'
        cursor=MockCursor(fetchone_val={'id':self.report_id,'approval_status':'pending_approval','source_manifest':self.manifest})
        with patch('backend.app.meeting_records._user',return_value=self.caller_row), \
             patch('backend.app.meeting_records.write_transaction',return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as caught:
                approve_meeting_record(self.report_id,ApproveMeetingRecordRequest(),self.request,str(self.caller_id))
        self.assertEqual(caught.exception.status_code,409)

    def transition_cursor(self, completed):
        app={'id':UUID(int=10),'status':'under_review','stage_type':'evc',
             'current_stage_instance_id':UUID(int=11),'workflow_stage_id':UUID(int=12),
             'workflow_definition_id':UUID(int=13)}
        edge={'to_stage_id':UUID(int=14),'guard_rule':{'require_approved_meeting_record':True},'default_sla_days':7}
        return MockCursor(fetchone_val=[app,{'count':0},{'completed':completed},{'id':UUID(int=15)}],
                          fetchall_val=[[edge],[{'role_code':'REGIONAL'}]])

    def test_evc_report_cannot_advance_before_visit_completion(self):
        cursor=self.transition_cursor(False)
        with self.assertRaises(HTTPException) as caught:
            _advance_evc_to_decision(cursor,{'id':self.report_id,'evc_visit_id':self.visit_id},self.caller_id,
                                    datetime.now(timezone.utc),'Approve',None)
        self.assertEqual(caught.exception.status_code,409)
        self.assertFalse(any('UPDATE public.applications' in sql for sql,_ in cursor.calls))

    def test_completed_evc_uses_configured_transition_and_records_history(self):
        cursor=self.transition_cursor(True)
        with patch('backend.app.meeting_records.append_event') as audit,patch('backend.app.meeting_records.enqueue'):
            _advance_evc_to_decision(cursor,{'id':self.report_id,'evc_visit_id':self.visit_id},self.caller_id,
                                    datetime.now(timezone.utc),'Approve',None)
        update=next(params for sql,params in cursor.calls if 'UPDATE public.applications' in sql)
        self.assertEqual(update[0],UUID(int=15))
        self.assertTrue(any('INSERT INTO public.stage_history' in sql for sql,_ in cursor.calls))
        audit.assert_called_once()

    def test_approve_meeting_record_already_approved_raises_409(self):
        payload = ApproveMeetingRecordRequest(reason="Double approval test")
        report_row = {"id": self.report_id, "current_version_id": self.version_id, "report_status": "approved", "approval_status":"approved"}
        cursor = MockCursor(fetchone_val=[report_row])

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                approve_meeting_record(self.report_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_request_meeting_record_changes(self):
        payload = RequestChangesRequest(comments="Revise laboratory capacity numbers", reason="Correction needed")
        report_row = {"id":self.report_id,"current_version_id": self.version_id, "approval_status":"pending_approval"}
        updated_ver = {"id": self.version_id, "approval_status": "draft"}
        cursor = MockCursor(fetchone_val=[report_row, updated_ver])

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.meeting_records.append_event"):
            res = request_meeting_record_changes(self.report_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["approval_status"], "draft")

    def test_list_meeting_record_sources(self):
        sources = [
            {"id": UUID(int=50), "meeting_record_version_id": self.version_id, "source_type": "evc_observation", "source_id": self.observation_id, "section_reference": "INFRA-01", "observation_text": "Good", "criterion_code": "INFRA-01"},
        ]
        cursor = MockCursor(fetchall_val=sources)

        with patch("backend.app.meeting_records._user", return_value=self.caller_row), \
             patch("backend.app.meeting_records._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_meeting_record_sources(self.report_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["section_reference"], "INFRA-01")
