# Final PRD completion plan

**Project:** AICTE Approval Workflow Automation and Institutional Compliance Monitoring Platform  
**Plan date:** 29 October 2026  
**Status:** execution backlog; completion has not been claimed  
**Authority:** `Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md`, v1.0, sections 1-22  
**Scope:** all five modules, shared services, Must and Should requirements, applicable integrations, security, operations, pilot acceptance and rollout readiness.

This is the consolidated execution plan replacing the competing seven-phase and nine-section completion narratives. The PRD remains the product authority. Existing code is reused only after its behavior passes the relevant acceptance gate. A page, endpoint, table, unit-test count, or successful build does not establish a finished workflow.

Planning policy: `planning=deep; context_depth=dependency; verification_depth=impact; delegation=none`. This deliverable creates a plan, requirement inventories and manual OCR test artifacts. It does not apply application fixes, database migrations, grants or provider configuration.

## 1. Completion contract

### 1.1 What "finished" means

The release is complete only when every applicable PRD requirement has an implementation reference, an executable acceptance check, fresh evidence from the release candidate, and an accountable acceptance owner. Every supported portal action must read or change authoritative persisted records and behave correctly after refresh, sign-out/sign-in, retry and concurrent access.

- Implement every PRD Must requirement and the requested Should behavior, including controlled cancellation, reopening and migration of active cases.
- Include institution profiles, workflows, all ten role dashboards, EVC, meeting records, compliance, documents, OCR, reminders, escalations, all eight reports, administration, integrations and operations.
- Exercise all 54 planned page templates, all ten role views and every API operation. Reconcile page counts with the actual route inventory instead of equating the 59 generated build entries with 59 independently verified workflows.
- Use Supabase authentication for actual accounts. Preserve the existing one-click persona entry points only as explicitly enabled development/evaluation sessions against persisted, scoped test records. Disable that issuer in production. A persona token is not a Supabase-authenticated account.
- Keep all business authorization on the server and in appropriate database policies. Client role selection is a view preference, never an authorization source.
- Pass the PRD section 20 journey and all sections 17.1-17.5 acceptance checks using actual browser actions, live API calls, persisted files, running workers and real integration outcomes where the integration is required.
- Record unresolved defects as open. Do not close a requirement because a mock, happy-path test or alternative screen exists.

### 1.2 No simulated operational success

Production request paths must not import business fixtures, apply local-only business reducers, substitute canned extraction text, manufacture confidence, fabricate issuer verification, declare an uncontacted provider connected, or mark local log output delivered.

Unit tests may use controlled fixtures and provider doubles to inject failures. Such tests establish algorithm behavior only. They cannot provide acceptance evidence for actual OCR, delivery, external connectivity, restored backups or a complete live journey.

Development seed data must stay labelled and segregated from authorized institutional records. The existing 180-institution dataset is synthetic; being stored in Supabase does not make it official government data. Production data onboarding requires a permitted source, validation, reconciliation, provenance and an approved import process. Do not delete the current seed during this work without an explicit, recoverable data migration decision.

### 1.3 Conditional scope is explicit

The PRD permits authenticated, confirmed manual availability. A real human-entered interval with source, freshness and audit evidence is a supported workflow, not a fake calendar API.

The PRD makes blockchain optional and conditions government-system, issuer and calendar integrations on approved interfaces. For each conditional feature, maintain an architecture/policy decision recording whether it is enabled and why. If enabled, implement and verify the real integration. If not applicable under the PRD, record the approved exclusion. Do not silently convert a missing mandatory feature to "optional".

DigiLocker/NAD, Aadhaar e-Sign, HSMs, Zoom/Teams/Meet and arbitrary COI rules are not automatic requirements merely because a progress report mentioned them. Implement them only when the PRD or a separately approved requirement actually calls for them. Do not invent statutory deadlines, registered DLT template IDs, institutional authority, signature policy or official APH rules.

External credentials, consent, provider registration, official rule sign-off and pilot acceptance are real dependencies. Missing dependencies remain **BLOCKED**, not **DONE**. Software scaffolding alone cannot make a production integration complete.

## 2. Starting evidence and immediate defects

The 29 October audit independently ran 180 backend tests, 28 frontend tests, TypeScript and the production build successfully. These are a regression baseline, not end-to-end certification. The read-only database inventory found 70 public tables with RLS enabled, 180 institutions, 1,088 applications, 2,161 documents, 163 EVC visits, 217 conditions, five expert profiles and five committee memberships. Counts can change and must be regenerated for the release candidate.

The generated inventory indexes **852 PRD source clauses** and **90 proposed API operations**. Of those API contracts, **55 currently have an exact method/path match** after parameter-name normalization. The other 35 need implementation or an explicitly approved equivalent mapping; this does not mean there are exactly 35 missing features. All generated acceptance statuses remain unassessed.

| Finding | Observed problem | Required correction | Work package |
| --- | --- | --- | --- |
| A01 | All eight live report definitions have placeholder metadata and zero usable column definitions | Version and validate actual column/filter contracts; render meaningful tables and exports | CP10 |
| A02 | Availability commands require `supersedes_id`/`superseded_at`, absent from the live schema | Apply a reviewed additive migration in a controlled maintenance sequence; verify both expert and institution correction paths | CP00, CP06 |
| A03 | No native Tesseract was detected; PNG metadata is read as "OCR" and confidence is manufactured | Install and health-check an actual engine; distinguish metadata/text-layer extraction from image recognition | CP05 |
| A04 | Local email/SMS logs report `delivered`; SMTP acceptance is also labelled delivered | Model simulation, acceptance and delivery separately; require provider evidence for delivery | CP09 |
| A05 | A reproduced provider failure is acknowledged as a processed event without delivery retry | Persist retryable delivery jobs/attempts and verify restart, outage and deduplication behavior | CP09 |
| A06 | Many writer policies use `USING (true)`; role grants check duplicates but not incompatible roles | Review least privilege and enforce approved permission, scope and conflict rules on every path | CP01 |
| A07 | Audit verifier validates individual digests without checking consecutive chain links | Define serialized chain semantics and validate linkage, missing events, branches and tampering | CP02 |
| A08 | Claimed state/alma-mater/history COI screening is not established by the EVC implementation | Remove unsupported claims; implement approved eligibility/composition/COI requirements and tests | CP06 |
| A09 | Several typed policy editors return "dedicated endpoint needed"; operational actions remain unsupported | Implement typed backend contracts and connect every permitted UI action | CP03, CP11 |
| A10 | Documentation describes a local demo provider even though the provider now fetches live snapshots | Reconcile documentation against actual final behavior and evidence | CP14 |
| A11 | The OCR/communications verification script is described as the entire lifecycle | Add full browser/API/persistence/failure-path journeys; keep narrow tests narrowly named | CP12 |
| A12 | Broad snapshot hydration and periodic polling are described as "real time" without measured latency | Publish freshness semantics, paginate/cache safely and prove agreed performance | CP10, CP13 |

