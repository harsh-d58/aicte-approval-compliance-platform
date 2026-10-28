# FastAPI implementation plan — PRD v1.0

Prepared: **27 October 2026**. Reconciled with the implementation on **28 October 2026**. Status: **B01 partially complete; B02 authentication and scoped reads implemented in part; no business writes or workers yet**.

This document tracks the FastAPI backend for the AICTE Approval Workflow Automation and Institutional Compliance Monitoring Platform. Product scope follows [Product Requirements Document (PRD), v1.0](<Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md>). The user selected **Supabase Auth** for the prototype, replacing the PRD's proposed Keycloak choice. The frontend plans do not add backend product requirements.

## Current implementation and evidence

| Area | Implemented now | Verification and remaining limit |
| --- | --- | --- |
| Existing PostgreSQL | `backend/check_database.py` inspects metadata using TLS and an explicitly read-only transaction. All **65 PRD entity names** exist as `public` tables. | [Schema mapping](backend/docs/schema_mapping.md) records table groups and selected identity columns. Foreign keys, version rules and immutable-record protections are not fully audited. `backend/docs/database_audit.json` is local and ignored. No schema or data writes were made. |
| Configuration and API shell | `backend/app/settings.py` loads ignored `backend/.env`; `main.py` provides `/api/v1`, `/health`, `/ready`, correlation IDs, PRD-shaped errors and validation responses. | `/ready` probes the database and checks that `SUPABASE_URL` is set; it does not test the Auth server or claim the full product is ready. |
| Supabase Auth | `auth.py` verifies ES256/RS256 access tokens against the configured project's JWKS; checks issuer, `authenticated` audience, expiry, issue time, user/session UUIDs, role and non-anonymous status. The connected project's public JWKS contains one ES256 key. | A forged token was rejected with 401 using the live JWKS. HS256 tokens are rejected. No real signed-in user journey is possible yet because `auth.users` has zero users. |
| Current user | `GET /api/v1/me` and `GET /api/v1/me/permissions` query `public.users`, active assignments and role permissions. | An unprovisioned synthetic subject was denied with 403. `public.users`, `roles`, `permissions` and `user_role_assignments` have zero rows; approved grants and a real account remain necessary. |
| Scoped records | `GET /api/v1/institutions`, `/institutions/{id}`, `/applications`, `/applications/{id}` are read-only. SQL checks active assignments, `institution.read` or `application.read`, and exact institution, direct region, application or explicit global scope as applicable. Lists use cursor pagination. | Queries ran against the connected empty database: lists returned zero records; missing/out-of-scope detail IDs returned 404. Positive-scope integration cannot be demonstrated until approved policy data exists. See [access policy](backend/docs/access_policy.md). |
| Tests and frontend | 12 backend tests cover API errors/readiness, token claims and rejection, cursor behaviour and scoped-read query contracts. The frontend still uses its demo adapter. | No real frontend-to-API session, statutory transition, audit/outbox, upload, EVC, compliance, notification or report journey is implemented. |

The ignored `backend/.env` contains the working `DATABASE_URL` and a Supabase project URL validated against the project's public JWKS. It is never committed. This local environment uses Python 3.12; `backend/requirements.txt` contains runtime pins and `backend/requirements-dev.txt` adds the test client. An earlier database authentication failure was resolved by encoding a password delimiter in the local URL. Do not create a replacement database or seed official roles and rules from frontend demo identities.

Checkboxes below represent the **full** package exit criteria. A partial read-only slice does not make B02, B03 or B05 complete.

## Frontend handoff and API gaps

The saved [frontend tracker](frontend_tracker.md) and [remaining-work audit](missing_frontend.md) report all 54 templates present, with 25 page rows partial and F01–F15 open. Those are earlier frontend audit findings; this backend work did not re-audit the pages or connect their demo adapter to the API. The PRD §9.2 inventory contains **90 proposed operations**; **six GET operations** from it are currently implemented. `/health` and `/ready` are additional operational endpoints outside the versioned business API.

### Remaining frontend behaviours and corresponding PRD API coverage

The F identifiers and page identifiers refer to the existing engineering trackers; **the PRD remains the sole source of product scope**. Finish the relevant client behaviour and server contract together, keeping pending verification/approval distinct from successful completion. Listed URLs are relative to `/api/v1`.

