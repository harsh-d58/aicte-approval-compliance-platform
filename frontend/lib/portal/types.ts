/** Frontend view models. Keep these when replacing the mock data source. */
export type Role =
  | "INSTITUTION" | "SCRUTINY" | "REGIONAL" | "EVC_COORDINATOR" | "EVC_EXPERT"
  | "COMPLIANCE" | "CENTRAL" | "POLICY" | "AUDITOR" | "SYSTEM";
export type Scope = { type: "INSTITUTION" | "REGION" | "APPLICATION" | "EVC" | "GLOBAL"; id: string };
export type ApplicationStatus =
  | "DRAFT" | "SUBMITTED" | "IN_REVIEW" | "RETURNED_FOR_DEFICIENCY" | "RESUBMITTED"
  | "AWAITING_EVC" | "AWAITING_COMMITTEE_ACTION" | "AWAITING_COMPLIANCE"
  | "DECISION_PENDING" | "APPROVED" | "REJECTED" | "WITHDRAWN" | "CLOSED";
export type DeliveryStatus = "QUEUED" | "PROCESSING" | "SENT" | "DELIVERED" | "FAILED" | "RETRY_PENDING" | "CANCELLED" | "UNKNOWN";
export type ReportCode = "region-performance" | "application-pendency" | "evc-status" | "undertaking-compliance" | "document-validity" | "overdue-actions" | "notification-delivery" | "case-closure";
export interface Region { id: string; name: string; code: string }
export interface User { id: string; displayName: string; email: string; status: "ACTIVE" | "DISABLED"; assignments: { role: Role; scope: Scope; validUntil: string | null }[] }
export interface Institution { id: string; code: string; name: string; type: string; regionId: string; status: string; campuses: { id: string; name: string; city: string; primary: boolean }[]; attributes: { key: string; value: string; verification: "VERIFIED" | "PENDING"; sourceVersionId: string | null }[] }
export interface Application { stageType?: string; applicationTypeId?: string; id: string; number: string; institutionId: string; campusId: string; type: string; academicYear: string; status: ApplicationStatus; workflowId: string; currentStage: string; stageEnteredAt: string | null; submittedAt: string | null; dueAt: string | null; ownerId: string | null; nextAction: string; version: number; closure: null | { at: string; authorityId: string; reason: string; reopened: boolean } }
export interface Submission { id: string; applicationId: string; number: number; submittedAt: string; submittedBy: string; noticeId: string | null; documentVersionIds: string[] }
export interface Workflow { applicationTypeId?: string; id: string; name: string; version: string; aphVersion: string; status: "DRAFT" | "PUBLISHED" | "RETIRED"; effectiveFrom: string | null; stages: { type?: string; code: string; name: string; slaDays: number; ownerRole: Role }[]; transitions: { from: string; to: string; guards: string[] }[] }
export interface StageEvent { id: string; applicationId: string; at: string; actorId: string; from: string; to: string; reason: string; workflowId: string }
export interface Deficiency { id: string; number: string; applicationId: string; issuedBy: string; issuedAt: string; responseDueAt: string; reason: string; status: "OPEN" | "RESPONDED" | "RESOLVED"; items: { id: string; criterion: string; description: string; documentId: string | null; status: "OPEN" | "RESPONDED" | "RESOLVED"; response: string | null; responseVersionId: string | null }[] }
export interface DocumentVersion { id: string; number: number; fileName: string; mimeType: string; sizeBytes: number; issuedAt: string | null; expiryDate: string | null; uploadedAt: string; uploadedBy: string; verification: "PENDING" | "VERIFIED" | "REJECTED"; scan: "PENDING" | "CLEAN" | "FAILED"; previewText: string }
export interface PortalDocument { id: string; institutionId: string; applicationId: string | null; campusId: string | null; type: string; issuer: string; reference: string; supportsExpiry: boolean; currentVersionId: string; versions: DocumentVersion[] }
export interface DocumentCheck { id: string; documentId: string; versionId: string; engine: string; processedAt: string | null; status: "QUEUED" | "COMPLETED" | "FAILED"; fields: { name: string; declared: string; extracted: string | null; confidence: number | null }[]; findings: { code: string; severity: string; description: string; review: "PENDING" | "ACCEPTED" | "CORRECTION_REQUIRED" }[] }
export interface Renewal { id: string; documentId: string; previousVersionId: string; submittedVersionId: string | null; dueAt: string; status: "OPEN" | "SUBMITTED" | "UNDER_REVIEW" | "VERIFIED"; assignedTo: string }
export interface Expert { id: string; userId: string; expertise: string[]; eligibility: "ELIGIBLE" | "INELIGIBLE"; availabilityMethod: "MANUAL" | "CALENDAR" }
export interface Availability { supersededAt?:string; supersedesId?:string; id: string; participantType: "EXPERT" | "INSTITUTION"; participantId: string; startAt: string; endAt: string; state: "AVAILABLE" | "BUSY"; source: "MANUAL" | "CALENDAR"; confirmedAt: string }
export interface Visit { policy?: { freshnessHours:number; preparationLeadHours:number; configurationId:string }; id: string; applicationId: string; campusId: string; status: "READY" | "AWAITING_AVAILABILITY" | "PROPOSED" | "CONFIRMED" | "POSTPONED" | "COMPLETED" | "CANCELLED"; requiredBy: string; durationMinutes: number; requiredMemberCount: number; coordinatorId: string; committee: { expertId: string; role: string; selectedBy: string; selectedAt: string }[]; confirmedSlotId: string | null; version: number; events: { at: string; type: string; actorId: string; reason: string }[] }
export interface Slot { id: string; visitId: string; startAt: string; endAt: string; rank: number; feasible: boolean; explanation: string[]; participantIds: string[]; snapshotAt: string; expiresAt: string; blockers: string[] }
export interface Invitation { id: string; visitId: string; recipientId: string; response: "PENDING" | "ACCEPTED" | "DECLINED"; delivery: DeliveryStatus; calendarStatus: "SYNCED" | "PENDING" | "FAILED" }
export interface Observation { id: string; visitId: string; criterion: string; text: string; authorId: string; sourceType: "STRUCTURED_FORM" | "COMMITTEE_NOTE"; status: "DRAFT" | "SUBMITTED" }
export interface MeetingRecord { id: string; visitId: string; type: "MINUTES" | "EVC_REPORT"; templateVersion: string; currentVersion: number; versions: { number: number; status: "DRAFT" | "IN_REVIEW" | "CHANGES_REQUESTED" | "APPROVED"; sections: { title: string; text: string; sourceIds: string[]; warning: string | null }[]; approvedBy: string | null; approvedAt: string | null; correctionReason: string | null }[] }
export interface ActionItem { id: string; visitId: string; observationId: string; description: string; responsibleRole: Role; dueAt: string; status: "OPEN" | "COMPLETED" }
export interface Decision { id: string; applicationId: string; type: "APPROVE" | "REJECT" | "CLOSE"; status: "DRAFT" | "APPROVED"; authorityId: string; reason: string; at: string | null }
export interface Condition { version?: number; id: string; applicationId: string; institutionId: string; sourceDecisionId: string; code: string; description: string; evidenceRequired: string[]; dueAt: string; status: "OPEN" | "EVIDENCE_SUBMITTED" | "UNDER_REVIEW" | "CLARIFICATION_REQUIRED" | "VERIFIED_COMPLIANT" | "VERIFIED_NON_COMPLIANT" | "CLOSED" | "REOPENED"; reviewerId: string; closureReason: string | null }
export interface Evidence { id: string; conditionId: string; submissionNumber: number; submittedAt: string; submittedBy: string; documentVersionIds: string[]; responseToVerificationId: string | null }
export interface Verification { id: string; evidenceId: string; reviewerId: string; result: "CLARIFICATION_REQUIRED" | "COMPLIANT" | "NON_COMPLIANT"; comments: string; at: string }
export interface Notification { id: string; recipientId: string; event: string; channel: "IN_APP" | "EMAIL" | "SMS"; status: DeliveryStatus; entityType: "APPLICATION" | "EVC" | "CONDITION" | "DOCUMENT"; entityId: string; createdAt: string; read: boolean; attempts: { number: number; at: string; result: DeliveryStatus; failureReason: string | null }[] }
export interface Escalation { id: string; entityType: string; entityId: string; ruleId: string; dueAt: string; triggeredAt: string; ownerId: string; level: number; status: "OPEN" | "RESOLVED"; reason: string; resolution: string | null }
export interface ReportDefinition { id: ReportCode; name: string; columns: string[]; filters: string[]; roles: Role[] }
export interface ReportRun { requestedRole?: Role; scope?: Scope; snapshotRows?: Record<string,string|number>[]; id: string; reportCode: ReportCode; requestedBy: string; generatedAt: string | null; period: { from: string; to: string }; filters: Record<string, string>; status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "EXPIRED"; snapshotAt: string; rowCount: number; format: "CSV" | "XLSX" | "PDF"; failureReason: string | null }
export interface AuditEvent { id: string; actorId: string; action: string; entityType: string; entityId: string; at: string; reason: string; correlationId: string; version: number; previousHash: string | null; eventHash: string; anchor: "DISABLED" | "PENDING" | "ANCHORED" | "FAILED" }
export interface Configuration { id: string; category: "APH" | "DOCUMENT_TYPE" | "DOCUMENT_REQUIREMENT" | "COMMITTEE" | "TEMPLATE" | "RETENTION" | "NOTIFICATION" | "ESCALATION" | "SETTINGS"; name: string; version: number; status: "DRAFT" | "PUBLISHED"; values: Record<string, string | number | boolean | string[] | number[]> }
export interface Integration { id: string; name: string; type: string; status: "MOCK" | "STALE" | "FAILED" | "DISABLED"; lastSyncAt: string | null; fieldOwnership: string; error: string | null }
export interface Job { id: string; type: string; entityId: string | null; integrationId: string | null; status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "RETRY_PENDING"; attempts: number; lastError: string | null; nextAttemptAt: string | null }
export interface Task { id: string; title: string; ownerId: string; applicationId: string | null; dueAt: string; href: string; status: "PENDING" | "BLOCKED" | "COMPLETED" }
export interface PortalCollections {
  regions: Region[]; users: User[]; institutions: Institution[]; applications: Application[];
  submissions: Submission[]; workflows: Workflow[]; stageEvents: StageEvent[]; deficiencies: Deficiency[];
  documents: PortalDocument[]; documentChecks: DocumentCheck[]; renewals: Renewal[];
  experts: Expert[]; availability: Availability[]; visits: Visit[]; slots: Slot[]; invitations: Invitation[];
  observations: Observation[]; meetingRecords: MeetingRecord[]; actionItems: ActionItem[];
  decisions: Decision[]; conditions: Condition[]; evidence: Evidence[]; verifications: Verification[];
  notifications: Notification[]; escalations: Escalation[]; reportDefinitions: ReportDefinition[];
  reportRuns: ReportRun[]; auditEvents: AuditEvent[]; configurations: Configuration[];
  integrations: Integration[]; jobs: Job[]; tasks: Task[];
}