Do not run schema changes concurrently with long verification transactions. The earlier metadata migration encountered a database deadlock and did not establish a successfully applied schema. A SQL file on disk is not evidence that a migration ran.

## 3. Traceability and execution records

Supporting inventories are generated from the exact PRD source:

- `completion/PRD_REQUIREMENT_LEDGER.json`: source-line clauses, original WF/BR identifiers where present, owner package, status, evidence fields and PRD source hash.
- `completion/PRD_API_COVERAGE.json`: every proposed PRD section 9.2 method/path, current OpenAPI presence, required compatibility decision and acceptance status.
- `completion/README.md`: inventory generation and maintenance rules.

Generated inventories are deliberately initialized **UNASSESSED**. Existing tests are not automatically attached as proof. Review every generated clause for atomicity; split combined obligations while retaining its source reference. Include normative paragraphs, the entity tables, metrics, NFRs, retention, integrations and section 21 decisions; do not track only WF-01 through WF-10.

Each requirement record must ultimately contain:

`requirement_id; PRD section/source lines; exact obligation; priority; conditional applicability; owner; implementation files/API/page; migration/config dependencies; acceptance test; negative/failure checks; observed evidence; release revision; reviewer; status`.

Allowed statuses: `UNASSESSED`, `PLANNED`, `IMPLEMENTING`, `READY_FOR_TEST`, `PASS`, `FAIL`, `BLOCKED`, `NOT_APPLICABLE_APPROVED`. Only fresh `PASS` or a justified approved conditional exclusion closes a record. No status may be inferred from a phase heading.

An implementation evidence bundle must include the tested revision, environment, sanitized migration version, command/result, test case, expected/actual outcome and relevant record IDs. Keep tokens, provider secrets and private document contents out of the bundle.

## 4. Delivery sequence and dependencies

| Order | Package | Depends on | Exit gate |
| --- | --- | --- | --- |
| 0 | CP00: establish a reproducible schema and baseline | Existing repository/database | Migrations and code match; drift check passes; backups and repair procedure exist |
| 1 | CP01: identity, permission and scope enforcement | CP00; approved access policy | All ten role/action/scope allow-deny matrices pass |
| 2 | CP02: transaction, concurrency, idempotency and audit | CP00-01 | Atomic rollback/replay/race and chain-integrity tests pass |
| 3 | CP03: typed master data and versioned configuration | CP00-02; approved policy inputs | Every catalogue has real draft/validate/publish/version behavior |
| 4 | CP04: application workflow and deficiency lifecycle | CP01-03 | Both prescribed route families and controlled lifecycle changes pass |
| 5 | CP05: private files, actual OCR and human document review | CP01-03 | Clean and unsafe file paths plus true image OCR pass |
| 6 | CP06: exact-committee scheduling and visit lifecycle | CP02-05; composition rules | Freshness, no-slot, races and complete lifecycle pass |
| 7 | CP07: source-linked meeting records | CP04-06; approved templates/sign-off | Draft-to-review-to-approved correction history passes |
| 8 | CP08: compliance, expiry, renewal and escalation rules | CP04-07 | Evidence verification and renewal closure pass without state loss |
| 9 | CP09: durable jobs and real communications | CP02-03; approved providers | Outage/restart/retry/receipt tests pass; no false delivery |
| 10 | CP10: one metric/report contract and live dashboards | Authoritative CP04-09 records | All ten dashboards and eight reports reconcile |
| 11 | CP11: complete portal, public pages and administration | Each owning API package | Every page/action has validated live behavior and accessible states |
| 12 | CP12: integrated acceptance and adversarial regression | CP00-11 | PRD section 20 plus sections 17.1-17.5 pass |
| 13 | CP13: deployment, observability, recovery and capacity | CP00-12; infrastructure decisions | Operational, restore, load and security gates pass |
| 14 | CP14: acceptance, documentation and release closure | All preceding gates | No unresolved applicable requirement, defect or false completion claim |

CP05 and CP09 can be developed alongside CP04 after their shared foundations are verified. CP10 may build contracts early but cannot pass reconciliation against invented or stale module data. Integrate the relevant UI with each package; CP11 is the final sweep, not permission to postpone UI wiring until the end.

## CP00. Reproducible schema, environments and migration safety

**PRD:** sections 4-6, 10, 13.6, 14-15. **Primary owners:** backend/database engineer and release operator.

- [ ] Inventory the actual database: columns, types, defaults, statuses, foreign keys, indexes, triggers, functions, policies, grants, object ownership and installed migration versions. Reconcile all 65 PRD logical entities and supplemental infrastructure.
- [ ] Introduce an ordered migration ledger with checksums and transactional application where supported. Record what actually ran; never infer installation from the presence of a numbered file.
- [ ] Reconcile migrations 010-015 and any later changes, including original versus submitted renewal versions, availability supersession fields, document issuer/reference fields and reader restrictions. Resolve duplicate numbering or overlapping migrations before applying them.
- [ ] Add an application startup/readiness check that rejects incompatible schema versions with a useful operator message rather than permitting a form to fail with a generic 500.
- [ ] Separate local development, controlled acceptance and production configuration. Supply validated environment examples for web, API, worker, database runtime roles, object storage, OCR, scanner and providers.
- [ ] Take a recoverable backup before shared-schema changes. Use bounded lock/statement timeouts, a migration window and a reviewed rollback/forward-repair procedure. Test migration from the current database and from an empty supported environment.
- [ ] Keep migration/owner credentials out of HTTP handlers and workers. Never fall back from a runtime credential to an owner credential when configuration is absent.
- [ ] Reconcile malformed/partial seed metadata through a labelled, idempotent maintenance script. Preserve history, retain audit evidence and produce before/after counts.
- [ ] Add schema drift validation to CI and deployment. Confirm both the application and worker use a compatible schema before accepting work.