| Backlog / affected pages | Required remaining behaviour | Explicit PRD coverage | Contract detail to settle |
| --- | --- | --- | --- |
| **F01 · P07/P44** | Controlled typed institution attributes, source provenance, campus address/ownership. | §§5.2/9.2; `PATCH /institutions/{id}` and `POST /institutions/{id}/campuses`. | Typed catalogue/verification payload and campus update semantics; dedicated attribute/campus-update URLs are not listed. |
| **F02 · P10/P12/P43/P44** | Applicable/effective workflow resolution; executable guards, stage owners and SLAs; safe unsupported-rule state. | WF-01–09, §§7.1/9.2/10; application submit/workflow/transitions and admin workflow create/validate/publish operations. | Executable guard catalogue, context/effectivity payloads and draft-edit contract. Published arbitrary text is not an executable rule. |
| **F03 · P13** | Multiple deficiency items; separate answers/version links; item acceptance/re-return and history. | §7.1; `POST /applications/{id}/deficiency-notices`, `POST /deficiency-notices/{id}/responses`, `POST /deficiency-items/{id}/resolve`. | Per-item response arrays, exact version references and resolution/re-return outcome payloads. Do not apply one answer to every item. |
| **F04 · P16/P44** | Published document type/requirement rules, expiry/type/size validation and campus/scope linkage; clarify logical versus version metadata editing. | §§5.4/7.5/13.2; upload-session, document registration and version operations in §9.2. | Document catalogue/rule exposure, independent file download contract and which metadata each operation may edit. |
| **F05 · P18** | Per-field/finding review, reason/reviewer/time provenance, extraction quality/missing/type states and reprocessing. | §§5.4/17.3; `POST /document-versions/{id}/ocr-checks`, `GET /document-versions/{id}/checks`, `POST /document-check-results/{id}/review`. | Multi-field extraction/retry representation and individual check-result identifiers. OCR remains advisory. |
| **F06 · P22/P25** | Scheduling horizon/time/location constraints, alternatives/deadline risk, retained attempts, bookings and invitation changes. | §7.3 steps 4–8, §§9.5–9.6/10.3/15; recommendation, confirmation, reschedule, postpone, events and invitations operations. | Institution availability, invitation acknowledgement/cancellation and old/new booking representation are not fully contracted in §9.2. |
| **F07 · P28/P29** | Differing/conflicting source warnings, generated draft questions/unresolved issues/actions and approved-version content inspection/corrections. | §7.3 step 9, §§9.2/9.7/13.3; observation, draft generation, record read/edit/review/approval/change/source operations. | Action-item lifecycle and historical-version selection/correction payloads; no AI provider or dedicated action/version URLs are prescribed. |
| **F08 · P19/P45/P46/P48** | Demonstrable configured reminder/expiry/deadline evaluation with recipients, repeats, escalation levels, deduplication and resolution. | §§7.4–7.5/8; notification/escalation rules, delivery attempts/retry and escalation resolution operations. | Scanners/outbox are internal worker behaviours; do not invent public scanner endpoints or treat seeded alerts as execution evidence. |
| **F09 · P36/P37** | Correct report-specific time bases, required filters and reconciliation of all eight downloaded outputs. | §§11.1–11.3/17.4; `GET /reports`, `POST /report-runs`, run status and authorised download operations. | Report/filter payload schemas, live viewer-row representation and snapshot metadata. Application submission time cannot stand in for every report's date field. |
| **F10 · P04/P09** | All §7.2 time, lead-time, verification, delivery-denominator, committee and freshness measures; accurate active/outcome definitions. | M2 §7.2 and report reconciliation §11.3. | No dashboard endpoint is named in §9.2. Agree the aggregate/filter/drill-down contract against the PRD rather than claiming one is already specified. |
| **F11 · P37/P38/P39** | Canonical selected-record/version verification, audit target/version and old/new state, sensitive download audit events. | BR-18/20, §§11.2/13.4–13.5; audit search/detail, `POST /audit-verifications`, anchors and report download. | Canonical representation/version selection and file/audit export contracts. Placeholder event strings are not protected cryptographic history. |
| **F12 · P41** | Compatible role/scopes, assignment validity dates, duplicates, expiration/revocation UX and server enforcement. | §§3.2/5.2/13.1; `POST /users/{id}/role-assignments` and `PATCH /users/{id}/role-assignments/{assignmentId}`. | Approved permission/scope policy and validity/revocation payloads. Do not invent an official role matrix from demo identities. |
| **F13 · P47** | Application import/update reconciliation, duplicates and authoritative-field ownership review, result/error recovery. | §§2.1/16.1; integration configuration/connectivity/job inspection operations exist. | No import-apply/reconciliation endpoint is listed. Discover authorised source ownership/interfaces; controlled sample imports are allowed for prototype scope. |
| **F14 · P05/P09/shared** | Remaining task/register filters, stale/offline/session/error recovery, coherent scenarios and broader acceptance. | §§9.1/14/17/20; common filters/pagination/error contracts and access controls. | No task-list API is listed. Define required assigned-work representation; test recovery without claiming formal accessibility/security certification from basic checks. |
| **F15 · P37/P44–P46/P48** | Attempt-level job history, bounded retry/backoff/max states, scheduled report setup and expired-download lifecycle. | §§8.3–8.4/11.2/15; `GET /admin/jobs`, notification retry, report run/status/download and rule operations. | General job retry, schedule configuration and expiry payloads are not explicitly listed. Distinguish internal worker execution from authorised administrative controls. |

### Next implementation sequence

1. Provision a real Supabase Auth user and its `public.users` identity mapping through the approved administration process; approve the two proposed read permission codes, scoped role grants and role matrix. Verify positive and negative institution/region/application access with real tokens. No automatic privilege grant follows sign-in.
2. Finish B01 constraint and version-token review, then B02 transaction safety: write authorisation, idempotency, `If-Match`, audit and outbox in the same committed change. The six current GET routes cover only a read slice.
3. Implement approved institution/profile and application/document/deficiency contracts (B03–B05), including F02–F05, against the existing schema. Keep frontend demo data separate until the live adapter is authorised and tested.
4. Continue B06–B10 for EVC, records, compliance, workers and all eight reports; prove the PRD §§17/20 permission, conflict and failure scenarios before marking package gates complete.

## 1. Scope and architectural boundary

PRD references: §§1–4, 18, 22.

- [ ] Implement **one modular FastAPI backend**, with business modules inside one deployable application (§4.1).
- [ ] Use the existing PostgreSQL database as the authoritative application/workflow state store; workers and integrations must pass consequential changes through the same business validation (§4.1).
- [ ] Implement M1 workflow, M2 dashboard data, M3 EVC management, M4 compliance and M5 document expiry/renewal, plus the shared institution, OCR, notification, reporting, configuration, integration and audit capabilities.
- [ ] Keep statutory scrutiny, expert selection, verification, findings, report approval and decisions under the authorised human roles.
- [ ] Keep optional permissioned-ledger work separate from the required append-only audit capability. Ledger failure must never block the main workflow.

Use the technology choices proposed in PRD §4.2, with the user's explicit Supabase Auth substitution:

| Layer | Current choice | Planning treatment |
| --- | --- | --- |
| API/business backend | Python FastAPI | Build the modular backend and typed request/response contracts. |
| Authoritative database | PostgreSQL | Existing database; map and integrate. |
| Background work | Redis and Celery | OCR, scanning deadlines/expiry, delivery/retries, calendar sync, exports and integration jobs. |
| Files | Encrypted, versioned object storage | Integrate a protected store; vendor is not specified by the PRD. |
| OCR | PaddleOCR **or** Tesseract | Evaluate the permitted alternatives; the PRD does not choose between them. |
| Identity | Supabase Auth for prototype per user's 28 October decision; approved AICTE/government SSO later | Verify project access tokens and enforce application permissions and scope. |
| Notifications | Email, SMS and in-platform adapters | Provider remains subject to approved access. |
| Calendar | Approved APIs or controlled availability entry | Manual confirmation is a valid fallback. |
| Monitoring | Prometheus and Grafana | API, worker, integration and database visibility. |
| Deployment | Docker | Reproducible deployment in an approved environment. |
| Optional ledger | Hyperledger Fabric or equivalent permissioned system | Conditional on governance/value/security decisions. |

