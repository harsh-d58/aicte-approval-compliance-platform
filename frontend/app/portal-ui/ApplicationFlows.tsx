"use client";
import { useState } from "react";
import CorrectionEvidencePicker from "./CorrectionEvidencePicker";
import DecisionAndClosure from "./DecisionAndClosure";
import { useWorkspace, Page, Panel, Links, Field, ActionForm, ReasonAction, Table, Unavailable, Meta, Versions, valuesOf, optionsOf, Link, Badge, s, formatDateTime, humanize } from "./domain-ui";
export default function ApplicationFlows({ mode }: {
    mode: "new" | "edit" | "review" | "deficiency" | "decision";
}) {
    const { data, params, allowed, router, execute, reload } = useWorkspace();
    const [itemCount, setItemCount] = useState(1);
    const [resolvingId, setResolvingId] = useState<string | null>(null);
    const [resolutionError, setResolutionError] = useState("");
    if (!data)
        return null;
    const app = data.applications.find(a => a.id === params.applicationId);
    const institution = data.institutions.find(i => i.id === app?.institutionId) ?? data.institutions[0];
    if (mode !== "new" && !app)
        return <Unavailable name="Application"/>;
    const base = app ? `/portal/applications/${app.id}` : "/portal/applications";
    const workflow = data.workflows.find(w => w.id === app?.workflowId);
    const notice = data.deficiencies.find(n => n.id === params.noticeId && n.applicationId === app?.id);
    if (mode === "edit" && app && app.status !== "DRAFT")
        return <Page title="Application already submitted" description="Only drafts can be edited. Use the case workspace for versioned responses and review actions."><Links items={[["Case overview", base]]}/></Page>;
    if (mode === "deficiency" && !notice)
        return <Unavailable name="Deficiency notice"/>;
    if ((mode === "new" || mode === "edit") && !allowed("INSTITUTION"))
        return <Unavailable name="Application editor"/>;
    return <Page title={mode === "new" ? "New application" : mode === "edit" ? "Resume application" : mode === "review" ? "Scrutiny & workflow" : mode === "decision" ? "Decision & closure" : notice!.number} description={app ? `${app.number} · record v${app.version} · ${humanize(app.status)}` : "Save a draft, review the sample route and submit a versioned declaration."}><Links items={[["Application register", "/portal/applications"], ...(app ? [["Case overview", base], ["Documents", "/portal/documents"]] as [
            string,
            string
        ][] : [])]}/>{app && <Panel title="Configured route"><div className={s.step}>{workflow?.stages.map(st => <span key={st.code} aria-current={st.code === app.currentStage ? "step" : undefined}>{st.name}{st.code === app.currentStage ? " · current" : ""}</span>) ?? "Workflow unavailable"}</div><p className={s.muted}>Sample APH: {workflow?.aphVersion ?? "Unavailable"}. The case retains its published workflow version.</p></Panel>}
 {(mode === "new" || mode === "edit") && institution && <Panel title="Application details"><ActionForm kind="application.save" id={app?.id} version={app?.version} after={r => router.push(`/portal/applications/${r.id}/edit`)} submit="Save draft"><div className={s.fields}><Field name="institutionId" label="Institution" value={institution.id} options={data.institutions.map(i => ({ id: i.id, name: i.name }))}/><Field name="campusId" label="Campus" value={app?.campusId ?? institution.campuses[0]?.id} options={institution.campuses.map(c => ({ id: c.id, name: c.name }))}/><Field name="type" label="Application type" value={app?.type ?? "EXTENSION_OF_APPROVAL"} options={optionsOf(["EXTENSION_OF_APPROVAL", "NEW_INSTITUTION", "INCREASE_IN_INTAKE"])}/><Field name="academicYear" label="Academic year (YYYY-YY)" value={app?.academicYear ?? "2027-28"}/><Field name="workflowId" label="Published sample workflow" value={app?.workflowId ?? data.workflows.find(w => w.status === "PUBLISHED")?.id} options={data.workflows.filter(w => w.status === "PUBLISHED").map(w => ({ id: w.id, name: `${w.name} · ${w.version} · ${w.aphVersion}` }))}/></div><p className={s.note}>Sample routes require lease and registration documents. Upload them in Documents before submission. These rules are illustrative pending approved APH policy.</p></ActionForm></Panel>}
 {mode === "edit" && app?.status === "DRAFT" && <Panel title="Review & submit"><Meta items={[["Institution", institution?.name], ["Year", app.academicYear], ["Workflow", workflow?.name]]}/><ActionForm kind="application.submit" id={app.id} version={app.version} submit="Submit application" build={fd => ({ declaration: fd.get("declaration") === "on" })} after={() => router.push(base)}><label className={s.check}><input name="declaration" type="checkbox" required/>I have reviewed the declared details and current documents for this demonstration submission.</label></ActionForm></Panel>}
 {mode === "review" && app && <><Panel title="Review checklist"><Table columns={["Document", "Current version", "Verification", "Findings"]} rows={data.documents.filter(d => d.institutionId === app.institutionId).map(d => [<Link key={d.id} href={`/portal/documents/${d.id}`}>{humanize(d.type)}</Link>, d.versions.find(v => v.id === d.currentVersionId)?.number, d.versions.find(v => v.id === d.currentVersionId)?.verification, data.documentChecks.filter(c => c.documentId === d.id).map(c => c.findings.map(f => f.review).join(", ")).join("; ") || "Not checked"])}/></Panel>{allowed("SCRUTINY", "REGIONAL") && <div className={s.grid}>{app.currentStage !== "SCRUTINY" && app.currentStage !== "INTAKE" ? <Panel title="Review progression"><p className={s.note}>Scrutiny completed. Case has advanced to <strong>{humanize(app.currentStage)}</strong>.</p><Links items={[["Case overview", base], ["Application register", "/portal/applications"]]}/></Panel> : <Panel title="Review progression"><ReasonAction kind="application.advance" id={app.id} version={app.version} label={app.status === "IN_REVIEW" ? "Complete scrutiny" : "Start / resume scrutiny"} after={() => router.push(base)}/></Panel>}{(!app.currentStage || app.currentStage === "SCRUTINY" || app.currentStage === "INTAKE") && <Panel title="Issue Multi-Item Deficiency Checklist (PRD §5.3, §7.1, BR-05)">
  <ActionForm
    kind="deficiency.issue"
    id={app.id}
    version={app.version}
    submit={`Issue Notice (${itemCount} Item${itemCount > 1 ? "s" : ""})`}
    after={r => router.push(`${base}/deficiencies/${r.id}`)}
    build={fd => {
      const items = [];
      for (let idx = 0; idx < itemCount; idx++) {
        const crit = String(fd.get(`criterion_${idx}`) || "").trim();
        const desc = String(fd.get(`description_${idx}`) || "").trim();
        const docId = String(fd.get(`documentId_${idx}`) || "").trim() || null;
        if (desc) {
          items.push({ criterion: crit || `Criterion ${idx + 1}`, description: desc, documentId: docId });
        }
      }
      return {
        items: items.length > 0 ? items : [{ criterion: String(fd.get("criterion_0") || "General"), description: String(fd.get("description_0") || "Required compliance correction"), documentId: fd.get("documentId_0") || null }],
        dueAt: fd.get("dueAt") || "",
        reason: fd.get("reason") || "Deficiency notice issued during scrutiny",
      };
    }}
  >
    <p className={s.note}>
      Construct an itemized statutory deficiency notice. Each compliance gap is tracked and resolved as an independent checklist item.
    </p>
    {Array.from({ length: itemCount }).map((_, idx) => (
      <fieldset key={idx} className={s.item} style={{ marginBottom: "1rem", padding: "0.75rem", border: "1px solid var(--border, #e5e7eb)", borderRadius: "6px" }}>
        <legend style={{ fontWeight: 600 }}>Checklist Item #{idx + 1}</legend>
        <Field name={`criterion_${idx}`} label="Criterion Code / Area (e.g. FIRE_SAFETY_NOC, CADRE_RATIO, INFRASTRUCTURE)" />
        <Field name={`description_${idx}`} label="Specific Non-Compliance Deficiency & Required Rectification" type="textarea" />
        <Field
          name={`documentId_${idx}`}
          label="Related Mandated Document (Optional)"
          required={false}
          options={data.documents.filter(d => d.institutionId === app.institutionId).map(d => ({ id: d.id, name: `${humanize(d.type)} (${d.issuer || "Institution"})` }))}
        />
      </fieldset>
    ))}
    <div style={{ marginBottom: "1rem" }}>
      {itemCount < 5 && (
        <button
          type="button"
          className={s.button}
          style={{ marginRight: "0.5rem", fontSize: "0.85rem" }}
          onClick={() => setItemCount(c => Math.min(5, c + 1))}
        >
          + Add Another Deficiency Item
        </button>
      )}
      {itemCount > 1 && (
        <button
          type="button"
          className={s.button}
          style={{ fontSize: "0.85rem" }}
          onClick={() => setItemCount(c => Math.max(1, c - 1))}
        >
          - Remove Last Item
        </button>
      )}
    </div>
    <Field name="dueAt" label="Statutory Response Deadline (IST)" type="datetime-local" />
    <Field name="reason" label="Formal Reason for Deficiency Notice" type="textarea" />
  </ActionForm>
</Panel>}</div>}{allowed("REGIONAL", "CENTRAL") && <Panel title="Assign / reassign scrutiny"><ReasonAction kind="application.assign" id={app.id} version={app.version} label="Assign case"><Field name="ownerId" label="Scrutiny officer" value={app.ownerId ?? ""} options={data.users.filter(u => u.status === "ACTIVE" && u.assignments.some(a => a.role === "SCRUTINY")).map(u => ({ id: u.id, name: u.displayName }))}/><Field name="dueAt" label="Review deadline (IST)" type="datetime-local"/></ReasonAction></Panel>}<Panel title="Deficiencies"><Table columns={["Notice", "Status", "Due"]} rows={data.deficiencies.filter(n => n.applicationId === app.id).map(n => [<Link key={n.id} href={`${base}/deficiencies/${n.id}`}>{n.number}</Link>, n.status, formatDateTime(n.responseDueAt)])}/></Panel></>}
 {mode === "deficiency" && notice && app && <>
  <Panel title="Itemized Deficiency Notice & Verification Checklist (PRD §5.3, §7.1, BR-05)">
    <Meta
      items={[
        ["Notice Number", notice.number],
        ["Notice Status", <Badge key="status" status={notice.status}/>],
        ["Issued At", formatDateTime(notice.issuedAt)],
        ["Response Due (IST)", formatDateTime(notice.responseDueAt)],
        ["Total Checklist Items", `${notice.items.length} items (${notice.items.filter(i => i.status === "RESOLVED").length} resolved)`],
      ]}
    />
    <p style={{ marginTop: "0.5rem" }}><strong>Reason for Notice:</strong> {notice.reason}</p>
    
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
      {notice.items.map((i, idx) => (
        <div key={i.id} className={s.item} style={{ padding: "1rem", border: "1px solid var(--border, #e5e7eb)", borderRadius: "6px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>Item #{idx + 1}: {i.criterion}</h3>
            <Badge status={i.status} />
          </div>
          <p><strong>Required Correction:</strong> {i.description}</p>
          <p><strong>Institutional Response:</strong> {i.response ?? <span style={{ color: "var(--muted, #6b7280)" }}>Pending institutional submission</span>}</p>
          <p className={s.muted} style={{ fontSize: "0.85rem" }}>
            Evidentiary Document Version: {i.responseVersionId ? `v${i.responseVersionId}` : "None attached"}
          </p>
          
          {allowed("SCRUTINY", "REGIONAL") && i.status === "OPEN" && <p className={s.note}>Awaiting the institution's submitted response. Accept or return the item after its response is submitted.</p>}
          {allowed("SCRUTINY", "REGIONAL") && i.status === "RESPONDED" && (
            <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <button
                type="button"
                className={s.button}
                disabled={Boolean(resolvingId)}
                onClick={async () => {
                  setResolvingId(i.id);
                  setResolutionError("");
                  try {
                    await execute({
                      kind: "deficiency.resolve",
                      id: notice.id,
                      expectedVersion: app.version,
                      values: { itemId: i.id, resolution: "ACCEPTED", reason: `Item #${idx + 1} (${i.criterion}) accepted by scrutiny officer` }
                    });
                  } catch (cause) {
                    setResolutionError(cause instanceof Error ? `${cause.message} Reloading this notice; only submitted responses can be reviewed.` : "Unable to accept this item. Reload the notice and check its response status.");
                    reload();
                  } finally {
                    setResolvingId(null);
                  }
                }}
              >
                ✓ Accept Item #{idx + 1}
              </button>
              <button
                type="button"
                className={s.button}
                style={{ backgroundColor: "rgba(220, 38, 38, 0.1)", borderColor: "#dc2626", color: "#dc2626" }}
                disabled={Boolean(resolvingId)}
                onClick={async () => {
                  setResolvingId(i.id);
                  setResolutionError("");
                  try {
                    await execute({
                      kind: "deficiency.resolve",
                      id: notice.id,
                      expectedVersion: app.version,
                      values: { itemId: i.id, resolution: "REJECTED", reason: `Item #${idx + 1} rejected: revision required` }
                    });
                  } catch (cause) {
                    setResolutionError(cause instanceof Error ? `${cause.message} Reloading this notice; only submitted responses can be reviewed.` : "Unable to return this item. Reload the notice and check its response status.");
                    reload();
                  } finally {
                    setResolvingId(null);
                  }
                }}
              >
                ⚠ Reject Item #{idx + 1} (Request Correction)
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
    {resolutionError && <p role="alert" className={s.error}>{resolutionError}</p>}
  </Panel>

  {allowed("INSTITUTION") && notice.status === "OPEN" && (
    <Panel title="Submit Itemized Correction Evidence">
      <ActionForm
        kind="deficiency.respond"
        id={notice.id}
        version={app.version}
        submit="Submit Comprehensive Response"
        build={fd => ({ itemResponses: notice.items.filter(item => item.status !== "RESOLVED").map(item => ({ itemId: item.id, versionId: String(fd.get(`evidence-${item.id}`) ?? ""), narrative: String(fd.get("response") ?? "") })) })}
      >
        <Field name="response" label="Institutional Explanatory Narrative & Rectification Actions" type="textarea" />
        <p className={s.note}>Upload the corrected file first, then select its exact version for each item. Entering a certificate reference above does not upload a document.</p>
        {notice.items.filter(item => item.status !== "RESOLVED").map(item => {
          return <fieldset key={item.id} className={s.item}><legend>{item.criterion || "Deficiency item"}</legend><p>{item.description}</p>
            <CorrectionEvidencePicker applicationId={app.id} noticeId={notice.id} itemId={item.id} />
          </fieldset>;
        })}
      </ActionForm>
    </Panel>
  )}

  {allowed("SCRUTINY", "REGIONAL") && notice.status === "RESPONDED" && (
    <Panel title="Batch Scrutiny Determination">
      <ReasonAction kind="deficiency.resolve" id={notice.id} version={app.version} label="Resolve All Remaining Items" />
    </Panel>
  )}
</>}
 {mode === "decision" && app && <DecisionAndClosure applicationId={app.id}/>}
 </Page>;
}