**Gate:** a fresh supported environment and an upgraded copy of the existing database reach the same schema; availability correction SQL and document metadata writes compile against both; interrupted/contended migration behavior is demonstrated safely.

## CP01. Supabase identity, scoped permissions and separation of duties

**PRD:** sections 3, 5.2, 9.2, 13.1; BR-04, BR-07, BR-13, BR-20. **Primary owner:** access/security engineer; policy owner approves the matrix.

- [ ] Approve a versioned matrix for the ten personas and service identities: action, entity, scope, grant authority, expiry, conflict pairs, sign-off authority and revocation behavior. Map region inheritance, assigned scrutiny cases, institution/campus membership and exact EVC membership explicitly.
- [ ] Preserve Supabase token issuer/audience/signature/session validation, refresh and logout. Test disabled, expired, revoked, unlinked and malformed identities. Enforce stronger authentication for privileged operations when the approved policy requires it.
- [ ] Preserve demo entry points in development only. Prove that production refuses demo-token issuance and acceptance. Synthetic identities and grants must not acquire access to official records.
- [ ] Centralize effective permission resolution. Replace scattered role-label shortcuts with approved action permissions and record-scope predicates. Recheck permissions on mutation, history, upload, download, export, retry, job operation and configuration publication.
- [ ] Enforce incompatible-role and overlapping-assignment rules in every grant path, including `/users/.../role-assignments` and `/portal/commands`. A duplicate-role check is insufficient. Race-test simultaneous grants.
- [ ] Review and replace permissive writer policies where record isolation is required. Use explicit transaction-local identity and least-privilege table/function grants; test policies with the actual reader, writer and worker connections. RLS being enabled is not itself scope enforcement.
- [ ] Protect user directories, expert availability, source transcripts and notification recipient details from unrelated callers. Do not return confidential collections and rely on the browser to hide them.
- [ ] Enforce assigned-case-only scrutiny and exact-committee expert access. Check role/scope combinations independently and test scope switching without stale cache leakage.
- [ ] Verify role administration cannot disable the last required administrator, self-escalate, grant outside the actor's authority or retain access through a frozen export after revocation.

**Gate:** exhaustive positive and negative tests for every persona/action/scope combination, direct SQL isolation checks, live authenticated API checks and browser scope-switch tests pass. The original read-only viewer remains read-only.

## CP02. Atomic writes, retries, concurrency and a verifiable audit chain

**PRD:** sections 8.2, 9.1, 10, 13.4-13.5; WF-09; BR-09/10/18/19/23/24.

- [ ] Inventory every sensitive command and its state, version, history, audit and outbox effects. Commit them in one transaction. Keep slow external network calls outside business transactions.
- [ ] Validate request hashes, actor isolation, expiry, same-key replay, changed-body conflict and concurrent requests. Serialize replay payloads consistently, including UUID/date/decimal fields. Recheck authorization before replaying a cached response.
- [ ] Preserve a retry key across network retries of one user intent. Do not mint a new key for each automatic retry and then claim duplicate prevention. Do not leave one key reusable for different edits.
- [ ] Apply version checks or locks to all mutable resources, including assignments, configurations, conditions, visits, invitations and record versions. Return 412 for stale edits and 409 for current-state/booking conflicts, with actionable sanitized details.
- [ ] Make supplemental command handlers obey the same safety contract as named endpoints. A shared advisory lock is not a substitute for per-resource versions, database invariants or permission checks.
- [ ] Specify audit-chain scope and ordering. Serialize append operations within each chain, persist sequence/previous hash, and avoid concurrent branches or silent unchained inserts. Do not swallow audit read/write failures and commit unaudited business changes.
- [ ] Verify both canonical event digest and predecessor linkage. Detect modification, deletion, reordered entries, duplicate sequence, missing predecessor and two children of the same predecessor. Define a legitimate genesis/checkpoint process for existing unchained history without rewriting protected evidence.
- [ ] Preserve actor/service identity, old/new state, reasons, correlation and exact version references without logging secrets or full sensitive payloads. Enforce append-only privileges and triggers, including TRUNCATE protection.
- [ ] If blockchain is enabled by decision, implement real hashing/anchoring/status/verification/retry and a tamper test. Keep source data off-chain and prove ledger outage does not block processing. If disabled, record the approved PRD-optional decision and retain the mandatory audit guarantees.

**Gate:** forced failure at each write step leaves no partial business action; simultaneous retries produce one result; stale edits cannot overwrite new data; concurrent audit appends retain a valid chain; deliberate tampering is detected.

## CP03. Institution master data and typed versioned configuration

**PRD:** sections 5.2-5.4, 7.1, 9.2, 12, 15, 21; WF-01/02/08; BR-01/02/21/23.

- [ ] Complete institution creation, authorized profile editing, campuses, identifiers, region mapping, source provenance, typed attributes and verification. Validate unique identifiers and typed values on the server.
- [ ] Implement an approved attribute catalogue with required/applicable fields, data type, allowed values, scope, source document/version and verification state. Complete the F01 backlog item.
- [ ] Implement typed draft/edit/validate/compare/publish/retire contracts for application categories, APH rule sets/versions, workflows, document categories/requirements, committee policies, templates, notification rules, escalation rules and controlled settings.
- [ ] Remove generic "dedicated endpoint needed" gaps. Do not store an apparently published rule in an unrelated generic setting while execution continues reading an unchanged typed table.
- [ ] Define effective dates, approval authority, change reason, revision comparison and immutable published versions. Prevent publication of incomplete or mutually inconsistent configuration.
- [ ] Resolve workflow application type and APH version from explicit approved inputs. Never silently choose the first application category or newest unrelated APH record.
- [ ] Bind new cases to the applicable published version and preserve historical bindings. Bind visit composition/freshness/duration to the intended effective policy rather than the latest global committee row.
- [ ] Implement controlled institution/application import: column mapping, preview, typed validation, identifier matching, duplicates, conflicts, field ownership, partial-failure report and audited idempotent commit. Complete F13; imported official records require an authorized source.
- [ ] Replace hardcoded UI catalogue choices with authorized live reference data. Preserve reference version identifiers throughout forms, APIs and stored cases.

