/** DELETE THIS FILE when data-source.ts uses live services.
 * Fictional, deterministic frontend fixtures. No real files, credentials or integrations.
 * Read through data-source.ts; keep page-local mutations separate from these seeds.
 */
import type { Application, ApplicationStatus, PortalCollections, Role, ReportDefinition } from "./types";

export const mockMeta = {
  now: "2026-10-26T12:00:00+05:30",
  timezone: "Asia/Kolkata",
  defaultUserId: "user-institution",
  defaultInstitutionId: "inst-001",
  source: "Fictional frontend demonstration data",
  rules: "Illustrative rules and dates; not approved APH policy",
} as const;

const roleUsers: { id: string; name: string; role: Role }[] = [
  { id: "user-institution", name: "Ananya Rao", role: "INSTITUTION" },
  { id: "user-scrutiny", name: "Rohan Mehta", role: "SCRUTINY" },
  { id: "user-regional", name: "Meera Desai", role: "REGIONAL" },
  { id: "user-coordinator", name: "Kabir Shah", role: "EVC_COORDINATOR" },
  { id: "user-compliance", name: "Nisha Sen", role: "COMPLIANCE" },
  { id: "user-central", name: "Arjun Iyer", role: "CENTRAL" },
  { id: "user-policy", name: "Tara Menon", role: "POLICY" },
  { id: "user-auditor", name: "Dev Sethi", role: "AUDITOR" },
  { id: "user-system", name: "Isha Kapoor", role: "SYSTEM" },
];
const experts = ["Aditi Sharma", "Vikram Rao", "Farah Khan", "Sanjay Nair", "Leena Das"];
const expertIds = experts.map((_, i) => `expert-00${i + 1}`);
const statuses: ApplicationStatus[] = [
  "RETURNED_FOR_DEFICIENCY", "AWAITING_EVC", "AWAITING_COMMITTEE_ACTION", "AWAITING_COMPLIANCE",
  "DRAFT", "CLOSED", "IN_REVIEW", "SUBMITTED", "RESUBMITTED", "DECISION_PENDING", "APPROVED", "REJECTED", "WITHDRAWN",
];
const institutionIds = ["inst-001", "inst-001", "inst-002", "inst-001", "inst-001", "inst-002", "inst-002", "inst-003", "inst-001", "inst-002", "inst-003", "inst-003", "inst-003"];
const stageFor: Record<ApplicationStatus, string> = {
  DRAFT: "INTAKE", SUBMITTED: "INTAKE", IN_REVIEW: "SCRUTINY", RETURNED_FOR_DEFICIENCY: "SCRUTINY",
  RESUBMITTED: "SCRUTINY", AWAITING_EVC: "EVC", AWAITING_COMMITTEE_ACTION: "EVC_REPORT",
  AWAITING_COMPLIANCE: "COMPLIANCE", DECISION_PENDING: "DECISION", APPROVED: "DECISION",
  REJECTED: "DECISION", WITHDRAWN: "CLOSURE", CLOSED: "CLOSURE",
};
const applications: Application[] = statuses.map((status, i) => {
  const draft = status === "DRAFT";
  const terminal = ["CLOSED", "REJECTED", "WITHDRAWN"].includes(status);
  const institutionId = institutionIds[i];
  return {
    id: `app-${String(i + 1).padStart(3, "0")}`, number: `${draft ? "DRAFT" : "DEMO"}-2027-${String(i + 1).padStart(4, "0")}`,
    institutionId, campusId: `campus-${institutionId.slice(-3)}`, type: "NEW_INSTITUTION", academicYear: "2027-28",
    status, workflowId: "workflow-evc-v1", currentStage: stageFor[status],
    stageEnteredAt: draft ? null : "2026-10-20T09:00:00+05:30", submittedAt: draft ? null : "2026-10-10T10:00:00+05:30",
    dueAt: draft || terminal ? null : i === 6 ? "2026-10-24T17:00:00+05:30" : "2026-11-18T17:00:00+05:30",
    ownerId: draft ? "user-institution" : "user-scrutiny", nextAction: terminal ? "View historical record" : `Continue ${stageFor[status].toLowerCase()} action`, version: 1,
    closure: terminal ? { at: "2026-10-23T15:00:00+05:30", authorityId: "user-regional", reason: `Sample ${status.toLowerCase()} outcome`, reopened: false } : null,
  };
});