The PRD does not prescribe an ORM, database driver, migration library, object-storage vendor, malware scanner, AI/LLM provider, Python version or detailed package layout. Select implementation details when building against the actual database; do not present them as PRD mandates or introduce additional platform services through this plan.

## 2. Priority and dependency order

The priorities below organise implementation; they do not replace the PRD's Must/Should distinctions. **P2 is required acceptance/operational work, not optional product scope.** The only optional feature track here is the permissioned ledger.

| Order | Priority | Backend work package | Depends on | Exit evidence |
| --- | --- | --- | --- | --- |
| B01 | P0 | Existing-database mapping and FastAPI contract foundation | Database handoff | PRD entities mapped; common API/error/pagination contracts checked. |
| B02 | P0 | Identity, scoped authorisation, concurrency, idempotency, audit and outbox foundation | B01 | Access denials, rollback, stale-version and duplicate-request tests pass. |
| B03 | P1 | Institution/profile and approved configuration services | B02 | Authorised profile changes and immutable/effective rule versions work. |
| B04 | P1 | Documents, protected files, worker foundation and OCR review | B02–B03 | Immutable upload/check/review journey with independent file permissions. |
| B05 | P1 | Application intake, workflow, deficiencies and decisions | B03–B04 | Configured sample routes and item-level correction journey pass. |
| B06 | P1 | EVC committee, availability, scheduling and lifecycle | B05; worker foundation | Exact-member scheduling and transactional conflict tests pass. |
| B07 | P1 | Meeting-to-Record Assistant and record approval | B06 | Source-linked drafts and immutable approved corrections pass. |
| B08 | P1 | Compliance, renewal, reminder and escalation execution | B04–B05; worker foundation | Evidence remains distinct from verification; time-driven rules execute. |
| B09 | P1 | Dashboard metrics and all eight report categories | Relevant B05–B08 data and delivery history | Scoped metrics, filters, snapshots and exports reconcile. |
| B10 | P1 | Approved integration adapters and reconciliation | B02 and relevant business modules | Allowed mock/controlled imports or approved interfaces preserve authority and history. |
| B11 | P2 | Operational controls and complete PRD acceptance | All required packages | §§17/20 evidence, security, recovery and approved workload results. |
| Conditional | Optional | Permissioned-ledger integration | Audit foundation; governance approval | Canonical version verification works; ledger outage leaves workflow available. |

Delivery adapters and operational instrumentation start when their first module needs them. B08/B11 finish those capabilities; they are not reasons to postpone security, audit, outbox, logs or failure handling until the end. Tests accompany each package.

## 3. B01 — Existing database and API foundation

PRD references: §§4–6, 9.1, 10, 14.

- [x] Connect to the existing PostgreSQL database with TLS and a read-only transaction; keep credentials in ignored local configuration and out of responses and committed files.
- [x] Map all 65 PRD §§5.2–5.7 entity names to existing `public` tables; record selected identity columns in [schema_mapping.md](backend/docs/schema_mapping.md).
- [ ] Complete the column-level data dictionary for every module and resolve any logical-to-physical field differences before its write API is built.
- [ ] Verify relevant existing foreign keys, uniqueness, editable version tokens and immutable-record protections. The PRD's schema is logical; equivalent existing names are acceptable (§5). Document any mismatch before proposing a targeted change; do not reset or rewrite existing records.
- [ ] Preserve distinctions between institution/user, application/submission, document/version, visit-specific membership/reusable committee, evidence/verification, notification/attempt and draft/approved record (§6.2).
- [ ] Establish backend modules corresponding to §4.1. Keep transport handling, business validation, persistence access and external adapters separable within the monolith. This is code organisation, not a microservice requirement.
- [x] Define `/api/v1` JSON GET routes and bearer-token dependencies for the implemented identity, institution and application reads.
- [ ] Verify HTTPS deployment and file-transfer contracts when those runtime paths are added (§9.1).
- [ ] Return `id`, `status`, timestamps and `version` where appropriate. Match §9.3–9.7 example field names and semantics; example UUIDs, dates, numbering and templates are illustrative.
- [x] Use cursor pagination with `data`, `page.limit` and `page.next_cursor` on the current institution/application lists; support their `status` filter and a 1–100 limit.
- [ ] Extend pagination and permitted filters to later lists and reports.
- [x] Standardise current API errors as `error.code`, `message`, `details` and `correlation_id`; exclude submitted values from validation details.
- [ ] Honour §9.1 status semantics: 200/201/202/204; 400/401/403/404/409/412/422/429/500/503. Inaccessible-record errors must not reveal records outside the caller's scope.

**Gate:** a documented database mapping, reviewed API inventory and common contract tests. Database recreation and database credentials committed to a file are not deliverables.

## 4. B02 — Identity and transactional safety

PRD references: §§3, 5.1–5.2, 7.1, 8.2, 9–10, 12–13.