**Gate:** each catalogue can be drafted, rejected on invalid input, published by the correct authority and consumed by its owning module. A rule update changes only intended future work. Existing cases and exports retain their original meaning.

## CP04. Full application workflow, scrutiny and deficiency correction

**PRD:** sections 5.3, 7.1, 9.2-9.3, 10, 12, 17.1; WF-01 through WF-10.

- [ ] Create and edit complete application drafts, including academic year, institution/campus, category and required declarations. Check all applicable document requirements against exact versions before submission.
- [ ] Resolve the correct approved workflow by institution context, category and effective rule version. Support Only Scrutiny, EVC-containing and other approved configured routes.
- [ ] Execute the published graph and its allowed guards. Validate connectivity, terminal stages, allowed cycles/returns, stage ownership, SLA values and guard references before publication. Reject unsupported guards; do not silently ignore them.
- [ ] Transition atomically: current stage completion, next instance, current pointer, owner assignment, entered/due timestamps, history, audit and outbox. Preserve a stage instance history instead of replacing it with high-level status labels.
- [ ] Implement named workflow/history/assignment APIs or approved documented equivalents for every PRD inventory operation. Return permitted next actions and blocking reasons to the frontend.
- [ ] Add multiple deficiency items per notice, criteria, descriptions, linked document/version, response deadlines and reasoned issuance. Persist each item's narrative, response version and outcome independently.
- [ ] Support numbered resubmissions linked to the original notice and exact document versions; retain previous submissions. Resolve, reject or return individual items with reasons and re-enter the configured review stage.
- [ ] Enforce decision authority, required prior scrutiny/EVC approvals, condition completeness and explicit closure criteria. A browser button or application status alone must not bypass the configured route.
- [ ] Complete WF-10 for active cases: authorized cancellation, reopening and version migration with reason, stage mapping, outstanding-work reconciliation, history and concurrency protection. A draft-only migration is not fulfillment of in-progress migration.
- [ ] Keep high-level status, stage-instance status and next action consistent. Implement deterministic mapping to approved terms without inventing official terminology.

**Gate:** live browser/API journeys traverse both route families; a multi-item deficiency is partly answered, returned, corrected and resolved; exact historical versions survive; invalid or unauthorized transitions and repeat submissions leave no duplicate state.

## CP05. Private files, actual OCR and human document verification

**PRD:** sections 5.4, 7.5, 9.2, 13.2, 15, 16.4, 17.3/17.5; BR-15/16/17.

- [ ] Configure real private object storage with durable immutable keys/versioning, encryption, checksums, retention and independent authorization. Verify files survive process/container restart and authorized access from another browser/device. Local disk is acceptable only for an explicitly selected durable local deployment with backup/recovery; it must not masquerade as connected cloud storage.
- [ ] Complete upload sessions, streamed/multipart/resumable transfer where appropriate, metadata registration and version append. Enforce type, size, magic bytes, extension policy, safe file names, traversal protection, atomic finalize and orphan cleanup.
- [ ] Configure a real malware scanner. Quarantine unscanned/rejected content, record scan evidence and fail safely when scanning is unavailable. Use a known harmless antivirus test pattern in a controlled test; do not treat magic-byte validation as malware scanning.
- [ ] Install an actual Tesseract or approved OCR engine with pinned dependencies/language packs and a readiness probe. Read validated configuration consistently. Provide an honest unavailable/degraded state when it cannot execute.
- [ ] Distinguish image OCR, PDF text-layer extraction, embedded metadata and declared metadata. Set `ocr_performed` only when pixels were recognized. Never use PNG Description/EXIF, alt text, fixture answers or declared values as extracted visual evidence.
- [ ] Process every relevant PDF page and image region in reading order, with resolution, orientation, skew, contrast and language handling. Support PNG/JPEG, scanned PDFs, text PDFs and mixed PDFs. Bound pages/pixels/time/memory and handle corrupt/encrypted/unsupported files safely.
- [ ] Store engine/version, source file hash, processing parameters, page/field provenance, confidence where actually measured, start/end/error state and reprocessing history. Do not boost confidence just because a regex matched. Use null/unknown when the engine provides no meaningful confidence.
- [ ] Extract reference/certificate number, issuer, issue/expiry dates and relevant typed fields from actual source text. Normalize dates with explicit locale and ambiguity handling. Flag missing/mismatched/expired/unreadable values. OCR cannot establish document authenticity.
- [ ] Run OCR asynchronously on clean immutable versions. Persist job state and individual findings; allow authorized reprocessing and manual review with reasons. Human verification remains a separate controlled action.
- [ ] Make the OCR studio upload arbitrary permitted files, show engine/source mode, original preview, actual extracted text, per-field evidence and error/review states. Saving a check must persist its real source version and results.
- [ ] Add genuine held-out scanned samples without metadata answers, including the government certificate pack delivered with this plan. Evaluate recognition against human labels. Separate field extraction from recognizing validity periods that do not explicitly print an expiry date.

**Gate:** a newly uploaded PNG and image-only multi-page PDF with zero extractable text yield actual recognized content; native engine removal yields unavailable, never fabricated success; unsafe files stay quarantined; human review and immutable version history work through the portal.

## CP06. Exact-committee EVC scheduling and complete visit lifecycle

**PRD:** sections 5.5, 7.3 steps 1-8, 9.4-9.6, 10.3-10.4, 17.2; BR-06 through BR-11.

