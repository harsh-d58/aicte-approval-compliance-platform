"""User-authorized recording setup for ONE synthetic prototype application.

Uses normal authenticated handlers, preserving history/audit and scoped roles.
The public sample is demonstration evidence, not this institution's certificate.
"""
import json
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app

CASE='b0ed2753-0bdf-5c0f-86fd-5e11f2c67e9e'
NOTICE='bc654d42-17b3-4d37-b278-8d0e7c1178d2'
ITEM='91d01ae2-fcce-4991-9b40-0310d2731b49'
DOCUMENT='96be1974-ebf8-47c9-a554-90768dc111ca'
VERSION='cd4c3587-5d58-4936-abaf-94b6738aca99'
DEFICIENCY='830da608-4348-5569-8343-427ce053a027'
EVC='11017cc3-d8b2-5b24-b59c-1b3c6015103e'


def main():
    client=TestClient(app)
    headers={}
    evidence={'application_id':CASE,'notice_id':NOTICE,'demo_recording_only':True,'steps':[]}
    output=Path('completion/recording-case-evidence.json')
    def log(step,result):
        evidence['steps'].append({'step':step,'result':result})
        output.write_text(json.dumps(evidence,indent=2,default=str),encoding='utf-8')
        print('PASS',step,flush=True)
    def call(persona,method,path,body=None):
        response=client.request(method,'/api/v1'+path,json=body,headers={**headers[persona],'Idempotency-Key':str(uuid4())})
        assert response.status_code in (200,201),(path,response.status_code,response.text)
        return response.json()
    for persona in ('institution','scrutiny','regional'):
        response=client.post('/api/v1/prototype/session',json={'persona_id':'user-'+persona})
        assert response.status_code==200,response.text
        headers[persona]={'Authorization':'Bearer '+response.json()['access_token']}
    case=call('institution','GET',f'/applications/{CASE}')
    assert case['application_number']=='AICTE-APP-2026-000002'
    log('existing application submitted and notice issued',{'status':case['status'],'version':case['version']})
    notices=call('regional','GET',f'/applications/{CASE}/deficiency-notices')['data']
    notice=next(row for row in notices if row['id']==NOTICE)
    assert len(notice['items'])==1 and notice['items'][0]['id']==ITEM
    history=call('regional','GET',f'/applications/{CASE}/history')['data']
    workflow=call('regional','GET','/workflows/'+case['workflow_definition_id'])
    assert any(row['id']==EVC for row in workflow['stages'])
    # Move through the published edge; never skip an unconfigured stage.
    if notice['status']!='resolved':
        if notice['items'][0]['resolution_status']!='submitted':
            result=call('institution','POST',f'/deficiency-notices/{NOTICE}/responses',{
                'item_responses':[{'item_id':ITEM,'related_document_id':DOCUMENT,'document_version_id':VERSION,
                    'narrative':'Recording demonstration: public Delhi Fire Service sample PDF uploaded and attached as test evidence. This is not a renewed Cedar Institute certificate.'}],
                'reason':'Project owner requested demo recording preparation; sample evidence only'})
            log('phase 03 versioned response persisted',result)
        result=call('scrutiny','POST',f'/deficiency-items/{ITEM}/resolve',{
            'resolution_status':'accepted',
            'reason':'Project-owner-authorized recording demonstration: accept the public sample for prototype workflow testing only; no real institutional certification asserted'})
        log('phase 04 scrutiny acceptance persisted',result)
    case=call('regional','GET',f'/applications/{CASE}')
    visits=call('regional','GET',f'/evc-visits?application_id={CASE}')['data']
    if not visits:
        history=call('regional','GET',f'/applications/{CASE}/history')['data']
        current=next((row['to_stage_id'] for row in reversed(history)),None)
        if current!=DEFICIENCY:
            case=call('regional','POST',f'/applications/{CASE}/transitions',{
                'to_stage_id':DEFICIENCY,'expected_version':case['version'],
                'reason':'User-authorized recording setup: traverse configured deficiency stage after resolution'})
            log('configured deficiency stage history',case)
        result=call('regional','POST',f'/applications/{CASE}/transitions',{
            'to_stage_id':EVC,'expected_version':case['version'],
            'reason':'User-authorized recording setup: resolved demo deficiency referred to configured EVC stage'})
        log('phase 04 configured EVC referral persisted',result)
    notices=call('regional','GET',f'/applications/{CASE}/deficiency-notices')['data']
    notice=next(row for row in notices if row['id']==NOTICE)
    assert notice['status']=='resolved' and notice['items'][0]['resolution_status']=='accepted'
    visits=call('regional','GET',f'/evc-visits?application_id={CASE}')['data']
    assert visits,'EVC work item must exist'
    final=call('regional','GET',f'/applications/{CASE}')
    history=call('regional','GET',f'/applications/{CASE}/history')['data']
    assert history[-1]['to_stage_id']==EVC
    log('final persisted verification',{'notice_status':notice['status'],'item_status':notice['items'][0]['resolution_status'],
        'application_status':final['status'],'current_stage':'EVC','visit_id':visits[0]['id'],'history_events':len(history)})
    print('VERDICT: PASS — requested demo case phases 01–04 persisted',flush=True)


if __name__=='__main__':main()
