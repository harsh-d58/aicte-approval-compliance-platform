# PRD technology and delivery checklist

Source: [Product Requirements Document (PRD), v1.0](<Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md>). Updated **29 October 2026** against the repository and the latest read-only database check. This is the project-wide checklist; [full_scale_implementation_plan.md](full_scale_implementation_plan.md) gives the execution order and gates, [fastapi_plan.md](fastapi_plan.md) holds detailed backend/API contracts, [frontend_tracker.md](frontend_tracker.md) tracks pages, and [missing_frontend.md](missing_frontend.md) tracks remaining frontend behaviour.

**Checkbox rule:** `[x]` means the stated, narrow deliverable was implemented and checked. `[ ]` means it remains open, including work that is only demonstrated with fictional browser data. This plan uses the PRD's five modules and shared capabilities. It does not turn example APH rules or provisional targets into approved policy.

**Identity decision:** PRD §4.2 proposes Keycloak for the prototype. The project uses **Supabase Auth** by the user's explicit decision; the PRD's role, scope, revocation and stronger-authentication requirements still apply. Future approved AICTE/government SSO remains a pilot decision.

## Current verified baseline

- [x] Next.js, React and TypeScript frontend with all 54 planned page templates and ten fictional dashboard views. These are demo UI coverage, not live PRD completion.
- [x] Default live frontend shell for Supabase sign-in and the six implemented identity/institution/application GET routes; unavailable business features are labelled pending. Explicit `NEXT_PUBLIC_PORTAL_MODE=demo` keeps fictional flows separate.
- [x] One ignored project root `.env` feeds both apps; only the Supabase project URL and publishable key are exposed to the browser. The public Auth settings endpoint accepted the key.
- [x] Existing PostgreSQL 17 database connects over TLS in a read-only transaction; all 65 PRD logical entity names exist as public tables. `/ready` returned 200.
- [x] Added a [repeatable synthetic dataset](backend/docs/mock_dataset.md): 10,211 rows in 22 tables for UI/query development. It is explicitly labelled DEMO and does not count as live workflow completion or official AICTE data.
- [x] FastAPI foundation with `/api/v1`, liveness/readiness, correlation IDs, PRD-shaped errors, bearer-token validation, current-user/permission reads and scoped institution/application reads.
- [x] Initial validation: 28 backend tests, 28 frontend demo tests, lint, TypeScript and frontend production build passed. A confirmed test account and scoped DEMO grant now exist; direct database calls verified one institution/six applications and denied other details. The user confirmed the same browser-visible counts. Real-token denial/revocation and the broader [official policy](backend/docs/access_policy_decisions.md) remain pending.
- [x] Installed an additive [outbox/idempotency migration](backend/migrations/001_outbox_idempotency.sql) in the connected prototype database; the [transaction contract](backend/docs/transaction_foundation.md) and outbox SQL passed a rolled-back smoke check. No business write route uses it yet.
- [x] Installed append-only audit triggers; UPDATE/DELETE rejection and canonical event-hash round trip passed a rolled-back smoke check. Restricted grants and live-action audit integration remain open.
- [x] Added a guarded [write transaction helper](backend/app/transactions.py) and deterministic idempotency hashes; write routes remain disabled.

## P0 — unblock trustworthy live work

### 1. Policy, identity and scope (§§2.3, 3, 13.1, 21)

Detailed task sequence and acceptance matrix: [identity_access_plan.md](identity_access_plan.md).

- [ ] Obtain approved prototype roles, permission codes, scope types, grant/revocation authority and stronger-authentication policy. Do not copy fictional demo roles into official grants without approval.
- [x] Create one authorised Supabase Auth test user and corresponding active `public.users` identity record through the approved narrow DEMO policy; sign-in does not auto-provision regulatory access.
- [x] Provision the approved DEMO institution viewer role, two read permissions and a 30-day scoped assignment with audit evidence.
- [ ] Provision approved roles, permissions, role-permission mappings and scoped assignments with validity periods.
- [ ] Verify real-token positive and negative access for institution, region, application and EVC scopes; verify disabled users, expired grants, cross-institution denial and timely revocation.
- [ ] Extend backend authorisation to every subsequent read, mutation, history, file and export, with independent scope checks and no privilege from browser-selected roles.

