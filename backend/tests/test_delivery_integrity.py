"""Failure-oriented checks for truthful delivery and audit verification."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import UUID

from backend.app.audit import event_digest, verify_chain_rows
from backend.app.communications.receipts import authenticate_receipt
from backend.app.outbox_worker import run_delivery_cycle, run_outbox_cycle


class DeliveryIntegrityTests(TestCase):
    def test_receipt_requires_signature_and_fresh_timestamp(self):
        raw, stamp, secret = b'{"outcome":"delivered"}', '1000', 's'*32
        signature = hmac.new(secret.encode(),stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        authenticate_receipt(raw,stamp,signature,secret,now=1000)
        with self.assertRaises(ValueError):
            authenticate_receipt(raw+b' ',stamp,signature,secret,now=1000)
        with self.assertRaises(ValueError):
            authenticate_receipt(raw,stamp,signature,secret,now=1400)

    def test_valid_event_hash_does_not_hide_a_fork(self):
        rows=[]
        for index in range(2):
            fields=dict(event_id=UUID(int=index+1),actor_id=None,action='TEST',entity_type='application',
                        entity_id=UUID(int=3),event_at=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=index),
                        correlation_id=None,reason='test',metadata={},previous_hash=None)
            row={**fields,'id':fields['event_id'],'event_hash':event_digest(**fields)}
            rows.append(row)
        result=verify_chain_rows(rows)
        self.assertFalse(result['valid'])
        self.assertEqual(result['errors'],[{'id':str(UUID(int=2)),'code':'PREDECESSOR_INVALID'}])

    def test_provider_runs_after_database_connections_are_closed(self):
        active=[]
        cursor=MagicMock()
        cursor.fetchone.return_value={'event_code':'EVC_ALERT','payload':{},'email':'test@example.invalid'}
        @contextmanager
        def connection():
            conn=MagicMock()
            conn.cursor.return_value.__enter__.return_value=cursor
            active.append(conn)
            try:
                yield conn
            finally:
                active.remove(conn)
        job={'id':UUID(int=1),'notification_id':UUID(int=2),'channel':'email'}
        def provider(*args,**kwargs):
            self.assertEqual(active,[])
            return [{'status':'accepted','provider_reference':'receipt-id'}]
        with patch('backend.app.outbox_worker.get_connection',connection), \
             patch('backend.app.outbox_worker.claim_jobs',return_value=[job]), \
             patch('backend.app.outbox_worker.dispatch_event',side_effect=provider), \
             patch('backend.app.outbox_worker.record_outcome',return_value=True) as record:
            self.assertEqual(run_delivery_cycle(),1)
            self.assertEqual(record.call_args.args[2]['status'],'accepted')

    def test_failed_handoff_retries_in_fresh_transaction(self):
        connections=[]
        @contextmanager
        def connection():
            conn=MagicMock()
            connections.append(conn)
            yield conn
        event={'id':UUID(int=1),'claim_token':UUID(int=2),'attempt_count':1}
        with patch('backend.app.outbox_worker.get_connection',connection), \
             patch('backend.app.outbox_worker.claim_due',return_value=[event]), \
             patch('backend.app.outbox_worker.process_single_event',side_effect=RuntimeError('sql aborted')), \
             patch('backend.app.outbox_worker.schedule_retry') as retry:
            self.assertEqual(run_outbox_cycle(),0)
            self.assertEqual(len(connections),3)
            self.assertIs(retry.call_args.args[0],connections[2].cursor.return_value.__enter__.return_value)

