"""Add deterministic synthetic live prototype scenarios; no existing case reset.
Run python -m backend.seed_live_prototype [--apply]. Default rolls back.
"""
import argparse
from collections import Counter
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL,UUID,uuid5
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from backend.app.audit import append_event
from backend.app.prototype import persona_subject
from backend.app.storage import store_file
ROOT=Path(__file__).resolve().parents[1]
def uid(kind,key='main'):
    return uuid5(NAMESPACE_URL,f'aicte-live-prototype-scenarios-v1/{kind}/{key}')
def sample_pdf():
    text=b'BT /F1 16 Tf 45 740 Td (DEMO ONLY - Prototype evidence sample) Tj 0 -24 Td /F1 11 Tf (Synthetic facilities update. Not an official certificate.) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(text)).encode()+b' >>\nstream\n'+text+b'\nendstream']
    output=b'%PDF-1.4\n'; offsets=[0]
    for number,obj in enumerate(objects,1):
        offsets.append(len(output)); output+=f'{number} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(output); output+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    output+=b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    return output+f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
def seed(apply=False):
    now=datetime.now(timezone.utc); future=(now+timedelta(days=7)).replace(hour=9,minute=0,second=0,microsecond=0)
    actor=UUID(persona_subject('user-institution')); scrutiny=UUID(persona_subject('user-scrutiny')); regional=UUID(persona_subject('user-regional')); coordinator=UUID(persona_subject('user-coordinator')); compliance=UUID(persona_subject('user-compliance')); expert=UUID(persona_subject('user-expert-001'))
    counts=Counter(); content=sample_pdf(); object_key=f'prototype-evidence/{uid("document-version")}.pdf'
    with psycopg.connect(dotenv_values(ROOT/'.env')['DATABASE_URL'],sslmode='require',connect_timeout=12,options='-c statement_timeout=30000 -c lock_timeout=5000',row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            def add(table,**row):
                columns=list(row); stmt=sql.SQL('INSERT INTO public.{} ({}) VALUES ({}) ON CONFLICT DO NOTHING').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns)),sql.SQL(',').join(sql.Placeholder() for _ in columns))
                cur.execute(stmt,tuple(row[c] for c in columns)); counts[table]+=cur.rowcount
            cur.execute("SELECT i.id,i.region_id,c.id AS campus FROM public.institutions i JOIN public.institution_campuses c ON c.institution_id=i.id AND c.is_primary WHERE i.institution_code='DEMO-INST-0001'")
            institution=cur.fetchone()
            if not institution: raise RuntimeError('Original DEMO institution is missing')
            inst= institution['id']; campus=institution['campus']
            cur.execute("SELECT id,role_code FROM public.roles WHERE role_code IN ('DEMO_SCRUTINY','DEMO_COMPLIANCE','DEMO_EVC_EXPERT')")
            roles={r['role_code']:r['id'] for r in cur.fetchall()}
            if len(roles)!=3: raise RuntimeError('Provision prototype personas first')
            expert_users=[expert]
            for number,name in enumerate(('DEMO Priya Kulkarni','DEMO Omar Khan','DEMO Leena Joseph','DEMO Vikram Bose'),2):
                who=uid('expert-user',number); email=f'expert-{number}@prototype.example.invalid'
                cur.execute('INSERT INTO auth.users (id,email,is_anonymous,created_at,updated_at,raw_app_meta_data,raw_user_meta_data) VALUES (%s,%s,false,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING',(who,email,now,now,Jsonb({'provider':'prototype-only'}),Jsonb({'demo_only':True})))
                add('users',id=who,identity_subject=str(who),display_name=name,email=email,status='active')
                add('expert_profiles',id=uid('expert-profile',number),user_id=who,expertise=['Engineering','Institutional review'],eligibility_status='eligible',availability_method='manual'); expert_users.append(who)
            add('application_types',id=uid('type'),code='DEMO-LIVE-PROTOTYPE',name='DEMO ONLY — Live prototype journey',description='Illustrative first prototype; not official APH policy',status='active')
            add('aph_rule_sets',id=uid('rules'),rule_set_code='DEMO-LIVE-RULES',title='DEMO ONLY — Illustrative prototype rules',source_reference='Project-owner prototype demonstration, not official statutory authority',status='published',effective_from=now.date(),created_by=regional)
            add('aph_rule_versions',id=uid('rules-version'),rule_set_id=uid('rules'),version_number=1,content_reference='demo://live-prototype/illustrative-rules',checksum=sha256(b'demo-live-illustrative-rules-v1').hexdigest(),created_by=regional)
            add('workflow_definitions',id=uid('workflow'),name='DEMO ONLY — Live prototype lifecycle',application_type_id=uid('type'),aph_rule_version_id=uid('rules-version'),status='published',version_number=1,created_by=regional)
            stages=('INTAKE','SCRUTINY','EVC','DECISION','COMPLIANCE','CLOSURE')
            for order,code in enumerate(stages,1): add('workflow_stages',id=uid('stage',code),workflow_definition_id=uid('workflow'),stage_code=code,stage_name=f'DEMO {code.title()}',stage_order=order,stage_type=code.lower(),default_sla_days=14,created_by=regional)
            for source,target in zip(stages,stages[1:]): add('workflow_transitions',id=uid('transition',source),workflow_definition_id=uid('workflow'),from_stage_id=uid('stage',source),to_stage_id=uid('stage',target),transition_type='demo_forward',guard_rule=Jsonb({}),requires_authorisation=True,created_by=regional)
            scenarios=(('DRAFT','draft','INTAKE'),('SCRUTINY','under_review','SCRUTINY'),('DEFICIENCY','deficiency_returned','SCRUTINY'),('EVC','under_review','EVC'),('DECISION','under_review','DECISION'),('COMPLIANCE','approved','COMPLIANCE'))
            for label,status,stage in scenarios:
                app=uid('application',label); instance=uid('stage-instance',label)
                add('applications',id=app,application_number=f'DEMO-LIVE-{label}-001',institution_id=inst,campus_id=campus,application_type_id=uid('type'),workflow_definition_id=uid('workflow'),status=status,submitted_at=None if label=='DRAFT' else now-timedelta(days=2),created_at=now-timedelta(days=3),created_by=actor,updated_by=actor)
                add('application_stage_instances',id=instance,application_id=app,workflow_stage_id=uid('stage',stage),status='in_progress',entered_at=now-timedelta(days=2),due_at=now+timedelta(days=12),created_by=regional)
                cur.execute('UPDATE public.applications SET current_stage_instance_id=%s WHERE id=%s AND current_stage_instance_id IS NULL',(instance,app))
                if label!='DRAFT': add('application_submissions',id=uid('submission',label),application_id=app,submission_number=1,submitted_by=actor,submitted_at=now-timedelta(days=2),submission_status='returned' if label=='DEFICIENCY' else 'submitted')
                add('assignments',id=uid('assignment',label),application_id=app,stage_instance_id=instance,assigned_user_id=scrutiny if label in ('SCRUTINY','DEFICIENCY') else compliance if label=='COMPLIANCE' else regional,assigned_at=now,due_at=now+timedelta(days=12),status='active',created_by=regional)
            cur.execute("SELECT a.id,a.current_stage_instance_id FROM public.applications a WHERE a.institution_id=%s AND a.application_number LIKE 'DEMO-APP-%%'",(inst,))
            for a in cur.fetchall(): add('assignments',id=uid('original-assignment',a['id']),application_id=a['id'],stage_instance_id=a['current_stage_instance_id'],assigned_user_id=scrutiny,assigned_role_id=roles['DEMO_SCRUTINY'],status='active',due_at=now+timedelta(days=7),created_by=regional)
            add('deficiency_notices',id=uid('notice'),application_id=uid('application','DEFICIENCY'),stage_instance_id=uid('stage-instance','DEFICIENCY'),notice_number=1,issued_by=scrutiny,issued_at=now-timedelta(days=1),response_due_at=now+timedelta(days=7),status='open',created_by=scrutiny)
            add('deficiency_items',id=uid('deficiency-item'),deficiency_notice_id=uid('notice'),criterion_code='DEMO-CAMPUS-EVIDENCE',description='DEMO ONLY — attach synthetic campus evidence and explain declared facilities',resolution_status='pending',created_by=scrutiny)
            add('document_types',id=uid('document-type'),document_type_code='DEMO-LIVE-EVIDENCE',name='DEMO ONLY — Prototype facilities evidence',description='Synthetic downloadable PDF, human verification pending',supports_expiry=True,metadata_schema=Jsonb({'demo_only':True}))
            add('documents',id=uid('document'),institution_id=inst,campus_id=campus,application_id=uid('application','COMPLIANCE'),document_type_id=uid('document-type'),document_scope='application',status='active',created_by=actor)
            add('document_versions',id=uid('document-version'),document_id=uid('document'),version_number=1,object_key=object_key,file_name='DEMO_Prototype_Facilities_Evidence.pdf',mime_type='application/pdf',size_bytes=len(content),sha256_hash=sha256(content).hexdigest(),uploaded_by=actor,uploaded_at=now,issue_date=now.date()-timedelta(days=330),expiry_date=now.date()+timedelta(days=35),verification_status='pending')
            cur.execute('UPDATE public.documents SET current_version_id=%s WHERE id=%s AND current_version_id IS NULL',(uid('document-version'),uid('document')))
            add('document_renewal_cases',id=uid('renewal'),document_id=uid('document'),current_version_id=uid('document-version'),renewal_due_at=now+timedelta(days=35),status='open',assigned_to=compliance,created_by=actor)
            add('compliance_conditions',id=uid('condition'),application_id=uid('application','COMPLIANCE'),institution_id=inst,condition_code='DEMO-LIVE-FACILITIES',description='DEMO ONLY — verify the prototype campus facilities update',due_at=now+timedelta(days=10),status='evidence_submitted',verification_role_id=roles['DEMO_COMPLIANCE'],created_by=regional)
            add('evidence_submissions',id=uid('evidence'),compliance_condition_id=uid('condition'),submitted_by=actor,submitted_at=now,submission_number=1,status='submitted')
            add('evidence_submission_files',evidence_submission_id=uid('evidence'),document_version_id=uid('document-version'))
            visit=uid('visit')
            add('evc_visits',id=visit,application_id=uid('application','EVC'),campus_id=campus,status='committee_selection',required_by=now+timedelta(days=14),coordinator_user_id=coordinator,created_by=coordinator)
            for number,who in enumerate(expert_users,1):
                add('evc_committee_members',id=uid('committee-member',number),evc_visit_id=visit,expert_user_id=who,committee_role='convener' if number==1 else 'member',selection_status='selected',selected_by=regional,selected_at=now)
                add('expert_availability',id=uid('expert-availability',number),expert_user_id=who,start_at=future,end_at=future+timedelta(hours=10),availability_status='available',source='manual_entry',last_confirmed_at=now)
                add('user_role_assignments',id=uid('expert-application-grant',number),user_id=who,role_id=roles['DEMO_EVC_EXPERT'],scope_type='application',scope_id=uid('application','EVC'),valid_from=now,valid_until=now+timedelta(days=30),status='active',created_by=regional)
            cur.execute("SELECT to_regclass('public.institution_availability') AS relation")
            if cur.fetchone()['relation']: add('institution_availability',id=uid('institution-availability'),institution_id=inst,start_at=future,end_at=future+timedelta(hours=10),availability_status='available',source='manual_entry',last_confirmed_at=now,created_by=actor)
            add('evc_visit_events',id=uid('visit-event'),evc_visit_id=visit,event_type='DEMO_COMMITTEE_SELECTED',event_at=now,actor_user_id=regional,reason='Illustrative local prototype committee selection',details=Jsonb({'demo_only':True,'member_count':5}))
            add('evc_observations',id=uid('observation'),evc_visit_id=visit,criterion_code='DEMO-FACILITIES',observation_text='DEMO ONLY — Draft preparation question: reconcile campus evidence. The visit has not occurred.',source_type='committee_note',created_by=expert,review_status='draft')
            add('evc_reports',id=uid('report'),evc_visit_id=visit,report_status='draft',template_version='DEMO-1',created_by=expert)
            sections=[{'title':'DEMO — Draft visit preparation','text':'Synthetic preparation note. The visit has not occurred.','sourceIds':[str(uid('observation'))],'warning':'Visit incomplete and source note draft.'}]
            add('meeting_record_versions',id=uid('meeting-version'),evc_report_id=uid('report'),record_type='evc_report',version_number=1,content_reference='demo://prototype/draft-only',source_manifest=Jsonb({'demo_only':True,'sections':sections}),created_by=expert,approval_status='draft')
            cur.execute('UPDATE public.evc_reports SET current_version_id=%s WHERE id=%s AND current_version_id IS NULL',(uid('meeting-version'),uid('report')))
            add('meeting_record_sources',id=uid('meeting-source'),meeting_record_version_id=uid('meeting-version'),source_type='committee_note',source_id=uid('observation'),section_reference='DEMO — Draft visit preparation')
            add('action_items',id=uid('action-item'),evc_visit_id=visit,description='DEMO ONLY — reconcile evidence before visit confirmation',responsible_role_id=roles['DEMO_EVC_EXPERT'],due_at=now+timedelta(days=5),status='open',source_observation_id=uid('observation'),created_by=expert)
            for who,label in ((actor,'Institution evidence awaits review'),(scrutiny,'Review assigned prototype applications'),(coordinator,'Confirm fresh exact-member availability'),(compliance,'Verify submitted prototype evidence')): add('notifications',id=uid('notification',who),event_code='DEMO_LIVE_PROTOTYPE_READY',recipient_user_id=who,related_entity_type='application',related_entity_id=uid('application','COMPLIANCE'),status='queued',payload=Jsonb({'demo_only':True,'channel':'IN_APP','read':False,'message':label+'. Synthetic in-app example, no external message sent.'}))
            add('escalation_rules',id=uid('escalation-rule'),event_code='DEMO_PROTOTYPE_REVIEW',threshold_minutes=60,recipient_role_id=roles['DEMO_SCRUTINY'],action_type='in_app',enabled=True,created_by=regional)
            add('escalation_events',id=uid('escalation'),rule_id=uid('escalation-rule'),related_entity_type='application',related_entity_id=uid('application','SCRUTINY'),triggered_at=now,recipient_user_id=scrutiny,resolution_status='active')
            add('background_jobs',id=uid('job'),job_type='DEMO_MANUAL_REVIEW_REMINDER',related_entity_type='application',related_entity_id=uid('application','SCRUTINY'),status='queued',attempt_count=0,last_error='Synthetic queued example, no external worker delivery claimed')
            if sum(counts.values()): append_event(cur,actor_id=None,action='DEMO_LIVE_SCENARIOS_SEEDED',entity_type='application',entity_id=uid('application','DRAFT'),correlation_id=None,reason='Project owner requested working first-prototype live dataset; supplemental records are synthetic',metadata={'demo_only':True,'inserted':dict(counts)})
        if not apply: conn.rollback()
        elif not (ROOT/'storage'/'documents'/object_key).exists(): store_file(object_key,content)
    print('Committed synthetic scenarios' if apply else 'Dry run passed, transaction rolled back'); print(dict(counts))
    print('Six DEMO-LIVE-*-001 applications linked to DEMO-INST-0001; no real approvals, OCR, scan success, or external deliveries fabricated')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--apply',action='store_true'); seed(parser.parse_args().apply)