### 2. Existing database and transaction design (§§5–6, 8.2, 10, 13.4)

- [x] Inventory PRD entities and initial identity/application fields against the existing database. See [schema mapping](backend/docs/schema_mapping.md).
- [x] Draft the additive outbox/idempotency schema without changing the shared database.
- [ ] Finish column, foreign-key, unique-index, check-constraint, trigger, grant and row-level policy review for each module before its writes are implemented.
- [x] Add durable `outbox_events` storage for the PRD §8.2 transaction pattern. The migration is installed and insert/lease/ack SQL passed a rolled-back smoke check.
- [ ] Connect business mutations and workers so the outbox event commits with state and is consumed with retry/deduplication.
- [ ] Specify idempotency-key storage and replay semantics for retry-sensitive operations (§10.1).
- [ ] Define version/`If-Match` or locking strategy for every concurrent edit and EVC booking; return 412 for stale versions and 409 for conflicts (§§9.1, 10.2–10.3).
- [x] Add reusable lock-and-version checks for applications, institutions and documents, plus 409/412 error mapping. A rolled-back DEMO transaction verified stale-version rejection and atomic audit/outbox/idempotency behaviour; other modules still need their own concurrency rules.
- [ ] Define audit append-only protections, actor/correlation/version references, hash-chain or equivalent integrity controls, retention and backup protection. Inspect database grants/triggers before claiming immutability.
- [ ] Resolve durable institution availability and item-level deficiency-response mapping, which the PRD behaviour requires but the logical entity list does not fully spell out.

### 3. Shared FastAPI safety and contract (§§4.1, 9–10, 13–14)