const reportDefinitions: ReportDefinition[] = [
  { id: "region-performance", name: "Region-wise performance", columns: ["Region", "Received", "Completed", "Stage pendency", "Processing time", "Overdue", "EVC completion", "Compliance"], filters: ["Date range", "Region", "Application type", "Institution type"], roles: ["CENTRAL", "REGIONAL"] },
  { id: "application-pendency", name: "Application pendency", columns: ["Application", "Institution", "Stage", "Stage age", "Application age", "Deadline", "Overdue duration", "Owner", "Next action"], filters: ["Region", "Stage", "Age band", "Officer", "Status"], roles: ["REGIONAL", "SCRUTINY", "CENTRAL"] },
  { id: "evc-status", name: "EVC status", columns: ["Application", "Selected committee", "Proposed date", "Confirmed date", "Scheduling status", "Deadline", "Conflicts", "Visit status", "Report status"], filters: ["Region", "Coordinator", "Date range", "Status"], roles: ["REGIONAL", "EVC_COORDINATOR", "EVC_EXPERT"] },
  { id: "undertaking-compliance", name: "Undertaking compliance", columns: ["Condition", "Due date", "Evidence status", "Verification status", "Overdue days", "Reviewer", "Escalation"], filters: ["Region", "Condition type", "Status", "Due period"], roles: ["COMPLIANCE", "REGIONAL"] },
  { id: "document-validity", name: "Document validity", columns: ["Institution", "Document type", "Issue date", "Expiry date", "Version", "Verification status", "Renewal status"], filters: ["Document type", "Region", "Expiry window", "Status"], roles: ["COMPLIANCE", "REGIONAL"] },
  { id: "overdue-actions", name: "Overdue actions", columns: ["Entity type", "Case", "Action", "Owner", "Due date", "Overdue duration", "Escalation level", "Resolution"], filters: ["Region", "Role", "Action type", "Overdue range"], roles: ["REGIONAL", "CENTRAL"] },
  { id: "notification-delivery", name: "Notification delivery", columns: ["Event", "Recipient category", "Channel", "Delivery status", "Attempt count", "Failure reason", "Last attempt"], filters: ["Date range", "Channel", "Event type", "Delivery status"], roles: ["CENTRAL", "SYSTEM", "AUDITOR"] },
  { id: "case-closure", name: "Case closure", columns: ["Application", "Closure date", "Final status", "Closure authority", "Reason", "Duration", "Reopen status"], filters: ["Region", "Date range", "Application type", "Closure outcome"], roles: ["CENTRAL", "REGIONAL", "AUDITOR"] },
];

