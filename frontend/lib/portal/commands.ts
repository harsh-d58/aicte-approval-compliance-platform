import type { PortalCollections, Role, User, ApplicationStatus, Configuration, ReportCode } from "./types";
import { demoNow, scopedSnapshot } from "./view-models";
export type CommandKind = "document.verify" | "institution.import" | "attribute.verify" | "renewal.start" | "actionitem.save" | "actionitem.complete" | "application.migrate" | "institution.save" | "campus.save" | "attribute.save" | "application.save" | "application.submit" | "application.assign" | "application.advance" | "application.cancel" | "application.reopen" | "deficiency.issue" | "deficiency.respond" | "deficiency.resolve" | "decision.record" | "document.save" | "document.check" | "document.review" | "renewal.submit" | "renewal.verify" | "committee.save" | "availability.save" | "visit.recommend" | "visit.confirm" | "visit.postpone" | "visit.cancel" | "visit.complete" | "invitation.respond" | "observation.save" | "record.generate" | "record.save" | "record.review" | "record.approve" | "record.changes" | "condition.create" | "evidence.submit" | "evidence.verify" | "condition.close" | "condition.reopen" | "notification.retry" | "notification.read" | "escalation.resolve" | "workflow.save" | "workflow.publish" | "config.save" | "config.publish" | "user.assignment" | "user.status" | "integration.test" | "integration.disable" | "job.retry" | "job.process" | "report.create" | "report.complete";
export interface Command {
    kind: CommandKind;
    id?: string;
    expectedVersion?: number;
    values?: Record<string, unknown>;
}
export interface CommandResult {
    data: PortalCollections;
    id: string;
    message: string;
}
export class CommandError extends Error {
    constructor(message: string, public code = "VALIDATION") { super(message); }
}
export const uid = (prefix: string) => `${prefix}-${globalThis.crypto.randomUUID()}`;
const fail = (message: string, code?: string): never => { throw new CommandError(message, code); };
const requireValue = (condition: unknown, message: string) => { if (!condition)
    fail(message); };
