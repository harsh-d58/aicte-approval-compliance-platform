"""Owner-authorised prerequisite setup for one synthetic recording case.

This never records a statutory application decision or closes its condition.
The completed visit is explicitly a demonstration fixture. Its submitted source,
draft, review and report approval use the normal scoped HTTP API.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import httpx
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.app.audit import append_event
from backend.app.outbox import enqueue
from backend.app.prototype import persona_subject
from backend.app.settings import Settings
from backend.app.transactions import write_transaction

CASE = UUID('76e9a91b-343a-5d90-8f73-8f96b7b83603')
CONDITION = UUID('0def79df-6df3-401c-ba69-e8a9a1d93c9c')
VISIT = uuid5(NAMESPACE_URL, 'setu:phase8-recording-prerequisite:' + str(CASE))
REASON = ('Project owner explicitly requested forced EVC prerequisite approval for '
          'Phase08 prototype recording. Synthetic demonstration only; no actual '
          'physical inspection asserted. Final application decision remains manual.')
OUTPUT = Path('completion/phase8-recording-ready.json')


def main():
    settings = Settings.load()
    actor = UUID(persona_subject('user-regional'))
    correlation = uuid4()
    evidence = {'application_id': str(CASE), 'condition_id': str(CONDITION),
                'visit_id': str(VISIT), 'demo_recording_only': True,
                'final_decision_recorded_by_setup': False, 'steps': []}

    def log(step, value):
        evidence['steps'].append({'step': step, 'result': value})
        OUTPUT.write_text(json.dumps(evidence, indent=2, default=str), encoding='utf-8')
        print('PASS', step, flush=True)

    # Check and seed only the exact case shown by the owner. Preserve all existing
    # application, undertaking, evidence, approval and other-visit history.
    with write_transaction(settings.database_write_url, str(actor)) as connection:
        with connection.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT a.*,s.stage_type FROM applications a JOIN application_stage_instances si ON si.id=a.current_stage_instance_id JOIN workflow_stages s ON s.id=si.workflow_stage_id WHERE a.id=%s FOR UPDATE OF a", (CASE,))
            app = cur.fetchone()
            assert app and app['application_number'] == 'AICTE-2026-DECISION-001'
            assert app['status'] == 'under_review' and app['stage_type'] == 'decision'
            cur.execute('SELECT id,condition_code,application_id,status,source_approval_id,evidence_requirements FROM compliance_conditions WHERE id=%s FOR UPDATE', (CONDITION,))
            condition = cur.fetchone()
            assert condition and condition['application_id'] == CASE
            assert condition['condition_code'] == 'COND-1793341210646'
            assert condition['status'] == 'open' and condition['source_approval_id'] is None
            assert condition['evidence_requirements'] == ['PWD Structural Safety Attestation', 'Geotagged Photographs']
            cur.execute('SELECT count(*) AS count FROM approval_decisions WHERE application_id=%s', (CASE,))
            assert cur.fetchone()['count'] == 0, 'Final decisions must be left to the owner'
            cur.execute("SELECT count(*) AS count FROM deficiency_items i JOIN deficiency_notices n ON n.id=i.deficiency_notice_id WHERE n.application_id=%s AND i.resolution_status NOT IN ('accepted','waived')", (CASE,))
            assert cur.fetchone()['count'] == 0, 'Unexpected unresolved deficiency; no automatic waiver'
            cur.execute('SELECT id,status FROM evc_visits WHERE application_id=%s', (CASE,))
            visits = cur.fetchall()
            assert all(row['id'] == VISIT for row in visits), 'Existing visit must not be overwritten'
            if not visits:
                now = datetime.now(timezone.utc)
                cur.execute("INSERT INTO evc_visits(id,application_id,campus_id,status,required_by,confirmed_start_at,confirmed_end_at,completed_at,coordinator_user_id,created_by,updated_by) VALUES(%s,%s,%s,'completed',%s,%s,%s,%s,%s,%s,%s)",
                            (VISIT, CASE, app['campus_id'], now + timedelta(days=30), now - timedelta(hours=1), now, now, actor, actor, actor))
                metadata = {'demo_recording_only': True, 'application_id': str(CASE),
                            'setup': 'owner-authorised Phase08 prerequisite preparation',
                            'physical_inspection_asserted': False}
                cur.execute("INSERT INTO evc_visit_events(evc_visit_id,event_type,actor_user_id,reason,details) VALUES(%s,'completed',%s,%s,%s)",
                            (VISIT, actor, REASON, Jsonb(metadata)))
                append_event(cur, actor_id=actor, action='DEMO_EVC_PREREQUISITE_PREPARED',
                             entity_type='application', entity_id=CASE, correlation_id=correlation,
                             reason=REASON, metadata={**metadata, 'visit_id': str(VISIT)})
                enqueue(cur, event_type='DEMO_EVC_PREREQUISITE_PREPARED', entity_type='application',
                        entity_id=CASE, payload={**metadata, 'visit_id': str(VISIT)}, correlation_id=correlation)
            else:
                assert visits[0]['status'] == 'completed'
            initial_version = app['version']
    log('one completed demonstration visit persisted; condition and final decision untouched', {'application_version': initial_version})

    with httpx.Client(base_url='http://localhost:8000/api/v1', timeout=70) as client:
        session = client.post('/prototype/session', json={'persona_id': 'user-regional'})
        assert session.status_code == 200, session.status_code
        client.headers['Authorization'] = 'Bearer ' + session.json()['access_token']

        def call(method, path, body=None, key=None):
            response = client.request(method, path, json=body,
                                      headers={'Idempotency-Key': key} if key else None)
            assert response.status_code in (200, 201), (path, response.status_code, response.text[:1000])
            return response.json()

        observations = call('GET', f'/evc-visits/{VISIT}/observations')['data']
        source = next((row for row in observations if row['criterion_code'] == 'DEMO_PHASE08_RECORDING'), None)
        if source is None:
            source = call('POST', f'/evc-visits/{VISIT}/observations', {
                'criterion_code': 'DEMO_PHASE08_RECORDING', 'source_type': 'document_check',
                'observation_text': ('Owner-authorised recording fixture: simulated positive EVC review '
                                     'for Phase08 conditional approval. No real physical inspection '
                                     'or institutional safety certification is asserted by this setup.'),
                'review_status': 'submitted', 'reason': REASON,
            }, key='phase8-recording-source-' + str(CASE))
        assert source['review_status'] == 'submitted'
        log('submitted demonstration source saved through scoped API', {'source_id': source['id']})
        reports = call('GET', '/portal/snapshot')['meetingRecords']
        existing = next((row for row in reports if row['visitId'] == str(VISIT) and row['type'] == 'EVC_REPORT'), None)
        if existing is None:
            draft = call('POST', f'/evc-visits/{VISIT}/meeting-record-drafts', {
                'record_type': 'evc_report', 'template_version': 'DEMO-PHASE08-RECORDING',
                'source_ids': [source['id']], 'reason': REASON,
            }, key='phase8-recording-draft-' + str(CASE))
            report_id = str(draft['report_id'])
        else:
            report_id = existing['id']
        report = call('GET', f'/meeting-records/{report_id}')
        if report['approval_status'] == 'draft':
            call('POST', f'/meeting-records/{report_id}/submit-review')
            report = call('GET', f'/meeting-records/{report_id}')
        if report['approval_status'] == 'pending_approval':
            call('POST', f'/meeting-records/{report_id}/approve', {'reason': REASON},
                 key='phase8-recording-report-approval-' + str(CASE))
        report = call('GET', f'/meeting-records/{report_id}')
        assert report['approval_status'] == report['report_status'] == 'approved'
        assert report['record_type'] == 'evc_report'
        log('source-backed report reviewed and approved through normal API', {'report_id': report_id, 'version_id': report['current_version_id']})

        snapshot = call('GET', '/portal/snapshot')
        app = next(row for row in snapshot['applications'] if row['id'] == str(CASE))
        condition = next(row for row in snapshot['conditions'] if row['id'] == str(CONDITION))
        assert app['status'] == 'DECISION_PENDING' and app['stageType'] == 'decision'
        assert app['version'] == initial_version and app['closure'] is None
        assert not any(row['applicationId'] == str(CASE) for row in snapshot['decisions'])
        assert condition['status'] == 'OPEN' and not condition['sourceDecisionId']
        assert condition['evidenceRequired'] == ['PWD Structural Safety Attestation', 'Geotagged Photographs']
        assert any(row['id'] == str(VISIT) and row['status'] == 'COMPLETED' for row in snapshot['visits'])
        log('live snapshot ready for manual APPROVE; undertaking remains open and no final decision exists',
            {'application_status': app['status'], 'condition_status': condition['status'], 'report_id': report_id})
    print('VERDICT: PASS', flush=True)


if __name__ == '__main__':
    main()