- [ ] Create EVC work only when the case's bound workflow requires it. Persist campus, readiness, deadline, coordinator, mandatory constraints and applicable composition/duration/freshness policy.
- [ ] Permit authorized officers to select/replace exactly the configured four or five eligible experts, with required composition, unique membership and reasoned changes. The scheduler must never choose or silently replace experts.
- [ ] Enforce applicable approved eligibility/COI checks where policy specifies them. Do not claim state/alma-mater/history screening without configured rules, source data and demonstrable rejection tests.
- [ ] Persist expert and institution availability with source, confirmation time, timezone, correction/supersession history and authorization. Ignore superseded intervals during scheduling while retaining history.
- [ ] Generate candidates from all exact selected experts plus the institution, required duration, busy blocks, confirmed bookings, preparation time, location/time constraints and deadline. Missing, stale or future-dated confirmation evidence cannot imply availability.
- [ ] Persist calculation version, membership snapshot, availability evidence, expiry, feasibility and explanations. Store failed/no-slot attempts, blocking constraints, nearby alternatives and deadline-risk escalation rather than only returning a transient message.
- [ ] Revalidate all constraints inside confirmation. Use a shared participant-booking invariant/locks and appropriate database exclusion/uniqueness protection across all API instances and all availability/membership mutation paths.
- [ ] Implement availability requests, invitations/resends, acknowledgement/decline, rescheduling, postponement, cancellation, reminders, completion and their event histories. Invalid transitions must fail consistently.
- [ ] Keep internal booking confirmation distinct from external calendar synchronization. Manual confirmation can be valid; unavailable provider sync must not say `SYNCED` or `SENT`.
- [ ] Permit completion only from an appropriate confirmed state and according to the approved visit timing/completion policy. Final report approval is a separate event.

**Gate:** all five experts and the institution are required; a correction/stale interval blocks a former proposal; two officers racing for the same participant/time produce one booking; no-slot and provider-outage paths remain visible and recoverable.

## CP07. Source-linked meeting records and human approval

**PRD:** sections 5.5, 7.3 step 9, 9.7, 13.3, 15, 17.2; BR-12/13/16/18.

- [ ] Implement separate minutes and EVC-report record types with approved template versions, criterion sections, unresolved questions and action items. Preserve their type through backend storage and frontend projection.
- [ ] Accept only authorized notes, structured observations and permitted transcript references. Store source IDs, author, permission, status and provenance. A draft observation is not automatically an approved source.
- [ ] Generate real source-linked draft sections without canned findings or invented conclusions. Flag absent, conflicting or unsupported input. Deterministic template assembly is acceptable if it actually consumes authorized records and is honestly described.
- [ ] Support edit/save, submit-review, request-changes, approve and reasoned correction versions through version-checked APIs. Validate source references belong to the same visit and are visible to the reviewer.
- [ ] Apply the approved sign-off roles/quorum. Freeze approved content and exact source versions. Corrections create a new reviewed version and retain the prior approved record.
- [ ] Link action items to observations, responsible roles, deadlines and completion evidence. Update outstanding-input dashboards and workflow guards from the same records.
- [ ] Protect source files/transcripts, signed artifacts where required, retention and downloads. Do not copy confidential source contents into ordinary audit or notification payloads.

**Gate:** a committee member creates an observation; a reviewer edits and approves a source-linked record; a subsequent correction retains the original version; missing sources and unauthorized approval are rejected.

## CP08. Compliance, renewal, reminders and escalation

**PRD:** sections 5.6, 7.4-7.5, 8.3-8.4, 15, 17.3; BR-14/15/16/24.

- [ ] Create conditions only from authorized applicable decisions; persist description, due date, requirements, institution, source decision and verification authority.
- [ ] Submit numbered evidence sets with exact immutable versions, narrative and links to clarification requests. Enforce ownership and prevent cross-case evidence substitution.
- [ ] Support review, clarification, compliant/non-compliant outcomes, explicit closure and authorized reopening with reasons and preserved history. Uploading evidence alone never fulfills a condition.
- [ ] Represent overdue without destroying the underlying evidence/review/clarification state. Scan every applicable active state, not a hardcoded subset that omits `OPEN` or `CLARIFICATION_REQUIRED`.
- [ ] Apply versioned per-category expiry rules and reminders. Non-expiring documents remain non-expiring. Store original/previous and submitted renewal versions separately.
- [ ] Prevent duplicate active renewal cases across all nonterminal states and concurrent scanners. Do not only check `status='open'` while ignoring submitted/under-review cases.
- [ ] Complete renewal only after applicable document/evidence verification and authorized decision. Validate newer version, category, institution, issue/expiry applicability and required source evidence.
- [ ] Implement durable reminder/escalation schedules, policy timezone, thresholds, repeat interval, recipient scope, maximum level, missed-window recovery, deduplication and reasoned resolution after the underlying issue is addressed.
- [ ] Do not invent an automated statutory penalty engine. If penalties are required by approved policy, model the explicit human-authorized decision and audit it; otherwise remove unsupported penalty claims.

**Gate:** an evidence clarification loop and negative outcome survive deadline crossing; an overdue renewal is submitted and verified without erasing the previous version; restart/concurrent scanning does not create duplicate cases or alerts.

## CP09. Durable background processing and real communications

**PRD:** sections 8, 10.5, 14, 16.3, 17.4; BR-18/19.

- [ ] Run a supervised, separately deployable worker/scheduler with actual queue/outbox consumption, job status, attempts, next retry, errors, heartbeat and recovery. Choose Redis/Celery or a justified equivalent; document the real deployed topology.
- [ ] Create logical notifications from configured events/rules with deterministic recipient/channel/template resolution. Business events without an already queued notification must not silently disappear.
- [ ] Commit leases before slow work and enforce lease renewal/ownership. Use durable consumer deduplication and provider idempotency where supported. Acknowledgement must mean the owning responsibility has been durably completed or handed to a persisted retrying delivery job.
- [ ] Use isolated transactions/savepoints for database failures. A failed SQL statement must not leave the whole transaction aborted and then attempt retry scheduling on that same failed transaction.
- [ ] Preserve delivery attempts and attempt numbering across retries. Handle transient failure, permanent rejection, timeout with unknown provider outcome, rate limiting, worker death before/after provider acceptance and duplicate callbacks.
- [ ] Configure actual approved SMTP/email and SMS adapters. Load credentials from the validated deployment configuration, not inconsistently from process environment while the rest of the app reads a dotenv file.
- [ ] Model `QUEUED`, `PROCESSING`, provider-accepted `SENT`, receipt-backed `DELIVERED`, `FAILED`, `RETRY_PENDING`, `CANCELLED` and `UNKNOWN` correctly. SMTP acceptance and HTTP 200 alone do not prove recipient delivery.
- [ ] Remove success-producing log fallbacks from operational paths. Unconfigured channels report unavailable/blocked; development simulations are explicitly separated and excluded from operational delivery KPIs.
- [ ] Obtain actual registered sender/entity/template identifiers if SMS is enabled. Parameterize approved deadline values and portal URLs; do not embed invented statutory "14 days", placeholder DLT identifiers or localhost links in real messages.
- [ ] Authenticate/verify provider callbacks, retain the actual provider message reference, mask recipient details in logs and store only necessary payloads.
- [ ] Expose retry/permanent-failure/dead-letter handling and operator resolution through real admin APIs and screens. Never let a "process job" button fabricate successful completion.