- [x] Establish modular FastAPI application and first six PRD §9.2 GET operations. The remaining proposed operations are listed in [fastapi_plan.md](fastapi_plan.md#18-exact-proposed-api-inventory--92).
- [ ] Complete PRD §9.1 pagination, errors, status codes, validation, HTTPS and file-transfer conventions across every endpoint.
- [ ] Apply permission, scope, input validation, rate limits where appropriate, correlation IDs and sensitive-action auditing to all routes.
- [ ] Make business state, history, assignment, audit and outbox changes atomic. Failed guards must leave state unchanged.
- [ ] Keep background workers and integrations behind the same backend validation for consequential state changes; retain one modular monolith for the initial implementation.

## P1 — SIH prototype capabilities (§18 Phase 1)

### 4. Institution profiles and approved configuration (M1/shared; §§5.2–5.4, 7.1, 9.2)

- [ ] Implement authorised user/role-assignment and institution/profile/campus APIs.
- [ ] Support controlled typed institution attributes, source references and verification status; enforce unique identifiers and explicit institutional representation.
- [ ] Model application categories, document requirements, APH rule sets and effective workflow versions from approved or clearly labelled sample configuration.
- [ ] Validate workflow stages, transitions, guards, owners and SLAs before publication; preserve historical application bindings and configuration-change history.
- [ ] Version and audit notification, escalation, template and other controlled settings under the authorised approval process.

### 5. Application workflow (M1; §§7.1, 9.2–9.3, 10, 12)

- [ ] Create, edit and submit drafts; bind the applicable institution, application type, APH version and workflow version.
- [ ] Implement prescribed Only Scrutiny and EVC-containing sample routes with valid transitions, assigned owners, due dates, stage history and pending actions.
- [ ] Enforce transition guards and human authority for returns, decisions and controlled reversals; prevent duplicate transitions.
- [ ] Support notices containing multiple deficiency items, reasoned returns, exact submission/document versions, per-item responses and authorised resolution or re-return.
- [ ] Record formal decisions, approval conditions and case closure without erasing history; treat cancellation/reopening/migration as controlled **Should** scope (WF-10).

### 6. Files, documents and OCR (M5/shared; §§5.4, 7.5, 9.2, 13.2, 15–17)

- [ ] Integrate encrypted, versioned object storage with private access, immutable document versions, checksums and authorised short-lived downloads.
- [ ] Enforce configured file type/size rules and malware scanning; support resumable or multipart uploads where appropriate.
- [ ] Implement upload sessions, registration, version listing, renewal cases and independent file authorisation.
- [ ] Choose PaddleOCR **or** Tesseract; persist engine/version, extracted fields, confidence, provenance and individual mismatch/missing/expiry/quality findings.
- [ ] Permit authorised reprocessing and reasoned human review. OCR and hashes must not independently establish authenticity or reject an application.
- [ ] Apply approved retention to files and OCR output while retaining required historical versions.

### 7. Redis/Celery workers and notification foundation (§§4.2, 8, 10.5)

- [ ] Add Redis and Celery with durable job status, attempts, retries, failure evidence and recovery after worker interruption.
- [ ] Consume transactional outbox events for notification and permitted downstream work.
- [ ] Run deadline and document-expiry scanners with configured timezones, thresholds, missed-window recovery and deduplication.
- [ ] Preserve logical notifications separately from delivery attempts; distinguish provider acceptance from confirmed delivery.
- [ ] Implement bounded retry/backoff, permanent-failure alerts, escalation windows/levels and authorised resolution.

### 8. EVC committee, scheduling and lifecycle (M3; §§7.3 steps 1–8, 9.2/9.4–9.6, 10.3)

- [ ] Create EVC work only when the applicable workflow requires it, with deadline, campus, duration, composition and coordinator.
- [ ] Let the authorised officer select or replace the exact eligible 4–5 experts under the configured rule; record replacement reasons. Never let the scheduler choose experts.
- [ ] Record selected experts' **and institution** availability, source, freshness and busy intervals; allow controlled manual entry without assuming calendar API access.
- [ ] Generate and explain feasible candidates within horizon, duration, location, lead-time, conflict and deadline constraints; preserve failed attempts and no-slot risk.
- [ ] Recheck all mandatory constraints and atomically reserve a confirmed slot; reject double-booking. Retain invitation, acknowledgement, rescheduling, postponement, cancellation and completion history.
- [ ] Show calendar/provider failures as stale or failed rather than falsely synchronised.

### 9. Meeting-to-Record Assistant (M3; §§7.3 step 9, 9.7, 13.3)

- [ ] Accept only authorised committee notes, structured observations and permitted transcript references.
- [ ] Generate source-linked draft minutes, criterion-wise observations, unresolved questions, action items and EVC report sections; flag missing/conflicting inputs.
- [ ] Support human edit, review, request-changes and authorised approval. Approved versions are immutable; corrections create new reasoned versions.
- [ ] Apply explicit transcript access and retention policy; never put confidential transcript text in ordinary audit metadata.

### 10. Undertakings, evidence and renewal (M4/M5; §§7.4–7.5, 9.2)

- [ ] Create conditions from authorised decisions with due dates, evidence requirements, responsible institution and verification authority.
- [ ] Preserve numbered evidence submissions and linked immutable document versions; allow clarification and multiple submissions.
- [ ] Require reasoned human verification before fulfilment or closure; preserve negative results, reopening and overdue status separately.
- [ ] Track document validity only for applicable types; complete renewal only after the new version passes configured verification.

### 11. Role dashboards and eight reports (M2/shared; §§7.2, 11, 17.4)

- [ ] Serve authoritative, scope-filtered dashboard measures for age, deadlines, workload, EVC, compliance, renewals, delivery and closure with source drill-down and freshness.
- [ ] Obtain approved metric definitions before performance use; reconcile dashboard totals with record and report definitions.
- [ ] Generate and authorise **region-wise performance** report.
- [ ] Generate and authorise **application pendency** report.
- [ ] Generate and authorise **EVC status** report.
- [ ] Generate and authorise **undertaking compliance** report.
- [ ] Generate and authorise **document validity** report.
- [ ] Generate and authorise **overdue actions** report.
- [ ] Generate and authorise **notification delivery** report.
- [ ] Generate and authorise **case closure** report.
- [ ] Support required filters, reporting periods, CSV/Excel and PDF outputs, large asynchronous runs, authorised scheduled distribution, expiring downloads and sensitive-export audit events.

### 12. Frontend live integration (Next.js/React/TypeScript; §§4.2, 7, 9, 14)

- [x] Preserve the working fictional prototype separately and expose a default live identity/institution/application read shell.
- [ ] Verify sign-in, account status, role/scope choice, permission changes and expired-session recovery with real authorised users.
- [ ] Connect each institution, application, document, EVC, compliance, notification, report, audit and administration action to its implemented API; remove pending states only after contract and permission tests pass.
- [ ] Replace demo-derived dashboard/report values with live scoped data, clear freshness/empty/error states and reconciled filters.
- [ ] Validate accessible keyboard, assistive-technology, responsive and recovery journeys against the PRD's WCAG 2.1 AA target.

### 13. Audit and optional anchoring (shared; §§13.4–13.5, 17.5)

- [ ] Produce protected audit events for every designated sensitive action, including reason, actor, entity, time, old/new state, correlation and version references.
- [ ] Provide authorised audit search/detail and canonical selected-record/version fingerprint verification; protect audit and source records from unauthorised alteration.
- [ ] Audit sensitive downloads and test that modified protected content is detected.
- [ ] **Optional:** if governance approves a permissioned ledger, anchor minimal hashes/metadata through Hyperledger Fabric or an equivalent system. Ledger outage must not block core workflow.

### 14. Approved external integration contracts (§§10.5, 16)

- [ ] Discover authoritative AICTE systems, approved interfaces, field ownership and import/export/reconciliation rules; until confirmed, use clearly labelled mock connectors or controlled sample imports.
- [ ] Add switchable email and SMS provider adapters with accepted/rejected, delivery, reference, failure and retryability evidence.
- [ ] Add approved calendar access where permitted; retain controlled availability entry as the fallback.
- [ ] Integrate document issuers/registries only through legitimate approved interfaces; extraction alone is not issuer verification.

## P2 — acceptance and controlled pilot (§§14, 17–18)

- [ ] Run unit, database integration and regression tests for every configured route, permission, retry, stale edit, concurrent booking, worker recovery and timezone boundary.
- [ ] Demonstrate one coherent PRD §20 case through deficiency correction, exact-member EVC, approved record, verified undertaking, triggered renewal/escalation, all eight downloads and audit history. Treat optional ledger step as conditional.
- [ ] Test realistic reads, uploads, OCR bursts, notifications, scheduling, exports and external delays against agreed workload data. The PRD's p95 read target and 99.5% availability are provisional until validated.
- [ ] Complete threat modelling, dependency scanning, access/file security tests, designated-audit completeness and encrypted backup restoration. Provisional RPO 15 minutes/RTO 4 hours need approval and measured recovery evidence.
- [ ] Package API and workers with Docker; add Prometheus/Grafana visibility for latency, errors, queues, OCR, calendar, delivery and database health.
- [ ] Run a limited authorised pilot; confirm APH mappings, report definitions, identity, hosting, retention, provider access and support procedures with AICTE owners.

## P3 — staged rollout (§18 Phase 3)

- [ ] Deploy only to an approved government cloud or other authorised environment with approved procurement, security, identity and data-sharing controls.
- [ ] Expand approved workflows, institutions and external integrations incrementally; publish new effective rule versions without silently migrating historical cases.
- [ ] Establish training, support, service management, monitoring, incident response and ongoing backup/security/performance checks.
- [ ] Reassess optional production blockchain governance and operating cost before any production ledger deployment.

## Open decisions that block official configuration (§§2.3, 21)

- [ ] Approved APH version, application categories, workflow guards, deadlines and migration policy.
- [ ] EVC composition, scheduling deadline/timezone, availability method and authorised calendar/meeting providers.
- [ ] Scrutiny/EVC templates, report approval and statutory decision authorities.
- [ ] Document requirements/expiry, notification channels/templates, report metrics and retention/transcript rules.
- [ ] Existing-system APIs, authoritative field ownership, hosting/identity policy and real workload/service levels.
- [ ] Whether optional permissioned-ledger governance is justified.

**Next executable gate:** verify the exact browser-visible scope, real-token denial and revocation, then replace the current `BYPASSRLS` database connection with a least-privilege role. The outbox/idempotency tables and append-only audit triggers are installed, but real mutation integration and restricted grants remain open. The ordered master plan is [full_scale_implementation_plan.md](full_scale_implementation_plan.md); the backend sequence is B01–B11 in [fastapi_plan.md](fastapi_plan.md).