- [x] Validate configured Supabase Auth ES256/RS256 bearer tokens against project JWKS and required claims; resolve an active `public.users` identity and active, time-valid assignments for the implemented GET routes. Reject anonymous, missing and unprovisioned users.
- [ ] Exercise those identity and assignment paths with a real Supabase Auth user, including disabled/revoked and expired-assignment cases; service identity policy is not defined yet.
- [x] Filter the current institution/application read queries by database permission and exact authorised scope; return 404 for missing and out-of-scope detail IDs.
- [ ] Implement Read, Create, Update, Assign, Transition, Return, Verify, Approve, Configure, Export and Administer permissions (§3.3), with institution/region/assigned-case/committee restrictions as applicable.
- [ ] Enforce scope in record queries, mutations, histories, source inputs, export requests, generated files and individual file access. User-supplied IDs or selected UI roles cannot grant access.
- [ ] Restrict experts to their assigned committee material and auditors to their authorised inspection/export permissions; technical administration must not imply statutory approval authority.
- [ ] Use stronger authentication for privileged actions where the approved identity policy requires it (§13.1).
- [ ] Persist idempotency results for retry-sensitive submission, EVC confirmation, notification dispatch, evidence and report-generation requests (§10.1).
- [ ] Enforce selected update preconditions through `If-Match`/record versions and return 412 for stale edits. Reject state/scheduling conflicts with the specified conflict semantics.
- [ ] Make consequential state/history/assignment changes atomic. A failed guard or permission check must leave business state unchanged.
- [ ] Persist an outbox event in the same transaction as the business change; workers use it for permitted downstream effects (§8.2).
- [ ] Ensure every designated sensitive action has a durable audit event associated with the committed change. Record actor, action, entity, timestamp, old/new status, reason, correlation and relevant version; protect against update/delete and avoid full sensitive payloads (§13.4).
- [ ] Store event timestamps in UTC, retain intended local timezones, and use policy-local dates for deadlines/expiry. Test offset/daylight-saving boundaries where relevant (§10.4).
- [ ] Apply rate limiting where appropriate, protected secret references and secure transport/storage (§§9.2, 13).

**Gate:** cross-institution/region/visit denial; invalid/expired actor denial; repeat request without duplicate business effects; stale edit rejected; failed transition rolled back; committed changes retain outbox/audit evidence.

## 5. B03 — Institutions, profiles and controlled configuration

PRD references: §§5.2–5.4, 5.7, 7.1, 9.2, BR-01/02/21/23, 21.

- [x] Implement the read-only institution list and detail slice with SQL permission/scope checks; the rest of B03 remains open.
- [ ] Implement the identity/user and institution/profile operations in the API inventory below, including scoped grants/revocations and permitted profile fields.
- [ ] Validate institution/campus relationships, reliable unique identifiers, region hierarchy and explicit authorised representation. Entering an institution code must not create access.
- [ ] Handle typed profile attributes through the controlled catalogue: text/date/number, source-document reference and verification status (§5.2).
- [ ] Support application categories, APH rule versions, workflow stages/transitions and document requirements as approved configuration, with correct application/institution context.
- [ ] Validate workflow references, permitted transition/guard semantics and approved publication/effective dates. Reject unsupported or invalid configurations rather than publishing non-executable rules.
- [ ] Preserve published versions and configuration-change history. New publications must not silently change an application's bound workflow/APH version.
- [ ] Version notification/escalation rules and controlled settings; require approval/effectivity where required. Keep integration credentials in a secret manager.
- [ ] Keep policy-dependent composition, deadlines, templates, document requirements, retention, numbering and authority mappings explicit and configurable. Do not turn PRD examples into official values.

**Gate:** permitted changes work; unauthorised changes fail; publication preserves old cases; applicable/effective configuration is resolved consistently.

## 6. B04 — Documents, workers and OCR review

PRD references: §§5.4, 7.5, 8.4, 9.2, BR-16/17/20, 13.2, 15–17.

- [ ] Implement controlled upload sessions, document registration, immutable version addition/listing, checks, human review and renewal-case opening using the listed APIs.
- [ ] Store files in encrypted protected object storage and metadata/checksums in the existing database. Preserve logical document, campus/scope links, issuer/reference, issue/expiry dates and exact submitted versions.
- [ ] Enforce configured type/size limits and malware checks; use resumable/multipart handling where appropriate. Never treat client-side file validation as authoritative scanning.
- [ ] Authorise files independently of the parent record, with short-lived authorised download access and no direct public storage access.
- [ ] Establish Redis/Celery execution with persisted job status, attempts, next retry and errors; jobs must survive/recover from worker failure according to configured policy.
- [ ] Queue OCR for an immutable version and retain engine name/version, extraction provenance/confidence, extracted fields and individual validation findings.
- [ ] Cover mismatched type/metadata, missing/uncertain fields, expiry and quality findings. Permit authorised reprocessing and reasoned human review of individual check outcomes.
- [ ] Prevent OCR or a checksum from establishing authenticity or automatically rejecting an application. Issuer verification requires an approved interface/process.
- [ ] Apply approved lifecycle/retention to files and OCR results while preserving required historical links.

**Gate:** old versions remain retrievable by authorised users; unsafe/invalid uploads and unauthorised downloads are rejected; failed OCR can be reprocessed; uncertain output reaches human review.

## 7. B05 — Applications and workflow engine

PRD references: §§5.3, 7.1, 9.2–9.3, 10, BR-01–06/18/21/23/24, 17.1.

- [x] Implement the read-only application list and detail slice with SQL permission/scope checks; intake, review and workflow work remain open.
- [ ] Implement application intake/search/read/draft edit, submission, path/history, transitions, assignments, deficiency notice/response and item resolution using the listed contracts.
- [ ] Resolve the applicable approved workflow from application type, institution context, rule version and effectivity. Support Only Scrutiny and EVC-containing sample routes where the approved configuration requires them.
- [ ] Retain the case's workflow and APH versions. Automatic advancement may occur only when all configured guards pass; manual authority requirements remain enforced.
- [ ] Follow §7.1 transition validation: authenticate/scope; lock or version-check case/stage; load bound workflow; validate transition/conditions; require return reasons; record history; update stage/assignment; schedule outbox work; commit atomically and retain audit evidence.
- [ ] Track stage entry/completion, ownership, due date, pending action and next responsible role; preserve reassignment history.
- [ ] Issue one or more deficiency items linked to criteria/documents; preserve notice, response deadline, each answer and submitted versions. Resolve each item or return it with reasons; do not advance with unresolved required deficiencies.
- [ ] Persist authorised formal decision/authority/reason and record-document linkage. Close according to the configured authority and retain history.
- [ ] Implement controlled cancellation/reopening/migration as **Should** scope (WF-10), with explicit authorised policy and reason; do not silently migrate live cases.
- [ ] Map suggested application/stage statuses to approved terminology; do not assume the sample status labels are final policy.

