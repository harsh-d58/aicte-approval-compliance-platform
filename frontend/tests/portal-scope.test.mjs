import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import { test } from "node:test";
import ts from "typescript";
import { createElement } from "react";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as jsxRuntime from "react/jsx-runtime";
const testDirectory = dirname(fileURLToPath(import.meta.url));
// Pure TypeScript view models have only erased type imports; no browser or test-runner dependency required.
function load(file, imports = {}) {
  const source = ts.transpileModule(readFileSync(resolve(testDirectory, "..", file), "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const target = { exports: {} };
  new Function("exports", "module", "require", source)(target.exports, target, name => {
    if (name in imports) return imports[name];
    throw new Error(`Unexpected test dependency: ${name}`);
  });
  return target.exports;
}
const { mockData } = load("lib/portal/mock-data.ts");
const { scopedSnapshot, safeReturnTo, activeApplication } = load("lib/portal/view-models.ts");
const user = id => mockData.users.find(u => u.id === id);
const { compatibleEvidence, deficiencyResponses } = load("lib/live/deficiency-evidence.ts");
const { executeLiveCommand } = load("lib/live/commands.ts", {"./deficiency-evidence":{deficiencyResponses}});
const { confirmableVisitSlots } = load("lib/live/visit-slots.ts");
const { workspaceAssignmentIndex } = load("lib/live/workspace-scope.ts");
const { recordApprovalBlock } = load("lib/live/record-approval.ts");
const { decisionState } = load("lib/live/decision-state.ts");

test("live decisions preserve approve, reject and close as different server outcomes", async () => {
  const bodies=[];
  for (const outcome of ["APPROVE","REJECT","CLOSE"]) {
    await executeLiveCommand({kind:"decision.record",id:"case",values:{outcome,reason:"Recorded determination"}},{applications:[{id:"case",version:2}]},{post:async(path,body)=>{bodies.push(body);return {};}});
  }
  assert.deepEqual(bodies.map(body=>[body.decision_type,body.decision_status]),[["approve","approved"],["reject","rejected"],["close","approved"]]);
});

test("approval condition saves the entered evidence checklist and evidence sends exact versions", async () => {
  const requests=[];
  const client={post:async(path,body)=>{requests.push({path,body});return {id:"condition"};}};
  const data={applications:[{id:"case",institutionId:"institution"}],decisions:[]};
  await executeLiveCommand({kind:"condition.create",id:"case",values:{description:"Seismic attestation",requirements:" PWD Structural Safety Attestation \nGeotagged Photographs\n",dueAt:"2026-12-30T12:00"}},data,client);
  assert.deepEqual(requests[0].body.evidence_requirements,["PWD Structural Safety Attestation","Geotagged Photographs"]);
  await executeLiveCommand({kind:"evidence.submit",id:"condition",values:{documentVersionIds:["exact-version"]}},data,client);
  assert.deepEqual(requests[1].body.document_version_ids,["exact-version"]);
});

test("decision workspace blocks pending EVC and case closure with open conditions", () => {
  const data={conditions:[],deficiencies:[],workflows:[{id:"workflow",stages:[{code:"CUSTOM_INSPECTION",type:"evc"}]}],visits:[],meetingRecords:[]};
  const application={id:"case",workflowId:"workflow",stageType:"decision",currentStage:"FINAL_REVIEW",status:"DECISION_PENDING"};
  assert.match(decisionState(data,application).blocker,/Complete the EVC visit/);
  data.visits=[{id:"visit",applicationId:"case",status:"COMPLETED"}];
  data.meetingRecords=[{visitId:"visit",type:"EVC_REPORT",currentVersion:2,versions:[{number:2,status:"APPROVED"}]}];
  assert.deepEqual(decisionState(data,application).outcomes,["APPROVE","REJECT"]);
  data.conditions=[{applicationId:"case",status:"OPEN"}];
  assert.match(decisionState(data,{...application,status:"APPROVED"}).blocker,/Close every verified approval condition/);
  data.conditions[0].status="CLOSED";
  assert.deepEqual(decisionState(data,{...application,status:"APPROVED"}).outcomes,["CLOSE"]);
});

test("decision page displays a saved condition with evidence requirements and its live link", () => {
  const data={applications:[{id:"case",number:"CASE-001",workflowId:"workflow",stageType:"decision",currentStage:"DECISION",status:"DECISION_PENDING",version:1}],
    conditions:[{id:"condition",code:"COND-001",applicationId:"case",description:"Seismic condition",evidenceRequired:["Attestation","Photographs"],dueAt:"2026-12-30",status:"OPEN",sourceDecisionId:"",version:1}],
    deficiencies:[],workflows:[{id:"workflow",stages:[{code:"EVC",type:"evc"}]}],visits:[],meetingRecords:[],decisions:[],users:[]};
  const {default:Workspace}=load("app/portal-ui/DecisionAndClosure.tsx",{
    "react/jsx-runtime":jsxRuntime,"@/lib/live/decision-state":{decisionState},
    "./domain-ui":{useWorkspace:()=>({data,allowed:(...roles)=>roles.includes("REGIONAL")}),
      Panel:({title,children})=>createElement("section",null,title,children),
      Table:({rows})=>createElement("div",null,...rows.flat()),
      Field:()=>null,ActionForm:({children})=>createElement("form",null,children),ReasonAction:()=>null,
      Link:({children,...props})=>createElement("a",props,children),Badge:({status})=>createElement("span",null,status),s:{},formatDateTime:value=>value}
  });
  const html=renderToStaticMarkup(createElement(Workspace,{applicationId:"case"}));
  assert.match(html,/Seismic condition/);assert.match(html,/Attestation; Photographs/);
  assert.match(html,/href="\/portal\/compliance\/condition"/);
  assert.match(html,/Complete the EVC visit and approve its report/);
});

test("EVC approval explains the missing completed visit while minutes stay independent", () => {
  assert.match(recordApprovalBlock({type:"EVC_REPORT",visitId:"visit"},[{id:"visit",status:"CONFIRMED"}]),/Complete the EVC visit/);
  assert.equal(recordApprovalBlock({type:"EVC_REPORT",visitId:"visit"},[{id:"visit",status:"COMPLETED"}]),"");
  assert.equal(recordApprovalBlock({type:"MINUTES",visitId:"visit"},[{id:"visit",status:"CONFIRMED"}]),"");
});

test("expert login selects a real committee scope instead of an unused first assignment", () => {
  const expert={id:"aditi",assignments:[{role:"EVC_EXPERT",scope:{type:"APPLICATION",id:"unused"}},{role:"EVC_EXPERT",scope:{type:"APPLICATION",id:"assigned"}}]};
  const data={experts:[{id:"profile",userId:"aditi"}],visits:[{id:"visit",applicationId:"assigned",committee:[{expertId:"profile"}]}]};
  assert.equal(workspaceAssignmentIndex(data,expert,0),1);
  assert.equal(workspaceAssignmentIndex(data,expert,1),1);
  assert.equal(workspaceAssignmentIndex({...data,visits:[]},expert,0),0);
});

test("expert scope selection never grants an unassigned visit or changes another role", () => {
  const data={experts:[{id:"someone-else",userId:"other"}],visits:[{id:"visit",applicationId:"assigned",committee:[{expertId:"someone-else"}]}]};
  assert.equal(workspaceAssignmentIndex(data,{id:"aditi",assignments:[{role:"EVC_EXPERT",scope:{type:"APPLICATION",id:"unused"}},{role:"EVC_EXPERT",scope:{type:"APPLICATION",id:"assigned"}}]},0),0);
  assert.equal(workspaceAssignmentIndex(data,{id:"regional",assignments:[{role:"REGIONAL",scope:{type:"REGION",id:"north"}}]},0),0);
});

test("confirmed visits cannot expose another confirmation action", async () => {
  const visit={id:"visit",status:"CONFIRMED"};
  const slots=[{id:"slot",visitId:"visit",feasible:true,expiresAt:"2099-01-01",startAt:"2098-01-01",endAt:"2098-01-02",rank:1}];
  assert.deepEqual(confirmableVisitSlots(visit,slots),[]);
  let requests=0;
  await assert.rejects(executeLiveCommand({kind:"visit.confirm",id:"visit",values:{slotId:"slot"}},{applications:[],visits:[visit],slots},{post:async()=>{requests++;return {};}}),/already confirmed/);
  assert.equal(requests,0);
});

test("slot picker excludes expired proposals and keeps the newest duplicate interval", () => {
  const common={visitId:"visit",feasible:true,startAt:"2026-11-05T09:00:00Z",endAt:"2026-11-05T17:00:00Z",rank:1};
  const slots=[{...common,id:"expired",expiresAt:"2026-10-29T18:52:00Z"},{...common,id:"current",expiresAt:"2026-10-30T18:52:00Z"},{...common,id:"newer",expiresAt:"2026-10-30T20:00:00Z"}];
  assert.deepEqual(confirmableVisitSlots({id:"visit",status:"PROPOSED"},slots,Date.parse("2026-10-29T22:00:00Z")).map(slot=>slot.id),["newer"]);
});

test("correction upload stays on the notice and exposes a local file chooser", () => {
  const data={applications:[{id:"case",institutionId:"institution"}],deficiencies:[{id:"notice",applicationId:"case",items:[{id:"item",status:"OPEN",documentId:"fire",criterion:"FIRE"}]}],documents:[{id:"fire",institutionId:"institution",type:"FIRE",versions:[]}],configurations:[]};
  const {default:Picker}=load("app/portal-ui/CorrectionEvidencePicker.tsx",{
    react:React,"react/jsx-runtime":jsxRuntime,
    "@/lib/live/deficiency-evidence":{compatibleEvidence},
    "@/lib/portal/files":{putFile:async()=>{}},
    "./domain-ui":{useWorkspace:()=>({data,execute:async()=>{throw new Error("Unexpected submit")}}),humanize:value=>value,s:{}}
  });
  const html=renderToStaticMarkup(createElement(Picker,{applicationId:"case",noticeId:"notice",itemId:"item"}));
  assert.match(html,/type="file"/);
  assert.match(html,/<button type="button"[^>]*>Upload correction evidence<\/button>/);
  assert(!html.includes('href='));
  assert.match(html,/name="evidence-item"/);
});

test("live response command sends the selected version to the real API contract", async () => {
  const data={applications:[{id:"case",institutionId:"institution"}],deficiencies:[{id:"notice",applicationId:"case",items:[{id:"item",status:"OPEN",documentId:"fire"}]}],documents:[{id:"fire",institutionId:"institution",type:"FIRE",versions:[{id:"v2",verification:"PENDING"}]}]};
  let posted;
  await executeLiveCommand({kind:"deficiency.respond",id:"notice",values:{documentVersionIds:["v2"],response:"Renewed evidence supplied"}},data,{post:async(path,body)=>{posted={path,body};return {};}});
  assert.equal(posted.path,"/deficiency-notices/notice/responses");
  assert.equal(posted.body.item_responses[0].document_version_id,"v2");
  assert.equal(posted.body.item_responses[0].related_document_id,"fire");
});

test("scrutiny cannot accept an open item before institutional submission", async () => {
  let requests=0;
  const data={applications:[],deficiencies:[{id:"notice",items:[{id:"item",status:"OPEN"}]}]};
  await assert.rejects(executeLiveCommand({kind:"deficiency.resolve",id:"notice",values:{itemId:"item",resolution:"ACCEPTED"}},data,{post:async()=>{requests++;return {};}}),/must submit/);
  assert.equal(requests,0);
});

test("batch determination reviews submitted responses and skips untouched items", async () => {
  const paths=[];
  const keys=[];
  const data={applications:[],deficiencies:[{id:"notice",items:[{id:"open",status:"OPEN"},{id:"ready",status:"RESPONDED"},{id:"ready-two",status:"RESPONDED"},{id:"done",status:"RESOLVED"}]}]};
  await executeLiveCommand({kind:"deficiency.resolve",id:"notice",values:{reason:"Reviewed submitted correction"}},data,{post:async(path,body,headers)=>{paths.push(path);keys.push(headers['Idempotency-Key']);return {};}});
  assert.deepEqual(paths,["/deficiency-items/ready/resolve","/deficiency-items/ready-two/resolve"]);
  assert.notEqual(keys[0],keys[1]);
});

test("live deficiency response submits the checked exact version and document ID", () => {
  const data = { applications:[{id:"case",institutionId:"institution"}], deficiencies:[{id:"notice",applicationId:"case",items:[{id:"item",documentId:"fire",status:"OPEN",criterion:"FIRE"}]}], documents:[
    {id:"fire",institutionId:"institution",applicationId:null,type:"FIRE",versions:[{id:"fire-v2",verification:"PENDING"}]}
  ]};
  const result = deficiencyResponses(data,"notice",{documentVersionIds:["fire-v2"],response:"Renewed certificate attached"});
  assert.deepEqual(result,[{item_id:"item",related_document_id:"fire",document_version_id:"fire-v2",narrative:"Renewed certificate attached"}]);
});

test("correction picker excludes sibling cases and wrong mandated document types", () => {
  const data = {applications:[{id:"case",institutionId:"institution"}],documents:[
    {id:"fire",institutionId:"institution",applicationId:null,type:"FIRE",versions:[{id:"valid",verification:"PENDING"}]},
    {id:"sibling",institutionId:"institution",applicationId:"other-case",type:"FIRE",versions:[{id:"wrong-case",verification:"VERIFIED"}]},
    {id:"land",institutionId:"institution",applicationId:"case",type:"LAND",versions:[{id:"wrong-type",verification:"VERIFIED"}]}
  ]};
  assert.deepEqual(compatibleEvidence(data,data.applications[0],{documentId:"fire"}).map(row=>row.version.id),["valid"]);
});

test("itemized correction preserves different versions per item and skips resolved items", () => {
  const data={applications:[{id:"case",institutionId:"institution"}], deficiencies:[{id:"notice",applicationId:"case",items:[
    {id:"one",documentId:"fire",status:"OPEN"},{id:"two",documentId:"land",status:"OPEN"},{id:"done",status:"RESOLVED"}]}],documents:[
    {id:"fire",institutionId:"institution",type:"FIRE",versions:[{id:"fv2",verification:"PENDING"}]},
    {id:"land",institutionId:"institution",type:"LAND",versions:[{id:"lv3",verification:"PENDING"}]}
  ]};
  const result=deficiencyResponses(data,"notice",{response:"Corrections supplied",itemResponses:[{itemId:"one",versionId:"fv2"},{itemId:"two",versionId:"lv3"}]});
  assert.deepEqual(result.map(row=>row.document_version_id),["fv2","lv3"]);
  assert.throws(()=>deficiencyResponses(data,"notice",{response:"Text alone is not an uploaded file"}),/compatible evidence version/);
});

test("institution dashboard and application register share only the assigned institution", () => {
  const data = scopedSnapshot(mockData, user("user-institution"), 0);
  assert.equal(data.applications.length, 5);
  assert.equal(data.applications.filter(a => activeApplication(a.status)).length, 4);
  assert.deepEqual(data.institutions.map(i => i.id), ["inst-001"]);
  assert(data.applications.every(a => a.institutionId === "inst-001"));
  assert(!data.applications.some(a => a.id === "app-003"));
  assert(data.notifications.every(n => n.recipientId === "user-institution"));
});
test("regional scope excludes south-region cases and associated records", () => {
  const data = scopedSnapshot(mockData, user("user-regional"), 0);
  assert(data.institutions.every(i => i.regionId === "region-west"));
  assert(!data.applications.some(a => ["app-008", "app-011", "app-012", "app-013"].includes(a.id)));
  assert(data.tasks.every(t => data.applications.some(a => a.id === t.applicationId)));
});
test("scrutiny users see assigned cases, rather than every case in their region", () => {
  const data = scopedSnapshot(mockData, user("user-scrutiny"), 0);
  assert(data.applications.every(a => a.ownerId === "user-scrutiny"));
  assert(!data.applications.some(a => a.status === "DRAFT"));
});
test("expert switching visits changes case scope and never exposes institution-wide documents", () => {
  const expert = user("user-expert-001");
  const first = scopedSnapshot(mockData, expert, 0);
  const second = scopedSnapshot(mockData, expert, 1);
  assert.deepEqual(first.visits.map(v => v.id), ["visit-001"]);
  assert.deepEqual(first.applications.map(a => a.id), ["app-002"]);
  assert.deepEqual(second.visits.map(v => v.id), ["visit-002"]);
  assert.deepEqual(second.applications.map(a => a.id), ["app-003"]);
  assert.equal(first.documents.length, 0);
  assert.equal(second.conditions.length, 0);
});
test("export categories and operational queues are role restricted", () => {
  const institution = scopedSnapshot(mockData, user("user-institution"), 0);
  assert.equal(institution.reportDefinitions.length, 0);
  assert.equal(institution.jobs.length, 0);
  assert.equal(scopedSnapshot(mockData, user("user-system"), 0).jobs.length, 3);
});
test("sign-in destinations reject external, malformed and unbuilt routes", () => {
  for (const value of ["https://example.com", "//example.com", "/portal/unknown", "/portal/../login", "javascript:alert(1)", "/\\example.com"]) assert.equal(safeReturnTo(value), "/portal");
  assert.equal(safeReturnTo("/portal/evc/visit-001/schedule"), "/portal/evc/visit-001/schedule");
  assert.equal(safeReturnTo("/portal/applications/app-001?tab=documents"), "/portal/applications/app-001?tab=documents");
  assert.equal(safeReturnTo("/portal/tasks?status=BLOCKED"), "/portal/tasks?status=BLOCKED");
});

const models=load("lib/portal/view-models.ts");
const {applyCommand,recommendVisit,workflowErrors}=load("lib/portal/commands.ts",{"./view-models":models});
const {getReportRows}=load("lib/portal/report-rows.ts",{"./view-models":models});
const writers=load("lib/portal/exports.ts");
const analytics=load("lib/portal/analytics.ts",{"./view-models":models});
const command=(data,actor,kind,id,values={},expectedVersion)=>applyCommand(data,data.users.find(u=>u.id===actor),0,{kind,id,values,expectedVersion});
test("commands reject disallowed roles and out-of-scope records atomically",()=>{
 const original=JSON.stringify(mockData);
 assert.throws(()=>command(mockData,"user-institution","decision.record","app-001",{reason:"Test",outcome:"APPROVE"}),/not permitted/);
 assert.throws(()=>command(mockData,"user-institution","application.submit","app-008",{declaration:true}),/scope/);
 assert.equal(JSON.stringify(mockData),original);
});
test("draft submission preserves exact versions, creates history and rejects a duplicate",()=>{
 const source=structuredClone(mockData);source.documents.find(d=>d.id==="doc-lease").applicationId=null;
 const r=command(source,"user-institution","application.submit","app-005",{declaration:true},1);
 assert.equal(r.data.applications.find(a=>a.id==="app-005").status,"SUBMITTED");
 assert.equal(r.data.submissions.filter(s=>s.applicationId==="app-005").length,1);
 assert(r.data.stageEvents.some(e=>e.applicationId==="app-005"));
 assert(r.data.tasks.some(e=>e.applicationId==="app-005"));
 assert.throws(()=>command(r.data,"user-institution","application.submit","app-005",{declaration:true}),/already/);
 assert.throws(()=>command(r.data,"user-scrutiny","application.advance","app-005",{reason:"Start"},1),/changed/);
});
test("deficiency response produces a numbered submission and requires manual resolution",()=>{
 const r=command(mockData,"user-institution","deficiency.respond","notice-001",{response:"Corrected lease attached",documentVersionIds:["version-lease-2"]});
 const app=r.data.applications.find(a=>a.id==="app-001");assert.equal(app.status,"RESUBMITTED");
 assert(r.data.submissions.some(s=>s.noticeId==="notice-001"&&s.documentVersionIds.includes("version-lease-2")));
 const started=command(r.data,"user-scrutiny","application.advance",app.id,{reason:"Review corrected evidence"});
 assert.throws(()=>command(started.data,"user-scrutiny","application.advance",app.id,{reason:"Finish"}),/Resolve all/);
 const resolved=command(started.data,"user-scrutiny","deficiency.resolve","notice-001",{reason:"Evidence reviewed"});
 assert.equal(resolved.data.deficiencies.find(n=>n.id==="notice-001").status,"RESOLVED");
});
test("uploads append versions without changing earlier evidence and enforce file limits",()=>{
 const values={institutionId:"inst-001",type:"LEASE",applicationId:"app-001",issuedAt:"2026-01-01",expiryDate:"2028-01-01",sizeBytes:1024,mimeType:"application/pdf",versionId:"local-test",fileName:"lease.pdf",issuer:"Demo",reference:"R1"};
 const r=command(mockData,"user-institution","document.save","doc-lease",values);
 assert.equal(r.data.documents.find(d=>d.id==="doc-lease").versions.length,3);
 assert.deepEqual(r.data.documents.find(d=>d.id==="doc-lease").versions[0],mockData.documents.find(d=>d.id==="doc-lease").versions[0]);
 assert.equal(r.data.documents.find(d=>d.id==="doc-lease").versions.at(-1).verification,"PENDING");
 assert.throws(()=>command(mockData,"user-institution","document.save","doc-lease",{...values,sizeBytes:20*1024*1024}),/10 MB/);
});
test("scheduling checks all exact selected experts, freshness, busy intervals and membership",()=>{
 assert(recommendVisit(mockData,"visit-001").candidates.some(c=>!c.blockers.length));
 const stale=structuredClone(mockData);stale.availability.filter(a=>a.participantId==="expert-005").forEach(a=>a.confirmedAt="2026-10-01T12:00:00+05:30");
 assert(recommendVisit(stale,"visit-001").blockers.some(b=>b.includes("expert-005")));
 const missing=structuredClone(mockData);missing.visits[0].committee.pop();assert(recommendVisit(missing,"visit-001").blockers.some(b=>b.includes("exactly")));
 const duplicate=mockData.visits[0].committee.map(m=>m.expertId);duplicate[4]=duplicate[0];
 assert.throws(()=>command(mockData,"user-regional","committee.save","visit-001",{expertIds:duplicate,reason:"Test"}),/distinct/);
 const r=command(mockData,"user-coordinator","visit.recommend","visit-001");const slot=r.data.slots.find(s=>s.visitId==="visit-001"&&s.feasible);
 assert(slot);const confirmed=command(r.data,"user-coordinator","visit.confirm","visit-001",{slotId:slot.id,reason:"All participants confirmed"});
 assert.equal(confirmed.data.visits[0].status,"CONFIRMED");assert(confirmed.data.invitations.length>=5);
 const institutionalInvite=confirmed.data.invitations.find(i=>i.visitId==="visit-001"&&i.recipientId==="user-institution");assert(institutionalInvite);
 const acknowledged=command(confirmed.data,"user-institution","invitation.respond",institutionalInvite.id,{response:"ACCEPTED"});assert.equal(acknowledged.data.invitations.find(i=>i.id===institutionalInvite.id).response,"ACCEPTED");
});
test("evidence upload never closes a condition; verified result and closure are separate",()=>{
 const r=command(mockData,"user-institution","evidence.submit","condition-001",{documentVersionIds:["version-safety-2"]});
 assert.equal(r.data.conditions[0].status,"EVIDENCE_SUBMITTED");
 assert.throws(()=>command(r.data,"user-compliance","condition.close","condition-001",{reason:"Close"}),/Verified compliant/);
 const verified=command(r.data,"user-compliance","evidence.verify","condition-001",{result:"COMPLIANT",reason:"Evidence reviewed against sample requirements"});
 assert.equal(verified.data.conditions[0].status,"VERIFIED_COMPLIANT");
 const closed=command(verified.data,"user-compliance","condition.close","condition-001",{reason:"Verified evidence accepted"});assert.equal(closed.data.conditions[0].status,"CLOSED");
});
test("approved meeting records create new correction versions rather than overwriting history",()=>{
 const record=mockData.meetingRecords.find(r=>r.id==="record-002");
 const original=structuredClone(record.versions[0]);const observations=mockData.observations.filter(o=>o.visitId===record.visitId&&o.status==="SUBMITTED");
 const sections=[{title:"Reviewed observations",text:"Reviewed source evidence",sourceIds:observations.map(o=>o.id),warning:null}];
 const r=command(mockData,"user-regional","record.save",record.id,{reason:"Corrected transcription",sections},record.currentVersion);
 assert.deepEqual(r.data.meetingRecords.find(r=>r.id===record.id).versions[0],original);
 assert.equal(r.data.meetingRecords.find(r=>r.id===record.id).currentVersion,record.currentVersion+1);
});
test("workflow validation detects disconnected stages and published edits clone",()=>{
 const w=mockData.workflows[0];assert.equal(workflowErrors(w).length,0);
 assert(workflowErrors({...w,transitions:[]}).some(e=>e.includes("reachable")));
 const r=command(mockData,"user-policy","workflow.save",w.id,{name:w.name,aphVersion:w.aphVersion,stages:w.stages,transitions:w.transitions});
 assert.notEqual(r.id,w.id);assert.equal(r.data.workflows.find(v=>v.id===w.id).status,"PUBLISHED");
});
test("all eight report selectors reconcile to declared columns and scoped data",()=>{
 assert.equal(mockData.reportDefinitions.length,8);for(const definition of mockData.reportDefinitions){const rows=getReportRows(definition.id,mockData);for(const row of rows)for(const column of definition.columns)assert(column in row,`${definition.id}: ${column}`);}
 const regional=scopedSnapshot(mockData,user("user-regional"),0);assert.equal(getReportRows("evc-status",regional).length,regional.visits.length);
});
test("a stale identity cannot execute after its canonical record is disabled",()=>{
 const source=structuredClone(mockData);source.users.find(u=>u.id==="user-institution").status="DISABLED";
 assert.throws(()=>applyCommand(source,user("user-institution"),0,{kind:"application.submit",id:"app-005",values:{declaration:true}}),/disabled/);
});
test("corrected availability preserves the old interval and excludes it from recommendations",()=>{
 const source=structuredClone(mockData);const interval=source.availability.find(a=>a.participantId==="inst-001"&&a.state==="AVAILABLE");
 const r=command(source,"user-institution","availability.save",interval.id,{participantId:"inst-001",participantType:"INSTITUTION",startAt:interval.startAt,endAt:interval.endAt,state:"BUSY"});
 assert(r.data.availability.find(a=>a.id===interval.id).supersededAt);
 assert.equal(r.data.availability.find(a=>a.id===r.id).supersedesId,interval.id);
 assert(!recommendVisit(r.data,"visit-001").candidates.some(c=>c.startAt===new Date(interval.startAt).toISOString()&&!c.blockers.length));
});
test("generated records show missing template sources and cannot be approved",()=>{
 const r=command(mockData,"user-coordinator","record.generate","visit-002",{type:"EVC_REPORT"});
 const record=r.data.meetingRecords.find(m=>m.id===r.id);assert(record.versions[0].sections.some(s=>s.warning));
 assert.throws(()=>command(r.data,"user-coordinator","record.review",r.id),/Complete the draft/);
});
test("published committee rule changes apply to future visits while existing visits retain policy",()=>{
 let source=structuredClone(mockData);source.documents.find(d=>d.id==="doc-lease").applicationId=null;source.documents.find(d=>d.id==="doc-lease").versions.find(v=>v.id==="version-lease-2").verification="VERIFIED";
 const config=command(source,"user-policy","config.save","committee-rule-001",{name:"Four-member sample",values:{memberCount:4,durationMinutes:120,availabilityFreshnessHours:12,preparationLeadHours:24}});
 const published=command(config.data,"user-policy","config.publish",config.id,{reason:"Approved sample change for demonstration"});
 const submitted=command(published.data,"user-institution","application.submit","app-005",{declaration:true});const started=command(submitted.data,"user-scrutiny","application.advance","app-005",{reason:"Start"});const advanced=command(started.data,"user-scrutiny","application.advance","app-005",{reason:"All current evidence verified"});
 const visit=advanced.data.visits.find(v=>v.applicationId==="app-005");assert.equal(visit.requiredMemberCount,4);assert.equal(visit.durationMinutes,120);assert.equal(visit.policy.freshnessHours,12);assert.equal(advanced.data.visits.find(v=>v.id==="visit-001").requiredMemberCount,5);
});
test("export snapshots remain fixed and CSV/XLSX/PDF contain genuine formats",async()=>{
 const rows=[{Name:"=not-a-formula",Count:4}];const created=command(mockData,"user-central","report.create",undefined,{reportCode:"application-pendency",dateFrom:"2026-01-01",dateTo:"2026-12-31"});
 const r=command(created.data,"user-central","report.complete",created.id,{rows,rowCount:1});rows[0].Count=99;assert.equal(r.data.reportRuns.find(r=>r.id===created.id).snapshotRows[0].Count,4);
 assert.match(await writers.csv(rows).text(),/'=not-a-formula/);
 const bytes=new Uint8Array(await writers.xlsx(rows).arrayBuffer());assert.deepEqual([...bytes.slice(0,4)],[80,75,3,4]);assert(new TextDecoder().decode(bytes).includes("xl/worksheets/sheet1.xml"));
 assert.match(await writers.pdf(rows).text(),/^%PDF-1\.4/);assert.match(await writers.pdf(rows).text(),/%%EOF$/);
});
test("analytics validates scope dimensions, applies OR within and AND across filters",()=>{
 const records=analytics.analyticsRecords(scopedSnapshot(mockData,user("user-regional"),0),"REGIONAL");
 const q=analytics.validateQuery({statuses:["IN_REVIEW","RETURNED_FOR_DEFICIENCY","MADE_UP"],regions:["region-west","region-south"],page:-3,dateFrom:"bad"},records);
 assert.deepEqual(q.regions,["region-west"]);assert.equal(q.page,1);assert.equal(q.dateFrom,"");
 const rows=analytics.filterAnalytics(records,q);assert(rows.length>0);assert(rows.every(r=>["IN_REVIEW","RETURNED_FOR_DEFICIENCY"].includes(r.status)&&r.regionId==="region-west"));
 assert(analytics.filterAnalytics(records,q,true).length>rows.length);
 assert.equal(analytics.groupAnalytics(records,"regionId").reduce((n,g)=>n+g.count,0),records.length);
 assert.equal(analytics.groupAnalytics([{...records[0],ownerId:""}],"ownerId")[0].count,1);
});
test("all ten dashboard datasets use their own domain grain",()=>{
 for(const role of Object.keys(analytics.dashboardCopy)){const account=mockData.users.find(u=>u.assignments.some(a=>a.role===role));const index=account.assignments.findIndex(a=>a.role===role);const scoped=scopedSnapshot(mockData,account,index);const records=analytics.analyticsRecords(scoped,role);assert(records.every(r=>r.id&&r.href.startsWith("/portal/")));if(role==="SYSTEM")assert.equal(records.length,scoped.jobs.length);if(role==="POLICY")assert.equal(records.length,scoped.workflows.length);if(role==="COMPLIANCE")assert.equal(records.length,scoped.conditions.length);}
});
test("a report snapshot cannot appear in another role identity's run list",()=>{
 const r=command(mockData,"user-central","report.create",undefined,{reportCode:"application-pendency",dateFrom:"2026-01-01",dateTo:"2026-12-31"});
 assert(!scopedSnapshot(r.data,user("user-regional"),0).reportRuns.some(run=>run.id===r.id));
});
test("the same expert cannot open a frozen report after switching visit assignments",()=>{
 const r=command(mockData,"user-expert-001","report.create",undefined,{reportCode:"evc-status",dateFrom:"2026-01-01",dateTo:"2026-12-31"});
 const actor=r.data.users.find(u=>u.id==="user-expert-001");assert(scopedSnapshot(r.data,actor,0).reportRuns.some(run=>run.id===r.id));assert(!scopedSnapshot(r.data,actor,1).reportRuns.some(run=>run.id===r.id));
 assert.throws(()=>applyCommand(r.data,actor,1,{kind:"report.complete",id:r.id,values:{rowCount:0,rows:[]}}),/unavailable/);
});
test("renewal submission rejects older and equal document versions",()=>{
 const source=structuredClone(mockData);source.renewals[0].previousVersionId="version-safety-2";
 assert.throws(()=>command(source,"user-institution","renewal.submit","renewal-001",{versionId:"version-safety-1"}),/newer/);
 assert.throws(()=>command(source,"user-institution","renewal.submit","renewal-001",{versionId:"version-safety-2"}),/newer/);
});
test("coherent EVC journey reaches approval, verified compliance and explicit closure",()=>{
 let state=structuredClone(mockData);const send=(actor,kind,id,values={})=>{const r=command(state,actor,kind,id,values);state=r.data;return r.id;};
 const app=state.applications.find(a=>a.id==="app-005");
 const docId=send("user-institution","document.save",undefined,{institutionId:app.institutionId,applicationId:app.id,type:"LEASE",issuedAt:"2026-01-01",expiryDate:"2028-01-01",issuer:"Demo issuer",reference:"TEST-JOURNEY",fileName:"demo.pdf",mimeType:"application/pdf",sizeBytes:1000,versionId:"journey-lease"});
 send("user-institution","application.submit",app.id,{declaration:true});send("user-scrutiny","application.advance",app.id,{reason:"Start review"});
 const check=send("user-scrutiny","document.check",docId,{versionId:"journey-lease",extracted:"2028-01-01"});send("user-scrutiny","document.review",check,{result:"ACCEPTED",reason:"Compared to original sample"});send("user-scrutiny","application.advance",app.id,{reason:"All sample requirements reviewed"});
 const visit=state.visits.find(v=>v.applicationId===app.id);send("user-regional","committee.save",visit.id,{expertIds:state.experts.filter(e=>e.eligibility==="ELIGIBLE").slice(0,5).map(e=>e.id),reason:"Officer-selected sample committee"});send("user-coordinator","visit.recommend",visit.id);const slot=state.slots.find(s=>s.visitId===visit.id&&s.feasible);assert(slot);send("user-coordinator","visit.confirm",visit.id,{slotId:slot.id,reason:"Common availability revalidated"});send("user-coordinator","visit.complete",visit.id,{reason:"Local visit completion simulation"});for(const criterion of ["Laboratories","Land","Staffing"])send("user-coordinator","observation.save",undefined,{visitId:visit.id,criterion,text:"Submitted authorised sample observation",submit:true});const record=send("user-coordinator","record.generate",visit.id,{type:"EVC_REPORT"});send("user-coordinator","record.review",record);send("user-regional","record.approve",record,{reason:"Reviewed all source sections"});
 send("user-regional","decision.record",app.id,{outcome:"APPROVE",reason:"Configured route complete"});const condition=send("user-regional","condition.create",app.id,{description:"Provide renewed lease",requirements:"Lease version",dueAt:"2026-11-30T17:00:00+05:30"});send("user-institution","evidence.submit",condition,{documentVersionIds:["journey-lease"]});send("user-compliance","evidence.verify",condition,{result:"COMPLIANT",reason:"Required evidence reviewed"});send("user-compliance","condition.close",condition,{reason:"Verified compliant"});send("user-regional","decision.record",app.id,{outcome:"CLOSE",reason:"All approval conditions closed"});assert.equal(state.applications.find(a=>a.id===app.id).status,"CLOSED");assert(state.auditEvents.length>mockData.auditEvents.length+15);
});
test("filtering never mutates the baseline fixtures", () => {
  const before = JSON.stringify(mockData);
  for (const account of mockData.users) account.assignments.forEach((_, index) => scopedSnapshot(mockData, account, index));
  assert.equal(JSON.stringify(mockData), before);
});

test("pending session UI preserves the nested route for Next.js validation without exposing it", () => {
  const PendingPortal = load("app/portal-ui/PendingPortal.tsx", { "react/jsx-runtime": jsxRuntime }).default;
  const html = renderToStaticMarkup(createElement(PendingPortal, {
    fallback: createElement("p", { role: "status" }, "Loading workspace"),
  }, createElement("section", { "data-route-probe": true }, "Application segment")));
  assert.match(html, /role="status"/);
  assert.match(html, /<div hidden="" inert=""><section data-route-probe="true">Application segment<\/section><\/div>/);
});
