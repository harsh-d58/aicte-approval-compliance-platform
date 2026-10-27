import type { PortalCollections, Role, User } from "./types";

export const demoNow = "2026-10-26T12:00:00+05:30";
export const roleNames: Record<Role, string> = {
  INSTITUTION: "Institutional representative", SCRUTINY: "Scrutiny officer", REGIONAL: "Regional officer",
  EVC_COORDINATOR: "EVC coordinator", EVC_EXPERT: "EVC expert", COMPLIANCE: "Compliance officer",
  CENTRAL: "Central administrator", POLICY: "Policy administrator", AUDITOR: "Auditor", SYSTEM: "System administrator",
};
export const roleDescriptions: Record<Role, string> = {
  INSTITUTION: "Your institution, applications and compliance, in one place.", SCRUTINY: "A clear view of your assigned cases and review priorities.",
  REGIONAL: "Follow regional progress and keep every case moving.", EVC_COORDINATOR: "Bring committees, institutions and schedules together.",
  EVC_EXPERT: "Your committee assignments, observations and reviews.", COMPLIANCE: "Follow the evidence. Keep every condition accountable.",
  CENTRAL: "A connected view of performance across regions.", POLICY: "Maintain the rules behind a consistent approval process.",
  AUDITOR: "Trace actions, inspect history and review record integrity.", SYSTEM: "Keep an eye on services, deliveries and operational health.",
};
export const humanize = (text: string) => text.toLowerCase().replaceAll("_", " ").replace(/^./, c => c.toUpperCase()).replace(/evc/gi, "EVC");
export const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" }).format(new Date(value)) : "Not set";
export const formatDateTime = (value: string | null) => value ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" }).format(new Date(value)) + " IST" : "Not set";
export const ageDays = (value: string | null, end = demoNow) => value ? Math.max(0, Math.floor((Date.parse(end) - Date.parse(value)) / 86400000)) : null;
export const isOverdue = (due: string | null) => !!due && Date.parse(due) < Date.parse(demoNow);
export const activeApplication = (status: string) => !["DRAFT", "CLOSED", "REJECTED", "WITHDRAWN"].includes(status);
export function scopeName(data: PortalCollections, user: User, index: number) {
  const { scope } = user.assignments[index];
  if (scope.type === "GLOBAL") return "All authorised regions";
  if (scope.type === "INSTITUTION") return data.institutions.find(i => i.id === scope.id)?.name ?? scope.id;
  if (scope.type === "REGION") return data.regions.find(r => r.id === scope.id)?.name ?? scope.id;
  return scope.type === "EVC" ? `Assigned committee · ${scope.id.replace("visit-", "EVC ")}` : scope.id;
}

