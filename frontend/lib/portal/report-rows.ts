/** Report selectors consume already scoped collections, including local edits. */
import { demoNow } from "./view-models";
import type { PortalCollections, ReportCode } from "./types";
type Row = Record<string, string | number>;
const days = (from: string | null, to: string) => from ? Math.max(0, Math.floor((Date.parse(to) - Date.parse(from)) / 86400000)) : 0;
/** Pass an already scope-filtered dataset from the future demo session layer. */
export function getReportRows(code: ReportCode, data: PortalCollections, now: string = demoNow): Row[] {
    const institution = (id: string) => data.institutions.find(v => v.id === id);
    const application = (id: string) => data.applications.find(v => v.id === id);
    const user = (id: string | null) => data.users.find(v => v.id === id)?.displayName ?? "Unassigned";
    const active = data.applications.filter(a => !["DRAFT", "CLOSED", "REJECTED", "WITHDRAWN"].includes(a.status));
    const date = (value: string | null) => value ?? "Not applicable";
    switch (code) {
        case "region-performance": return data.regions.map(region => {
            const apps = data.applications.filter(a => institution(a.institutionId)?.regionId === region.id && a.submittedAt);
            const closed = apps.filter(a => a.closure);
            const visits = data.visits.filter(v => apps.some(a => a.id === v.applicationId));
            const conditions = data.conditions.filter(c => apps.some(a => a.id === c.applicationId));
            return { Region: region.name, Received: apps.length, Completed: closed.length,
                "Stage pendency": active.filter(a => apps.some(v => v.id === a.id)).map(a => a.currentStage).join(", "),
                "Processing time": closed.length ? `${Math.round(closed.reduce((sum, a) => sum + days(a.submittedAt, a.closure!.at), 0) / closed.length)} days (closed cases)` : "No closed cases",
                Overdue: apps.filter(a => a.dueAt && Date.parse(a.dueAt) < Date.parse(now) && !a.closure).length,
                "EVC completion": `${visits.filter(v => v.status === "COMPLETED").length}/${visits.length}`,
                Compliance: `${conditions.filter(c => c.status === "CLOSED").length}/${conditions.length} closed` };
        });
        case "application-pendency": return active.map(a => ({ Application: a.number, Institution: institution(a.institutionId)?.name ?? a.institutionId,
            Stage: a.currentStage, "Stage age": days(a.stageEnteredAt, now), "Application age": days(a.submittedAt, now), Deadline: date(a.dueAt),
            "Overdue duration": a.dueAt ? days(a.dueAt, now) : 0, Owner: user(a.ownerId), "Next action": a.nextAction }));
        case "evc-status": return data.visits.map(v => {
            const confirmed = data.slots.find(s => s.id === v.confirmedSlotId);
            const proposal = data.slots.find(s => s.visitId === v.id && s.feasible);
            const record = data.meetingRecords.find(r => r.visitId === v.id && r.type === "EVC_REPORT");
            return { Application: application(v.applicationId)?.number ?? v.applicationId, "Selected committee": v.committee.map(m => user(data.experts.find(e => e.id === m.expertId)?.userId ?? null)).join(", "),
                "Proposed date": date(proposal?.startAt ?? null), "Confirmed date": date(confirmed?.startAt ?? null), "Scheduling status": v.status,
                Deadline: v.requiredBy, Conflicts: data.slots.filter(s => s.visitId === v.id && !s.feasible).flatMap(s => s.blockers).join("; ") || "None",
                "Visit status": v.status, "Report status": record?.versions.find(r => r.number === record.currentVersion)?.status ?? "Not started" };
        });
        case "undertaking-compliance": return data.conditions.map(c => {
            const submissions = data.evidence.filter(e => e.conditionId === c.id);
            const latest = submissions.sort((a, b) => b.submissionNumber - a.submissionNumber)[0];
            const verification = latest && data.verifications.find(v => v.evidenceId === latest.id);
            return { Condition: c.code, "Due date": c.dueAt, "Evidence status": latest ? "SUBMITTED" : "NOT_SUBMITTED",
                "Verification status": verification?.result ?? c.status, "Overdue days": c.status === "CLOSED" ? 0 : days(c.dueAt, now),
                Reviewer: user(c.reviewerId), Escalation: data.escalations.find(e => e.entityId === c.id)?.status ?? "None" };
        });
        case "document-validity": return data.documents.map(d => {
            const version = d.versions.find(v => v.id === d.currentVersionId)!;
            return { Institution: institution(d.institutionId)?.name ?? d.institutionId, "Document type": d.type, "Issue date": date(version.issuedAt),
                "Expiry date": d.supportsExpiry ? date(version.expiryDate) : "Not applicable", Version: version.number, "Verification status": version.verification,
                "Renewal status": data.renewals.find(r => r.documentId === d.id)?.status ?? "Not required" };
        });
        case "overdue-actions": return [
            ...data.tasks.filter(t => t.status !== "COMPLETED" && Date.parse(t.dueAt) < Date.parse(now)).map(t => ({ "Entity type": "TASK", Case: t.applicationId ?? "", Action: t.title, Owner: user(t.ownerId), "Due date": t.dueAt, "Overdue duration": days(t.dueAt, now), "Escalation level": 0, Resolution: t.status })),
            ...data.conditions.filter(c => c.status !== "CLOSED" && Date.parse(c.dueAt) < Date.parse(now)).map(c => ({ "Entity type": "CONDITION", Case: c.applicationId, Action: c.description, Owner: user(c.reviewerId), "Due date": c.dueAt, "Overdue duration": days(c.dueAt, now), "Escalation level": data.escalations.find(e => e.entityId === c.id)?.level ?? 0, Resolution: c.status })),
        ];
        case "notification-delivery": return data.notifications.map(n => ({ Event: n.event, "Recipient category": data.users.find(u => u.id === n.recipientId)?.assignments[0]?.role ?? "Unknown",
            Channel: n.channel, "Delivery status": n.status, "Attempt count": n.attempts.length,
            "Failure reason": n.attempts.at(-1)?.failureReason ?? "None", "Last attempt": n.attempts.at(-1)?.at ?? "Not attempted" }));
        case "case-closure": return data.applications.filter(a => a.closure).map(a => ({ Application: a.number, "Closure date": a.closure!.at,
            "Final status": a.status, "Closure authority": user(a.closure!.authorityId), Reason: a.closure!.reason,
            Duration: days(a.submittedAt, a.closure!.at), "Reopen status": a.closure!.reopened ? "Reopened" : "Not reopened" }));
    }
}
