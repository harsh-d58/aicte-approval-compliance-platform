"""HTTP acceptance for the integrated prototype, using real database records."""
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app

def main():
 c=TestClient(app)
 headers={}
 snapshots={}
 for key in ['institution','scrutiny','regional','coordinator','expert-001','compliance','central','policy','auditor','system']:
  r=c.post('/api/v1/prototype/session',json={'persona_id':'user-'+key});assert r.status_code==200,(key,r.status_code,r.text)
  h={'Authorization':'Bearer '+r.json()['access_token']};headers[key]=h
  r=c.get('/api/v1/portal/snapshot',headers=h);assert r.status_code==200,(key,r.status_code,r.text)
  snapshots[key]=r.json()
  print('PASS',key,'applications',len(r.json()['applications']),'documents',len(r.json()['documents']),'visits',len(r.json()['visits']),flush=True)
 data=snapshots['institution'];institution=data['institutions'][0]
 workflow=next(w for w in data['workflows'] if w['status']=='PUBLISHED')
 app_type=next(a['applicationTypeId'] for a in data['applications'] if a['workflowId']==workflow['id'])
 body={'institution_id':institution['id'],'campus_id':institution['campuses'][0]['id'],'workflow_definition_id':workflow['id'],'application_type_id':app_type,'reason':'DEMO HTTP persistence acceptance'}
 idem='portal-http-proof-'+str(uuid4());h={**headers['institution'],'Idempotency-Key':idem}
 r=c.post('/api/v1/applications',json=body,headers=h);assert r.status_code==201,('create',r.status_code,r.text)
 created=r.json();r=c.post('/api/v1/applications',json=body,headers=h);assert r.status_code==201 and r.json()['id']==created['id'],('retry',r.status_code,r.text)
 print('PASS persisted draft and same-key retry',flush=True)
 r=c.post('/api/v1/applications/'+created['id']+'/submit',json={'expected_version':created['version'],'reason':'DEMO submitted through live HTTP'},headers={**headers['institution'],'Idempotency-Key':str(uuid4())})
 assert r.status_code==200,('submit',r.status_code,r.text)
 r=c.get('/api/v1/portal/snapshot',headers=headers['institution']);assert next(a for a in r.json()['applications'] if a['id']==created['id'])['status']=='SUBMITTED'
 print('PASS submit visible in refreshed snapshot',flush=True)
 r=c.post('/api/v1/applications/'+created['id']+'/decisions',json={'decision_type':'approve','decision_status':'approved','decision_authority':'Unauthorized institution','reason':'DEMO wrong role check','expected_version':2},headers=headers['institution'])
 assert r.status_code==403,('wrong role',r.status_code,r.text)
 print('PASS institution cannot approve a case',flush=True)
 r=c.get('/api/v1/reports',headers=headers['central']);assert r.status_code==200
 for definition in r.json()['data']:
  code=definition['report_code']
  run=c.post('/api/v1/reports/'+code+'/runs',json={'format':'csv','filters':{'date_from':'2026-01-01','date_to':'2026-12-31'}},headers={**headers['central'],'Idempotency-Key':str(uuid4())})
  assert run.status_code==201,(code,run.status_code,run.text)
  result=run.json();download=c.get('/api/v1/report-runs/'+result['id']+'/download',headers=headers['central'])
  assert download.status_code==200,(code,download.status_code,download.text)
  hidden=c.get('/api/v1/report-runs/'+result['id']+'/download',headers=headers['institution'])
  assert hidden.status_code==404,('foreign export',hidden.status_code)
  print('PASS report',code,'rows',len(result['data']),'frozen download / foreign denial',flush=True)
 print('VERDICT: PASS',flush=True)
if __name__=='__main__':main()