**Gate:** all configured sample routes pass; invalid/unauthorised/duplicate transitions fail safely; item-level resubmission retains original evidence; publication leaves historical routing intact.

## 8. B06 — EVC committee and scheduling

PRD references: §§5.5, 7.3 steps 1–8, 8.4, 9.2/9.4–9.6, 10.3–10.5, BR-06–11, 15–17.

- [ ] Activate an EVC only when the case's workflow/rules require it; retain campus, deadline, applicable composition, duration, constraints and coordinator.
- [ ] Persist the exact officer-selected committee for each visit. Validate eligible profiles, authority, distinct active members and configured 4–5-person composition. Replacement requires authority and a reason.
- [ ] Collect availability for every selected expert **and the institution**, with interval/source/last-confirmed/status. Support controlled manual entry without assuming calendar API access.
- [ ] Account for stale availability, known busy periods and existing confirmed bookings; retain only authorised calendar details needed for conflict checks.
- [ ] Generate candidates inside the permitted search horizon; check exact participants, duration, time/location constraints, deadline and preparation lead time.
- [ ] Rank feasible candidates using approved criteria and explanatory results; a ranking cannot override a mandatory constraint.
- [ ] Retain calculation versions, availability snapshots, expiry and failed attempts. No feasible slot must identify blockers, nearest alternatives where possible, deadline risk, notification and configured escalation.
- [ ] Confirm only after rechecking all required resources, membership and deadline, then reserve atomically in the database. Concurrent overlapping confirmations must not both succeed; return 409 on conflict.
- [ ] Track confirmation, rescheduling, postponement, cancellation, completion, outstanding inputs, invitations/reminders and acknowledgements where supported. Preserve old/new event and invitation evidence rather than overwriting history.
- [ ] External calendar failure must remain a visible stale/failed state. A platform booking or queued invitation does not prove external synchronisation/delivery.

**Gate:** exact-member tests; stale/no-slot explanations; no silent expert substitution; two concurrent bookings cannot double-book; lifecycle changes retain history.

## 9. B07 — Meeting-to-Record Assistant

PRD references: §§5.5, 7.3 step 9, 9.2/9.7, BR-12/13/16, 13.3, 15, 17.2.

- [ ] Accept authorised committee notes, structured observations and permitted transcript references. Validate every source against the actor's visit scope.
- [ ] Generate draft minutes, criterion-wise observations, follow-up questions/unresolved issues, action items and EVC report sections using the applicable template.
- [ ] Persist source manifests and section-to-source references. Flag missing/conflicting inputs; do not invent findings or statutory outcomes.
- [ ] Support draft read/edit, submit-review, request-changes, authorised approval and permitted source inspection using the listed endpoints.
- [ ] Freeze approved versions; correction creates a new version with explanation. Keep draft/approved histories distinguishable and inspectable.
- [ ] Restrict transcript/recording use and retention to approved policy; exclude confidential transcript content from ordinary audit metadata.

The PRD specifies output, traceability and human approval, but no particular generative model or AI provider. This plan does not introduce one as a requirement.

**Gate:** missing/conflicting inputs are flagged; unauthorised sources are rejected; generated content stays draft until authorised approval; corrections preserve approved versions.

## 10. B08 — Compliance, renewals, notifications and escalation

PRD references: §§5.6–5.7, 7.4–7.5, 8, 9.2, BR-14/15/19, 15–17.

- [ ] Create conditions from an approved application/decision with due date, evidence requirements, responsible institution and verification authority.
- [ ] Preserve numbered evidence submissions and exact file versions. Record positive/negative verification or clarification with reviewer, timestamp and reason; new responses link back to the review.
- [ ] Keep evidence submission, verification and closure distinct. Close only under configured acceptance criteria; reopen only through authorised reasoned action. An overdue flag must not erase the underlying lifecycle status.
- [ ] Track renewal cases against logical documents and accepted/new versions. Complete renewal only when the new version satisfies the configured review/verification requirements.
- [ ] Scan deadlines and document expiry using configured schedules/timezones. Apply expiry only to applicable document types, with per-type reminder thresholds and proper replaced/accepted-version handling.
- [ ] Recover missed expiry scan windows and retain scanner/job failure evidence (§8.4).
- [ ] Resolve recipients, channels and template versions from rules and outbox events. Persist logical notifications separately from every delivery attempt.
- [ ] Distinguish QUEUED/PROCESSING/SENT/DELIVERED/FAILED/RETRY_PENDING/CANCELLED/UNKNOWN as supported. Provider acceptance is not delivery confirmation.
- [ ] Apply bounded retries/backoff, record provider references, failure category/retryability and last attempt, and alert on permanent/repeated failures.
- [ ] Implement escalation trigger/threshold, role/scope, channel, repeat interval, maximum level and resolution conditions; deduplicate the same rule/entity/window.
- [ ] Provide authorised notification detail/attempts/retry and escalation history/resolution APIs. Retry must preserve prior attempt evidence.

**Gate:** a real test-clock deadline/expiry evaluation produces the configured alerts; repeated scans do not duplicate the same window; evidence upload cannot auto-close; failed delivery and its retries remain visible.

## 11. B09 — Dashboard data, reports and audit verification

PRD references: §§7.2, 9.2, 11, BR-18/20, 13.4–13.5, 15, 17.4–17.5.

- [ ] Derive role/scoped dashboard data from authoritative records: region/stage/institution/type/officer/committee aggregations, pending/overdue/completed/blocked work, workload/backlog, EVC/report status, conditions and renewals.
- [ ] Implement §7.2 measures: application age, active-stage age, time remaining, overdue duration, stage pendency, EVC lead time, evidence verification time, delivery rate with stated outcome denominator and closure duration using its configured start.
- [ ] Include source drill-down, freshness and integration-delay information. Obtain official metric definitions before using them for performance assessment.
- [ ] Use the same status/deadline/permission definitions for dashboards, live records and reports. Do not create a separate set of contradictory totals.
- [ ] Register and generate **all eight mandatory reports** with the §11.1 fields, filters and typical authorised audiences:

