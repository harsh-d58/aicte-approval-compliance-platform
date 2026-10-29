"""The live audit endpoint reports actual failures and simulates on a copy."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import UUID

from backend.app.audit import event_digest
from backend.app.records import verify_audit_chain


class AuditEndpointTests(TestCase):
    def verify(self, simulate=False, corrupt=False):
        fields=dict(event_id=UUID(int=1),actor_id=None,action='TEST',entity_type='application',
                    entity_id=UUID(int=2),event_at=datetime(2026,1,1,tzinfo=timezone.utc),
                    correlation_id=None,reason='original',metadata={},previous_hash=None)
        row={**fields,'id':fields['event_id'],'event_hash':event_digest(**fields)}
        if corrupt:
            row['reason']='changed'
        cursor=MagicMock()
        cursor.fetchall.side_effect=[[row],[{'tgname':'audit_events_no_update_delete'}]]
        connection=MagicMock()
        connection.__enter__.return_value.cursor.return_value.__enter__.return_value=cursor
        request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(database_url='unused'))))
        with patch('backend.app.records._user'),patch('backend.app.records._require_audit_access'),patch('backend.app.records._read_connection',return_value=connection):
            result=verify_audit_chain(request,'subject',limit_recent=8,simulate=simulate)
        return result,row,cursor

    def test_real_corruption_is_reported(self):
        result,_,_=self.verify(corrupt=True)
        self.assertFalse(result['valid'])
        self.assertEqual(result['total_events'],1)
        self.assertEqual(result['errors'][0]['code'],'HASH_INVALID')

    def test_simulation_verifies_modified_copy_without_writes(self):
        result,row,cursor=self.verify(simulate=True)
        self.assertFalse(result['valid'])
        self.assertTrue(result['simulation'])
        self.assertEqual(result['simulated_event_id'],str(row['id']))
        self.assertEqual(row['reason'],'original')
        self.assertTrue(all(call.args[0].lstrip().startswith('SELECT') for call in cursor.execute.call_args_list))

    def test_healthy_chain_reports_actual_count(self):
        result,_,_=self.verify()
        self.assertTrue(result['valid'])
        self.assertEqual(result['total_events'],1)