export const mockData: PortalCollections = {
  regions: [
    { id: "region-west", name: "West demonstration region", code: "DEMO-W" },
    { id: "region-south", name: "South demonstration region", code: "DEMO-S" },
  ],
  users: [
    ...roleUsers.map(u => ({
      id: u.id, displayName: u.name, email: `${u.id}@example.test`, status: "ACTIVE" as const,
      assignments: [{ role: u.role, scope: u.role === "INSTITUTION"
        ? { type: "INSTITUTION" as const, id: "inst-001" }
        : ["CENTRAL", "POLICY", "AUDITOR", "SYSTEM"].includes(u.role)
          ? { type: "GLOBAL" as const, id: "global" } : { type: "REGION" as const, id: "region-west" }, validUntil: null }],
    })),
    ...experts.map((name, i) => ({ id: `user-expert-00${i + 1}`, displayName: name, email: `expert${i + 1}@example.test`, status: "ACTIVE" as const,
      assignments: [{ role: "EVC_EXPERT" as const, scope: { type: "EVC" as const, id: "visit-001" }, validUntil: "2026-12-01" }, { role: "EVC_EXPERT" as const, scope: { type: "EVC" as const, id: "visit-002" }, validUntil: "2026-12-01" }] })),
  ],
  institutions: [
    { id: "inst-001", code: "DEMO-INST-001", name: "Sahyadri Demonstration Institute of Technology", type: "Technical institute", regionId: "region-west", status: "ACTIVE", campuses: [{ id: "campus-001", name: "Main campus", city: "Pune", primary: true }], attributes: [{ key: "lease_expiry", value: "2027-03-31", verification: "PENDING", sourceVersionId: "version-lease-1" }] },
    { id: "inst-002", code: "DEMO-INST-002", name: "Konkan Demonstration College of Engineering", type: "Engineering college", regionId: "region-west", status: "ACTIVE", campuses: [{ id: "campus-002", name: "Main campus", city: "Nashik", primary: true }], attributes: [] },
    { id: "inst-003", code: "DEMO-INST-003", name: "Deccan Demonstration Polytechnic", type: "Polytechnic", regionId: "region-south", status: "ACTIVE", campuses: [{ id: "campus-003", name: "Main campus", city: "Bengaluru", primary: true }], attributes: [] },
  ],
  applications,
  submissions: [
    { id: "submission-001", applicationId: "app-001", number: 1, submittedAt: "2026-10-10T10:00:00+05:30", submittedBy: "user-institution", noticeId: null, documentVersionIds: ["version-lease-1", "version-registration-1"] },
    { id: "submission-009-1", applicationId: "app-009", number: 1, submittedAt: "2026-10-10T10:00:00+05:30", submittedBy: "user-institution", noticeId: null, documentVersionIds: ["version-lease-1"] },
    { id: "submission-009-2", applicationId: "app-009", number: 2, submittedAt: "2026-10-24T11:00:00+05:30", submittedBy: "user-institution", noticeId: "notice-002", documentVersionIds: ["version-lease-2"] },
  ],
  workflows: [
    { id: "workflow-evc-v1", name: "Scrutiny and EVC sample route", version: "1.0", aphVersion: "DEMO-APH-v1", status: "PUBLISHED", effectiveFrom: "2026-10-01", stages: [
      { code: "INTAKE", name: "Intake", slaDays: 2, ownerRole: "SCRUTINY" },
      { code: "SCRUTINY", name: "Scrutiny", slaDays: 7, ownerRole: "SCRUTINY" },
      { code: "EVC", name: "Expert visit", slaDays: 14, ownerRole: "REGIONAL" },
      { code: "EVC_REPORT", name: "Committee record", slaDays: 5, ownerRole: "EVC_COORDINATOR" },
      { code: "DECISION", name: "Authorised decision", slaDays: 5, ownerRole: "REGIONAL" },
      { code: "COMPLIANCE", name: "Compliance", slaDays: 30, ownerRole: "COMPLIANCE" },
      { code: "CLOSURE", name: "Closure", slaDays: 2, ownerRole: "REGIONAL" },
    ], transitions: [
      { from: "INTAKE", to: "SCRUTINY", guards: ["Required metadata present"] },
      { from: "SCRUTINY", to: "EVC", guards: ["Deficiencies resolved", "EVC required by sample route"] },
      { from: "EVC", to: "EVC_REPORT", guards: ["Visit completed"] },
      { from: "EVC_REPORT", to: "DECISION", guards: ["Committee record approved"] },
      { from: "DECISION", to: "COMPLIANCE", guards: ["Approval with conditions recorded"] },
      { from: "COMPLIANCE", to: "CLOSURE", guards: ["Required evidence verified", "Closure authorised"] },
    ] },
    { id: "workflow-scrutiny-v1", name: "Only scrutiny sample route", version: "1.0", aphVersion: "DEMO-APH-v1", status: "PUBLISHED", effectiveFrom: "2026-10-01", stages: [
      { code: "SCRUTINY", name: "Scrutiny", slaDays: 7, ownerRole: "SCRUTINY" }, { code: "DECISION", name: "Decision", slaDays: 5, ownerRole: "REGIONAL" },
    ], transitions: [{ from: "SCRUTINY", to: "DECISION", guards: ["Review complete", "No EVC required"] }] },
    { id: "workflow-evc-v2", name: "Scrutiny and EVC sample route", version: "2.0", aphVersion: "DEMO-APH-v2", status: "DRAFT", effectiveFrom: null, stages: [], transitions: [] },
  ],
  stageEvents: [
    { id: "stage-001", applicationId: "app-001", at: "2026-10-10T10:00:00+05:30", actorId: "user-institution", from: "DRAFT", to: "SUBMITTED", reason: "Initial submission", workflowId: "workflow-evc-v1" },
    { id: "stage-002", applicationId: "app-001", at: "2026-10-20T09:00:00+05:30", actorId: "user-scrutiny", from: "IN_REVIEW", to: "RETURNED_FOR_DEFICIENCY", reason: "Lease date mismatch", workflowId: "workflow-evc-v1" },
  ],
  deficiencies: [
    { id: "notice-001", number: "DEMO-DEF-001", applicationId: "app-001", issuedBy: "user-scrutiny", issuedAt: "2026-10-20T09:00:00+05:30", responseDueAt: "2026-11-02T17:00:00+05:30", reason: "Lease validity requires clarification", status: "OPEN", items: [{ id: "item-001", criterion: "DEMO-LAND-01", description: "Confirm the lease expiry date and supply the corrected declaration.", documentId: "doc-lease", status: "OPEN", response: null, responseVersionId: null }] },
    { id: "notice-002", number: "DEMO-DEF-002", applicationId: "app-009", issuedBy: "user-scrutiny", issuedAt: "2026-10-21T09:00:00+05:30", responseDueAt: "2026-11-03T17:00:00+05:30", reason: "Correct lease declaration", status: "RESPONDED", items: [{ id: "item-002", criterion: "DEMO-LAND-01", description: "Upload corrected declaration", documentId: "doc-lease", status: "RESPONDED", response: "Corrected declaration provided", responseVersionId: "version-lease-2" }] },
  ],
  documents: [
    { id: "doc-lease", institutionId: "inst-001", applicationId: "app-001", campusId: "campus-001", type: "LEASE", issuer: "Demonstration property authority", reference: "DEMO-LEASE-01", supportsExpiry: true, currentVersionId: "version-lease-2", versions: [
      { id: "version-lease-1", number: 1, fileName: "sample-lease-v1.pdf", mimeType: "application/pdf", sizeBytes: 245000, issuedAt: "2024-04-01", expiryDate: "2027-03-31", uploadedAt: "2026-10-09T09:00:00+05:30", uploadedBy: "user-institution", verification: "PENDING", scan: "CLEAN", previewText: "Fictional lease: extracted validity ends 31 March 2026; declared expiry is 31 March 2027. Manual review required." },
      { id: "version-lease-2", number: 2, fileName: "sample-lease-v2.pdf", mimeType: "application/pdf", sizeBytes: 248000, issuedAt: "2026-10-23", expiryDate: "2027-03-31", uploadedAt: "2026-10-24T10:00:00+05:30", uploadedBy: "user-institution", verification: "PENDING", scan: "CLEAN", previewText: "Fictional corrected declaration: lease valid until 31 March 2027. Awaiting human review." },
    ] },
    { id: "doc-registration", institutionId: "inst-001", applicationId: null, campusId: null, type: "REGISTRATION", issuer: "Demonstration register", reference: "DEMO-REG-01", supportsExpiry: false, currentVersionId: "version-registration-1", versions: [
      { id: "version-registration-1", number: 1, fileName: "sample-registration.pdf", mimeType: "application/pdf", sizeBytes: 102000, issuedAt: "2020-01-01", expiryDate: null, uploadedAt: "2026-10-09T09:00:00+05:30", uploadedBy: "user-institution", verification: "VERIFIED", scan: "CLEAN", previewText: "Fictional registration. This sample document type has no expiry date." },
    ] },
    { id: "doc-safety", institutionId: "inst-001", applicationId: "app-004", campusId: "campus-001", type: "SAFETY_CERTIFICATE", issuer: "Demonstration safety office", reference: "DEMO-SAFE-01", supportsExpiry: true, currentVersionId: "version-safety-1", versions: [
      { id: "version-safety-1", number: 1, fileName: "sample-safety-v1.pdf", mimeType: "application/pdf", sizeBytes: 150000, issuedAt: "2025-11-05", expiryDate: "2026-11-05", uploadedAt: "2026-10-01T09:00:00+05:30", uploadedBy: "user-institution", verification: "VERIFIED", scan: "CLEAN", previewText: "Fictional certificate approaching expiry on 5 November 2026." },
      { id: "version-safety-2", number: 2, fileName: "sample-safety-v2.pdf", mimeType: "application/pdf", sizeBytes: 152000, issuedAt: "2026-10-24", expiryDate: "2027-11-05", uploadedAt: "2026-10-25T09:00:00+05:30", uploadedBy: "user-institution", verification: "PENDING", scan: "CLEAN", previewText: "Fictional renewal version. Submission alone does not complete renewal." },
    ] },
  ],
  documentChecks: [
    { id: "check-lease-1", documentId: "doc-lease", versionId: "version-lease-1", engine: "Mock OCR v1", processedAt: "2026-10-10T10:05:00+05:30", status: "COMPLETED", fields: [{ name: "expiry_date", declared: "2027-03-31", extracted: "2026-03-31", confidence: 0.62 }], findings: [{ code: "DATE_MISMATCH", severity: "REVIEW", description: "Declared and extracted lease dates differ", review: "CORRECTION_REQUIRED" }] },
    { id: "check-safety-2", documentId: "doc-safety", versionId: "version-safety-2", engine: "Mock OCR v1", processedAt: null, status: "QUEUED", fields: [], findings: [] },
  ],
  renewals: [{ id: "renewal-001", documentId: "doc-safety", previousVersionId: "version-safety-1", submittedVersionId: "version-safety-2", dueAt: "2026-11-05T17:00:00+05:30", status: "UNDER_REVIEW", assignedTo: "user-compliance" }],
  experts: expertIds.map((id, i) => ({ id, userId: `user-expert-00${i + 1}`, expertise: [i % 2 ? "Infrastructure" : "Technical education"], eligibility: "ELIGIBLE", availabilityMethod: i === 4 ? "MANUAL" : "CALENDAR" })),
  availability: [
    ...expertIds.map((id, i) => ({ id: `availability-00${i + 1}`, participantType: "EXPERT" as const, participantId: id, startAt: "2026-11-10T10:00:00+05:30", endAt: "2026-11-10T13:00:00+05:30", state: "AVAILABLE" as const, source: i === 4 ? "MANUAL" as const : "CALENDAR" as const, confirmedAt: "2026-10-26T11:30:00+05:30" })),
    { id: "availability-inst", participantType: "INSTITUTION", participantId: "inst-001", startAt: "2026-11-10T10:00:00+05:30", endAt: "2026-11-10T13:00:00+05:30", state: "AVAILABLE", source: "MANUAL", confirmedAt: "2026-10-26T11:35:00+05:30" },
    { id: "busy-001", participantType: "EXPERT", participantId: "expert-002", startAt: "2026-11-09T10:00:00+05:30", endAt: "2026-11-09T13:00:00+05:30", state: "BUSY", source: "CALENDAR", confirmedAt: "2026-10-26T11:30:00+05:30" },
  ],
  visits: [
    { id: "visit-001", applicationId: "app-002", campusId: "campus-001", status: "PROPOSED", requiredBy: "2026-11-18T17:00:00+05:30", durationMinutes: 180, requiredMemberCount: 5, coordinatorId: "user-coordinator", committee: expertIds.map(expertId => ({ expertId, role: "MEMBER", selectedBy: "user-regional", selectedAt: "2026-10-25T10:00:00+05:30" })), confirmedSlotId: null, version: 4, events: [{ at: "2026-10-25T10:00:00+05:30", type: "COMMITTEE_SELECTED", actorId: "user-regional", reason: "Five eligible experts selected by the officer" }] },
    { id: "visit-002", applicationId: "app-003", campusId: "campus-002", status: "COMPLETED", requiredBy: "2026-10-25T17:00:00+05:30", durationMinutes: 180, requiredMemberCount: 5, coordinatorId: "user-coordinator", committee: expertIds.map(expertId => ({ expertId, role: "MEMBER", selectedBy: "user-regional", selectedAt: "2026-10-15T10:00:00+05:30" })), confirmedSlotId: "slot-completed", version: 6, events: [{ at: "2026-10-22T13:00:00+05:30", type: "COMPLETED", actorId: "user-coordinator", reason: "Sample visit completed; report pending" }] },
  ],
  slots: [
    { id: "slot-001", visitId: "visit-001", startAt: "2026-11-10T10:00:00+05:30", endAt: "2026-11-10T13:00:00+05:30", rank: 1, feasible: true, explanation: ["All five selected experts are available", "Institution confirmed", "No known busy blocks", "Before the 18 November deadline"], participantIds: [...expertIds, "inst-001"], snapshotAt: mockMeta.now, expiresAt: "2026-10-26T12:15:00+05:30", blockers: [] },
    { id: "slot-blocked", visitId: "visit-001", startAt: "2026-11-09T10:00:00+05:30", endAt: "2026-11-09T13:00:00+05:30", rank: 0, feasible: false, explanation: ["Known conflict for selected expert; other participants have not confirmed this interval"], participantIds: [...expertIds, "inst-001"], snapshotAt: mockMeta.now, expiresAt: "2026-10-26T12:15:00+05:30", blockers: ["expert-002 busy", "Missing availability for remaining participants"] },
    { id: "slot-completed", visitId: "visit-002", startAt: "2026-10-22T10:00:00+05:30", endAt: "2026-10-22T13:00:00+05:30", rank: 1, feasible: true, explanation: ["Historical confirmed sample slot"], participantIds: [...expertIds, "inst-002"], snapshotAt: "2026-10-20T10:00:00+05:30", expiresAt: "2026-10-20T10:15:00+05:30", blockers: [] },
  ],
  invitations: expertIds.map((_, i) => ({ id: `invitation-00${i + 1}`, visitId: "visit-002", recipientId: `user-expert-00${i + 1}`, response: "ACCEPTED", delivery: i === 4 ? "SENT" : "DELIVERED", calendarStatus: i === 4 ? "PENDING" : "SYNCED" })),
  observations: [
    { id: "observation-001", visitId: "visit-002", criterion: "DEMO-LAB-01", text: "Sample lab inventory was inspected; supporting inventory list attached to the committee note.", authorId: "user-expert-001", sourceType: "STRUCTURED_FORM", status: "SUBMITTED" },
    { id: "observation-002", visitId: "visit-002", criterion: "DEMO-LAND-01", text: "Lease clarification remains unresolved in the sample notes.", authorId: "user-expert-002", sourceType: "COMMITTEE_NOTE", status: "SUBMITTED" },
  ],
  meetingRecords: [
    { id: "record-001", visitId: "visit-002", type: "EVC_REPORT", templateVersion: "DEMO-TEMPLATE-v1", currentVersion: 1, versions: [{ number: 1, status: "IN_REVIEW", sections: [
      { title: "Laboratory observations", text: "Laboratory inventory inspected per the submitted committee observation.", sourceIds: ["observation-001"], warning: null },
      { title: "Land and premises", text: "Clarification required before finalising this section.", sourceIds: ["observation-002"], warning: "Unresolved source input" },
      { title: "Staffing", text: "", sourceIds: [], warning: "No authorised observation supplied. Committee input required." },
    ], approvedBy: null, approvedAt: null, correctionReason: null }] },
    { id: "record-002", visitId: "visit-002", type: "MINUTES", templateVersion: "DEMO-MINUTES-v1", currentVersion: 1, versions: [{ number: 1, status: "APPROVED", sections: [{ title: "Discussion and follow-up", text: "Committee requested clarification of land records.", sourceIds: ["observation-002"], warning: null }], approvedBy: "user-regional", approvedAt: "2026-10-23T10:00:00+05:30", correctionReason: null }] },
  ],
  actionItems: [{ id: "action-001", visitId: "visit-002", observationId: "observation-002", description: "Obtain supporting lease clarification", responsibleRole: "REGIONAL", dueAt: "2026-10-28T17:00:00+05:30", status: "OPEN" }],
  decisions: [
    { id: "decision-001", applicationId: "app-004", type: "APPROVE", status: "APPROVED", authorityId: "user-regional", reason: "Sample conditional approval", at: "2026-10-01T10:00:00+05:30" },
    { id: "decision-002", applicationId: "app-010", type: "APPROVE", status: "DRAFT", authorityId: "user-regional", reason: "Pending authorised review", at: null },
  ],
  conditions: [
    { id: "condition-001", applicationId: "app-004", institutionId: "inst-001", sourceDecisionId: "decision-001", code: "DEMO-COND-01", description: "Provide renewed campus safety evidence", evidenceRequired: ["New safety certificate version", "Institution declaration"], dueAt: "2026-10-24T17:00:00+05:30", status: "CLARIFICATION_REQUIRED", reviewerId: "user-compliance", closureReason: null },
    { id: "condition-002", applicationId: "app-004", institutionId: "inst-001", sourceDecisionId: "decision-001", code: "DEMO-COND-02", description: "Confirm institutional registration", evidenceRequired: ["Registration document"], dueAt: "2026-10-30T17:00:00+05:30", status: "CLOSED", reviewerId: "user-compliance", closureReason: "Evidence accepted by authorised reviewer" },
  ],
  evidence: [
    { id: "evidence-001", conditionId: "condition-001", submissionNumber: 1, submittedAt: "2026-10-25T09:10:00+05:30", submittedBy: "user-institution", documentVersionIds: ["version-safety-2"], responseToVerificationId: null },
    { id: "evidence-002", conditionId: "condition-002", submissionNumber: 1, submittedAt: "2026-10-20T09:10:00+05:30", submittedBy: "user-institution", documentVersionIds: ["version-registration-1"], responseToVerificationId: null },
  ],
  verifications: [
    { id: "verification-001", evidenceId: "evidence-001", reviewerId: "user-compliance", result: "CLARIFICATION_REQUIRED", comments: "Provide the accompanying declaration; uploaded certificate alone is incomplete.", at: "2026-10-25T14:00:00+05:30" },
    { id: "verification-002", evidenceId: "evidence-002", reviewerId: "user-compliance", result: "COMPLIANT", comments: "Registration evidence accepted", at: "2026-10-21T14:00:00+05:30" },
  ],
  notifications: [
    { id: "notification-001", recipientId: "user-institution", event: "DEFICIENCY_ISSUED", channel: "IN_APP", status: "DELIVERED", entityType: "APPLICATION", entityId: "app-001", createdAt: "2026-10-20T09:01:00+05:30", read: false, attempts: [{ number: 1, at: "2026-10-20T09:01:00+05:30", result: "DELIVERED", failureReason: null }] },
    { id: "notification-002", recipientId: "user-institution", event: "CONDITION_OVERDUE", channel: "EMAIL", status: "RETRY_PENDING", entityType: "CONDITION", entityId: "condition-001", createdAt: "2026-10-25T09:00:00+05:30", read: false, attempts: [{ number: 1, at: "2026-10-25T09:00:00+05:30", result: "FAILED", failureReason: "Mock provider timeout" }, { number: 2, at: "2026-10-25T09:05:00+05:30", result: "FAILED", failureReason: "Mock provider unavailable" }] },
    { id: "notification-003", recipientId: "user-expert-005", event: "EVC_INVITATION", channel: "EMAIL", status: "SENT", entityType: "EVC", entityId: "visit-002", createdAt: "2026-10-20T10:01:00+05:30", read: true, attempts: [{ number: 1, at: "2026-10-20T10:01:00+05:30", result: "SENT", failureReason: null }] },
  ],
  escalations: [{ id: "escalation-001", entityType: "CONDITION", entityId: "condition-001", ruleId: "rule-escalation-001", dueAt: "2026-10-24T17:00:00+05:30", triggeredAt: "2026-10-25T09:00:00+05:30", ownerId: "user-regional", level: 1, status: "OPEN", reason: "Evidence remains unverified after the illustrative due date", resolution: null }],
  reportDefinitions,
  reportRuns: reportDefinitions.map((report, i) => ({ id: `run-00${i + 1}`, reportCode: report.id, requestedBy: "user-central", generatedAt: i === 6 ? null : mockMeta.now, period: { from: "2026-10-01", to: "2026-10-26" }, filters: {}, status: i === 6 ? "FAILED" : "COMPLETED", snapshotAt: mockMeta.now, rowCount: 0, format: "CSV", failureReason: i === 6 ? "Mock export worker timeout" : null })),
  auditEvents: [
    { id: "audit-001", actorId: "user-scrutiny", action: "DEFICIENCY_ISSUED", entityType: "APPLICATION", entityId: "app-001", at: "2026-10-20T09:00:00+05:30", reason: "Lease date mismatch", correlationId: "correlation-001", version: 1, previousHash: null, eventHash: "demo-hash-001-not-a-real-digest", anchor: "DISABLED" },
    { id: "audit-002", actorId: "user-regional", action: "COMMITTEE_SELECTED", entityType: "EVC", entityId: "visit-001", at: "2026-10-25T10:00:00+05:30", reason: "Five eligible experts selected", correlationId: "correlation-002", version: 4, previousHash: "demo-hash-001-not-a-real-digest", eventHash: "demo-hash-002-not-a-real-digest", anchor: "PENDING" },
  ],
  configurations: [
    { id: "aph-001", category: "APH", name: "Illustrative APH mapping", version: 1, status: "PUBLISHED", values: { code: "DEMO-APH-v1", source: "Sample only; policy owner confirmation required" } },
    { id: "document-type-lease", category: "DOCUMENT_TYPE", name: "Lease", version: 1, status: "PUBLISHED", values: { supportsExpiry: true, reminderDays: [30, 15, 7], maxSizeMb: 10, allowedMimeTypes: ["application/pdf"] } },
    { id: "document-type-registration", category: "DOCUMENT_TYPE", name: "Registration", version: 1, status: "PUBLISHED", values: { supportsExpiry: false } },
    { id: "document-requirement-001", category: "DOCUMENT_REQUIREMENT", name: "Sample new-institution requirements", version: 1, status: "DRAFT", values: { documentTypes: ["LEASE", "REGISTRATION"], applicationType: "NEW_INSTITUTION" } },
    { id: "committee-rule-001", category: "COMMITTEE", name: "Sample committee composition", version: 1, status: "PUBLISHED", values: { memberCount: 5, durationMinutes: 180, availabilityFreshnessHours: 24, preparationLeadHours: 48 } },
    { id: "template-001", category: "TEMPLATE", name: "Sample EVC report", version: 1, status: "PUBLISHED", values: { sections: ["Laboratories", "Land", "Staffing"], code: "DEMO-TEMPLATE-v1" } },
    { id: "rule-notification-001", category: "NOTIFICATION", name: "Deficiency issued", version: 1, status: "PUBLISHED", values: { event: "DEFICIENCY_ISSUED", channel: "IN_APP", recipientRole: "INSTITUTION", enabled: true } },
    { id: "rule-escalation-001", category: "ESCALATION", name: "Sample overdue condition escalation", version: 1, status: "PUBLISHED", values: { thresholdMinutes: 60, recipientRole: "REGIONAL", maxLevel: 2, enabled: true } },
    { id: "retention-001", category: "RETENTION", name: "Retention policy pending", version: 1, status: "DRAFT", values: { transcriptCollectionEnabled: false, policyApproved: false } },
    { id: "setting-001", category: "SETTINGS", name: "Sample portal settings", version: 1, status: "PUBLISHED", values: { timezone: "Asia/Kolkata", ledgerEnabled: false } },
  ],
  integrations: [
    { id: "integration-calendar", name: "Calendar connector", type: "CALENDAR", status: "STALE", lastSyncAt: "2026-10-24T08:00:00+05:30", fieldOwnership: "Availability intervals only; manual confirmation takes precedence when authorised", error: "Mock sync delay; manual availability remains available" },
    { id: "integration-email", name: "Email connector", type: "EMAIL", status: "FAILED", lastSyncAt: "2026-10-25T08:00:00+05:30", fieldOwnership: "Delivery evidence only", error: "Mock provider unavailable" },
    { id: "integration-import", name: "Application import", type: "LEGACY_IMPORT", status: "MOCK", lastSyncAt: null, fieldOwnership: "Sample import mapping; authoritative fields undecided", error: null },
    { id: "integration-ledger", name: "Optional ledger", type: "LEDGER", status: "DISABLED", lastSyncAt: null, fieldOwnership: "Hashes only; no document content", error: null },
  ],
  jobs: [
    { id: "job-001", type: "NOTIFICATION_DELIVERY", entityId: "notification-002", integrationId: "integration-email", status: "RETRY_PENDING", attempts: 2, lastError: "Mock provider unavailable", nextAttemptAt: "2026-10-26T12:10:00+05:30" },
    { id: "job-002", type: "OCR", entityId: "version-safety-2", integrationId: null, status: "QUEUED", attempts: 0, lastError: null, nextAttemptAt: null },
    { id: "job-003", type: "REPORT_GENERATION", entityId: "run-007", integrationId: null, status: "FAILED", attempts: 1, lastError: "Mock export worker timeout", nextAttemptAt: null },
  ],
  tasks: [
    { id: "task-001", title: "Respond to lease deficiency", ownerId: "user-institution", applicationId: "app-001", dueAt: "2026-11-02T17:00:00+05:30", href: "/portal/applications/app-001/deficiencies/notice-001", status: "PENDING" },
    { id: "task-002", title: "Confirm selected experts' common slot", ownerId: "user-coordinator", applicationId: "app-002", dueAt: "2026-11-18T17:00:00+05:30", href: "/portal/evc/visit-001/schedule", status: "PENDING" },
    { id: "task-003", title: "Review overdue compliance clarification", ownerId: "user-compliance", applicationId: "app-004", dueAt: "2026-10-24T17:00:00+05:30", href: "/portal/compliance/condition-001", status: "BLOCKED" },
  ],
};

