"use client";
import { decisionState } from "@/lib/live/decision-state";
import { useWorkspace, Panel, Field, ActionForm, ReasonAction, Table, Link, Badge, s, formatDateTime } from "./domain-ui";

export default function DecisionAndClosure({applicationId}:{applicationId:string}) {
  const {data,allowed,user}=useWorkspace();
  const application=data?.applications.find(row=>row.id===applicationId);
  if (!data || !application) return null;
  const state=decisionState(data,application);
  const canDecide=allowed("REGIONAL","CENTRAL");
  const mutable=!["APPROVED","REJECTED","CLOSED","WITHDRAWN"].includes(application.status);
  const decisions=data.decisions.filter(row=>row.applicationId===application.id);
  const visits=data.visits.filter(row=>row.applicationId===application.id);
  const reports=data.meetingRecords.filter(row=>row.type==="EVC_REPORT" && visits.some(visit=>visit.id===row.visitId));
  const migrations=data.workflows.filter(row=>row.status==="PUBLISHED" && row.id!==application.workflowId
    && (!application.applicationTypeId || !row.applicationTypeId || row.applicationTypeId===application.applicationTypeId)
    && row.stages.some(stage=>stage.code===application.currentStage));
  return <>
    <Panel title="Decision history">{decisions.length ? <Table columns={["Outcome","Authority","At (IST)","Reason"]} rows={decisions.map(row=>[
      row.type,data.users.find(user=>user.id===row.authorityId)?.displayName ?? row.authorityId,formatDateTime(row.at),row.reason])}/> : <p>No decision has been recorded for {application.number}.</p>}
      <p>Current application status: <Badge status={application.status}/></p>
    </Panel>
    <Panel title="Approval conditions"><Table columns={["Condition / undertaking","Evidence required","Due (IST)","Status","Action"]} rows={state.conditions.map(condition=>[
      <span key="description">{condition.code}<small>{condition.description}</small></span>,
      condition.evidenceRequired.length ? condition.evidenceRequired.join("; ") : "No evidence checklist recorded",
      formatDateTime(condition.dueAt),<Badge key="status" status={condition.status}/>,
      <Link key="link" href={`/portal/compliance/${condition.id}`}>Open condition and evidence</Link>])}/>
      <p className={s.note}>Creating a condition saves an undertaking. Approval keeps the case open until those obligations are fulfilled and explicitly closed.</p>
      {allowed("REGIONAL") && mutable && state.conditions.filter(condition=>!condition.sourceDecisionId).map(condition=><details key={condition.id} className={s.item}>
        <summary>Edit required evidence: {condition.code}</summary>
        <ActionForm kind="condition.update" id={condition.id} version={condition.version} submit="Save required evidence">
          <Field name="requirements" label="Evidence required (one per line)" type="textarea" value={condition.evidenceRequired.join("\n")} required={false}/>
          <Field name="reason" label="Reason for correction" type="textarea"/>
        </ActionForm>
      </details>)}
    </Panel>
    {canDecide && <Panel title={application.status==="APPROVED" ? "Explicit case closure" : "Authorised decision"}>
      {state.blocker && <p role="status" className={s.note}>{state.blocker}</p>}
      {(mutable || application.status==="APPROVED") && <fieldset disabled={Boolean(state.blocker)} style={{border:0,padding:0,margin:0,minWidth:0}}>
      <ReasonAction key={`${application.id}-${application.status}`} kind="decision.record" id={application.id} version={application.version} defaults={{authority:user?.displayName ?? "Authorised officer"}} label={application.status==="APPROVED" ? "Close application" : "Record decision"}>
        <Field name="outcome" label="Decision" options={(state.outcomes.length ? state.outcomes : application.status==="APPROVED" ? ["CLOSE"] : ["APPROVE","REJECT"]).map(id=>({id,name:id==="CLOSE"?"Close application":id==="APPROVE"?"Approve":"Reject"}))}/>
        <p className={s.note}>Approve, Reject and Close record different outcomes. Case closure requires every condition to be closed.</p>
      </ReasonAction></fieldset>}
      {state.blocker && <div>
        <p>Decision case: <strong>{application.number}</strong>. Inspection and report approval must belong to this application.</p>
        {visits.map(visit=><p key={visit.id}><Link href={`/portal/evc/${visit.id}`}>Open this application&apos;s EVC visit</Link> <Badge status={visit.status}/></p>)}
        {reports.map(record=><p key={record.id}><Link href={`/portal/meeting-records/${record.id}`}>Review this application&apos;s EVC report</Link> <Badge status={record.versions.find(version=>version.number===record.currentVersion)?.status ?? "DRAFT"}/></p>)}
        {!visits.length && state.blocker.includes("EVC") && <p>No EVC visit is linked to {application.number}.</p>}
      </div>}
    </Panel>}
    {allowed("REGIONAL") && state.canAddCondition && <Panel title="Add approval condition">
      <ActionForm kind="condition.create" id={application.id} submit="Create condition">
        <Field name="description" label="Condition / undertaking" type="textarea"/>
        <Field name="requirements" label="Evidence required (one per line)" type="textarea"/>
        <Field name="dueAt" label="Due (IST)" type="datetime-local"/>
      </ActionForm>
    </Panel>}
    {allowed("POLICY","CENTRAL") && mutable && <Panel title="Explicit workflow migration">
      {migrations.length ? <ReasonAction kind="application.migrate" id={application.id} version={application.version} label="Migrate active case" defaults={{stageCode:application.currentStage}}>
        <Field name="workflowId" label="Compatible published workflow" options={migrations.map(row=>({id:row.id,name:`${row.name} - ${row.version}`}))}/>
        <p className={s.note}>The current stage is explicitly mapped by its code. Historical submissions and workflow references are retained.</p>
      </ReasonAction> : <p>No compatible published workflow is available for this application type and stage.</p>}
    </Panel>}
    {allowed("REGIONAL") && (application.status==="CLOSED" || mutable) && <Panel title="Case lifecycle">
      <ReasonAction kind={application.status==="CLOSED"?"application.reopen":"application.cancel"} id={application.id} version={application.version} label={application.status==="CLOSED"?"Reopen case":"Withdraw case"}/>
    </Panel>}
  </>;
}
