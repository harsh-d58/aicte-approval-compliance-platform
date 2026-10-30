"""Live restricted-role lifecycle acceptance; every test row rolls back.

Only the transaction connection is reused so all normal business SQL and
authorization checks see the same isolated fixture. No provider I/O occurs.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4
import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException
from backend.app.settings import Settings
from backend.app.prototype import persona_subject
from backend.app.authorization import check_request
from backend.app.compliance import (CreateConditionRequest, SubmitEvidenceRequest, VerifyEvidenceRequest,
    CloseConditionRequest, create_compliance_condition, submit_condition_evidence,
    verify_evidence_submission, close_compliance_condition)
from backend.app.decisions import CreateDecisionRequest, record_statutory_decision


def main():
    settings=Settings.load(); correlation=uuid4(); checks=[]
    regional=persona_subject('user-regional'); institution=persona_subject('user-institution'); reviewer=persona_subject('user-compliance')
    case=uuid4(); stage_instance=uuid4(); visit=uuid4(); report=uuid4(); record=uuid4(); document=uuid4(); version=uuid4()
    def passed(message): checks.append(message); print('PASS',message,flush=True)
    with psycopg.connect(settings.database_write_url,sslmode='require',autocommit=True,row_factory=dict_row,connect_timeout=15) as connection:
        @contextmanager
        def reuse(_url,subject):
            with connection.transaction():
                connection.execute("SELECT set_config('aicte.subject_id',%s,true)",(subject,))
                yield connection
        with connection.transaction(force_rollback=True):
            connection.execute("SELECT set_config('aicte.subject_id',%s,true)",(regional,))
            with connection.cursor() as cur:
                cur.execute("SELECT a.institution_id,a.campus_id,a.workflow_definition_id,a.application_type_id,s.id AS stage_id FROM applications a JOIN workflow_stages s ON s.workflow_definition_id=a.workflow_definition_id AND s.stage_type='decision' WHERE a.id=%s",('76e9a91b-343a-5d90-8f73-8f96b7b83603',))
                template=cur.fetchone(); assert template
                now=datetime.now(timezone.utc)
                cur.execute("INSERT INTO applications(id,application_number,institution_id,campus_id,application_type_id,workflow_definition_id,status,created_by,updated_by,version) VALUES(%s,%s,%s,%s,%s,%s,'under_review',%s,%s,1)",(case,'DEMO-ROLLBACK-DECISION-'+uuid4().hex[:8],template['institution_id'],template['campus_id'],template['application_type_id'],template['workflow_definition_id'],regional,regional))
                cur.execute("INSERT INTO application_stage_instances(id,application_id,workflow_stage_id,status,entered_at,created_by) VALUES(%s,%s,%s,'in_progress',%s,%s)",(stage_instance,case,template['stage_id'],now,regional))
                cur.execute('UPDATE applications SET current_stage_instance_id=%s WHERE id=%s',(stage_instance,case))
                cur.execute("INSERT INTO evc_visits(id,application_id,status,required_by,confirmed_start_at,confirmed_end_at,completed_at,created_by) VALUES(%s,%s,'completed',%s,%s,%s,%s,%s)",(visit,case,now+timedelta(days=30),now-timedelta(days=2,hours=8),now-timedelta(days=2),now-timedelta(days=1),regional))
                cur.execute("INSERT INTO evc_reports(id,evc_visit_id,report_status,template_version,created_by) VALUES(%s,%s,'approved','ROLLBACK-ACCEPTANCE',%s)",(report,visit,regional))
                cur.execute("INSERT INTO meeting_record_versions(id,evc_report_id,record_type,version_number,content_reference,source_manifest,approval_status,created_by,approved_by,approved_at) VALUES(%s,%s,'evc_report',1,%s,'{}','approved',%s,%s,%s)",(record,report,'urn:rollback-acceptance:'+str(record),regional,regional,now))
                cur.execute('UPDATE evc_reports SET current_version_id=%s WHERE id=%s',(record,report))
                cur.execute("SELECT d.document_type_id,v.object_key,v.mime_type,v.size_bytes,v.sha256_hash FROM document_versions v JOIN documents d ON d.id=v.document_id WHERE v.id=%s",('cd4c3587-5d58-4936-abaf-94b6738aca99',))
                source=cur.fetchone();assert source
                cur.execute("INSERT INTO documents(id,institution_id,application_id,document_type_id,document_scope,status,created_by) VALUES(%s,%s,%s,%s,'application','active',%s)",(document,template['institution_id'],case,source['document_type_id'],institution))
                cur.execute("INSERT INTO document_versions(id,document_id,version_number,object_key,file_name,mime_type,size_bytes,sha256_hash,uploaded_by) VALUES(%s,%s,1,%s,'DEMO rollback metadata fixture.pdf',%s,%s,%s,%s)",(version,document,'rollback-metadata-only/'+str(version),source['mime_type'],source['size_bytes'],source['sha256_hash'],institution))
                cur.execute('UPDATE documents SET current_version_id=%s WHERE id=%s',(version,document))
            def invoke(subject,path,function,*args,expected=None,method='POST'):
                request=SimpleNamespace(url=SimpleNamespace(path='/api/v1'+path),method=method,
                    app=SimpleNamespace(state=SimpleNamespace(settings=settings)),state=SimpleNamespace(correlation_id=str(correlation)))
                try:
                    with patch('backend.app.authorization.write_transaction',reuse),patch('backend.app.compliance.write_transaction',reuse),patch('backend.app.decisions.write_transaction',reuse):
                        check_request(request,subject,None)
                        value=function(*args,request,subject)
                    if expected: raise AssertionError('Expected rejection '+str(expected))
                    return value
                except HTTPException as error:
                    if expected!=error.status_code: raise
                    return error.status_code
            condition=invoke(regional,'/compliance-conditions',create_compliance_condition,CreateConditionRequest(
                institution_id=template['institution_id'],application_id=case,condition_code='ROLLBACK-'+uuid4().hex[:8],
                description='Rolled-back live acceptance undertaking',evidence_requirements=['Attestation','Photographs'],due_at=now+timedelta(days=60)))
            condition_id=UUID(str(condition['id']));assert condition['evidence_requirements']==['Attestation','Photographs']
            passed('condition and evidence checklist persist in real PostgreSQL transaction')
            def decision(kind,status,expected=None):
                current=connection.execute('SELECT version FROM applications WHERE id=%s',(case,)).fetchone()['version']
                return invoke(regional,f'/applications/{case}/decisions',record_statutory_decision,case,CreateDecisionRequest(decision_type=kind,decision_status=status,decision_authority='Rollback acceptance only',reason='Isolated lifecycle acceptance; no real decision committed',expected_version=current),expected=expected)
            with connection.transaction(force_rollback=True):
                rejection=decision('reject','rejected')
                assert connection.execute('SELECT status FROM applications WHERE id=%s',(case,)).fetchone()['status']=='rejected'
                assert rejection['application_status']=='rejected'
            passed('reject records rejection rather than approval (isolated savepoint rolled back)')
            approval=decision('approve','approved')
            saved=connection.execute('SELECT status,closed_at FROM applications WHERE id=%s',(case,)).fetchone()
            assert saved['status']=='approved' and saved['closed_at'] is None
            linked=connection.execute('SELECT source_approval_id FROM compliance_conditions WHERE id=%s',(condition_id,)).fetchone()
            assert str(linked['source_approval_id'])==str(approval['id'])
            passed('approval leaves case open and links undertaking to approval record')
            decision('close','approved',409);passed('case closure rejected while condition is open')
            evidence=invoke(institution,f'/compliance-conditions/{condition_id}/evidence-submissions',submit_condition_evidence,condition_id,SubmitEvidenceRequest(document_version_ids=[version],remarks='Rollback evidence only'))
            evidence_id=UUID(str(evidence['id']))
            decision('close','approved',409);passed('submitted evidence alone does not permit closure')
            invoke(reviewer,f'/evidence-submissions/{evidence_id}/verifications',verify_evidence_submission,evidence_id,VerifyEvidenceRequest(result='accepted',comments='Rollback test verification; no real determination committed'))
            passed('independent compliance officer verifies latest institution evidence')
            invoke(reviewer,f'/compliance-conditions/{condition_id}/close',close_compliance_condition,condition_id,CloseConditionRequest(reason='Rollback test condition closure'))
            passed('compliance role can explicitly close verified condition')
            decision('close','approved')
            saved=connection.execute('SELECT status,closed_at FROM applications WHERE id=%s',(case,)).fetchone()
            assert saved['status']=='closed' and saved['closed_at']
            outcomes=connection.execute('SELECT decision_type FROM approval_decisions WHERE application_id=%s ORDER BY decision_at',(case,)).fetchall()
            assert [row['decision_type'] for row in outcomes]==['approve','close']
            passed('explicit case closure preserves original approval and records closed timestamp')
            assert connection.execute('SELECT count(*) AS count FROM audit_events WHERE correlation_id=%s',(correlation,)).fetchone()['count']>=6
            passed('all lifecycle operations have atomic audit evidence')
        assert not connection.execute('SELECT 1 FROM applications WHERE id=%s',(case,)).fetchone()
        passed('test application and all related mutations rolled back')
    Path('completion/decision-closure-live-evidence.json').write_text(json.dumps({'checks':checks,'all_rolled_back':True},indent=2),encoding='utf-8')
    print('VERDICT: PASS',flush=True)


if __name__=='__main__':main()