**Gate:** actual controlled recipients receive the expected messages when providers are configured; receipt status matches evidence; forced outages retry and become visible; process termination and restart do not lose work or corrupt histories. External test sends require authorized recipients.

## CP10. Authoritative dashboards and all eight reports

**PRD:** sections 7.2, 11, 14, 17.4; BR-20. **Owner:** backend analytics engineer with business/report owner.

- [ ] Repair all eight persisted report definitions: actual ordered columns, types, labels, filters, permissible roles/scopes, version and enabled status. Validate definitions against generated rows on publication and at acceptance.
- [ ] Use one versioned semantic contract for dashboard KPIs, drill-down lists, report previews and exports. Do not maintain diverging client formulas and unrelated broad SQL queries without reconciliation tests.
- [ ] Implement the PRD metric definitions for application/stage age, due/overdue time, stage pendency, scheduling lead time, verification time, delivery rate denominator and closure duration. Approve the official definitions.
- [ ] Give every report the correct date grain: intake/submission for case cohorts, visit dates for visit reports, due/verification dates for compliance, validity dates for documents, attempted/delivered dates for notifications and closure dates for closure reports. Display the grain and timezone.
- [ ] Preserve all applied dimensions, role/scope, query, column filters and period in the server request and frozen result. Do not silently discard filters or truncate a report at an arbitrary 200 rows.
- [ ] Generate actual immutable report outputs with timestamp, period, definition version, row count, source freshness and SHA-256 manifest. Download authorization rechecks current permissions and the captured data scope, not just original requester identity.
- [ ] Support required downloadable formats with genuine encoding and layout. Validate CSV escaping/formula injection, XLSX structure, PDF pagination/fonts, meaningful empty output and export expiry. Expired/deleted output has a recoverable state.
- [ ] Implement ten useful dashboard variants with the correct domain grain, scoped navigation, filters, cross-filter/highlight, drill-through, data inspection and meaningful error/empty/stale/loading states.
- [ ] Implement incremental/paginated authorized reads and safe reference caching. Scope caches by identity/permissions/version. Measure the current full-table snapshot cost and avoid downloading all confidential records merely to calculate a count.
- [ ] State actual freshness. Polling is polling; if push is selected, subscriptions must be scoped and revocation-aware. Refresh after committed changes and prevent older responses from overwriting newer state.

| Report | Minimum acceptance |
| --- | --- |
| Region-wise performance | Distinct cases/institutions and correct region mapping; no campus-join multiplication |
| Application pendency | Current stage, stage/application age, owner, due time and next action reconcile to case records |
| EVC status | Exact selected committee, proposal/confirmation, deadline, conflicts, visit and report states |
| Undertaking compliance | Due date, numbered evidence, latest verification, reviewer and escalation remain distinguishable |
| Document validity | Correct current version, type applicability, issue/expiry, verification and renewal state |
| Overdue actions | Every applicable outstanding task/condition/action, owner, duration, level and resolution |
| Notification delivery | Logical notification versus channel attempts; honest denominator and receipt-backed outcomes |
| Case closure | Actual closure, authority, reason, duration and reopening history; approval is not automatically closure |

**Gate:** each role's dashboard, contributing list, preview and frozen export agree on a known dataset; filters change the expected population; all eight reports have visible columns, real files, correct scope and no hidden row cap.

## CP11. Complete live portal, administration and public pages

**PRD:** sections 3, 7, 9, 13-14; existing P01-P54 and F01/F02/F03/F13/F14 inventories.

- [ ] Build a route/action inventory linking every page, drawer, button, form, filter, bulk action, download and navigation destination to its owning requirement and live API.
- [ ] Remove production imports of mock-data/mock-reports, browser-only business reducers, successful no-op actions and unimplemented permission-visible controls. Keep deterministic examples only in clearly separate tests/development tooling.
- [ ] Complete all forms against real catalogues and identifiers. Validate dependent institution/application/campus/version choices, timezone-aware dates, numeric/boolean values and required declarations on both client and server.
- [ ] Await actual persistence before success/navigation; prevent duplicate clicks; retain input on failure; surface actionable validation/conflict/stale/dependency errors. Restore current state after refresh or a new session.
- [ ] Finish typed profile attributes, workflow builder validation and execution, multi-item deficiency authoring, controlled import reconciliation and operational administration. Resolve all existing F-series backlog items with evidence, not by renaming them.
- [ ] Make OCR studio, file previews, check saving, human verification and renewal review usable on actual uploaded files. Do not navigate to an extraction ID where a check-result ID is required.
- [ ] Ensure all ten roles have appropriate navigation and actions. An auditor can inspect but cannot mutate; system administration does not itself grant statutory decisions.
- [ ] Verify role/scope switching, session expiry, revocation, focus refresh and polling do not leak stale data or falsely show successful changes. Restore deep links and reject external return destinations.
- [ ] Complete public help, accessibility, privacy/website policy content and sitemap with approved text and functioning destinations. Remove unsupported "official rules enforced" assertions and obsolete fixed demo timestamps.
- [ ] Complete responsive, keyboard, focus, screen-reader, contrast, reduced-motion and error-announcement behavior. Formal WCAG 2.1 AA testing and cross-browser coverage are acceptance work, not a visual-design claim.

**Gate:** every inventoried permitted control has a tested normal, forbidden, invalid-input, stale/concurrent and unavailable-dependency state as applicable. No core workflow depends on which browser originally uploaded or edited the record.

## CP12. Acceptance journeys and proof that the features work together

