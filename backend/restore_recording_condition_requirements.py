"""Repair the owner's dropped script checklist through the scoped normal API."""
import json
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app

CONDITION='0def79df-6df3-401c-ba69-e8a9a1d93c9c'
APPLICATION='76e9a91b-343a-5d90-8f73-8f96b7b83603'
REQUIREMENTS=['PWD Structural Safety Attestation','Geotagged Photographs']


def main():
    client=TestClient(app)
    login=client.post('/api/v1/prototype/session',json={'persona_id':'user-regional'})
    assert login.status_code==200,login.text
    headers={'Authorization':'Bearer '+login.json()['access_token']}
    response=client.get('/api/v1/compliance-conditions/'+CONDITION,headers=headers)
    assert response.status_code==200,response.text
    condition=response.json()
    assert condition['application_id']==APPLICATION
    assert condition['description']=='Submit certified seismic retrofitting compliance for Academic Block within 60 days.'
    if condition.get('evidence_requirements'):
        assert condition['evidence_requirements']==REQUIREMENTS,'Existing checklist differs; leave it unchanged'
        print('Checklist already restored; no duplicate update',flush=True)
    else:
        response=client.patch('/api/v1/compliance-conditions/'+CONDITION,headers={**headers,'Idempotency-Key':str(uuid4())},json={
            'evidence_requirements':REQUIREMENTS,'expected_version':condition['version'],
            'reason':'Restore the exact evidence checklist from the owner-supplied Phase08 recording script after the client dropped this field'})
        assert response.status_code==200,response.text
        print('PASS existing condition checklist repaired through scoped API',flush=True)
    response=client.get('/api/v1/compliance-conditions/'+CONDITION,headers=headers)
    assert response.status_code==200,response.text
    saved=response.json()
    assert saved['evidence_requirements']==REQUIREMENTS
    assert saved['status']=='open'
    Path('completion/condition-checklist-repair.json').write_text(json.dumps({key:saved[key] for key in ['id','application_id','status','version','evidence_requirements']},indent=2),encoding='utf-8')
    print('VERDICT: PASS - checklist persisted; condition remains open; no final decision made',flush=True)


if __name__=='__main__':main()
