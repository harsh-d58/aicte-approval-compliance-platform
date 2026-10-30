import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {test} from "node:test";
import ts from "typescript";

const root=fileURLToPath(new URL('../',import.meta.url));
function load(file,imports={}){
 const source=ts.transpileModule(readFileSync(resolve(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 new Function('module','exports','require',source)(module,module.exports,name=>{if(name in imports)return imports[name];throw Error(name);});
 return module.exports;
}
const fixtures=load('lib/portal/mock-data.ts');
const models=load('lib/portal/view-models.ts');
const commands=load('lib/portal/commands.ts',{'./view-models':models});
// Minimal asynchronous IndexedDB boundary, storing structured clones just as
// browsers do. It tests repository behavior rather than replacing its commands.
function storage(){
 const records=new Map();let created=false;
 return {records,open(){const request={};queueMicrotask(()=>{
  request.result={createObjectStore(){},close(){},transaction(){
   const tx={};const store={get(key){const req={};queueMicrotask(()=>{req.result=structuredClone(records.get(key));req.onsuccess?.();queueMicrotask(()=>tx.oncomplete?.());});return req;},put(value,key){records.set(key,structuredClone(value));}};
   tx.objectStore=()=>store;return tx;
  }};
  if(!created){created=true;request.onupgradeneeded?.();}request.onsuccess?.();
 });return request;}};
}
test('shared browser state persists persona changes, immutable snapshots and genuinely hashed audit events',async()=>{
 const previous=globalThis.indexedDB;const fake=storage();globalThis.indexedDB=fake;
 try{
  const dependencies={'../portal/commands':commands,'../portal/mock-data':fixtures,'../portal/view-models':models};
  const {demoRepository}=load('lib/demo/repository.ts',dependencies);
  const original=await demoRepository.snapshot();
  assert.equal((await demoRepository.verifyAudit()).valid,true);
  const mine=original.notifications.find(n=>n.recipientId==='user-institution');assert(mine);
  await demoRepository.execute({kind:'notification.read',id:mine.id,values:{read:!mine.read}},'user-institution',0);
  const restored=load('lib/demo/repository.ts',dependencies).demoRepository;
  assert.equal((await restored.snapshot()).notifications.find(n=>n.id===mine.id).read,!mine.read);
  const source=original.integrations[0];assert(source);
  await restored.execute({kind:'integration.test',id:source.id},'user-system',0);
  const updated=await restored.snapshot();
  assert.equal(updated.integrations.find(i=>i.id===source.id).status,'MOCK');
  assert.equal(updated.auditEvents.length,original.auditEvents.length+1);
  assert.match(updated.auditEvents.at(-1).eventHash,/^[a-f0-9]{64}$/);
  assert.equal(original.auditEvents.length,fixtures.mockData.auditEvents.length,'returned snapshot never mutated');
  assert.equal((await restored.verifyAudit()).valid,true);
  const simulated=await restored.verifyAudit(true);assert.equal(simulated.valid,false);assert.equal(simulated.simulation,true);
  assert.equal((await restored.verifyAudit()).valid,true,'simulation did not persist');
  const saved=fake.records.get('shared-demo');saved.data.auditEvents.at(-1).reason+=' altered';
  assert.equal((await restored.verifyAudit()).valid,false,'stored tampering is detected, not silently rehashed');
  await assert.rejects(restored.execute({kind:'integration.test',id:source.id},'user-institution',0),/not permitted/);
 }finally{globalThis.indexedDB=previous;}
});
test('preapproval undertaking is editable, links to the manual approval and rejects stale edits',()=>{
 let state=structuredClone(fixtures.mockData);
 const app=state.applications.find(a=>a.status==='DECISION_PENDING');assert(app);
 const actor=state.users.find(u=>u.id==='user-regional');
 function send(kind,id,values,expectedVersion){const result=commands.applyCommand(state,actor,0,{kind,id,values,expectedVersion});state=result.data;return result;}
 const condition=send('condition.create',app.id,{description:'Local seismic condition',requirements:'Attestation\nPhotographs',dueAt:'2026-12-30T10:00:00+05:30'}).id;
 assert.equal(state.conditions.find(c=>c.id===condition).sourceDecisionId,'');
 send('condition.update',condition,{requirements:'Attestation\nPhotographs\nReview notes',reason:'Clarify evidence'},1);
 assert.throws(()=>send('condition.update',condition,{requirements:'Old checklist',reason:'Stale'},1),/changed/);
 assert.deepEqual(state.conditions.find(c=>c.id===condition).evidenceRequired,['Attestation','Photographs','Review notes']);
 const visit=structuredClone(state.visits[0]);visit.id='test-completed-visit';visit.applicationId=app.id;visit.status='COMPLETED';state.visits.push(visit);
 state.meetingRecords.push({id:'test-report',visitId:visit.id,type:'EVC_REPORT',currentVersion:1,versions:[{number:1,status:'APPROVED',sections:[]}]});
 // This fixture case's configured prerequisites must still be satisfied by the
 // actual reducer, then the originally unlinked condition follows its decision.
 send('decision.record',app.id,{outcome:'APPROVE',reason:'Verified prototype prerequisites'});
 assert.ok(state.conditions.find(c=>c.id===condition).sourceDecisionId);
 assert.equal(state.conditions.find(c=>c.id===condition).status,'OPEN');
});