/** Demonstration filtering only. Live services must enforce this boundary server-side. */
export function scopedSnapshot(data: PortalCollections, user: User, index: number): PortalCollections {
  const { role, scope } = user.assignments[index];
  const expertVisit = scope.type === "EVC" ? data.visits.find(v => v.id === scope.id && v.committee.some(m => data.experts.some(e => e.id === m.expertId && e.userId === user.id))) : undefined;
  const applications = data.applications.filter(a => {
    const institution = data.institutions.find(i => i.id === a.institutionId);
    const within = scope.type === "GLOBAL" || (scope.type === "REGION" && institution?.regionId === scope.id)
      || (scope.type === "INSTITUTION" && a.institutionId === scope.id) || (scope.type === "APPLICATION" && a.id === scope.id)
      || (scope.type === "EVC" && expertVisit?.applicationId === a.id);
    return within && (role !== "SCRUTINY" || a.ownerId === user.id);
  });
  const appIds = new Set(applications.map(a => a.id));
  const institutions = data.institutions.filter(i => scope.type === "GLOBAL" || (scope.type === "REGION" && role !== "SCRUTINY" && i.regionId === scope.id) || applications.some(a => a.institutionId === i.id) || (scope.type === "INSTITUTION" && i.id === scope.id));
  const institutionIds = new Set(institutions.map(i => i.id));
  const visits = data.visits.filter(v => appIds.has(v.applicationId) && (role !== "EVC_EXPERT" || v.id === scope.id));
  const visitIds = new Set(visits.map(v => v.id));
  const documents = data.documents.filter(d => role !== "EVC_EXPERT" && institutionIds.has(d.institutionId) && (!d.applicationId || appIds.has(d.applicationId)));
  const selectedExperts = new Set(visits.flatMap(v=>v.committee.map(m=>m.expertId)));
  const availability = data.availability.filter(a => role === "EVC_EXPERT" ? a.participantType === "EXPERT" && data.experts.some(e=>e.id===a.participantId&&e.userId===user.id) : a.participantType === "EXPERT" ? selectedExperts.has(a.participantId) : institutionIds.has(a.participantId));
  const documentIds = new Set(documents.map(d => d.id));
  const conditions = data.conditions.filter(c => role !== "EVC_EXPERT" && appIds.has(c.applicationId));
  const conditionIds = new Set(conditions.map(c => c.id));
  const evidence = data.evidence.filter(e => conditionIds.has(e.conditionId));
  const globalAdmin = scope.type === "GLOBAL";
  return { ...data, applications, institutions, visits, documents, conditions, evidence, availability, regions: data.regions.filter(r=>scope.type === "GLOBAL" || (scope.type === "REGION" && scope.id === r.id) || institutions.some(i=>i.regionId===r.id)),
    tasks: data.tasks.filter(t => (!t.applicationId || appIds.has(t.applicationId)) && (t.ownerId === user.id || ["REGIONAL", "CENTRAL"].includes(role))),
    notifications: data.notifications.filter(n => n.recipientId === user.id),
    submissions: data.submissions.filter(s => appIds.has(s.applicationId)), stageEvents: data.stageEvents.filter(s => appIds.has(s.applicationId)),
    deficiencies: data.deficiencies.filter(d => appIds.has(d.applicationId)), decisions: data.decisions.filter(d => appIds.has(d.applicationId)),
    documentChecks: data.documentChecks.filter(c => documentIds.has(c.documentId)), renewals: data.renewals.filter(r => documentIds.has(r.documentId)),
    slots: data.slots.filter(s => visitIds.has(s.visitId)), observations: data.observations.filter(o => visitIds.has(o.visitId)),
    meetingRecords: data.meetingRecords.filter(r => visitIds.has(r.visitId)), actionItems: data.actionItems.filter(a => visitIds.has(a.visitId)),
    invitations: data.invitations.filter(i => visitIds.has(i.visitId) && (role !== "EVC_EXPERT" || i.recipientId === user.id)),
    verifications: data.verifications.filter(v => evidence.some(e => e.id === v.evidenceId)),
    escalations: data.escalations.filter(e => appIds.has(e.entityId) || conditionIds.has(e.entityId) || visitIds.has(e.entityId)),
    auditEvents: data.auditEvents.filter(e => globalAdmin || appIds.has(e.entityId) || visitIds.has(e.entityId) || institutionIds.has(e.entityId) || documentIds.has(e.entityId) || conditionIds.has(e.entityId) || data.deficiencies.some(n => n.id === e.entityId && appIds.has(n.applicationId)) || data.meetingRecords.some(r => r.id === e.entityId && visitIds.has(r.visitId))),
    reportDefinitions: data.reportDefinitions.filter(r => r.roles.includes(role)), reportRuns: data.reportRuns.filter(r => r.requestedBy === user.id && (r.scope ? r.scope.type === scope.type && r.scope.id === scope.id && r.requestedRole === role : scope.type === "GLOBAL") && data.reportDefinitions.some(d => d.id === r.reportCode && d.roles.includes(role))),
    jobs: globalAdmin && role === "SYSTEM" ? data.jobs : [], integrations: globalAdmin && role === "SYSTEM" ? data.integrations : [],
    configurations: role === "POLICY" || role === "CENTRAL" ? data.configurations : [],
    workflows: role === "POLICY" || role === "CENTRAL" ? data.workflows : data.workflows.filter(w => w.status === "PUBLISHED" || applications.some(a => a.workflowId === w.id)),
  };
}

const builtPaths = [/^\/portal$/, /^\/portal\/(access|tasks|account|notifications|institutions|applications|documents|renewals|evc|availability|compliance|escalations|reports|report-runs|audit)(?:\/[a-zA-Z0-9-]+){0,4}$/, /^\/portal\/admin\/(users|workflows|rules|notification-rules|escalation-rules|integrations|jobs)(?:\/[a-zA-Z0-9-]+)?$/];
export function safeReturnTo(value: string | null | undefined) {
  if (!value || value.includes("\\") || value.startsWith("//")) return "/portal";
  try { const url = new URL(value, "https://portal.invalid"); return url.origin === "https://portal.invalid" && builtPaths.some(p => p.test(url.pathname)) ? url.pathname + url.search : "/portal"; } catch { return "/portal"; }
}