export function can(role: Role, ...roles: Role[]) { return roles.includes(role); }
export function workflowErrors(workflow: PortalCollections["workflows"][number]): string[] {
    const errors: string[] = [];
    const stages = new Set(workflow.stages.map(s => s.code));
    if (!workflow.name.trim() || !workflow.aphVersion.trim())
        errors.push("Name and APH reference are required.");
    if (workflow.stages.length < 2)
        errors.push("At least two stages are required.");
    if (stages.size !== workflow.stages.length)
        errors.push("Stage codes must be unique.");
    if (workflow.stages.some(s => !/^[A-Z][A-Z0-9_]*$/.test(s.code) || !s.name.trim() || !Number.isFinite(s.slaDays) || s.slaDays < 0))
        errors.push("Stages require a valid code, name and non-negative SLA.");
    if (workflow.transitions.some(t => !stages.has(t.from) || !stages.has(t.to) || t.from === t.to || !t.guards.length || t.guards.some(g => !g.trim())))
        errors.push("Transitions need valid distinct stages and explicit guards.");
    if (workflow.stages.length) {
        const reached = new Set([workflow.stages[0].code]);
        for (let i = 0; i < stages.size; i++)
            workflow.transitions.forEach(t => { if (reached.has(t.from))
                reached.add(t.to); });
        if (reached.size !== stages.size)
            errors.push("Every stage must be reachable from the first stage.");
    }
    return errors;
}
export function recommendVisit(data: PortalCollections, visitId: string) {
    const visit = data.visits.find(v => v.id === visitId);
    requireValue(visit, "Visit unavailable.");
    const v = visit!;
    const app = data.applications.find(a => a.id === v.applicationId)!;
    const participants = [...v.committee.map(m => m.expertId), app.institutionId];
    const blockers: string[] = [];
    if (new Set(v.committee.map(m => m.expertId)).size !== v.requiredMemberCount || v.committee.some(m => !data.experts.some(e => e.id === m.expertId && e.eligibility === "ELIGIBLE")))
        blockers.push("Committee must contain distinct eligible experts.");
    if (v.committee.length !== v.requiredMemberCount)
        blockers.push(`Select exactly ${v.requiredMemberCount} experts first.`);
    const freshnessHours = v.policy?.freshnessHours ?? 24;
    const preparationHours = v.policy?.preparationLeadHours ?? 48;
    const fresh = (at: string) => Date.parse(demoNow) - Date.parse(at) >= 0 && Date.parse(demoNow) - Date.parse(at) <= freshnessHours * 3600000;
    const windows = participants.map(id => data.availability.filter(a => a.participantId === id && !a.supersededAt && a.state === "AVAILABLE" && fresh(a.confirmedAt)));
    participants.forEach((id, i) => { if (!windows[i].length)
        blockers.push(`${id}: missing or stale availability.`); });
    const candidates: {
        startAt: string;
        endAt: string;
        blockers: string[];
    }[] = [];
    if (!blockers.length)
        for (const first of windows[0]) {
            let intervals = [{ start: Date.parse(first.startAt), end: Date.parse(first.endAt) }];
            for (const list of windows.slice(1))
                intervals = intervals.flatMap(interval => list.map(w => ({ start: Math.max(interval.start, Date.parse(w.startAt)), end: Math.min(interval.end, Date.parse(w.endAt)) })).filter(w => w.end - w.start >= v.durationMinutes * 60000));
            for (const interval of intervals) {
                const boundaries = new Set([Math.max(interval.start, Date.parse(demoNow) + preparationHours * 3600000)]);
                data.availability.filter(a => participants.includes(a.participantId) && !a.supersededAt && a.state === "BUSY").forEach(a => { const end = Date.parse(a.endAt); if (end >= interval.start && end < interval.end)
                    boundaries.add(end); });
                data.visits.filter(other => other.id !== v.id && other.status === "CONFIRMED" && (other.committee.some(m => participants.includes(m.expertId)) || data.applications.find(a => a.id === other.applicationId)?.institutionId === app.institutionId)).forEach(other => { const slot = data.slots.find(s => s.id === other.confirmedSlotId); if (slot) {
                    const end = Date.parse(slot.endAt);
                    if (end >= interval.start && end < interval.end)
                        boundaries.add(end);
                } });
                for (const start of boundaries) {
                    if (start < Date.parse(demoNow) + preparationHours * 3600000)
                        continue;
                    const end = start + v.durationMinutes * 60000;
                    if (end > interval.end || end > Date.parse(v.requiredBy))
                        continue;
                    const conflicts = data.availability.filter(a => participants.includes(a.participantId) && !a.supersededAt && a.state === "BUSY" && Date.parse(a.startAt) < end && Date.parse(a.endAt) > start).map(a => `${a.participantId} is busy.`);
                    data.visits.filter(other => other.id !== v.id && other.status === "CONFIRMED").forEach(other => { const slot = data.slots.find(s => s.id === other.confirmedSlotId); const otherApp = data.applications.find(a => a.id === other.applicationId); if (slot && Date.parse(slot.startAt) < end && Date.parse(slot.endAt) > start && (otherApp?.institutionId === app.institutionId || other.committee.some(m => participants.includes(m.expertId))))
                        conflicts.push(`Confirmed booking conflict: ${other.id}.`); });
                    candidates.push({ startAt: new Date(start).toISOString(), endAt: new Date(end).toISOString(), blockers: conflicts });
                }
            }
        }
    const unique = candidates.filter((c, i, all) => all.findIndex(v => v.startAt === c.startAt) === i).sort((a, b) => a.startAt.localeCompare(b.startAt));
    if (!unique.some(c => !c.blockers.length) && !blockers.length)
        blockers.push("No common interval meets duration, preparation time, conflicts and the deadline.");
    return { participants, candidates: unique, blockers };
}
/** All commands operate only on fictional frontend records. Live services must enforce the same checks. */
export function applyCommand(snapshot: PortalCollections, actor: User, index: number, command: Command): CommandResult {
    const currentActor = snapshot.users.find(user => user.id === actor.id);
    requireValue(currentActor && currentActor.status === "ACTIVE", "Your demonstration identity is unavailable or disabled.");
    actor = currentActor!;
    const assignment = actor.assignments[index];
    requireValue(actor.status === "ACTIVE" && assignment && (!assignment.validUntil || Date.parse(assignment.validUntil) >= Date.parse(demoNow)), "Your assignment is unavailable or expired.");
    const role = assignment.role;
    const scoped = scopedSnapshot(snapshot, actor, index);
    const data = structuredClone(snapshot);
    const input = command.values ?? {};
    let id = command.id ?? "";
    let message = "Changes saved to this demonstration.";
    const text = (key: string, required = true) => { const value = typeof input[key] === "string" ? (input[key] as string).trim() : ""; if (required && !value)
        fail(`${key.replaceAll(/([A-Z])/g, " $1")} is required.`); return value; };
    const list = (key: string): string[] => Array.isArray(input[key]) ? (input[key] as unknown[]).filter((v): v is string => typeof v === "string") : [];
    const number = (key: string, fallback = 0) => { const n = Number(input[key] ?? fallback); requireValue(Number.isFinite(n), `${key} must be a number.`); return n; };
    const date = (key: string, future = false) => { const raw = text(key); const value = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(raw) ? `${raw}:00+05:30` : raw; requireValue(Number.isFinite(Date.parse(value)) && (!future || Date.parse(value) > Date.parse(demoNow)), `${key} must be ${future ? "after the demonstration clock" : "a valid date"}.`); return value; };
    const permit = (...roles: Role[]) => { if (!roles.includes(role))
        fail("This action is not permitted for your current role.", "FORBIDDEN"); };
    const version = (record: {
        version: number;
    }) => { if (command.expectedVersion !== undefined && record.version !== command.expectedVersion)
        fail("This record has changed. Reload and reconcile your unsaved values.", "VERSION_CONFLICT"); };
    const appById = (appId = id) => { requireValue(scoped.applications.some(a => a.id === appId), "Application unavailable in this scope."); return data.applications.find(a => a.id === appId)!; };
    const docById = (docId = id) => { requireValue(scoped.documents.some(d => d.id === docId), "Document unavailable in this scope."); return data.documents.find(d => d.id === docId)!; };
    const visitById = (visitId = id) => { requireValue(scoped.visits.some(v => v.id === visitId), "Visit unavailable in this scope."); return data.visits.find(v => v.id === visitId)!; };
    const conditionById = () => { requireValue(scoped.conditions.some(c => c.id === id), "Condition unavailable in this scope."); return data.conditions.find(c => c.id === id)!; };
    const institutional = (institutionId: string) => { permit("INSTITUTION"); requireValue(assignment.scope.type === "INSTITUTION" && assignment.scope.id === institutionId, "Institution unavailable in this assignment."); };
    const notify = (institutionId: string, event: string, entityType: "APPLICATION" | "EVC" | "CONDITION" | "DOCUMENT", entityId: string) => data.users.filter(u => u.assignments.some(a => a.role === "INSTITUTION" && a.scope.id === institutionId)).forEach(u => data.notifications.unshift({ id: uid("notification"), recipientId: u.id, event, channel: "IN_APP", status: "DELIVERED", entityType, entityId, createdAt: demoNow, read: false, attempts: [{ number: 1, at: demoNow, result: "DELIVERED", failureReason: null }] }));
    const task = (applicationId: string, ownerId: string, title: string, dueAt: string, href: string) => { if (!data.tasks.some(t => t.applicationId === applicationId && t.ownerId === ownerId && t.title === title && t.status !== "COMPLETED"))
        data.tasks.push({ id: uid("task"), applicationId, ownerId, title, dueAt, href, status: "PENDING" }); };
    const finishTasks = (appId: string, ownerId: string) => data.tasks.filter(t => t.applicationId === appId && t.ownerId === ownerId).forEach(t => { t.status = "COMPLETED"; });
    const transition = (app: PortalCollections["applications"][number], status: ApplicationStatus, stage: string, reason: string) => { data.stageEvents.push({ id: uid("stage"), applicationId: app.id, at: demoNow, actorId: actor.id, from: app.status, to: status, reason, workflowId: app.workflowId }); app.status = status; app.currentStage = stage; app.stageEnteredAt = demoNow; app.version++; app.nextAction = status === "CLOSED" ? "View historical record" : `Continue ${stage.toLowerCase()} action`; };
    const selectedVersions = (institutionId: string) => { const ids = list("documentVersionIds"); requireValue(ids.length, "Select at least one document version."); requireValue(ids.every(versionId => data.documents.some(d => d.institutionId === institutionId && d.versions.some(v => v.id === versionId && v.scan === "CLEAN"))), "Each version must belong to this institution and pass local validation."); return ids; };
    switch (command.kind) {
        case "institution.import": {
            permit("SYSTEM");
            const rows = input.rows as {
                code: string;
                name: string;
                regionId: string;
                type: string;
                campusName: string;
                city: string;
            }[];
            requireValue(Array.isArray(rows) && rows.length > 0 && rows.length <= 200, "Import requires 1â€“200 previewed rows.");
            const codes = new Set(data.institutions.map(i => i.code.toLowerCase()));
            for (const row of rows) {
                requireValue(row.code?.trim() && row.name?.trim() && row.type?.trim() && row.campusName?.trim() && row.city?.trim() && data.regions.some(r => r.id === row.regionId), "Every import row needs valid mapped fields and an existing region.");
                requireValue(!codes.has(row.code.toLowerCase()), "Duplicate institution code in import or existing records.");
                codes.add(row.code.toLowerCase());
            }
            text("reason");
            for (const row of rows)
                data.institutions.push({ id: uid("inst"), code: row.code.trim(), name: row.name.trim(), type: row.type.trim(), regionId: row.regionId, status: "ACTIVE", campuses: [{ id: uid("campus"), name: row.campusName.trim(), city: row.city.trim(), primary: true }], attributes: [] });
            id = uid("import");
            message = `Imported ${rows.length} fictional institution records locally.`;
            break;
        }
        case "attribute.verify": {
            permit("REGIONAL", "CENTRAL");
            requireValue(scoped.institutions.some(i => i.id === id), "Institution unavailable.");
            const attribute = data.institutions.find(i => i.id === id)?.attributes.find(a => a.key === text("key"));
            requireValue(attribute?.sourceVersionId && scoped.documents.some(d => d.versions.some(v => v.id === attribute.sourceVersionId && v.verification === "VERIFIED")), "A verified source document version is required.");
            text("reason");
            attribute!.verification = "VERIFIED";
            break;
        }
        case "renewal.start": {
            const doc = docById();
            institutional(doc.institutionId);
            requireValue(doc.supportsExpiry, "Non-expiring categories do not require renewal.");
            requireValue(!data.renewals.some(r => r.documentId === id && r.status !== "VERIFIED"), "An active renewal already exists.");
            const v = doc.versions.find(v => v.id === doc.currentVersionId)!;
            requireValue(v.expiryDate, "Declare an expiry date first.");
            id = uid("renewal");
            data.renewals.push({ id, documentId: doc.id, previousVersionId: v.id, submittedVersionId: null, dueAt: v.expiryDate!, status: "OPEN", assignedTo: "user-compliance" });
            break;
        }
        case "application.migrate": {
            permit("REGIONAL", "CENTRAL");
            const app = appById();
            version(app);
            requireValue(!app.closure && app.status !== "DRAFT", "Only active submitted cases can migrate.");
            const target = data.workflows.find(w => w.id === text("workflowId") && w.status === "PUBLISHED");
            requireValue(target && target.id !== app.workflowId && target.stages.some(s => s.code === app.currentStage), "Choose a different published workflow containing the current stage.");
            const reason = text("reason");
            const coiOverrideReason = text("coiOverrideReason", false) || null;
            const previous = app.workflowId;
            app.workflowId = target!.id;
            app.version++;
            data.stageEvents.push({ id: uid("stage"), applicationId: app.id, at: demoNow, actorId: actor.id, from: app.currentStage, to: app.currentStage, reason: `Migration from ${previous} to ${app.workflowId}: ${reason}`, workflowId: app.workflowId });
            break;
        }
        case "actionitem.save": {
            permit("EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL");
            const visitId = text("visitId");
            visitById(visitId);
            const observationId = text("observationId");
            requireValue(data.observations.some(o => o.id === observationId && o.visitId === visitId && o.status === "SUBMITTED"), "Choose a submitted source observation.");
            id = uid("action");
            data.actionItems.push({ id, visitId, observationId, description: text("description"), responsibleRole: text("responsibleRole") as Role, dueAt: date("dueAt", true), status: "OPEN" });
            break;
        }
        case "actionitem.complete": {
            permit("EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL");
            const item = data.actionItems.find(a => a.id === id && scoped.actionItems.some(s => s.id === id));
            requireValue(item && item.status === "OPEN", "Open action item unavailable.");
            text("reason");
            item!.status = "COMPLETED";
            break;
        }
        case "institution.save": {
            const existing = id ? data.institutions.find(i => i.id === id) : undefined;
            if (existing) {
                requireValue(scoped.institutions.some(i => i.id === id), "Institution unavailable.");
                permit("INSTITUTION", "REGIONAL", "CENTRAL");
            }
            else
                permit("REGIONAL", "CENTRAL");
            const regionId = existing?.regionId ?? text("regionId");
            requireValue(data.regions.some(r => r.id === regionId) && (assignment.scope.type === "GLOBAL" || assignment.scope.id === regionId || (existing && assignment.scope.id === existing.id)), "Region is outside your assignment.");
            const code = text("code");
            requireValue(!data.institutions.some(i => i.code.toLowerCase() === code.toLowerCase() && i.id !== id), "This institution code already exists.");
            if (existing) {
                existing.name = text("name");
                existing.code = code;
                existing.type = text("type");
            }
            else {
                id = uid("inst");
                data.institutions.push({ id, code, name: text("name"), type: text("type"), regionId, status: "ACTIVE", campuses: [{ id: uid("campus"), name: text("campusName"), city: text("city"), primary: true }], attributes: [] });
            }
            break;
        }
        case "campus.save":
        case "attribute.save": {
            requireValue(scoped.institutions.some(i => i.id === id), "Institution unavailable.");
            permit("INSTITUTION", "REGIONAL", "CENTRAL");
            const institution = data.institutions.find(i => i.id === id)!;
            if (command.kind === "campus.save")
                institution.campuses.push({ id: uid("campus"), name: text("name"), city: text("city"), primary: !institution.campuses.length });
            else {
                const key = text("key");
                const attribute = { key, value: text("value"), verification: "PENDING" as const, sourceVersionId: text("sourceVersionId", false) || null };
                const position = institution.attributes.findIndex(a => a.key === key);
                if (position < 0)
                    institution.attributes.push(attribute);
                else
                    institution.attributes[position] = attribute;
            }
            break;
        }
        case "application.save": {
            const institutionId = text("institutionId");
            institutional(institutionId);
            const institution = data.institutions.find(i => i.id === institutionId)!;
            const campusId = text("campusId");
            requireValue(institution.campuses.some(c => c.id === campusId), "Choose an authorised campus.");
            requireValue(/^\d{4}-\d{2}$/.test(text("academicYear")), "Academic year must use YYYY-YY.");
            const workflowId = text("workflowId");
            requireValue(data.workflows.some(w => w.id === workflowId && w.status === "PUBLISHED"), "Select a published sample workflow.");
            if (id) {
                const app = appById();
                version(app);
                requireValue(app.status === "DRAFT", "Only draft applications can be edited.");
                Object.assign(app, { campusId, type: text("type"), academicYear: text("academicYear"), workflowId, version: app.version + 1 });
            }
            else {
                id = uid("app");
                data.applications.push({ id, number: `DRAFT-2027-${String(data.applications.length + 1).padStart(4, "0")}`, institutionId, campusId, type: text("type"), academicYear: text("academicYear"), status: "DRAFT", workflowId, currentStage: "INTAKE", stageEnteredAt: null, submittedAt: null, dueAt: null, ownerId: actor.id, nextAction: "Complete and submit the draft", version: 1, closure: null });
            }
            break;
        }
        case "application.submit": {
            const app = appById();
            institutional(app.institutionId);
            version(app);
            requireValue(app.status === "DRAFT", "This draft has already been submitted.");
            requireValue(input.declaration === true, "Confirm the declaration before submitting.");
            const documents = data.documents.filter(d => d.institutionId === app.institutionId && (!d.applicationId || d.applicationId === app.id));
            const required = ["LEASE", "REGISTRATION"];
            requireValue(required.every(type => documents.some(d => d.type === type && d.versions.some(v => v.id === d.currentVersionId && v.scan === "CLEAN"))), "Sample route requires locally validated lease and registration documents.");
            const workflow = data.workflows.find(w => w.id === app.workflowId)!;
            requireValue(workflow.status === "PUBLISHED", "Workflow is no longer available.");
            app.submittedAt = demoNow;
            app.number = app.number.replace("DRAFT", "AICTE");
            app.ownerId = data.users.find(u => u.status === "ACTIVE" && u.assignments.some(a => a.role === "SCRUTINY" && (a.scope.type === "GLOBAL" || a.scope.id === data.institutions.find(i => i.id === app.institutionId)?.regionId)))?.id ?? null;
            app.dueAt = new Date(Date.parse(demoNow) + 7 * 86400000).toISOString();
            transition(app, "SUBMITTED", workflow.stages[0].code, "Institution declaration and required sample documents submitted");
            data.submissions.push({ id: uid("submission"), applicationId: app.id, number: 1, submittedAt: demoNow, submittedBy: actor.id, noticeId: null, documentVersionIds: documents.map(d => d.currentVersionId) });
            if (app.ownerId)
                task(app.id, app.ownerId, "Review submitted application", app.dueAt, `/portal/applications/${app.id}/review`);
            notify(app.institutionId, "APPLICATION_SUBMITTED", "APPLICATION", app.id);
            break;
        }
        case "application.assign": {
            permit("REGIONAL", "CENTRAL");
            const app = appById();
            version(app);
            const ownerId = text("ownerId");
            requireValue(data.users.some(u => u.id === ownerId && u.status === "ACTIVE" && u.assignments.some(a => a.role === "SCRUTINY" && (a.scope.type === "GLOBAL" || a.scope.id === data.institutions.find(i => i.id === app.institutionId)?.regionId))), "Choose an active scrutiny officer in the case region.");
            text("reason");
            app.ownerId = ownerId;
            app.dueAt = date("dueAt", true);
            app.version++;
            data.tasks.filter(t => t.applicationId === app.id && t.status !== "COMPLETED").forEach(t => { if (t.ownerId !== "user-institution")
                t.ownerId = ownerId; });
            task(app.id, ownerId, "Review assigned application", app.dueAt, `/portal/applications/${app.id}/review`);
            break;
        }
        case "deficiency.issue": {
            permit("SCRUTINY", "REGIONAL");
            const app = appById();
            version(app);
            requireValue(["SUBMITTED", "IN_REVIEW", "RESUBMITTED"].includes(app.status), "A deficiency can be issued only during active review.");
            const reason = text("reason");
            const description = text("description");
            const criterion = text("criterion");
            const due = date("dueAt", true);
            const noticeId = uid("notice");
            const valuesItems = command.values?.items;
            const rawItems = Array.isArray(valuesItems) && valuesItems.length > 0
                ? (valuesItems as Array<Record<string, unknown>>)
                : [{ criterion, description, documentId: text("documentId", false) || null }];
            const deficiencyItems = rawItems.map(it => ({
                id: uid("item"),
                criterion: String(it.criterion ?? "General"),
                description: String(it.description ?? ""),
                documentId: it.documentId ? String(it.documentId) : null,
                status: "OPEN" as const,
                response: null,
                responseVersionId: null,
            }));
            data.deficiencies.push({ id: noticeId, number: `DEF-2026-${String(data.deficiencies.length + 1).padStart(3, "0")}`, applicationId: app.id, issuedBy: actor.id, issuedAt: demoNow, responseDueAt: due, reason, status: "OPEN", items: deficiencyItems });
            transition(app, "RETURNED_FOR_DEFICIENCY", "SCRUTINY", reason);
            notify(app.institutionId, "DEFICIENCY_ISSUED", "APPLICATION", app.id);
            const representative = data.users.find(u => u.assignments.some(a => a.role === "INSTITUTION" && a.scope.id === app.institutionId));
            if (representative)
                task(app.id, representative.id, "Respond to deficiency notice", due, `/portal/applications/${app.id}/deficiencies/${noticeId}`);
            id = noticeId;
            break;
        }
        case "deficiency.respond":
        case "deficiency.resolve": {
            const notice = data.deficiencies.find(n => n.id === id);
            requireValue(notice && scoped.deficiencies.some(n => n.id === id), "Notice unavailable.");
            const app = appById(notice!.applicationId);
            version(app);
            if (command.kind === "deficiency.respond") {
                institutional(app.institutionId);
                requireValue(notice!.status === "OPEN", "This notice has already received a response.");
                const response = text("response");
                const versions = selectedVersions(app.institutionId);
                notice!.items.forEach(item => { item.response = response; item.responseVersionId = versions[0]; item.status = "RESPONDED"; });
                notice!.status = "RESPONDED";
                data.submissions.push({ id: uid("submission"), applicationId: app.id, number: data.submissions.filter(s => s.applicationId === app.id).length + 1, submittedAt: demoNow, submittedBy: actor.id, noticeId: id, documentVersionIds: versions });
                transition(app, "RESUBMITTED", "SCRUTINY", "Institution submitted a versioned deficiency response");
                finishTasks(app.id, actor.id);
                if (app.ownerId)
                    task(app.id, app.ownerId, "Review deficiency response", app.dueAt ?? demoNow, `/portal/applications/${app.id}/review`);
            }
            else {
                permit("SCRUTINY", "REGIONAL");
                requireValue(notice!.status === "RESPONDED" || notice!.items.some(i => i.status === "RESPONDED"), "A response must be submitted first.");
                text("reason");
                const valItemId = command.values?.itemId;
                const valRes = command.values?.resolution;
                if (valItemId) {
                    const item = notice!.items.find(i => i.id === valItemId);
                    if (item) {
                        item.status = valRes === "REJECTED" ? "OPEN" : "RESOLVED";
                    }
                    if (notice!.items.every(i => i.status === "RESOLVED")) {
                        notice!.status = "RESOLVED";
                        app.version++;
                    } else if (valRes === "REJECTED") {
                        notice!.status = "OPEN";
                    }
                } else {
                    notice!.items.forEach(item => { item.status = "RESOLVED"; });
                    notice!.status = "RESOLVED";
                    app.version++;
                }
            }
            break;
        }
        case "application.advance": {
            permit("SCRUTINY", "REGIONAL");
            const app = appById();
            version(app);
            const reason = text("reason");
            const workflow = data.workflows.find(w => w.id === app.workflowId)!;
            if (app.status === "SUBMITTED" || app.status === "RESUBMITTED") {
                transition(app, "IN_REVIEW", "SCRUTINY", reason);
                break;
            }
            requireValue(app.status === "IN_REVIEW", "This action is only available during scrutiny.");
            requireValue(data.deficiencies.filter(n => n.applicationId === app.id).every(n => n.status === "RESOLVED"), "Resolve all deficiency items before advancing.");
            const requiredDocs = data.documents.filter(d => d.institutionId === app.institutionId && ["LEASE", "REGISTRATION"].includes(d.type) && (!d.applicationId || d.applicationId === app.id));
            requireValue(["LEASE", "REGISTRATION"].every(type => requiredDocs.some(d => d.type === type && d.versions.some(v => v.id === d.currentVersionId && v.verification === "VERIFIED"))), "Verify required current lease and registration evidence before completing scrutiny.");
            const next = workflow.transitions.find(t => t.from === "SCRUTINY");
            requireValue(next, "No configured scrutiny transition is available.");
            if (next!.to === "EVC") {
                transition(app, "AWAITING_EVC", "EVC", reason);
                const visitId = uid("visit");
                const policy = data.configurations.filter(c => c.category === "COMMITTEE" && c.status === "PUBLISHED").at(-1);
                if (!data.visits.some(v => v.applicationId === app.id && v.status !== "CANCELLED"))
                    data.visits.push({ id: visitId, applicationId: app.id, campusId: app.campusId, status: "READY", requiredBy: new Date(Date.parse(demoNow) + 21 * 86400000).toISOString(), durationMinutes: Number(policy?.values.durationMinutes ?? 180), requiredMemberCount: Number(policy?.values.memberCount ?? 5), policy: { freshnessHours: Number(policy?.values.availabilityFreshnessHours ?? 24), preparationLeadHours: Number(policy?.values.preparationLeadHours ?? 48), configurationId: policy?.id ?? "sample-default" }, coordinatorId: "user-coordinator", committee: [], confirmedSlotId: null, version: 1, events: [] });
            }
            else
                transition(app, "DECISION_PENDING", "DECISION", reason);
            finishTasks(app.id, actor.id);
            break;
        }
        case "application.cancel":
        case "application.reopen": {
            permit("REGIONAL");
            const app = appById();
            version(app);
            const reason = text("reason");
            if (command.kind === "application.cancel") {
                requireValue(!app.closure, "Case is already terminal.");
                transition(app, "WITHDRAWN", "CLOSURE", reason);
                app.closure = { at: demoNow, authorityId: actor.id, reason, reopened: false };
            }
            else {
                requireValue(app.closure, "Only a closed case can be reopened.");
                transition(app, "IN_REVIEW", "SCRUTINY", reason);
                app.closure = null;
                app.dueAt = new Date(Date.parse(demoNow) + 7 * 86400000).toISOString();
            }
            break;
        }
        case "decision.record": {
            permit("REGIONAL");
            const app = appById();
            version(app);
            const reason = text("reason");
            const outcome = text("outcome");
            requireValue(["APPROVE", "REJECT", "CLOSE"].includes(outcome), "Choose a valid decision.");
            if (outcome === "CLOSE") {
                requireValue(["APPROVED", "AWAITING_COMPLIANCE"].includes(app.status), "Only an approved case can close through this action.");
                requireValue(data.conditions.filter(c => c.applicationId === app.id).every(c => c.status === "CLOSED"), "All required conditions must be verified and closed.");
                transition(app, "CLOSED", "CLOSURE", reason);
                app.closure = { at: demoNow, authorityId: actor.id, reason, reopened: false };
            }
            else {
                requireValue(app.status === "DECISION_PENDING", "Case must reach the authorised decision stage first.");
                const requiresEvc = data.workflows.find(w => w.id === app.workflowId)?.stages.some(s => s.code === "EVC");
                requireValue(!requiresEvc || data.visits.some(v => v.applicationId === app.id && v.status === "COMPLETED" && data.meetingRecords.some(r => r.visitId === v.id && r.type === "EVC_REPORT" && r.versions.some(ver => ver.number === r.currentVersion && ver.status === "APPROVED"))), "An approved EVC report is required for this route.");
                transition(app, outcome === "APPROVE" ? "APPROVED" : "REJECTED", "DECISION", reason);
                if (outcome === "REJECT")
                    app.closure = { at: demoNow, authorityId: actor.id, reason, reopened: false };
            }
            data.decisions.push({ id: uid("decision"), applicationId: app.id, type: outcome as "APPROVE" | "REJECT" | "CLOSE", status: "APPROVED", authorityId: actor.id, reason, at: demoNow });
            notify(app.institutionId, "DECISION_RECORDED", "APPLICATION", app.id);
            break;
        }
        case "document.save": {
            const institutionId = text("institutionId");
            institutional(institutionId);
            const type = text("type");
            requireValue(["LEASE", "REGISTRATION", "SAFETY_CERTIFICATE"].includes(type), "Choose a configured sample document type.");
            const supportsExpiry = type !== "REGISTRATION";
            const expiryDate = supportsExpiry ? date("expiryDate") : null;
            const issuedAt = date("issuedAt");
            requireValue(!expiryDate || Date.parse(expiryDate) > Date.parse(issuedAt), "Expiry must follow the issue date.");
            const appId = text("applicationId", false);
            if (appId)
                requireValue(scoped.applications.some(a => a.id === appId && a.institutionId === institutionId), "Application must belong to this institution.");
            const document = id ? docById() : null;
            if (document)
                requireValue(document.type === type, "A new version must retain its document type.");
            const sizeBytes = number("sizeBytes");
            const mimeType = text("mimeType");
            requireValue(sizeBytes > 0 && sizeBytes <= 10 * 1024 * 1024 && ["application/pdf", "image/png", "image/jpeg"].includes(mimeType), "Choose a PDF, PNG or JPEG within the sample 10 MB limit.");
            const versionId = text("versionId");
            const newVersion = { id: versionId, number: (document?.versions.length ?? 0) + 1, fileName: text("fileName"), mimeType, sizeBytes, issuedAt, expiryDate, uploadedAt: demoNow, uploadedBy: actor.id, verification: "PENDING" as const, scan: "CLEAN" as const, previewText: "User-selected local file. Local type/size validation complete; malware scanning and issuer verification are not performed by this prototype." };
            if (document) {
                document.versions.push(newVersion);
                document.currentVersionId = versionId;
            }
            else {
                id = uid("doc");
                data.documents.push({ id, institutionId, applicationId: appId || null, campusId: null, type, issuer: text("issuer"), reference: text("reference"), supportsExpiry, currentVersionId: versionId, versions: [newVersion] });
            }
            message = "Local file registered. Verification is still pending.";
            break;
        }
        case "document.check": {
            permit("SCRUTINY", "COMPLIANCE", "REGIONAL", "INSTITUTION");
            const doc = docById();
            const versionId = text("versionId");
            const v = doc.versions.find(v => v.id === versionId);
            requireValue(v, "Version unavailable.");
            const declared = v!.expiryDate ?? "Not applicable";
            const extracted = text("extracted");
            const checkId = uid("check");
            data.documentChecks.push({ id: checkId, documentId: doc.id, versionId, engine: "Explicit local OCR simulation", processedAt: demoNow, status: "COMPLETED", fields: [{ name: "expiry_date", declared, extracted, confidence: .62 }], findings: [{ code: declared === extracted ? "MATCH" : "DATE_MISMATCH", severity: "REVIEW", description: "Simulated extraction supplied for human review; no OCR engine was contacted.", review: "PENDING" }] });
            id = checkId;
            break;
        }
        case "document.review": {
            permit("SCRUTINY", "COMPLIANCE", "REGIONAL");
            const check = data.documentChecks.find(c => c.id === id);
            requireValue(check && scoped.documentChecks.some(c => c.id === id), "Check unavailable.");
            requireValue(check!.status === "COMPLETED" && check!.fields.length > 0, "Complete a check or create a local manual extraction simulation before recording the assessment.");
            text("reason");
            const result = text("result");
            requireValue(["ACCEPTED", "CORRECTION_REQUIRED"].includes(result), "Choose a review outcome.");
            check!.findings.forEach(f => { f.review = result as "ACCEPTED" | "CORRECTION_REQUIRED"; });
            const doc = docById(check!.documentId);
            const v = doc.versions.find(v => v.id === check!.versionId)!;
            v.verification = result === "ACCEPTED" ? "VERIFIED" : "REJECTED";
            break;
        }
        case "renewal.submit": {
            const renewal = data.renewals.find(r => r.id === id);
            requireValue(renewal && scoped.renewals.some(r => r.id === id), "Renewal unavailable.");
            const doc = docById(renewal!.documentId);
            institutional(doc.institutionId);
            const versionId = text("versionId");
            requireValue(versionId !== renewal!.previousVersionId && doc.versions.some(v => v.id === versionId && v.scan === "CLEAN" && v.number > (doc.versions.find(old=>old.id===renewal!.previousVersionId)?.number??0)), "Choose a newer locally validated version.");
            renewal!.submittedVersionId = versionId;
            renewal!.status = "SUBMITTED";
            break;
        }
        case "renewal.verify": {
            permit("COMPLIANCE");
            const renewal = data.renewals.find(r => r.id === id);
            requireValue(renewal && scoped.renewals.some(r => r.id === id) && renewal.submittedVersionId && ["SUBMITTED", "UNDER_REVIEW"].includes(renewal.status), "A submitted renewal is required.");
            text("reason");
            const doc = docById(renewal!.documentId);
            doc.versions.find(v => v.id === renewal!.submittedVersionId)!.verification = "VERIFIED";
            doc.currentVersionId = renewal!.submittedVersionId!;
            renewal!.status = "VERIFIED";
            notify(doc.institutionId,"RENEWAL_VERIFIED","DOCUMENT",doc.id);
            break;
        }
        case "committee.save": {
            permit("REGIONAL");
            const visit = visitById();
            version(visit);
            requireValue(!["COMPLETED", "CANCELLED"].includes(visit.status), "Historical visits cannot change membership.");
            const expertIds = list("expertIds");
            requireValue(expertIds.length === visit.requiredMemberCount && new Set(expertIds).size === expertIds.length, `Choose exactly ${visit.requiredMemberCount} distinct experts.`);
            requireValue(expertIds.every(id => data.experts.some(e => e.id === id && e.eligibility === "ELIGIBLE")), "All experts must be eligible.");
            const reason = text("reason");
            const coiOverrideReason = text("coiOverrideReason", false) || null;
            visit.committee = expertIds.map(expertId => ({ expertId, role: "MEMBER", selectedBy: actor.id, selectedAt: demoNow }));
            for (const expertId of expertIds) {
                const expert = data.experts.find(e => e.id === expertId)!;
                const member = data.users.find(u => u.id === expert.userId)!;
                if (!member.assignments.some(a => a.role === "EVC_EXPERT" && a.scope.id === visit.id))
                    member.assignments.push({ role: "EVC_EXPERT", scope: { type: "EVC", id: visit.id }, validUntil: visit.requiredBy });
            }
            visit.confirmedSlotId = null;
            visit.status = "AWAITING_AVAILABILITY";
            visit.version++;
            visit.events.push({ at: demoNow, type: "COMMITTEE_SELECTED", actorId: actor.id, reason, ...(coiOverrideReason ? { details: { coi_override: true, coi_override_reason: coiOverrideReason } } : {}) });
            break;
        }
        case "availability.save": {
            const participantId = text("participantId");
            const type = text("participantType");
            if (type === "EXPERT") {
                permit("EVC_EXPERT");
                requireValue(data.experts.some(e => e.id === participantId && e.userId === actor.id), "You can record only your own availability.");
            }
            else {
                requireValue(type === "INSTITUTION", "Participant type unavailable.");
                institutional(participantId);
            }
            const startAt = date("startAt", true);
            const endAt = date("endAt", true);
            requireValue(Date.parse(endAt) > Date.parse(startAt), "End must follow start.");
            const state = text("state");
            requireValue(["AVAILABLE", "BUSY"].includes(state), "Choose availability or busy.");
            const previous = id ? data.availability.find(a => a.id === id && a.participantId === participantId && a.participantType === type && !a.supersededAt) : null;
            if (id)
                requireValue(previous, "Only an active interval for this participant can be corrected.");
            if (previous)
                previous.supersededAt = demoNow;
            id = uid("availability");
            data.availability.push({ id, supersedesId: previous?.id, participantType: type as "EXPERT" | "INSTITUTION", participantId, startAt, endAt, state: state as "AVAILABLE" | "BUSY", source: "MANUAL", confirmedAt: demoNow });
            break;
        }
        case "visit.recommend": {
            permit("REGIONAL", "EVC_COORDINATOR");
            const visit = visitById();
            version(visit);
            requireValue(!["CONFIRMED", "COMPLETED", "CANCELLED"].includes(visit.status), "Reopen scheduling before requesting new candidates.");
            const result = recommendVisit(data, id);
            data.slots = data.slots.filter(s => s.visitId !== id);
            result.candidates.forEach((candidate, i) => data.slots.push({ id: uid("slot"), visitId: id, ...candidate, rank: i + 1, feasible: !candidate.blockers.length, explanation: [`All ${visit.committee.length} officer-selected experts and the institution checked`, "Duration, preparation, known conflicts and deadline checked", `Availability confirmed within the visit policy freshness window (${visit.policy?.freshnessHours ?? 24} hours)`], participantIds: result.participants, snapshotAt: demoNow, expiresAt: new Date(Date.parse(demoNow) + 15 * 60000).toISOString() }));
            visit.status = result.candidates.some(c => !c.blockers.length) ? "PROPOSED" : "AWAITING_AVAILABILITY";
            visit.version++;
            if (result.blockers.length) {
                message = result.blockers.join(" ");
                if (!data.escalations.some(e => e.entityId === visit.id && e.status === "OPEN"))
                    data.escalations.push({ id: uid("escalation"), entityType: "EVC", entityId: visit.id, ruleId: "rule-escalation-001", dueAt: visit.requiredBy, triggeredAt: demoNow, ownerId: actor.id, level: 1, status: "OPEN", reason: message, resolution: null });
            }
            break;
        }
        case "visit.confirm": {
            permit("REGIONAL", "EVC_COORDINATOR");
            const visit = visitById();
            version(visit);
            requireValue(visit.status === "PROPOSED", "Visit is not awaiting confirmation.");
            const slot = data.slots.find(s => s.id === text("slotId") && s.visitId === id);
            requireValue(slot && slot.feasible && Date.parse(slot.expiresAt) >= Date.parse(demoNow), "Recommendation expired or is unavailable.");
            const current = recommendVisit(data, id);
            requireValue(current.candidates.some(c => c.startAt === slot!.startAt && !c.blockers.length) && current.participants.length === slot!.participantIds.length && current.participants.every(p => slot!.participantIds.includes(p)), "Availability or membership changed. Generate fresh recommendations.");
            visit.confirmedSlotId = slot!.id;
            visit.status = "CONFIRMED";
            visit.version++;
            data.tasks.filter(t => t.href === `/portal/evc/${visit.id}/schedule`).forEach(t => t.status = "COMPLETED");
            visit.events.push({ at: demoNow, type: "CONFIRMED", actorId: actor.id, reason: text("reason") });
            const institutionId=data.applications.find(a=>a.id===visit.applicationId)!.institutionId;
            const representatives=data.users.filter(u=>u.status==="ACTIVE"&&u.assignments.some(a=>a.role==="INSTITUTION"&&a.scope.id===institutionId));
            representatives.forEach(u=>data.invitations.push({id:uid("invitation"),visitId:id,recipientId:u.id,response:"PENDING",delivery:"QUEUED",calendarStatus:"PENDING"}));
            notify(institutionId,"EVC_CONFIRMED","EVC",id);
            visit.committee.forEach(m => { const recipientId = data.experts.find(e => e.id === m.expertId)!.userId; data.invitations.push({ id: uid("invitation"), visitId: id, recipientId, response: "PENDING", delivery: "QUEUED", calendarStatus: "PENDING" }); });
            break;
        }
        case "visit.postpone":
        case "visit.cancel":
        case "visit.complete": {
            permit("REGIONAL", "EVC_COORDINATOR");
            const visit = visitById();
            version(visit);
            const reason = text("reason");
            requireValue(!["CANCELLED", "COMPLETED"].includes(visit.status), "Historical visit is immutable.");
            if (command.kind === "visit.complete")
                requireValue(visit.status === "CONFIRMED", "Confirm the visit before completion.");
            visit.status = command.kind === "visit.complete" ? "COMPLETED" : command.kind === "visit.cancel" ? "CANCELLED" : "POSTPONED";
            if (visit.status !== "COMPLETED")
                visit.confirmedSlotId = null;
            visit.version++;
            visit.events.push({ at: demoNow, type: visit.status, actorId: actor.id, reason });
            if (visit.status === "COMPLETED") {
                const app = appById(visit.applicationId);
                transition(app, "AWAITING_COMMITTEE_ACTION", "EVC_REPORT", "Visit completion recorded in the local demonstration");
            }
            break;
        }
        case "invitation.respond": {
            permit("EVC_EXPERT", "INSTITUTION");
            const invitation = data.invitations.find(i => i.id === id && i.recipientId === actor.id && scoped.visits.some(v => v.id === i.visitId));
            requireValue(invitation, "Invitation unavailable.");
            const response = text("response");
            requireValue(["ACCEPTED", "DECLINED"].includes(response), "Choose accept or decline.");
            invitation!.response = response as "ACCEPTED" | "DECLINED";
            break;
        }
        case "observation.save": {
            permit("EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL");
            const visitId = text("visitId");
            visitById(visitId);
            const content = text("text");
            const criterion = text("criterion");
            const observation = id ? data.observations.find(o => o.id === id && o.authorId === actor.id && o.status === "DRAFT") : null;
            if (id)
                requireValue(observation, "Only your own draft can be edited.");
            if (observation)
                Object.assign(observation, { text: content, criterion, status: input.submit ? "SUBMITTED" : "DRAFT" });
            else {
                id = uid("observation");
                data.observations.push({ id, visitId, criterion, text: content, authorId: actor.id, sourceType: "STRUCTURED_FORM", status: input.submit ? "SUBMITTED" : "DRAFT" });
            }
            break;
        }
        case "record.generate": {
            permit("EVC_COORDINATOR", "REGIONAL");
            const visit = visitById();
            requireValue(visit.status === "COMPLETED", "Complete the visit before generating records.");
            const selectedSources = list("observationIds");
            const sources = data.observations.filter(o => o.visitId === id && o.status === "SUBMITTED" && (!selectedSources.length || selectedSources.includes(o.id)));
            requireValue(sources.length, "Submit authorised observations first.");
            const visitId = id;
            const template = data.configurations.filter(c => c.category === "TEMPLATE" && c.status === "PUBLISHED").at(-1);
            const titles = Array.isArray(template?.values.sections) ? template!.values.sections as string[] : [...new Set(sources.map(o => o.criterion))];
            id = uid("record");
            const type = text("type");
            requireValue(["MINUTES", "EVC_REPORT"].includes(type), "Choose minutes or EVC report.");
            data.meetingRecords.push({ id, visitId, type: type as "MINUTES" | "EVC_REPORT", templateVersion: data.configurations.filter(c => c.category === "TEMPLATE" && c.status === "PUBLISHED").at(-1)?.id ?? "DEMO-TEMPLATE-v1", currentVersion: 1, versions: [{ number: 1, status: "DRAFT", sections: titles.map(title => { const matching = sources.filter(o => o.criterion.toLowerCase() === title.toLowerCase()); return { title, text: matching.map(o => o.text).join("\n"), sourceIds: matching.map(o => o.id), warning: matching.length ? null : "Missing authorised source for this template section. Review and supply referenced content." }; }), approvedBy: null, approvedAt: null, correctionReason: null }] });
            break;
        }
        case "record.save":
        case "record.review":
        case "record.approve":
        case "record.changes": {
            permit("EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL");
            const record = data.meetingRecords.find(r => r.id === id && scoped.meetingRecords.some(s => s.id === id));
            requireValue(record, "Record unavailable.");
            const current = record!.versions.find(v => v.number === record!.currentVersion)!;
            requireValue(command.expectedVersion === undefined || command.expectedVersion === record!.currentVersion, "Record version changed; reload and reconcile.");
            if (command.kind === "record.save") {
                const sections = input.sections as typeof current.sections;
                requireValue(Array.isArray(sections) && sections.length && sections.every(s => s.title.trim() && s.text.trim() && s.sourceIds.length && s.sourceIds.every(id => data.observations.some(o => o.id === id && o.visitId === record!.visitId && o.status === "SUBMITTED"))), "Each section needs text and valid source references.");
                if (current.status === "APPROVED") {
                    const correctionReason = text("reason");
                    const next = { ...structuredClone(current), number: current.number + 1, status: "DRAFT" as const, sections, approvedBy: null, approvedAt: null, correctionReason };
                    record!.versions.push(next);
                    record!.currentVersion = next.number;
                }
                else {
                    requireValue(current.status !== "IN_REVIEW", "Request changes before editing a record in review.");
                    current.sections = sections;
                }
            }
            else if (command.kind === "record.review") {
                requireValue(["DRAFT", "CHANGES_REQUESTED"].includes(current.status) && current.sections.every(s => s.text.trim()), "Complete the draft before review.");
                current.status = "IN_REVIEW";
            }
            else if (command.kind === "record.changes") {
                requireValue(current.status === "IN_REVIEW", "Record is not in review.");
                current.correctionReason = text("reason");
                current.status = "CHANGES_REQUESTED";
            }
            else {
                permit("REGIONAL", "EVC_EXPERT");
                requireValue(current.status === "IN_REVIEW" && current.sections.every(s => s.text.trim() && s.sourceIds.length && !s.warning), "Review requires complete source-linked sections without unresolved warnings.");
                current.status = "APPROVED";
                current.approvedBy = actor.id;
                current.approvedAt = demoNow;
                const visit = visitById(record!.visitId);
                if (record!.type === "EVC_REPORT") {
                    const app = appById(visit.applicationId);
                    transition(app, "DECISION_PENDING", "DECISION", "Committee-approved report available");
                }
            }
            break;
        }
        case "condition.create": {
            permit("REGIONAL");
            const app = appById();
            requireValue(app.status === "APPROVED" || app.status === "AWAITING_COMPLIANCE", "An approved decision is required.");
            const decision = data.decisions.find(d => d.applicationId === app.id && d.type === "APPROVE" && d.status === "APPROVED");
            requireValue(decision, "Approved source decision unavailable.");
            const description = text("description");
            const requirements = text("requirements").split("\n").map(s => s.trim()).filter(Boolean);
            id = uid("condition");
            data.conditions.push({ id, applicationId: app.id, institutionId: app.institutionId, sourceDecisionId: decision!.id, code: `DEMO-COND-${data.conditions.length + 1}`, description, evidenceRequired: requirements, dueAt: date("dueAt", true), status: "OPEN", reviewerId: "user-compliance", closureReason: null });
            transition(app, "AWAITING_COMPLIANCE", "COMPLIANCE", "Approval condition created");
            notify(app.institutionId, "CONDITION_CREATED", "CONDITION", id);
            break;
        }
        case "evidence.submit": {
            const condition = conditionById();
            institutional(condition.institutionId);
            requireValue(condition.status !== "CLOSED", "Closed conditions cannot accept evidence.");
            const ids = selectedVersions(condition.institutionId);
            const evidenceId = uid("evidence");
            data.evidence.push({ id: evidenceId, conditionId: id, submissionNumber: data.evidence.filter(e => e.conditionId === id).length + 1, submittedAt: demoNow, submittedBy: actor.id, documentVersionIds: ids, responseToVerificationId: data.verifications.find(v => data.evidence.some(e => e.id === v.evidenceId && e.conditionId === id) && v.result === "CLARIFICATION_REQUIRED")?.id ?? null });
            condition.status = "EVIDENCE_SUBMITTED";
            task(condition.applicationId, condition.reviewerId, "Review submitted compliance evidence", condition.dueAt, `/portal/compliance/${condition.id}`);
            break;
        }
        case "evidence.verify": {
            permit("COMPLIANCE");
            const condition = conditionById();
            const evidence = data.evidence.filter(e => e.conditionId === id).sort((a, b) => b.submissionNumber - a.submissionNumber)[0];
            requireValue(evidence && ["EVIDENCE_SUBMITTED", "UNDER_REVIEW"].includes(condition.status), "New evidence must be submitted first.");
            const result = text("result");
            requireValue(["COMPLIANT", "NON_COMPLIANT", "CLARIFICATION_REQUIRED"].includes(result), "Choose a verification result.");
            data.verifications.push({ id: uid("verification"), evidenceId: evidence.id, reviewerId: actor.id, result: result as "COMPLIANT" | "NON_COMPLIANT" | "CLARIFICATION_REQUIRED", comments: text("reason"), at: demoNow });
            notify(condition.institutionId,`EVIDENCE_${result}`,"CONDITION",condition.id);
            condition.status = result === "COMPLIANT" ? "VERIFIED_COMPLIANT" : result === "NON_COMPLIANT" ? "VERIFIED_NON_COMPLIANT" : "CLARIFICATION_REQUIRED";
            break;
        }
        case "condition.close":
        case "condition.reopen": {
            permit("COMPLIANCE", "REGIONAL");
            const condition = conditionById();
            const reason = text("reason");
            if (command.kind === "condition.close")
                requireValue(condition.status === "VERIFIED_COMPLIANT", "Verified compliant evidence is required before closure.");
            else
                requireValue(condition.status === "CLOSED", "Only a closed condition can be reopened.");
            condition.status = command.kind === "condition.close" ? "CLOSED" : "REOPENED";
            condition.closureReason = reason;
            notify(condition.institutionId,command.kind==="condition.close"?"CONDITION_CLOSED":"CONDITION_REOPENED","CONDITION",condition.id);
            if (command.kind === "condition.close")
                data.tasks.filter(t => t.href === `/portal/compliance/${condition.id}`).forEach(t => t.status = "COMPLETED");
            break;
        }
        case "notification.read": {
            const n = data.notifications.find(n => n.id === id && n.recipientId === actor.id);
            requireValue(n, "Notification unavailable.");
            n!.read = !!input.read;
            break;
        }
        case "notification.retry": {
            permit("SYSTEM", "CENTRAL");
            const n = data.notifications.find(n => n.id === id);
            requireValue(n && ["FAILED", "RETRY_PENDING"].includes(n.status), "Only retryable failures can be queued.");
            n!.status = "QUEUED";
            n!.attempts.push({ number: n!.attempts.length + 1, at: demoNow, result: "QUEUED", failureReason: null });
            data.jobs.push({ id: uid("job"), type: "NOTIFICATION_DELIVERY", entityId: id, integrationId: "integration-email", status: "QUEUED", attempts: 0, lastError: null, nextAttemptAt: null });
            break;
        }
        case "escalation.resolve": {
            permit("REGIONAL", "CENTRAL", "SYSTEM");
            const escalation = data.escalations.find(e => e.id === id && scoped.escalations.some(s => s.id === id));
            requireValue(escalation, "Escalation unavailable.");
            const condition = data.conditions.find(c => c.id === escalation!.entityId);
            const visit = data.visits.find(v => v.id === escalation!.entityId);
            requireValue(condition?.status === "CLOSED" || (visit && ["CONFIRMED", "COMPLETED", "CANCELLED"].includes(visit.status)), "Resolve the underlying condition or scheduling issue first.");
            escalation!.resolution = text("reason");
            escalation!.status = "RESOLVED";
            break;
        }
        case "workflow.save": {
            permit("POLICY", "CENTRAL");
            const source = id ? data.workflows.find(w => w.id === id) : null;
            requireValue(!id || source, "Workflow unavailable.");
            const stages = input.stages as PortalCollections["workflows"][number]["stages"];
            const transitions = input.transitions as PortalCollections["workflows"][number]["transitions"];
            requireValue(Array.isArray(stages) && Array.isArray(transitions), "Stages and transitions are required.");
            const draft = { id: source?.status === "DRAFT" ? source.id : uid("workflow"), name: text("name"), version: source?.status === "DRAFT" ? source.version : String(Number.parseFloat(source?.version ?? "0") + 1), aphVersion: text("aphVersion"), status: "DRAFT" as const, effectiveFrom: null, stages, transitions };
            id = draft.id;
            const position = data.workflows.findIndex(w => w.id === id);
            if (position >= 0)
                data.workflows[position] = draft;
            else
                data.workflows.push(draft);
            break;
        }
        case "workflow.publish": {
            permit("POLICY", "CENTRAL");
            const workflow = data.workflows.find(w => w.id === id);
            requireValue(workflow && workflow.status === "DRAFT", "Only a draft can be published.");
            const errors = workflowErrors(workflow!);
            requireValue(!errors.length, errors.join(" "));
            text("reason");
            workflow!.effectiveFrom = date("effectiveFrom");
            workflow!.status = "PUBLISHED";
            break;
        }
        case "config.save": {
            permit("POLICY", "CENTRAL");
            const source = data.configurations.find(c => c.id === id);
            const values = input.values as Configuration["values"];
            requireValue(values && typeof values === "object" && !Array.isArray(values) && Object.values(values).every(v => (typeof v === "string" || typeof v === "boolean" || (typeof v === "number" && Number.isFinite(v))) || (Array.isArray(v) && v.every(x => typeof x === "string" || (typeof x === "number" && Number.isFinite(x))))), "Use typed primitive values or lists.");
            const category = source?.category ?? text("category");
            requireValue(["APH", "DOCUMENT_TYPE", "DOCUMENT_REQUIREMENT", "COMMITTEE", "TEMPLATE", "RETENTION", "NOTIFICATION", "ESCALATION", "SETTINGS"].includes(category), "Unknown configuration category.");
            if (category === "ESCALATION")
                requireValue(Number(values.thresholdMinutes) > 0 && Number(values.maxLevel) > 0, "Positive threshold and maximum level are required.");
            if (category === "NOTIFICATION")
                requireValue(values.event && values.channel && values.recipientRole, "Event, channel and recipient role are required.");
            if (category === "COMMITTEE")
                requireValue([4, 5].includes(Number(values.memberCount)) && Number(values.durationMinutes) > 0 && Number(values.availabilityFreshnessHours) > 0 && Number(values.preparationLeadHours) >= 0, "Sample committee size must be four or five, with valid positive duration/freshness and nonnegative preparation hours.");
            id = source?.status === "DRAFT" ? source.id : uid("config");
            const next: Configuration = { id, category: category as Configuration["category"], name: text("name"), version: source ? source.version + Number(source.status !== "DRAFT") : 1, status: "DRAFT", values };
            const position = data.configurations.findIndex(c => c.id === id);
            if (position >= 0)
                data.configurations[position] = next;
            else
                data.configurations.push(next);
            break;
        }
        case "config.publish": {
            permit("POLICY", "CENTRAL");
            const config = data.configurations.find(c => c.id === id && c.status === "DRAFT");
            requireValue(config, "Only draft configuration can be published.");
            text("reason");
            config!.status = "PUBLISHED";
            break;
        }
        case "user.assignment": {
            permit("SYSTEM");
            requireValue(assignment.scope.type === "GLOBAL", "Global identity administration is required.");
            const user = data.users.find(u => u.id === id);
            requireValue(user, "User unavailable.");
            const action = text("action");
            text("reason");
            if (action === "revoke") {
                const position = number("assignmentIndex");
                requireValue(user!.id !== actor.id && user!.assignments[position], "You cannot revoke your current identity or an absent assignment.");
                user!.assignments.splice(position, 1);
            }
            else {
                const nextRole = text("role") as Role;
                requireValue(["INSTITUTION", "SCRUTINY", "REGIONAL", "EVC_COORDINATOR", "EVC_EXPERT", "COMPLIANCE", "CENTRAL", "POLICY", "AUDITOR", "SYSTEM"].includes(nextRole), "Choose a valid role.");
                const scopeType = text("scopeType");
                const scopeId = text("scopeId");
                requireValue(["GLOBAL", "INSTITUTION", "REGION", "EVC", "APPLICATION"].includes(scopeType) && ((scopeType === "GLOBAL" && scopeId === "all") || (scopeType === "INSTITUTION" && data.institutions.some(i => i.id === scopeId)) || (scopeType === "REGION" && data.regions.some(r => r.id === scopeId)) || (scopeType === "EVC" && data.visits.some(v => v.id === scopeId)) || (scopeType === "APPLICATION" && data.applications.some(a => a.id === scopeId))), "Choose an existing scope.");
                user!.assignments.push({ role: nextRole, scope: { type: scopeType as "GLOBAL" | "INSTITUTION" | "REGION" | "EVC" | "APPLICATION", id: scopeId }, validUntil: text("validUntil", false) || null });
            }
            break;
        }
        case "user.status": {
            permit("SYSTEM");
            const user = data.users.find(u => u.id === id);
            requireValue(user && user.id !== actor.id, "You cannot disable your own demo identity.");
            text("reason");
            user!.status = user!.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
            break;
        }
        case "integration.test":
        case "integration.disable": {
            permit("SYSTEM");
            const integration = data.integrations.find(i => i.id === id);
            requireValue(integration, "Integration unavailable.");
            integration!.status = command.kind === "integration.disable" ? "DISABLED" : "MOCK";
            integration!.lastSyncAt = command.kind === "integration.test" ? demoNow : integration!.lastSyncAt;
            integration!.error = command.kind === "integration.test" ? "Local simulation only. No external connection was made." : "Disabled in the demonstration.";
            message = "Local integration simulation updated; no external service contacted.";
            break;
        }
        case "job.retry":
        case "job.process": {
            permit("SYSTEM");
            const job = data.jobs.find(j => j.id === id);
            requireValue(job, "Job unavailable.");
            requireValue(["FAILED", "RETRY_PENDING", "QUEUED"].includes(job!.status), "Job is not retryable or pending.");
            job!.attempts++;
            job!.status = command.kind === "job.retry" ? "QUEUED" : "COMPLETED";
            if (command.kind === "job.process") {
                job!.lastError = null;
                const n = data.notifications.find(n => n.id === job!.entityId);
                if (n) {
                    n.status = "SENT";
                    n.attempts.push({ number: n.attempts.length + 1, at: demoNow, result: "SENT", failureReason: "Local delivery simulation; no external message sent." });
                }
            }
            break;
        }
        case "report.create": {
            const code = text("reportCode") as ReportCode;
            requireValue(scoped.reportDefinitions.some(r => r.id === code), "Report category is not permitted.");
            const from = date("dateFrom");
            const to = date("dateTo");
            requireValue(Date.parse(to) >= Date.parse(from), "End date must follow start date.");
            id = uid("run");
            data.reportRuns.unshift({ id, reportCode: code, requestedBy: actor.id, requestedRole:role, scope:structuredClone(assignment.scope), generatedAt: null, period: { from, to }, filters: { columnFilters: text("columnFilters", false), query: text("query", false), regionId: text("regionId", false), status: text("status", false) }, status: "QUEUED", snapshotAt: demoNow, rowCount: 0, format: "CSV", failureReason: null });
            break;
        }
        case "report.complete": {
            const run = data.reportRuns.find(r => r.id === id && r.requestedBy === actor.id);
            requireValue(run && scoped.reportRuns.some(r=>r.id===run.id) && scoped.reportDefinitions.some(d => d.id === run.reportCode), "Export unavailable.");
            requireValue(run!.status === "QUEUED" || run!.status === "FAILED", "Export is already complete.");
            const rows = input.rows as Record<string, string | number>[] | undefined;
            requireValue(!rows || (Array.isArray(rows) && rows.every(row => typeof row === "object" && Object.values(row).every(v => typeof v === "string" || typeof v === "number"))), "Invalid report rows.");
            run!.snapshotRows = rows ? structuredClone(rows) : undefined;
            run!.rowCount = rows?.length ?? number("rowCount");
            run!.status = input.failure ? "FAILED" : "COMPLETED";
            run!.failureReason = input.failure ? text("failure") : null;
            run!.generatedAt = demoNow;
            break;
        }
        default: return fail("Unsupported action.");
    }
    if (command.kind !== "notification.read")
        data.auditEvents.push({ id: uid("audit"), actorId: actor.id, action: command.kind.toUpperCase().replaceAll(".", "_"), entityType: command.kind.split(".")[0].toUpperCase(), entityId: id, at: demoNow, reason: typeof input.reason === "string" ? input.reason : message, correlationId: uid("correlation"), version: 1, previousHash: data.auditEvents.at(-1)?.eventHash ?? null, eventHash: `demo-event-${data.auditEvents.length + 1}-not-a-cryptographic-anchor`, anchor: "DISABLED" });
    return { data, id, message };
}