| Report | Required filter dimensions |
| --- | --- |
| Region-wise performance | Date range, region, application type, institution type |
| Application pendency | Region, stage, age band, officer, status |
| EVC status | Region, coordinator, date range, status |
| Undertaking compliance | Region, condition type, status, due period |
| Document validity | Document type, region, expiry window, status |
| Overdue actions | Region, role, action type, overdue range |
| Notification delivery | Date range, channel, event type, delivery status |
| Case closure | Region, closure date range, application type, closure outcome |

- [ ] Define reporting time bases consistently with the report's underlying fields; retain reporting period, filters, generation timestamp and freshness. State live-query versus point-in-time snapshot semantics.
- [ ] Generate CSV/Excel and PDF summaries where required; make large runs asynchronous with status/failure/retry, authorised scheduled distribution, expiring links and temporary-file cleanup.
- [ ] Recheck role/scope for run visibility and actual download. Audit sensitive exports and avoid unnecessary personal data.
- [ ] Implement authorised audit search/detail and canonical selected-record/version fingerprint verification. Protect source records and version references; local illustrative hashes are not authoritative verification.
- [ ] If optional anchoring is enabled, compare recomputed canonical hashes with the anchored value and show mismatch/reference/status without placing sensitive content on-chain.

**Gate:** all eight filtered downloads reconcile against known records and permitted scope; dashboard totals agree; unauthorised file/report/audit access fails; selected-version verification detects modification.

## 12. B10 — Integration contracts

PRD references: §§4.2, 10.5, 16, 18, 21.

- [ ] Discover which approved systems own institution identifiers, applications and each authoritative field; document allowed import/export/bidirectional operations and authentication/data-sharing rules.
- [ ] Support idempotent import/update reconciliation, duplicate handling, job/error evidence and recovery for authorised institution/application exchanges.
- [ ] Until external interfaces are confirmed, use mock connectors or controlled sample imports, as §16.1 allows. Do not invent existing AICTE endpoints.
- [ ] Implement interchangeable email/SMS adapters and approved calendar interfaces with freshness/failure evidence. Retain controlled availability entry when API access is unavailable.
- [ ] Integrate issuer/registry checks only where a legitimate approved interface exists; keep extraction/field comparison distinct from issuer verification.
- [ ] Allow integration failure/retry without bypassing workflow validation or corrupting statutory state.

**Gate:** field ownership, duplicates, failures, retries and stale availability are explicit; mocks cannot be mistaken for actual delivery/official synchronisation.

## 13. B11 — Operational and acceptance gates

PRD references: §§8.4, 13–15, 17–20.

- [ ] Package the backend/workers for Docker deployment and approved hosting; protect secret references, transport, stored data, audit records and encryption keys.
- [ ] Expose authorised operational job/integration views and monitor API latency/errors, queues, OCR, calendar sync, notification delivery and database health using the proposed monitoring stack.
- [ ] Apply policy-driven retention, archival and deletion without breaking required history/foreign keys. Expire temporary export files and links.
- [ ] Complete unit, database integration and regression tests for configured routes/guards; include duplicate requests, concurrent edits, concurrent scheduling, worker/service recovery and timezone boundaries.
- [ ] Test all §17 cases: workflow/history, committee/availability/drafts, evidence/expiry/OCR, delivery/reports and access/files/audit/secrets/backup restoration.
- [ ] Complete threat modelling, dependency scanning and security tests before production. Verify 100% designated sensitive actions have traceable audit events.
- [ ] Validate realistic read/search/dashboard, submission/upload, OCR, notification/scanner bursts, scheduling, export and delayed-integration workloads against agreed figures.
- [ ] Treat p95 common-read <500 ms, 99.5% monthly availability, RPO 15 minutes and RTO 4 hours as **provisional PRD planning targets**, not measured results or approved service promises.
- [ ] Test encrypted backup restoration and document incident/recovery procedures, including separate audit/key protection.
- [ ] Check integrated key journeys against the PRD's WCAG 2.1 AA target and formal validation boundary. Backend errors/contracts must support accessible recovery in the frontend.

### One coherent §20 acceptance journey

Use controlled fictional records and trace one case and its linked entities. These are acceptance steps, not permission to replace the existing database with test data. Keep test effects isolated from real operational records.

- [ ] 1. Authorised institution opens an application.
- [ ] 2. Link institution profile and validate required document metadata.
- [ ] 3. OCR flags a type/lease-expiry inconsistency.
- [ ] 4. Route into the prescribed scrutiny stage.
- [ ] 5. Officer issues a reasoned deficiency.
- [ ] 6. Institution corrects information, preserving a new version.
- [ ] 7. Activate the required EVC work item.
- [ ] 8. Authorised officer selects the configured 4–5 experts.
- [ ] 9. Check those exact experts and institution availability.
- [ ] 10. Show conflicts, feasible alternatives and explanations.
- [ ] 11. Revalidate/confirm the slot and issue recorded invitations.
- [ ] 12. Generate source-linked draft minutes, observations, actions and report.
- [ ] 13. Reviewer edits and approves the record.
- [ ] 14. Create an undertaking, submit evidence and verify it.
- [ ] 15. Approaching expiry triggers a renewal alert.
- [ ] 16. A missed test deadline triggers escalation and delivery history.
- [ ] 17. Dashboards expose pendency, EVC, compliance, overdue and closure state.
- [ ] 18. Generate/download all eight report categories under authorised roles.
- [ ] 19. Inspect actor/action/timestamp and linked audit history.
- [ ] 20. **Conditional:** if ledger enabled, modify a sample and demonstrate fingerprint mismatch. If disabled, record this conditional step as not applicable; do not claim anchored verification.

Keep API/database/worker and integrated browser evidence for this journey. Separate seeded rows or isolated passing tests do not prove that the complete event-driven scenario executed.

