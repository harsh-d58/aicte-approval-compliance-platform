"""Unit tests for statutory decisions and human authority governance."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.concurrency import StaleVersion
from backend.app.decisions import (
    CreateDecisionRequest,
    list_application_decisions,
    record_statutory_decision,
)
from backend.app.settings import Settings
from backend.app.decision_lifecycle import decision_outcome, check_decision_prerequisites


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
        self.executed.append((sql, params))

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


class DecisionRouteTests(TestCase):
    def setUp(self):
        self.app_id = UUID(int=1)
        self.decision_id = UUID(int=2)
        self.caller_id = UUID(int=3)
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
            "display_name": "Executive Committee Chair",
            "email": "chair@example.com",
            "status": "active",
        }

    def test_record_statutory_decision_approval_keeps_application_open_for_conditions(self):
        payload = CreateDecisionRequest(
            decision_type="approval",
            decision_status="approved",
            decision_authority="Executive Committee",
            reason="All statutory norms and infrastructure verified compliant",
            expected_version=3,
        )
        app_row = {"id": self.app_id, "application_number": "APP-2026-ABCD", "status": "under_review", "stage_type":"decision", "workflow_definition_id":UUID(int=7), "institution_id":UUID(int=8)}
        decision_row = {
            "id": self.decision_id,
            "application_id": self.app_id,
            "decision_type": "approval",
            "decision_status": "approved",
            "decision_authority": "Executive Committee",
            "decision_at": "2026-10-29T00:00:00Z",
            "reason": payload.reason,
            "record_document_id": None,
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[app_row, {"count":0}, {"required":False}, decision_row])

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.decisions.lock_versioned", return_value=None), \
             patch("backend.app.decisions.bump_version", return_value=4), \
             patch("backend.app.decisions.append_event", return_value=None), \
             patch("backend.app.decisions.enqueue", return_value=None):
            res = record_statutory_decision(self.app_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.decision_id)
        self.assertEqual(res["decision_status"], "approved")
        self.assertEqual(res["application_version"], 4)
        status_updates = [params for sql, params in cursor.executed if "SET status = %s, closed_at" in sql]
        self.assertEqual(len(status_updates), 1)
        self.assertEqual(status_updates[0][0], "approved")
        self.assertIsNone(status_updates[0][1])
        link = next(params for sql,params in cursor.executed if 'SET source_approval_id' in sql)
        self.assertEqual(link[0],self.decision_id)
        self.assertEqual(link[3],self.app_id)

    def test_record_statutory_decision_stale_version_raises_412(self):
        payload = CreateDecisionRequest(
            decision_type="approval",
            decision_status="approved",
            decision_authority="Executive Committee",
            reason="Version conflict test",
            expected_version=1,
        )
        cursor = MockCursor()

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.decisions.lock_versioned", side_effect=StaleVersion("Stale")):
            with self.assertRaises(HTTPException) as ctx:
                record_statutory_decision(self.app_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 412)

    def test_record_statutory_decision_already_closed_raises_409(self):
        payload = CreateDecisionRequest(
            decision_type="approval",
            decision_status="approved",
            decision_authority="Executive Committee",
            reason="Already approved test",
            expected_version=3,
        )
        app_row = {"id": self.app_id, "application_number": "APP-2026-ABCD", "status": "approved"}
        cursor = MockCursor(fetchone_val=[app_row])

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.decisions.lock_versioned", return_value=None), \
             patch("backend.app.decisions.bump_version", return_value=4):
            with self.assertRaises(HTTPException) as ctx:
                record_statutory_decision(self.app_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_list_application_decisions(self):
        decisions = [
            {
                "id": self.decision_id,
                "application_id": self.app_id,
                "decision_type": "approval",
                "decision_status": "approved",
                "decision_authority": "Executive Committee",
                "decision_at": "2026-10-29T00:00:00Z",
                "reason": "Approved",
                "record_document_id": None,
                "created_at": "2026-10-29T00:00:00Z",
            }
        ]
        cursor = MockCursor(fetchall_val=decisions)

        with patch("backend.app.decisions._user", return_value=self.caller_row), \
             patch("backend.app.decisions._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_application_decisions(self.app_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["decision_type"], "approval")

    def test_close_approved_case_records_distinct_closure_and_preserves_approval(self):
        payload=CreateDecisionRequest(decision_type='close',decision_status='approved',decision_authority='Regional authority',reason='All undertakings independently verified and closed',expected_version=4)
        cursor=MockCursor(fetchone_val=[{'id':self.app_id,'application_number':'CASE','status':'approved'},
            {'id':self.decision_id,'decision_type':'close','decision_status':'approved'}],fetchall_val=[{'id':UUID(int=50),'status':'closed'}])
        with patch('backend.app.decisions._user',return_value=self.caller_row),patch('backend.app.decisions.write_transaction',return_value=nullcontext(MockConnection(cursor))),patch('backend.app.decisions.lock_versioned'),patch('backend.app.decisions.bump_version',return_value=5),patch('backend.app.decisions.append_event') as audit,patch('backend.app.decisions.enqueue') as outbox:
            result=record_statutory_decision(self.app_id,payload,self.request,str(self.caller_id))
        self.assertEqual(result['application_status'],'closed')
        update=next(params for sql,params in cursor.executed if 'SET status = %s, closed_at' in sql)
        self.assertEqual(update[0],'closed')
        self.assertIsNotNone(update[1])
        self.assertEqual(audit.call_args.kwargs['action'],'APPLICATION_CLOSED')
        self.assertEqual(outbox.call_args.kwargs['event_type'],'APPLICATION_CLOSED')
        self.assertFalse(any('UPDATE public.approval_decisions' in sql for sql,_ in cursor.executed))

    def test_unclosed_condition_blocks_case_closure_without_writes(self):
        payload=CreateDecisionRequest(decision_type='close',decision_status='approved',decision_authority='Regional authority',reason='Attempt premature closure',expected_version=4)
        cursor=MockCursor(fetchone_val={'id':self.app_id,'status':'approved'},fetchall_val=[{'id':UUID(int=50),'status':'compliant'}])
        with patch('backend.app.decisions._user',return_value=self.caller_row),patch('backend.app.decisions.write_transaction',return_value=nullcontext(MockConnection(cursor))),patch('backend.app.decisions.lock_versioned'),patch('backend.app.decisions.bump_version') as bump,patch('backend.app.decisions.append_event') as audit:
            with self.assertRaises(HTTPException) as raised:
                record_statutory_decision(self.app_id,payload,self.request,str(self.caller_id))
        self.assertEqual(raised.exception.status_code,409)
        bump.assert_not_called();audit.assert_not_called()
        self.assertFalse(any(sql.lstrip().startswith(('INSERT','UPDATE','DELETE')) for sql,_ in cursor.executed))

    def test_reject_never_updates_application_as_approved(self):
        payload=CreateDecisionRequest(decision_type='reject',decision_status='rejected',decision_authority='Regional authority',reason='Statutory reasons recorded',expected_version=4)
        cursor=MockCursor(fetchone_val=[{'id':self.app_id,'application_number':'CASE','status':'under_review','stage_type':'decision','workflow_definition_id':UUID(int=7)}, {'count':0},{'required':False},{'id':self.decision_id,'decision_type':'reject','decision_status':'rejected'}])
        with patch('backend.app.decisions._user',return_value=self.caller_row),patch('backend.app.decisions.write_transaction',return_value=nullcontext(MockConnection(cursor))),patch('backend.app.decisions.lock_versioned'),patch('backend.app.decisions.bump_version',return_value=5),patch('backend.app.decisions.append_event'),patch('backend.app.decisions.enqueue'):
            result=record_statutory_decision(self.app_id,payload,self.request,str(self.caller_id))
        self.assertEqual(result['application_status'],'rejected')
        self.assertEqual(next(params[0] for sql,params in cursor.executed if 'SET status = %s, closed_at' in sql),'rejected')

    def test_outcome_aliases_and_status_pairing(self):
        self.assertEqual(decision_outcome('approval','approved'),('approve','approved'))
        self.assertEqual(decision_outcome('CLOSE','approved'),('close','closed'))
        self.assertEqual(decision_outcome('reject','draft'),('reject',None))
        for kind,status in [('reject','approved'),('close','rejected'),('approve','withdrawn')]:
            with self.subTest(kind=kind),self.assertRaises(HTTPException) as raised:
                decision_outcome(kind,status)
            self.assertEqual(raised.exception.status_code,422)

    def test_decision_requires_configured_decision_stage(self):
        with self.assertRaises(HTTPException) as raised:
            check_decision_prerequisites(MockCursor(),{'id':self.app_id,'status':'under_review','stage_type':'evc'},'approve','approved')
        self.assertEqual(raised.exception.status_code,409)

    def test_workflow_without_evc_does_not_require_unconfigured_inspection(self):
        cur=MockCursor(fetchone_val=[{'count':0},{'required':False}])
        check_decision_prerequisites(cur,{'id':self.app_id,'status':'under_review','stage_type':'decision','workflow_definition_id':UUID(int=7)},'approve','approved')
        self.assertFalse(any('FROM public.evc_visits' in sql for sql,_ in cur.executed))

    def test_approved_minutes_or_uncompleted_visit_cannot_satisfy_evc_requirement(self):
        cur=MockCursor(fetchone_val=[{'count':0},{'required':True},{'ready':False}])
        with self.assertRaises(HTTPException) as raised:
            check_decision_prerequisites(cur,{'id':self.app_id,'status':'under_review','stage_type':'decision','workflow_definition_id':UUID(int=7)},'approve','approved')
        self.assertEqual(raised.exception.status_code,409)
        readiness_sql=cur.executed[-1][0]
        self.assertIn("m.record_type='evc_report'",readiness_sql)
        self.assertIn("v.status='completed'",readiness_sql)

    def test_retry_key_is_bound_to_application_id(self):
        payload=CreateDecisionRequest(decision_type='approve',decision_status='approved',decision_authority='Regional authority',reason='Approved after review',expected_version=4)
        with patch('backend.app.decisions._user',return_value=self.caller_row),patch('backend.app.decisions._read_connection',return_value=nullcontext(MockConnection(MockCursor()))),patch('backend.app.decisions.find_result',return_value=(201,{'id':'prior'})) as cached:
            result=record_statutory_decision(self.app_id,payload,self.request,str(self.caller_id),idempotency_key='retry')
        self.assertEqual(result,{'id':'prior'})
        self.assertEqual(cached.call_args.kwargs['body']['application_id'],str(self.app_id))
