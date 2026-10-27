import type { PortalCollections, Role } from "./types";
import { ageDays, demoNow, humanize } from "./view-models";
export interface AnalyticsRecord {
    id: string;
    label: string;
    status: string;
    stage: string;
    institutionId: string;
    regionId: string;
    ownerId: string;
    type: string;
    year: string;
    date: string | null;
    dueAt: string | null;
    href: string;
    detail: string;
}
export interface DashboardQuery {
    version: 1;
    statuses: string[];
    stages: string[];
    regions: string[];
    institutions: string[];
    owners: string[];
    types: string[];
    years: string[];
    dateFrom: string;
    dateTo: string;
    overdue: boolean;
    quick: string;
    sort: string;
    page: number;
}
export const defaultQuery: DashboardQuery = { version: 1, statuses: [], stages: [], regions: [], institutions: [], owners: [], types: [], years: [], dateFrom: "", dateTo: "", overdue: false, quick: "", sort: "priority", page: 1 };
export const dashboardCopy: Record<Role, {
    title: string;
    subtitle: string;
    grain: string;
    primary: string;
    href: string;
}> = {
    INSTITUTION: { title: "Your institution, in focus.", subtitle: "Applications, obligations and the next step forward.", grain: "Applications", primary: "New application", href: "/portal/applications/new" },
    SCRUTINY: { title: "A clearer review queue.", subtitle: "Your assigned cases, evidence and review deadlines.", grain: "Assigned applications", primary: "Open review queue", href: "/portal/applications" },
    REGIONAL: { title: "Your region. A connected view.", subtitle: "Pendency, officer workload and the visits that need attention.", grain: "Regional applications", primary: "Review escalations", href: "/portal/escalations" },
    CENTRAL: { title: "Progress across every region.", subtitle: "Explore regional performance and trace the records behind it.", grain: "Applications", primary: "Performance report", href: "/portal/reports/region-performance" },
    EVC_COORDINATOR: { title: "Bring the next visit together.", subtitle: "Selected committees, shared availability and report readiness.", grain: "Expert visits", primary: "Open scheduling queue", href: "/portal/evc" },
    EVC_EXPERT: { title: "Your expertise. In context.", subtitle: "Assigned visits, invitations and source-linked observations.", grain: "Assigned visits", primary: "Confirm availability", href: "/portal/availability" },
    COMPLIANCE: { title: "Follow the evidence forward.", subtitle: "Separate submissions, verified results and authorised closure.", grain: "Approval conditions", primary: "Review evidence", href: "/portal/compliance" },
    POLICY: { title: "Consistency starts with the rules.", subtitle: "Published workflows and the drafts shaping the next version.", grain: "Workflow versions", primary: "Build workflow", href: "/portal/admin/workflows/new" },
    AUDITOR: { title: "Every action has a history.", subtitle: "Trace actors, reasons and the source of each recorded change.", grain: "Audit events", primary: "Verify local integrity", href: "/portal/audit/verify" },
    SYSTEM: { title: "Keep the work moving.", subtitle: "Operational queues, delivery attempts and connector freshness.", grain: "Operational jobs", primary: "Open jobs console", href: "/portal/admin/jobs" }
};
export function analyticsRecords(data: PortalCollections, role: Role): AnalyticsRecord[] {
    const base = { stage: "", institutionId: "", regionId: "", ownerId: "", type: "", year: "", date: null, dueAt: null, detail: "" };
    const appContext = (id: string) => { const a = data.applications.find(a => a.id === id); const i = data.institutions.find(i => i.id === a?.institutionId); return { institutionId: i?.id ?? "", regionId: i?.regionId ?? "", year: a?.academicYear ?? "" }; };
    if (role === "POLICY")
        return data.workflows.map(w => ({ ...base, id: w.id, label: w.name, status: w.status, stage: w.aphVersion, type: "WORKFLOW", date: w.effectiveFrom, href: `/portal/admin/workflows/${w.id}`, detail: `v${w.version} · ${w.stages.length} stages · ${w.aphVersion}` }));
    if (role === "SYSTEM")
        return data.jobs.map(j => ({ ...base, id: j.id, label: humanize(j.type), status: j.status, type: j.type, date: j.nextAttemptAt, dueAt: j.nextAttemptAt, href: "/portal/admin/jobs", detail: `${j.attempts} attempts · ${j.lastError ?? "No error recorded"}` }));
    if (role === "AUDITOR")
        return data.auditEvents.map(e => ({ ...base, id: e.id, label: humanize(e.action), status: e.anchor, stage: e.entityType, type: e.action, ownerId: e.actorId, date: e.at, href: "/portal/audit", detail: `${e.entityId} · ${e.reason} · ${e.correlationId}` }));
    if (role === "COMPLIANCE")
        return data.conditions.map(c => ({ ...base, ...appContext(c.applicationId), id: c.id, label: c.code, status: c.status, stage: "COMPLIANCE", type: "UNDERTAKING", ownerId: c.reviewerId, date: data.decisions.find(d => d.id === c.sourceDecisionId)?.at ?? null, dueAt: c.dueAt, href: `/portal/compliance/${c.id}`, detail: c.description }));
    if (role === "EVC_COORDINATOR" || role === "EVC_EXPERT")
        return data.visits.map(v => ({ ...base, ...appContext(v.applicationId), id: v.id, label: data.applications.find(a => a.id === v.applicationId)?.number ?? v.id, status: v.status, stage: "EVC", ownerId: v.coordinatorId, type: "VISIT", date: data.slots.find(s => s.id === v.confirmedSlotId)?.startAt ?? null, dueAt: v.requiredBy, href: `/portal/evc/${v.id}`, detail: `${v.committee.length}/${v.requiredMemberCount} selected experts · ${data.meetingRecords.filter(r => r.visitId === v.id).length} meeting records` }));
    return data.applications.map(a => ({ ...base, ...appContext(a.id), id: a.id, label: a.number, status: a.status, stage: a.currentStage, ownerId: a.ownerId ?? "", type: a.type, year: a.academicYear, date: a.submittedAt, dueAt: a.dueAt, href: `/portal/applications/${a.id}`, detail: `${a.nextAction} · ${ageDays(a.stageEnteredAt) ?? "unavailable"} days in stage` }));
}
export const complete = (r: AnalyticsRecord) => ["CLOSED", "REJECTED", "WITHDRAWN", "COMPLETED", "PUBLISHED", "ANCHORED"].includes(r.status);
export const overdue = (r: AnalyticsRecord) => !complete(r) && !!r.dueAt && Date.parse(r.dueAt) < Date.parse(demoNow);
export function validateQuery(raw: unknown, records: AnalyticsRecord[]): DashboardQuery { const q = raw && typeof raw === "object" ? raw as Partial<DashboardQuery> : {}; const next = { ...defaultQuery }; for (const [key, field] of [["statuses", "status"], ["stages", "stage"], ["regions", "regionId"], ["institutions", "institutionId"], ["owners", "ownerId"], ["types", "type"], ["years", "year"]] as const) {
    const allowed = new Set(records.map(r => r[field]));
    next[key] = Array.isArray(q[key]) ? [...new Set(q[key]!.filter(v => typeof v === "string" && allowed.has(v)))] : [];
} const date = (v: unknown) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) ? v : ""; next.dateFrom = date(q.dateFrom); next.dateTo = date(q.dateTo); if (next.dateFrom && next.dateTo && next.dateFrom > next.dateTo) {
    next.dateFrom = "";
    next.dateTo = "";
} next.overdue = q.overdue === true; next.quick = ["open", "complete", "overdue"].includes(q.quick ?? "") ? q.quick! : ""; next.sort = q.sort === "label" ? "label" : "priority"; next.page = Number.isFinite(q.page) ? Math.max(1, Math.floor(q.page!)) : 1; return next; }
export function filterAnalytics(records: AnalyticsRecord[], q: DashboardQuery, ignoreStatus = false) { return records.filter(r => (ignoreStatus || !q.statuses.length || q.statuses.includes(r.status)) && (!q.stages.length || q.stages.includes(r.stage)) && (!q.regions.length || q.regions.includes(r.regionId)) && (!q.institutions.length || q.institutions.includes(r.institutionId)) && (!q.owners.length || q.owners.includes(r.ownerId)) && (!q.types.length || q.types.includes(r.type)) && (!q.years.length || q.years.includes(r.year)) && (!q.dateFrom || !!r.date && r.date.slice(0, 10) >= q.dateFrom) && (!q.dateTo || !!r.date && r.date.slice(0, 10) <= q.dateTo) && (!q.overdue || overdue(r)) && (!q.quick || (q.quick === "complete" ? complete(r) : q.quick === "overdue" ? overdue(r) : !complete(r)))); }
export function groupAnalytics(records: AnalyticsRecord[], field: keyof AnalyticsRecord) { return [...new Set(records.map(r => r[field] || "Unassigned"))].map(key => ({ key: String(key || "Unassigned"), count: records.filter(r => (r[field] || "Unassigned") === key).length })).sort((a, b) => b.count - a.count || a.key.localeCompare(b.key)); }