## 14. Contract gaps inside the PRD

The PRD has **90 proposed method/path operations in §9.2**. Other sections describe required behaviours without complete HTTP contracts. Preserve those requirements and resolve contract details before implementation; do not silently drop them or label invented URLs as PRD endpoints.

| Required behaviour | PRD basis | Contract detail still to specify |
| --- | --- | --- |
| Dashboard aggregates/drill-down | §7.2 | Request/response resources, filters and time/metric representation; no dashboard URL is listed. |
| Institution typed attributes, verification and campus updates | §5.2 | Field permissions/catalogue representation and update/verification contract beyond listed profile/campus operations. |
| Formal decisions and controlled case cancellation/reopen/migration | §§5.3, 7.1, BR-24 | Whether/how represented by listed transitions or separate operations; WF-10 remains Should scope. |
| Required document catalogue/rules and version file downloads | §§5.4, 7.5, 13.2 | Metadata/configuration representation and independent authorised download contract; `/documents/{id}` is metadata. |
| Institution availability, invitation response and visit cancellation | §§5.5, 7.3 | How these behaviours are exposed alongside listed expert availability and visit operations. |
| Action-item lifecycle and approved-version corrections/history | §§5.5, 7.3 | Version-selection/correction and action completion contracts beyond listed draft/review endpoints. |
| Renewal submission, verification and completion | §§5.6, 7.5 | Only opening a renewal case is explicitly listed in §9.2. Define remaining lifecycle without assuming upload alone completes it. |
| Workflow draft edits, other rule catalogues and publication details | §§5.3–5.7, 7.1, BR-21 | Payload/edit/effectivity/approval semantics beyond listed create/validate/publish and rule operations. |
| Delivery callbacks, scheduled exports and integration imports/retries | §§8, 11.2, 16 | Provider/internal-worker contracts and authorised configuration/status/retry handling; public routes are not specified. |
| Retention execution and operational controls | §§8.4, 13.6, 15 | Worker/administrative contracts; no additional public endpoint is assumed. |

Resolve these using the corresponding PRD behaviour and approved policy decisions. They are specification handoff items, not additional feature proposals. The existing frontend's URL layout does not settle backend API contracts.

## 15. Open policy and provider decisions

PRD references: §§2.3, 14, 16, 21.

Keep these unresolved until the authorised owner supplies the values. Prototype fixtures can be clearly labelled sample configuration, not official policy.

- [ ] Applicable APH version, exact routes/guards/deadlines and official categories/identifiers.
- [ ] Committee composition, scheduling timezone/deadline, availability method and approved calendar/meeting providers.
- [ ] Scrutiny/EVC templates and sign-off/decision authorities.
- [ ] Document requirements, expiry rules, notification channels/templates and official report/metric definitions.
- [ ] Existing-system API access, field ownership and reconciliation policy.
- [ ] Approved hosting/identity requirements, record/transcript retention and actual workload/service levels.
- [ ] Whether cross-organisation ledger governance justifies optional anchoring.

The PRD's prototype/pilot/rollout estimates remain indicative (§18); this plan does not promise a new delivery date or assume that approvals already exist.

## 16. Explicit scope exclusions

PRD references: §§2.2, 7.3, 13.5, 16.

No automatic statutory approval/rejection, automatic expert selection/replacement, student application flows, unapproved replacement of the existing AICTE portal, unauthorised external integrations, assumed universal calendar access, universal document expiry, OCR-as-authenticity verification or mandatory production blockchain is included.

## 17. Business-rule traceability

All 24 rules in §12 apply across the implementation, rather than being optional UI checks. This table identifies their primary implementation and acceptance owners.

| PRD rules | Backend package | Required evidence |
| --- | --- | --- |
| BR-01–03 | B03/B05 | Valid institution/type, applicable approved workflow, permitted transition and passing guards. |
| BR-04–05 | B02/B05/B07 | Authority for returns/decisions/approval, required reasons and preserved submissions. |
| BR-06 | B05/B06 | EVC activated only when the applicable route/rules require it. |
| BR-07–08 | B06 | Authorised human committee selection and scheduling against those exact active members. |
| BR-09–11 | B06/B08 | Mandatory availability checks, confirmation revalidation and no-slot risk/escalation without overrides. |
| BR-12–13 | B07 | Generated records remain drafts until authorised approval. |
| BR-14–15 | B08 | Evidence upload cannot fulfil a condition; renewal requires configured verification. |
| BR-16–17 | B04 | Immutable document versions; uncertain OCR requires review and cannot independently reject a case. |
| BR-18 | B02/all mutation packages | Every designated sensitive workflow action has a protected, traceable audit event. |
| BR-19 | B08 | Logical notification, provider delivery evidence and retry attempts remain distinct. |
| BR-20 | B02/B09 | Actual report downloads enforce role and data scope. |
| BR-21 | B03 | Configuration publication/changes are versioned, approved and auditable. |
| BR-22 | Conditional ledger/B02 | Ledger unavailable/disabled never blocks normal workflow. |
| BR-23 | B03/B05 | Existing cases retain their original rule references unless migration is approved. |
| BR-24 | B05 | Closure requires configured authority and retains case history. |

## 18. Exact proposed API inventory — §9.2

All paths below are relative to **`/api/v1`**. This appendix reproduces the PRD's method/path inventory and purposes. These are proposed internal platform contracts, not existing external AICTE APIs. All operations need server-side authorisation/input validation and sensitive-action audit handling. Optional anchoring semantics remain conditional even though its status operation appears in the inventory.

### Identity and user scope

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/me` | Current user profile and authorised scopes |
| GET | `/me/permissions` | Effective permissions |
| GET | `/users` | Search users within permitted scope |
| POST | `/users/{id}/role-assignments` | Grant a scoped role, subject to permission |
| PATCH | `/users/{id}/role-assignments/{assignmentId}` | Change or revoke role assignment |

### Institutions and profiles

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/institutions` | Search authorised institution records |
| POST | `/institutions` | Create institution record, if permitted |
| GET | `/institutions/{id}` | Read institution profile |
| PATCH | `/institutions/{id}` | Update permitted fields |
| GET | `/institutions/{id}/campuses` | List campuses |
| POST | `/institutions/{id}/campuses` | Add campus |
| GET | `/institutions/{id}/documents` | List authorised document records |
| GET | `/institutions/{id}/applications` | List applications for the institution |

