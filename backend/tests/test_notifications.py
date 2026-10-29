"""Unit tests for notifications, delivery attempts, retries, and escalation rules."""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.notifications import (
    CreateEscalationRuleRequest,
    CreateNotificationRequest,
    ResolveEscalationRequest,
    RetryNotificationRequest,
    create_escalation_rule,
    get_notification,
    list_escalation_events,
    list_escalation_rules,
    list_notifications,
    process_notification_outbox,
    queue_notification,
    resolve_escalation_event,
    retry_notification_delivery,
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
        if isinstance(self.fetchall_val, list) and self.fetchall_val and isinstance(self.fetchall_val[0], list):
            return self.fetchall_val.pop(0)
        return self.fetchall_val


class MockConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor


class NotificationRouteTests(TestCase):
    def test_simulation_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            RetryNotificationRequest(channel='email', simulate_failure=True)

    def setUp(self):
        self.notif_id = UUID(int=1)
        self.recipient_id = UUID(int=2)
        self.caller_id = UUID(int=3)
        self.role_id = UUID(int=4)
        self.event_id = UUID(int=5)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=99))),
        )
        self.subject = "test-subject"
        for name in ('notification_authority', 'append_event'):
            patched = patch('backend.app.notifications.' + name)
            patched.start()
            self.addCleanup(patched.stop)

    @patch("backend.app.notifications.enqueue", return_value=None)
    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_queue_notification_success(self, mock_user, mock_tx, mock_enq):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[
                # Recipient check
                {"id": self.recipient_id},
                # Insert notification
                {
                    "id": self.notif_id,
                    "event_code": "DEFICIENCY_NOTICE_ISSUED",
                    "recipient_user_id": self.recipient_id,
                    "related_entity_type": "deficiency_notice",
                    "related_entity_id": UUID(int=10),
                    "created_at": datetime.now(timezone.utc),
                    "status": "queued",
                    "payload": {"title": "Deficiency Notice"},
                },
            ]
        )
        mock_tx.return_value.__enter__.return_value = cur

        req = CreateNotificationRequest(
            event_code="DEFICIENCY_NOTICE_ISSUED",
            recipient_user_id=self.recipient_id,
            related_entity_type="deficiency_notice",
            related_entity_id=UUID(int=10),
            payload={"title": "Deficiency Notice"},
        )
        res = queue_notification(req, self.request, self.subject)
        self.assertEqual(res["event_code"], "DEFICIENCY_NOTICE_ISSUED")
        self.assertEqual(res["status"], "queued")

    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_queue_notification_recipient_not_found(self, mock_user, mock_tx):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(fetchone_val=None)
        mock_tx.return_value.__enter__.return_value = cur

        req = CreateNotificationRequest(
            event_code="DEFICIENCY_NOTICE_ISSUED",
            recipient_user_id=self.recipient_id,
        )
        with self.assertRaises(HTTPException) as ctx:
            queue_notification(req, self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("backend.app.notifications._read_connection")
    @patch("backend.app.notifications._user")
    def test_get_notification(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val={
                "id": self.notif_id,
                "event_code": "DEFICIENCY_NOTICE_ISSUED",
                "recipient_user_id": self.recipient_id,
                "related_entity_type": None,
                "related_entity_id": None,
                "created_at": datetime.now(timezone.utc),
                "status": "sent",
                "payload": {},
            },
            fetchall_val=[
                {
                    "id": UUID(int=20),
                    "notification_id": self.notif_id,
                    "channel": "email",
                    "attempt_number": 1,
                    "attempted_at": datetime.now(timezone.utc),
                    "result": "success",
                    "provider_reference": "gw_email_1234",
                    "failure_reason": None,
                    "created_at": datetime.now(timezone.utc),
                }
            ],
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        res = get_notification(self.notif_id, self.request, self.subject)
        self.assertEqual(res["status"], "sent")
        self.assertEqual(len(res["attempts"]), 1)
        self.assertEqual(res["attempts"][0]["result"], "success")

    @patch("backend.app.notifications.refresh_notification")
    @patch("backend.app.notifications.queue_jobs")
    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_retry_queues_without_fabricated_attempt(self, user, tx, queue, refresh):
        user.return_value = {"id":self.caller_id,"subject":self.subject}
        cur=MockCursor(fetchone_val=[{"id":self.notif_id,"status":"failed"},
            {"id":UUID(int=30),"status":"failed","attempt_count":2}])
        tx.return_value.__enter__.return_value=cur
        res=retry_notification_delivery(self.notif_id,RetryNotificationRequest(channel="email"),self.request,self.subject)
        self.assertEqual(res["status"],"queued")
        self.assertNotIn("attempt_number",res)
        queue.assert_called_once_with(cur,self.notif_id,["email"])

    @patch("backend.app.notifications.queue_jobs")
    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_retry_unknown_requires_reconciliation(self,user,tx,queue):
        user.return_value={"id":self.caller_id,"subject":self.subject}
        cur=MockCursor(fetchone_val=[{"id":self.notif_id,"status":"failed"},
            {"id":UUID(int=30),"status":"unknown","attempt_count":2}])
        tx.return_value.__enter__.return_value=cur
        with self.assertRaises(HTTPException) as caught:
            retry_notification_delivery(self.notif_id,RetryNotificationRequest(channel="sms"),self.request,self.subject)
        self.assertEqual(caught.exception.status_code,409)

    @patch("backend.app.notifications.queue_jobs")
    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_process_outbox_only_queues_handoffs(self,user,tx,queue):
        user.return_value={"id":self.caller_id,"subject":self.subject}
        cur=MockCursor(fetchall_val=[{"id":self.notif_id}])
        tx.return_value.__enter__.return_value=cur
        res=process_notification_outbox(self.request,self.subject,limit=10)
        self.assertEqual(res["queued_count"],1)
        self.assertEqual(res["notification_ids"],[str(self.notif_id)])
        queue.assert_called_once_with(cur,self.notif_id)

    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_create_escalation_rule(self, mock_user, mock_tx):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[
                # Role lookup
                {"id": self.role_id},
                # Insert rule
                {
                    "id": UUID(int=40),
                    "event_code": "DEFICIENCY_OVERDUE",
                    "threshold_minutes": 1440,
                    "recipient_role_id": self.role_id,
                    "action_type": "notify_regional_officer",
                    "enabled": True,
                    "version": 1,
                    "created_at": datetime.now(timezone.utc),
                },
            ]
        )
        mock_tx.return_value.__enter__.return_value = cur

        req = CreateEscalationRuleRequest(
            event_code="DEFICIENCY_OVERDUE",
            threshold_minutes=1440,
            recipient_role_id=self.role_id,
            action_type="notify_regional_officer",
        )
        res = create_escalation_rule(req, self.request, self.subject)
        self.assertEqual(res["event_code"], "DEFICIENCY_OVERDUE")
        self.assertEqual(res["threshold_minutes"], 1440)

    @patch("backend.app.notifications.notification_transaction")
    @patch("backend.app.notifications._user")
    def test_resolve_escalation_event(self, mock_user, mock_tx):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[
                {"id": self.event_id, "resolution_status": "active"},
                {
                    "id": self.event_id,
                    "rule_id": UUID(int=40),
                    "resolution_status": "resolved",
                    "resolved_at": datetime.now(timezone.utc),
                },
            ]
        )
        mock_tx.return_value.__enter__.return_value = cur

        req = ResolveEscalationRequest(
            resolution_status="resolved",
            reason="Deficiency response submitted by institution",
        )
        res = resolve_escalation_event(self.event_id, req, self.request, self.subject)
        self.assertEqual(res["resolution_status"], "resolved")