**PRD:** all section 17 checks and the complete section 20 scenario.

Use an isolated authorized acceptance environment with actual Supabase accounts, real database policies, actual stored files, native OCR, a running worker and approved provider test recipients. Development personas can be checked separately; they do not replace real identity-provider tests. Use uniquely labelled acceptance records and a documented cleanup/retention policy.

### Mandatory journeys

1. **Only Scrutiny:** authenticated institution -> complete profile and required files -> draft -> submit -> assigned scrutiny -> permitted transition -> authorized decision -> explicit closure -> reconciled reports/audit.
2. **Multi-item deficiency:** issue several items -> reject an unauthorized response -> partial response -> new document version -> return one item -> numbered resubmission -> reasoned item resolution -> guarded advance.
3. **Full EVC:** readiness -> officer selects four/five experts -> exact expert and institution availability -> stale/busy/no-slot explanations -> escalation -> corrected availability -> recommendation -> concurrent confirmation conflict -> invitations/acknowledgement -> completed visit.
4. **Meeting-to-record:** authorized observations -> missing/conflicting source flag -> draft minutes/report/actions -> human edit -> review -> approved immutable version -> reasoned correction version -> workflow progression.
5. **Compliance:** approved source decision -> due condition -> multiple evidence submissions -> clarification -> compliant and non-compliant outcomes -> explicit closure/reopening -> preserved underlying state after overdue scanning.
6. **Expiry/renewal:** expiring and non-expiring categories -> configured thresholds -> real reminder -> missed window recovery -> one active renewal -> newer immutable file -> manual verification -> completion with old version preserved.
7. **Real OCR:** government PNG, image-only PDF, searchable PDF, multiple pages, skew/low quality, mismatched declared metadata, corrupt and unsupported files -> actual extraction/provenance -> honest confidence/unavailable state -> human review.
8. **Communications failure:** accepted request, delivery receipt, transient outage, permanent rejection, timeout/unknown result, duplicate callback and worker restart -> durable attempts/retry/alerts and honest dashboard status.
9. **Reports:** all eight categories through every allowed role/scope/date grain -> visible nonempty and empty tables -> actual downloads -> immutable snapshot after source changes -> denied foreign/revoked access -> expiry behavior.
10. **Access and concurrency:** cross-institution, unrelated expert, unassigned scrutiny, disabled/revoked identity, incompatible grants, stale versions, double submit and simultaneous booking -> expected 401/403/404/409/412 with no partial effects.
11. **Audit integrity:** business action with complete audit/outbox -> concurrent appends -> deliberately modified/deleted/reordered verification fixture -> detected mismatch; ledger outage if enabled does not block processing.
12. **Recovery:** worker/API/object-store interruption, database restore, file restore, redeployment and resumed schedules -> consistent authorized state and documented measured recovery.

For every journey retain screenshots/video where useful, sanitized request/response evidence, source/created version IDs, database state checks, worker/provider evidence and expected-versus-actual totals. Browser screenshots supplement state assertions; they do not replace them.

### Test layers

- Unit/property tests for pure guards, state machines, interval algorithms, field parsing and metric definitions.
- Database integration tests against actual migrations, constraints, RLS roles, transactions, row versions and retry races.
- Contract tests for every PRD API method/path or approved compatibility mapping and every frontend command.
- Browser E2E tests for real persistence, forms, navigation, permissions, file handling and all mandatory journeys.
- Failure injection for provider outage, malformed responses, stale availability, process crash, replay and recovery.
- Security/accessibility/load/restore tests in CP13.

**Gate:** the complete acceptance matrix is green after the last relevant change. Neither 180 passing unit tests nor a 59-page build closes this gate by itself. Narrow OCR/template scripts must not be labelled complete-lifecycle proof.

## CP13. Deployment, observability, privacy, capacity and recovery

**PRD:** sections 4, 13-16, 18-19, 21.

- [ ] Package reproducible frontend/API/worker/scheduler/OCR/scanner services and external database/object-storage configuration. Provide health checks, process supervision, dependency ordering, restart behavior and controlled migration jobs.
- [ ] Configure HTTPS, approved origins, secret management/rotation, secure cookies/tokens where applicable, bounded timeouts, connection pooling, upload protections, request limits and rate limiting.
- [ ] Keep worker, API and migration privileges distinct. Disable debug docs/error leakage and development persona routes in production. Audit unused endpoints and integration test tools before exposure.
- [ ] Monitor request latency/errors, database health/pool saturation, outbox age, job failures, missed schedules, OCR/scan readiness, storage failures, stale calendars, notification outcomes and export generation. Provide actionable alerts and redacted correlation traces.
- [ ] Implement approved retention, archive, legal-hold where applicable and deletion schedules for every PRD section 15 category. Preserve required foreign keys and immutable historical evidence; expire temporary exports.
- [ ] Encrypt/protect backups and keys separately. Restore database, object versions and audit evidence into a clean environment; measure data loss and restoration duration. Test replay/recovery of scheduled work after restoration.
- [ ] Confirm actual workload and service objectives with owners. The PRD planning targets are common-read p95 below 500 ms, 99.5% availability, RPO 15 minutes and RTO four hours; they are provisional, not existing service guarantees.
- [ ] Run agreed realistic concurrent sessions, searches, uploads/submissions, OCR queues, deadline bursts, scheduling, reports and integration delays. Tune and rerun based on measured failures; do not claim national-scale capacity from seeded row counts.
- [ ] Complete threat modelling, dependency/secret scanning, access-control testing, file-security testing and security review. Validate WCAG 2.1 AA practices with automated and manual keyboard/screen-reader/zoom checks across supported browsers.
- [ ] Document incident, restore, provider-outage, key-loss, stuck-job, failed-migration, rule-change and rollback procedures. Assign operators and support/escalation responsibilities.

**Gate:** deploy into a clean environment from documented artifacts; pass operational smoke, recovery, load, accessibility and security gates with measured evidence and approved unresolved-risk disposition.

## CP14. Final acceptance and release closure

**PRD:** sections 17-22; all packages.

