"""Scoped report semantics shared with the portal's live record projection."""
from datetime import datetime, timezone
import json

def report_rows(code, data, filters, now=None):
 now=now or datetime.now(timezone.utc).isoformat()
 def days(start,end=now):
  if not start:return 0
  return max(0,int((datetime.fromisoformat(end.replace('Z','+00:00'))-datetime.fromisoformat(start.replace('Z','+00:00'))).total_seconds()//86400))
 def user(ident):return next((u['displayName'] for u in data['users'] if u['id']==ident),'Unassigned')
 inst={i['id']:i for i in data['institutions']}; region=filters.get('region_id'); start=filters.get('date_from',''); end=filters.get('date_to','')
 apps=[a for a in data['applications'] if (not region or inst.get(a['institutionId'],{}).get('regionId')==region) and (not filters.get('status') or a['status']==str(filters['status']).upper()) and (not a['submittedAt'] or ((not start or a['submittedAt'][:10]>=start) and (not end or a['submittedAt'][:10]<=end)))]
 ids={a['id'] for a in apps}; active=[a for a in apps if a['status'] not in ('DRAFT','CLOSED','REJECTED','WITHDRAWN')]
 conditions=[c for c in data['conditions'] if c['applicationId'] in ids]; visits=[v for v in data['visits'] if v['applicationId'] in ids]
 code=code.removeprefix('DEMO-').lower().replace('_','-'); rows=[]
 if code=='region-performance':
  for r in data['regions']:
   if region and r['id']!=region:continue
   cases=[a for a in apps if inst.get(a['institutionId'],{}).get('regionId')==r['id'] and a['submittedAt']]; case_ids={a['id'] for a in cases}; closed=[a for a in cases if a['closure']]; evc=[v for v in visits if v['applicationId'] in case_ids]; cs=[c for c in conditions if c['applicationId'] in case_ids]
   avg=int(sum(days(a['submittedAt'],a['closure']['at']) for a in closed)/len(closed)+.5) if closed else 0
   rows.append({'Region':r['name'],'Received':len(cases),'Completed':len(closed),'Stage pendency':', '.join(a['currentStage'] for a in active if a['id'] in case_ids),'Processing time':str(avg)+' days (closed cases)' if closed else 'No closed cases','Overdue':sum(bool(a['dueAt'] and a['dueAt']<now and not a['closure']) for a in cases),'EVC completion':str(sum(v['status']=='COMPLETED' for v in evc))+'/'+str(len(evc)),'Compliance':str(sum(c['status']=='CLOSED' for c in cs))+'/'+str(len(cs))+' closed'})
 elif code=='application-pendency':
  rows=[{'Application':a['number'],'Institution':inst.get(a['institutionId'],{}).get('name',a['institutionId']),'Stage':a['currentStage'],'Stage age':days(a['stageEnteredAt']),'Application age':days(a['submittedAt']),'Deadline':a['dueAt'] or 'Not applicable','Overdue duration':days(a['dueAt']),'Owner':user(a['ownerId']),'Next action':a['nextAction']} for a in active]
 elif code=='evc-status':
  experts={e['id']:e for e in data['experts']}; apps_by_id={a['id']:a for a in apps}
  for v in visits:
   ss=[s for s in data['slots'] if s['visitId']==v['id']]; proposed=next((s for s in ss if s['feasible']),{}); confirmed=next((s for s in ss if s['id']==v['confirmedSlotId']),{}); record=next((r for r in data['meetingRecords'] if r['visitId']==v['id'] and r['type']=='EVC_REPORT'),{}); version=next((r for r in record.get('versions',[]) if r['number']==record.get('currentVersion')),{})
   rows.append({'Application':apps_by_id.get(v['applicationId'],{}).get('number',v['applicationId']),'Selected committee':', '.join(user(experts.get(m['expertId'],{}).get('userId')) for m in v['committee']),'Proposed date':proposed.get('startAt','Not applicable'),'Confirmed date':confirmed.get('startAt','Not applicable'),'Scheduling status':v['status'],'Deadline':v['requiredBy'],'Conflicts':'; '.join(b for s in ss if not s['feasible'] for b in s['blockers']) or 'None','Visit status':v['status'],'Report status':version.get('status','Not started')})
 elif code=='undertaking-compliance':
  for c in conditions:
   evidence=max((e for e in data['evidence'] if e['conditionId']==c['id']),key=lambda e:e['submissionNumber'],default={}); verification=next((v for v in data['verifications'] if v['evidenceId']==evidence.get('id')),{}); escalation=next((e for e in data['escalations'] if e['entityId']==c['id']),{})
   rows.append({'Condition':c['code'],'Due date':c['dueAt'],'Evidence status':'SUBMITTED' if evidence else 'NOT_SUBMITTED','Verification status':verification.get('result',c['status']),'Overdue days':0 if c['status']=='CLOSED' else days(c['dueAt']),'Reviewer':user(c['reviewerId']),'Escalation':escalation.get('status','None')})
 elif code=='document-validity':
  for d in data['documents']:
   if d['applicationId'] and d['applicationId'] not in ids:continue
   if region and inst.get(d['institutionId'],{}).get('regionId')!=region:continue
   v=next((v for v in d['versions'] if v['id']==d['currentVersionId']),{}); renewal=next((r for r in data['renewals'] if r['documentId']==d['id']),{})
   rows.append({'Institution':inst.get(d['institutionId'],{}).get('name',d['institutionId']),'Document type':d['type'],'Issue date':v.get('issuedAt') or 'Not applicable','Expiry date':(v.get('expiryDate') or 'Not applicable') if d['supportsExpiry'] else 'Not applicable','Version':v.get('number',0),'Verification status':v.get('verification','PENDING'),'Renewal status':renewal.get('status','Not required')})
 elif code=='overdue-actions':
  for t in data['tasks']:
   if t['status']!='COMPLETED' and t['dueAt'] and t['dueAt']<now and (not t['applicationId'] or t['applicationId'] in ids):rows.append({'Entity type':'TASK','Case':t['applicationId'] or '','Action':t['title'],'Owner':user(t['ownerId']),'Due date':t['dueAt'],'Overdue duration':days(t['dueAt']),'Escalation level':0,'Resolution':t['status']})
  for c in conditions:
   if c['status']!='CLOSED' and c['dueAt'] and c['dueAt']<now:
    escalation=next((e for e in data['escalations'] if e['entityId']==c['id']),{})
    rows.append({'Entity type':'CONDITION','Case':c['applicationId'],'Action':c['description'],'Owner':user(c['reviewerId']),'Due date':c['dueAt'],'Overdue duration':days(c['dueAt']),'Escalation level':escalation.get('level',0),'Resolution':c['status']})
 elif code=='notification-delivery':
  users={u['id']:u for u in data['users']}
  for n in data['notifications']:
   if (start and n['createdAt'][:10]<start) or (end and n['createdAt'][:10]>end):continue
   last=n['attempts'][-1] if n['attempts'] else {}; assignments=users.get(n['recipientId'],{}).get('assignments',[])
   rows.append({'Event':n['event'],'Recipient category':assignments[0]['role'] if assignments else 'Unknown','Channel':n['channel'],'Delivery status':n['status'],'Attempt count':len(n['attempts']),'Failure reason':last.get('failureReason') or 'None','Last attempt':last.get('at','Not attempted')})
 elif code=='case-closure':rows=[{'Application':a['number'],'Closure date':a['closure']['at'],'Final status':a['status'],'Closure authority':user(a['closure']['authorityId']),'Reason':a['closure']['reason'],'Duration':days(a['submittedAt'],a['closure']['at']),'Reopen status':'Reopened' if a['closure']['reopened'] else 'Not reopened'} for a in apps if a['closure']]
 column_filters=filters.get('column_filters') or {}
 if isinstance(column_filters,str):column_filters=json.loads(column_filters or '{}')
 query=str(filters.get('query') or '').lower()
 return [r for r in rows if (not query or query in ' '.join(str(v) for v in r.values()).lower()) and all(not value or str(r.get(key,''))==str(value) for key,value in column_filters.items())]
