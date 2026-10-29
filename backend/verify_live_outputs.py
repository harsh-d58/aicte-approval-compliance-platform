"""Real authenticated audit checks and frozen exports; no provider messages."""
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile
from fastapi.testclient import TestClient
from pypdf import PdfReader
from backend.app.main import app


def main():
    client = TestClient(app)
    session = client.post('/api/v1/prototype/session',json={'persona_id':'user-auditor'})
    assert session.status_code==200,session.text
    headers={'Authorization':'Bearer '+session.json()['access_token']}
    results={}
    for simulate in (False,True):
        response=client.get('/api/v1/audit/verify-chain',params={'simulate':str(simulate).lower()},headers=headers)
        assert response.status_code==200,response.text
        value=response.json()
        results['audit_simulation' if simulate else 'audit_actual']={key:value[key] for key in ('valid','total_events','errors','simulation','simulated_event_id','active_triggers')}
        if simulate:
            assert any(error['code']=='HASH_INVALID' and error['id']==value['simulated_event_id'] for error in value['errors'])
        print('PASS actual audit endpoint', 'simulation' if simulate else 'stored ledger','events',value['total_events'],'integrity',value['valid'],flush=True)
    catalogue=client.get('/api/v1/reports',headers=headers)
    assert catalogue.status_code==200,catalogue.text
    code=next(row['report_code'] for row in catalogue.json()['data'] if 'REGION' in row['report_code'])
    response=client.post('/api/v1/reports/'+code+'/runs',json={'format':'pdf','filters':{'date_from':'2026-01-01','date_to':'2026-12-31'}},headers={**headers,'Idempotency-Key':str(uuid4())})
    assert response.status_code==201,response.text
    run=response.json(); results['report_run_id']=run['id']
    output=Path('output/reports/live_verification');output.mkdir(parents=True,exist_ok=True)
    for format in ('csv','json','xlsx','pdf'):
        exported=client.get('/api/v1/report-runs/'+run['id']+'/download',params={'format':format},headers=headers)
        assert exported.status_code==200,(format,exported.text)
        content=exported.content
        if format=='pdf':
            assert content.startswith(b'%PDF-')
            assert len(PdfReader(BytesIO(content)).pages)>0
        elif format=='xlsx':
            with ZipFile(BytesIO(content)) as archive: assert 'xl/workbook.xml' in archive.namelist()
        elif format=='json':
            assert exported.json()['data']==run['data']
        else: assert b'Snapshot SHA-256' in content
        (output/('region-performance.'+format)).write_bytes(content)
        results[format]={'bytes':len(content),'path':str(output/('region-performance.'+format))}
        print('PASS frozen',format,len(content),'bytes',flush=True)
    Path('completion/live-output-evidence.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('VERDICT: PASS — endpoint behavior; audit integrity is reported separately',flush=True)


if __name__=='__main__':main()