- [ ] Resolve every section 21 policy/integration/workload/hosting/retention decision with its accountable owner. Mark missing approvals as blocked and identify exactly what is required.
- [ ] Reconcile the PRD clause ledger, API catalogue, P01-P54 pages, F-series backlog, all 24 business rules and all CP gates against the tested release candidate.
- [ ] Obtain business acceptance of workflow routes, metric definitions, committee rules, templates, document requirements, decision/sign-off roles and provider outcomes.
- [ ] Complete a controlled pilot with authorized users, observed defects, usability feedback, support readiness and measured performance. Record explicit pilot exit criteria and results.
- [ ] Replace obsolete claims in brief, frontend progress/tracker, full-scale plan, technology/API/access plans, README and operational handoff. Keep implementation, test, live integration and production acceptance claims separate.
- [ ] Produce a final evidence index, deployed configuration manifest without secrets, migration inventory, API specification, user/operator manuals, training material and release/rollback instructions.
- [ ] Confirm no open critical/high defects, no unimplemented required controls, no failing/ignored mandatory tests and no hidden fallback paths. Remaining medium/low defects require explicit owner acceptance and cannot contradict "nothing left".
- [ ] Treat optional/conditional exclusions as signed scope decisions, not unfinished hidden tasks. Do not claim full completion while an applicable mandatory external integration or policy prerequisite remains blocked.

**Final release condition:** all applicable ledger entries are `PASS`, all approved exclusions are explicit, CP00-CP14 gates pass for the same release revision, real-user journeys and restored operations work, and the owner accepts the evidence. Until then the correct status is "in progress".

## 5. Business-rule closure checklist

| PRD rule | Owning work and proof |
| --- | --- |
| BR-01 | CP03-04: valid institution/category, same-scope campus and source validation |
| BR-02 | CP03-04: approved effective rule selection, not newest/first arbitrary record |
| BR-03 | CP04: graph edge and every guard validated; invalid transition rolls back |
| BR-04 | CP01/04/07: permission and scope checks on returns, decisions and approvals |
| BR-05 | CP04: reasoned deficiency with immutable prior submission history |
| BR-06 | CP04/06: EVC creation only for the bound workflow requirement |
| BR-07 | CP01/06: officer selection/replacement; scheduler never chooses members |
| BR-08 | CP06: exact current membership used and snapshotted |
| BR-09 | CP06: all selected experts plus institution satisfy mandatory availability |
| BR-10 | CP02/06: transaction-time revalidation and booking-race rejection |
| BR-11 | CP06/09: persisted no-slot explanation, deadline warning and escalation |
| BR-12 | CP07: source-based draft; no automatic finding or approval |
| BR-13 | CP01/07: configured human approval/sign-off authority |
| BR-14 | CP08: upload is separate from verification and closure |
| BR-15 | CP05/08: renewal completion requires applicable verification |
| BR-16 | CP05/07/08: immutable historical versions and metadata |
| BR-17 | CP05: uncertain OCR requires review and cannot reject an application alone |
| BR-18 | CP02: every designated sensitive operation has same-transaction audit |
| BR-19 | CP09: notification creation, provider acceptance, receipt and retries distinct |
| BR-20 | CP01/10: current role/scope enforced independently on downloads |
| BR-21 | CP03: versioned, approved, audited configuration consumed by execution |
| BR-22 | CP02/14: optional ledger decision and non-blocking outage behavior |
| BR-23 | CP03/04: historical workflow bindings survive changes; authorized mapped migration |
| BR-24 | CP04/08: controlled closure/reopening without erased history |

## 6. External dependency register

| Dependency | Needed evidence | Behavior while absent |
| --- | --- | --- |
| Official APH/category/document/committee rules | Named policy owner, version, effective date and approved mapping | Explicitly labelled evaluation configuration; production acceptance blocked |
| Supabase production identity/access policy | Approved project, account lifecycle, privileged MFA policy and role grants | No fabricated official access; development identity remains gated |
| Native OCR and language packs | Installed engine/version, readiness and held-out pixel recognition | OCR unavailable; source file still available for authorized human review |
| Private storage and malware scanner | Actual durable store, access tests, scan results and failure policy | Quarantine/unavailable state; no clean-file claim |
| Email/SMS if enabled | Approved endpoint/sender/templates, controlled recipients and acceptance/receipt evidence | Unavailable channel with visible retry/blocking state, never log-as-delivered |
| Calendar/meeting provider if enabled | Consent, approved scopes, real sync and revocation tests | Real manual availability and internal scheduling; external sync unavailable |
| Government issuer or legacy APIs if applicable | Documented approved interface, authority, source ownership and reconciliation | Honest unavailable capability; authorized manual verification/import where PRD permits |
| Ledger if enabled | Governance, participating organizations, real endpoint and verification evidence | Core workflow proceeds; anchor work retries with visible state |
| Hosting, retention, recovery, workload and pilot | Approved owners, measured tests and recorded acceptance | Production/pilot gate remains blocked; do not invent acceptance |

## 7. OCR files delivered with this plan

See `output/pdf/ocr_manual_test/README.md` for the unchanged public government PDF, pixel-only PNG, image-only PDF, source URL, SHA-256 hashes, expected fields and a manual test procedure.

The official source is the Delhi Fire Service publication at https://dfs.delhi.gov.in/node/15964. The downloaded certificate concerns Hari Vidhya Bhawan School and is supplied as a public OCR test specimen. Its original issue details are not replaced with fictional values. The derived image-only versions have no embedded extraction answers.

Start with the PNG and image-only PDF to test actual OCR; use the original PDF as a separate PDF-text-layer control. The current native-engine gap must be fixed before an unsuccessful pixel-recognition test can pass. This artifact pack does not claim that the application implementation has been repaired by creating the files.

## 8. Implementation handoff instruction

Implement this plan package by package against the attached PRD and generated ledgers. Read the current target, callers, schema and tests before changes. Preserve unrelated user work. Reproduce each audited defect, repair it, rerun the same reproducer and retain evidence. Migrate safely before deploying code that requires new columns. Wire each completed backend capability to its real portal action and verify refresh/retry/scope behavior immediately. Do not substitute mocks or rename unsupported actions as completed. Do not invent official rules, approvals, provider receipts or OCR confidence. Keep external prerequisites explicit. Update completion status only after the corresponding gate passes against the final revision.