/** Scenario overrides are isolated from the baseline; a demo controller applies them locally. */
export const mockScenarios = {
  default: { description: "Connected baseline across all five modules", changes: [] },
  staleAvailability: { description: "Expert 5 confirmation is older than the sample 24-hour policy", changes: [{ collection: "availability", id: "availability-005", patch: { confirmedAt: "2026-10-15T09:00:00+05:30" } }] },
  noFeasibleSlot: { description: "No recommendation passes all mandatory participants", changes: [{ collection: "slots", id: "slot-001", patch: { feasible: false, blockers: ["expert-005 unavailable throughout the remaining permitted window"] } }] },
  confirmationConflict: { description: "A previously feasible slot becomes unavailable before confirmation", error: { code: "EVC_SLOT_CONFLICT", status: 409, message: "The selected slot is no longer available." } },
  versionConflict: { description: "Another reviewer has saved a newer record", error: { code: "VERSION_CONFLICT", status: 412, message: "Reload the latest version before saving." } },
  empty: { description: "Filtered list has no results", result: [] },
  forbidden: { description: "Record outside the selected user's authorised scope", error: { code: "FORBIDDEN", status: 403, message: "This record is unavailable in your current access scope." } },
  failedLoad: { description: "Recoverable page loading failure", error: { code: "UNAVAILABLE", status: 503, message: "Unable to load data. Try again." } },
  uploadRejected: { description: "File exceeds the illustrative limit", error: { code: "FILE_TOO_LARGE", status: 422, message: "Choose a PDF smaller than the configured 10 MB sample limit." } },
  pendingScan: { description: "Uploaded version cannot be previewed until scanning completes", changes: [{ collection: "documents", id: "doc-safety", versionId: "version-safety-2", patch: { scan: "PENDING" } }] },
  expiredDownload: { description: "Completed export's temporary download is no longer available", changes: [{ collection: "reportRuns", id: "run-001", patch: { status: "EXPIRED" } }] },
  integrityMismatch: { description: "Illustrative fingerprint mismatch; no real ledger verification", expected: "demo-fingerprint-original", actual: "demo-fingerprint-modified", matches: false },
} as const;