### Applications and workflow

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| POST | `/applications` | Create a draft application |
| GET | `/applications` | Search authorised applications |
| GET | `/applications/{id}` | Retrieve case summary |
| PATCH | `/applications/{id}` | Update permitted draft fields |
| POST | `/applications/{id}/submit` | Submit application |
| GET | `/applications/{id}/workflow` | Read workflow path and current stage |
| GET | `/applications/{id}/history` | Read authorised case history |
| POST | `/applications/{id}/transitions` | Request a permitted transition |
| POST | `/applications/{id}/assignments` | Assign case or task |
| POST | `/applications/{id}/deficiency-notices` | Issue authorised deficiency notice |
| POST | `/deficiency-notices/{id}/responses` | Submit institutional response |
| POST | `/deficiency-items/{id}/resolve` | Record authorised resolution |

### Documents and OCR

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| POST | `/documents/upload-sessions` | Obtain a controlled upload session |
| POST | `/documents` | Register document metadata |
| GET | `/documents/{id}` | Retrieve document metadata |
| GET | `/documents/{id}/versions` | List document versions |
| POST | `/documents/{id}/versions` | Add a new version |
| POST | `/document-versions/{id}/ocr-checks` | Queue OCR and validation |
| GET | `/document-versions/{id}/checks` | Read OCR and validation outcomes |
| POST | `/document-check-results/{id}/review` | Record authorised review |
| POST | `/document-renewal-cases` | Open a renewal case |

### EVC and scheduling

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/evc-visits` | Search EVC queue |
| POST | `/applications/{id}/evc-visits` | Create an EVC work item if required |
| GET | `/evc-visits/{id}` | Read visit details |
| PUT | `/evc-visits/{id}/committee-members` | Record authorised committee selection |
| POST | `/evc-visits/{id}/availability-requests` | Request availability from selected experts |
| POST | `/experts/{id}/availability` | Submit availability |
| GET | `/experts/{id}/availability` | Read permitted availability |
| POST | `/evc-visits/{id}/slot-recommendations` | Generate feasible slot recommendations |
| GET | `/evc-visits/{id}/slot-recommendations` | List recommendations |
| POST | `/evc-visits/{id}/confirm-schedule` | Confirm a recommended slot |
| POST | `/evc-visits/{id}/reschedule` | Request authorised rescheduling |
| POST | `/evc-visits/{id}/postpone` | Record postponement |
| POST | `/evc-visits/{id}/complete` | Record visit completion |
| GET | `/evc-visits/{id}/events` | Read visit history |
| POST | `/evc-visits/{id}/invitations` | Send or resend invitations |

### EVC reports and meeting records

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| POST | `/evc-visits/{id}/observations` | Record authorised observations |
| POST | `/evc-visits/{id}/meeting-record-drafts` | Generate a draft from authorised inputs |
| GET | `/meeting-records/{id}` | Read draft or approved record |
| PATCH | `/meeting-records/{id}` | Edit draft, subject to permissions |
| POST | `/meeting-records/{id}/submit-review` | Submit draft for committee review |
| POST | `/meeting-records/{id}/approve` | Approve a record |
| POST | `/meeting-records/{id}/request-changes` | Return draft with review comments |
| GET | `/meeting-records/{id}/sources` | Inspect source references where permitted |

### Undertakings and evidence

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/compliance-conditions` | Search conditions |
| POST | `/applications/{id}/compliance-conditions` | Create a condition |
| GET | `/compliance-conditions/{id}` | Read condition |
| POST | `/compliance-conditions/{id}/evidence-submissions` | Submit evidence |
| GET | `/evidence-submissions/{id}` | Read submission |
| POST | `/evidence-submissions/{id}/verification` | Record authorised verification |
| POST | `/compliance-conditions/{id}/close` | Close condition where permitted |
| POST | `/compliance-conditions/{id}/reopen` | Reopen with reason and authorisation |

### Notifications and escalations

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/notifications` | List notifications in scope |
| GET | `/notifications/{id}` | Read notification status |
| POST | `/notifications/{id}/retry` | Retry failed delivery if permitted |
| GET | `/notifications/{id}/attempts` | Read delivery attempts |
| GET | `/escalations` | Search active and historical escalations |
| POST | `/escalations/{id}/resolve` | Record authorised resolution |

### Reports and audit

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/reports` | List available report definitions |
| POST | `/report-runs` | Generate report |
| GET | `/report-runs/{id}` | Read report status |
| GET | `/report-runs/{id}/download` | Download authorised output |
| GET | `/audit-events` | Search authorised audit records |
| GET | `/audit-events/{id}` | Read audit event |
| POST | `/audit-verifications` | Verify a record fingerprint |
| GET | `/audit-anchors` | Read authorised ledger anchoring status |

### Configuration and integrations

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/admin/workflow-definitions` | List configured workflows |
| POST | `/admin/workflow-definitions` | Create a draft workflow definition |
| POST | `/admin/workflow-definitions/{id}/validate` | Validate workflow configuration |
| POST | `/admin/workflow-definitions/{id}/publish` | Publish an approved version |
| GET | `/admin/notification-rules` | List notification rules |
| POST | `/admin/notification-rules` | Create or update a draft rule |
| GET | `/admin/escalation-rules` | List escalation rules |
| POST | `/admin/escalation-rules` | Create or update a draft rule |
| GET | `/admin/integrations` | List approved integration configurations |
| POST | `/admin/integrations/{id}/test` | Test authorised integration connectivity |
| GET | `/admin/jobs` | Read job status and failures |

**Inventory check:** 90 method/path operations; all copied from PRD §9.2. No additional endpoint paths are introduced by this plan.

