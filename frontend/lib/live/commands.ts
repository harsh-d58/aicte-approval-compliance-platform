import type { Command } from "@/lib/portal/commands";
import type { PortalCollections } from "@/lib/portal/types";
import { deficiencyResponses } from "./deficiency-evidence";

/** The provider owns tokens and refreshes the snapshot only after this resolves. */
export interface LiveCommandClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T>;
  patch<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T>;
  put<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T>;
  del<T>(path: string): Promise<T>;
}

type Row = Record<string, unknown>;
type Envelope = { data: Row[] };
const text = (value: unknown) => typeof value === "string" ? value : "";
const list = (value: unknown): string[] => Array.isArray(value) ? value.map(String) : [];
const code = (value: unknown) => text(value).replace(/^DEMO-/, "").replaceAll("-", "_").toUpperCase();
const resultId = (result: Row, fallback = "") => String(result.id ?? result.report_id ?? result.document_id ?? fallback);

/** Translate view-model commands to the existing FastAPI contracts. Never apply local state. */
export async function executeLiveCommand(
  command: Command, data: PortalCollections, client: LiveCommandClient,
): Promise<{ id: string; message: string }> {
  const values = { ...(command.values ?? {}) };
  for (const key of ["dueAt", "startAt", "endAt", "validUntil"]) {
    const value = values[key];
    if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(value)) values[key] = value + "+05:30";
  }
  const liveCommand = { ...command, values };
  const id = command.id ?? "";
  const reason = text(values.reason) || "Prototype user action";
  const app = data.applications.find(a => a.id === id);
  const version = command.expectedVersion ?? app?.version;
  const headers: Record<string, string> = { "Idempotency-Key": crypto.randomUUID() };
  if (version !== undefined) headers["If-Match"] = String(version);
  const post = (path: string, body: unknown) => client.post<Row>(path, body, headers);
  const put = (path: string, body: unknown) => client.put<Row>(path, body, headers);
  let response: Row;
  let returnedId = id;

  switch (command.kind) {
    case "document.save": {
      const {getFile} = await import("@/lib/portal/files");
      const file = await getFile(text(values.versionId));
      if (!file) throw new Error("Choose the file again before uploading.");
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = ""; for (let offset=0;offset<bytes.length;offset+=8192) binary += String.fromCharCode(...bytes.subarray(offset,offset+8192));
      const document = data.documents.find(d=>d.id===id) as (PortalCollections["documents"][number] & {version?:number}) | undefined;
      response = await post("/portal/documents", {document_id:id || null,institution_id:values.institutionId,application_id:values.applicationId || null,document_type:values.type,file_name:values.fileName,mime_type:values.mimeType,content_base64:btoa(binary),issue_date:values.issuedAt || null,expiry_date:values.expiryDate || null,expected_version:document?.version,issuer:values.issuer,reference:values.reference});
      returnedId = resultId(response); break;
    }
    case "institution.save": {
      if (!id) return client.post<{ id: string; message: string }>("/portal/commands", liveCommand, headers);
      const current = await client.get<Row>(`/institutions/${id}`);
      response = await client.patch<Row>(`/institutions/${id}`, {
        official_name: values.name, institution_type: values.type,
        region_id: values.regionId || undefined,
        expected_version: command.expectedVersion ?? current.version, reason,
      }, headers);
      break;
    }
    case "campus.save":
      response = await post(`/institutions/${id}/campuses`, {
        campus_name: values.name, address: { city: values.city }, reason,
      });
      returnedId = id;
      break;
    case "attribute.save":
    case "attribute.verify": {
      const key = text(values.key);
      const existing = data.institutions.find(i => i.id === id)?.attributes.find(a => a.key === key);
      const sourceVersionId = text(values.sourceVersionId) || existing?.sourceVersionId;
      const sourceDocument = data.documents.find(d => d.versions.some(v => v.id === sourceVersionId));
      response = await put(`/institutions/${id}/attributes`, { attributes: [{
        attribute_key: key, value_text: text(values.value) || existing?.value,
        source_document_id: sourceDocument?.id,
        verified_status: command.kind === "attribute.verify" ? "verified" : "unverified",
      }], reason });
      break;
    }
    case "application.save": {
      if (id) {
        response = await put(`/applications/${id}`, { campus_id: values.campusId || null, expected_version: version, reason });
      } else {
        const workflows = await client.get<Envelope>("/workflows");
        const workflow = workflows.data.find(w => String(w.id) === text(values.workflowId)) ?? workflows.data[0];
        if (!workflow) throw new Error("The selected live workflow is unavailable. Refresh before creating a draft.");
        response = await post("/applications", {
          institution_id: values.institutionId, campus_id: values.campusId || null,
          workflow_definition_id: workflow.id, application_type_id: workflow.application_type_id, reason,
        });
        returnedId = resultId(response);
      }
      break;
    }
    case "application.submit":
      if (values.declaration !== true) throw new Error("Confirm the declaration before submitting.");
      response = await post(`/applications/${id}/submit`, { expected_version: version, reason });
      break;
    case "application.advance": {
      if (!app) throw new Error("Application unavailable.");
      const workflow = await client.get<Row>(`/workflows/${app.workflowId}`);
      const stages = (workflow.stages ?? []) as Row[];
      const transitions = (workflow.transitions ?? []) as Row[];
      const current = stages.find(s => code(s.stage_code) === code(app.currentStage));
      const transition = transitions.find(t => String(t.from_stage_id) === String(current?.id));
      if (!transition?.to_stage_id) throw new Error("No live transition is configured for this stage.");
      response = await post(`/applications/${id}/transitions`, { to_stage_id: transition.to_stage_id, expected_version: version, reason });
      break;
    }
    case "deficiency.issue": {
      const rawItems = Array.isArray(values.items) && values.items.length > 0
        ? (values.items as Array<Record<string, unknown>>)
        : [{ criterion: text(values.criterion), description: text(values.description), documentId: text(values.documentId) || null }];
      const dueParsed = values.dueAt ? Math.ceil((Date.parse(text(values.dueAt)) - Date.now()) / 86400000) : 14;
      const responseDueDays = Number.isFinite(dueParsed) && dueParsed > 0 ? Math.max(1, Math.min(180, dueParsed)) : 14;
      const noticeReason = text(values.reason) || reason || "Deficiency notice issued during scrutiny";
      response = await post(`/applications/${id}/deficiency-notices`, {
        response_due_days: responseDueDays,
        items: rawItems.map(it => ({
          criterion_code: String(it.criterion ?? "General"),
          description: String(it.description ?? ""),
          related_document_id: it.documentId ? String(it.documentId) : null,
        })),
        reason: noticeReason.length >= 3 ? noticeReason : "Deficiency notice issued during scrutiny",
      });
      returnedId = resultId(response);
      break;
    }
    case "deficiency.respond": {
      response = await post(`/deficiency-notices/${id}/responses`, {
        item_responses: deficiencyResponses(data, id, values),
        reason: text(values.response) || reason,
      });
      break;
    }
    case "deficiency.resolve": {
      const notice = data.deficiencies.find(n => n.id === id);
      if (!notice?.items.length) throw new Error("Deficiency notice unavailable.");
      if (values.itemId) {
        const item = notice.items.find(item => item.id === values.itemId);
        if (!item || item.status !== "RESPONDED") throw new Error("The institution must submit this item's response before it can be reviewed. Refresh the notice if it was just submitted.");
        const resStatus = values.resolution === "REJECTED" ? "rejected" : values.resolution === "WAIVED" ? "waived" : "accepted";
        await post(`/deficiency-items/${values.itemId}/resolve`, { resolution_status: resStatus, reason });
      } else {
        const submitted = notice.items.filter(item => item.status === "RESPONDED");
        if (!submitted.length) throw new Error("No submitted item responses are ready for review.");
        for (const item of submitted) {
          await client.post(`/deficiency-items/${item.id}/resolve`, { resolution_status: "accepted", reason }, {...headers,"Idempotency-Key":crypto.randomUUID()});
        }
      }
      response = { id };
      break;
    }
    case "decision.record": {
      const outcome = text(values.outcome).toUpperCase();
      const statuses: Record<string, string> = {APPROVE:"approved",REJECT:"rejected",CLOSE:"approved"};
      if (!statuses[outcome]) throw new Error("Choose Approve, Reject or Close.");
      response = await post(`/applications/${id}/decisions`, {
        decision_type: outcome.toLowerCase(), decision_status: statuses[outcome],
        decision_authority: text(values.authority) || "Prototype authorised decision officer", reason, expected_version: version,
      });
      break;
    }
    case "document.check": {
      const versionId = text(values.versionId) || data.documents.find(d => d.id === id)?.currentVersionId;
      if (!versionId) throw new Error("Choose an available document version.");
      response = await post(`/document-versions/${versionId}/ocr-checks`, { reason });
      returnedId = resultId((response.checks as Row[] | undefined)?.[0] ?? response);
      break;
    }
    case "document.review":
      response = await post(`/document-check-results/${id}/review`, {
        review_status: values.result === "ACCEPTED" ? "accepted" : "rejected", reason,
      });
      break;
    case "renewal.start":
      response = await post("/document-renewal-cases", { document_id: id, reason });
      returnedId = resultId(response);
      break;
    case "committee.save": {
      const expertIds = list(values.expertIds);
      response = await put(`/evc-visits/${id}/committee-members`, { members: expertIds.map((expertId, index) => ({
        expert_user_id: data.experts.find(e => e.id === expertId)?.userId ?? expertId,
        committee_role: index === 0 ? "convener" : "member",
      })), reason });
      break;
    }
    case "availability.save":
      return client.post<{id:string;message:string}>("/portal/commands",liveCommand,headers);
    case "visit.recommend": {
      const visit = data.visits.find(v => v.id === id);
      response = await post(`/evc-visits/${id}/slot-recommendations`, {
        search_horizon_days: 30, visit_duration_hours: (visit?.durationMinutes ?? 480) / 60,
      });
      break;
    }
    case "visit.confirm": {
      const visit = data.visits.find(visit => visit.id === id);
      if (visit?.status === "CONFIRMED") throw new Error("This visit is already confirmed. Refresh to see its saved schedule.");
      const slot = data.slots.find(s => s.id === values.slotId && s.visitId === id);
      if (!slot) throw new Error("Choose an available proposed slot.");
      if (!slot.feasible || !(Date.parse(slot.expiresAt) > Date.now())) throw new Error("This recommendation expired. Generate fresh recommendations before confirming.");
      response = await post(`/evc-visits/${id}/confirm-schedule`, {
        slot_recommendation_id: slot.id, confirmed_start_at: slot.startAt, confirmed_end_at: slot.endAt, reason,
      });
      break;
    }
    case "visit.complete":
      response = await post(`/evc-visits/${id}/complete`, { reason });
      break;
    case "observation.save":
      return client.post<{id:string;message:string}>("/portal/commands", liveCommand, headers);
    case "record.generate":
      response = await post(`/evc-visits/${id}/meeting-record-drafts`, {
        record_type: values.type === "EVC_REPORT" ? "evc_report" : "minutes", source_ids: list(values.observationIds), reason,
      });
      returnedId = resultId(response);
      break;
    case "record.review":
      response = await post(`/meeting-records/${id}/submit-review`, { reason });
      break;
    case "record.approve":
      response = await post(`/meeting-records/${id}/approve`, { reason });
      break;
    case "record.changes":
      response = await post(`/meeting-records/${id}/request-changes`, { reason, comments: reason });
      break;
    case "condition.create": {
      if (!app) throw new Error("Application unavailable.");
      response = await post("/compliance-conditions", {
        institution_id: app.institutionId, application_id: id,
        source_approval_id: data.decisions.find(d => d.applicationId === id && d.type === "APPROVE" && d.status === "APPROVED")?.id,
        condition_code: `COND-${Date.now()}`, description: values.description, due_at: values.dueAt,
        evidence_requirements: text(values.requirements).split(/\r?\n/).map(value => value.trim()).filter(Boolean),
      });
      returnedId = resultId(response);
      break;
    }
    case "condition.update": {
      const condition = data.conditions.find(row => row.id === id);
      response = await client.patch<Row>(`/compliance-conditions/${id}`, {
        evidence_requirements:text(values.requirements).split(/\r?\n/).map(value => value.trim()).filter(Boolean),
        expected_version:condition?.version ?? command.expectedVersion, reason,
      }, headers);
      break;
    }
    case "evidence.submit":
      response = await post(`/compliance-conditions/${id}/evidence-submissions`, { document_version_ids: list(values.documentVersionIds ?? values.versionIds), remarks: reason });
      break;
    case "evidence.verify": {
      const evidence = data.evidence.filter(e => e.conditionId === id).sort((a, b) => b.submissionNumber - a.submissionNumber)[0];
      if (!evidence) throw new Error("No evidence has been submitted for this condition.");
      const results: Record<string, string> = { COMPLIANT: "accepted", NON_COMPLIANT: "rejected", CLARIFICATION_REQUIRED: "needs_clarification" };
      response = await post(`/evidence-submissions/${evidence.id}/verifications`, { result: results[text(values.result)], comments: reason });
      break;
    }
    case "condition.close":
    case "condition.reopen":
      response = await post(`/compliance-conditions/${id}/${command.kind.endsWith("close") ? "close" : "reopen"}`, { reason });
      break;
    case "notification.retry":
      response = await post(`/notifications/${id}/retry`, { channel: data.notifications.find(n => n.id === id)?.channel.toLowerCase() ?? "in_app" });
      break;
    case "escalation.resolve":
      response = await post(`/escalation-events/${id}/resolve`, { resolution_status: "resolved", reason });
      break;
    case "report.create": {
      const reports = await client.get<Envelope>("/reports");
      const report = reports.data.find(r => code(r.report_code) === code(values.reportCode));
      if (!report) throw new Error("Report category unavailable in the live database.");
      response = await post(`/reports/${report.report_code}/runs`, { format: "csv", filters: {
        date_from: values.dateFrom, date_to: values.dateTo, region_id: values.regionId || undefined,
        status: values.status || undefined, query: values.query || undefined, column_filters: values.columnFilters || undefined,
      } });
      returnedId = resultId(response);
      break;
    }
    case "report.complete":
      throw new Error("Live reports are generated by the server. Refresh the report run to inspect its actual result.");
    default:
      return client.post<{ id: string; message: string }>("/portal/commands", liveCommand, headers);
  }
  void response;
  return { id: returnedId, message: "Saved to the live database." };
}
