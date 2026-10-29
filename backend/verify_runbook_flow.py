"""Persist one evaluation case through intake/scrutiny; never fake a site visit.

Uses real HTTP handlers, prototype identities and the configured runtime DB roles.
Evaluation narratives are explicitly labelled; this is not a statutory assessment.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.prototype import persona_subject


def main():
    client = TestClient(app)
    headers = {}
    evidence = {"started_at": datetime.now(timezone.utc).isoformat(), "steps": []}
    output = Path('completion/runbook-live-evidence.json')
    def record(step, **values):
        evidence['steps'].append({'step': step, **values})
        output.write_text(json.dumps(evidence, indent=2, default=str), encoding='utf-8')
        print('PASS', step, values, flush=True)
    def call(persona, method, path, body=None, expected=200):
        response = client.request(method, '/api/v1'+path, json=body,
                                  headers={**headers[persona], 'Idempotency-Key':str(uuid4())})
        assert response.status_code == expected, (method, path, response.status_code, response.text)
        return response.json()
    for persona in ('institution', 'regional', 'scrutiny'):
        response = client.post('/api/v1/prototype/session', json={'persona_id':'user-'+persona})
        assert response.status_code == 200, response.text
        headers[persona] = {'Authorization':'Bearer '+response.json()['access_token']}
    record('00 persona sessions', personas=list(headers))
    data = call('institution','GET','/portal/snapshot')
    institution = next(i for i in data['institutions'] if 'Cedar' in i['name'])
    workflows = call('institution','GET','/workflows')['data']
    workflow = next(w for w in workflows if w['status']=='published' and 'live prototype' in w['name'].lower())
    definition = call('institution','GET','/workflows/'+workflow['id'])
    stages = definition['stages']
    draft = call('institution','POST','/applications',{
        'institution_id':institution['id'],'campus_id':institution['campuses'][0]['id'],
        'application_type_id':workflow['application_type_id'],'workflow_definition_id':workflow['id'],
        'reason':'Evaluation run of supplied workflow; no statutory compliance asserted'},201)
    ident = draft['id']; evidence['application_id'] = ident
    record('01 persisted draft',application_id=ident)
    case = call('institution','POST',f'/applications/{ident}/submit',{
        'expected_version':draft['version'],'reason':'Evaluation declaration and submission'})
    record('02 submission',status=case['status'])
    call('regional','POST',f'/applications/{ident}/assignments',{
        'assigned_user_id':persona_subject('user-scrutiny'), 'expected_version':case['version'],
        'due_at':(datetime.now(timezone.utc)+timedelta(days=7)).isoformat(),
        'reason':'Assign evaluation case to scrutiny officer'},201)
    case = call('scrutiny','GET',f'/applications/{ident}')
    scrutiny = next(stage for stage in stages if stage['stage_type']=='scrutiny')
    case = call('scrutiny','POST',f'/applications/{ident}/transitions',{
        'to_stage_id':scrutiny['id'],'expected_version':case['version'],'reason':'Start evaluation scrutiny'})
    record('03 scrutiny assigned and started',status=case['status'])
    notice = call('scrutiny','POST',f'/applications/{ident}/deficiency-notices',{
        'response_due_days':14, 'reason':'Evaluation of two-item correction lifecycle',
        'items':[{'criterion_code':'EVALUATION_01','description':'Explain first evaluation correction'},
                 {'criterion_code':'EVALUATION_02','description':'Explain second evaluation correction'}]},201)
    record('04 two-item notice',notice_id=notice['id'],item_count=len(notice['items']))
    response = call('institution','POST',f"/deficiency-notices/{notice['id']}/responses",{
        'item_responses':[{'item_id':item['id'],'narrative':'Evaluation correction narrative '+str(i+1)} for i,item in enumerate(notice['items'])],
        'reason':'Evaluation narrative-only response; no certificate verification claimed'})
    assert response['status']=='responded'
    record('05 itemized response',status=response['status'])
    for item in notice['items']:
        call('scrutiny','POST',f"/deficiency-items/{item['id']}/resolve",{
            'resolution_status':'accepted','reason':'Accept evaluation narrative for lifecycle test only'})
    case = call('scrutiny','GET',f'/applications/{ident}')
    evc_stage = next(stage for stage in stages if stage['stage_type']=='evc')
    call('scrutiny','POST',f'/applications/{ident}/transitions',{
        'to_stage_id':evc_stage['id'],'expected_version':case['version'],
        'reason':'Complete evaluation scrutiny after both responses resolved'})
    visible = call('institution','GET','/portal/snapshot')
    current = next(a for a in visible['applications'] if a['id']==ident)
    assert current['status']=='AWAITING_EVC',current
    saved_notice = next(n for n in visible['deficiencies'] if n['id']==notice['id'])
    assert all(item['status']=='RESOLVED' and item['response'] for item in saved_notice['items'])
    visits = [v for v in visible['visits'] if v['applicationId']==ident]
    assert len(visits)==1,visits
    record('06 resolved, advanced, visit created, narratives survived refresh',status=current['status'],visit_id=visits[0]['id'])
    history = call('regional','GET',f'/applications/{ident}/history')['data']
    assert len(history)>=3
    record('timeline persisted',events=len(history))
    evidence['remaining']=['Real clean file scan and uploaded evidence acceptance','Committee screening and confirmed available slot','Actual visit completion before EVC approval','Decision, condition evidence, verification and closure','Live audit and export verification']
    output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print('VERDICT: PASS — intake and scrutiny; later stages explicitly pending',flush=True)


if __name__ == '__main__': main()
