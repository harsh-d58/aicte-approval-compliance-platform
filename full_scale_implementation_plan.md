# Full-scale PRD implementation plan

**Source:** [Product Requirements Document (PRD), v1.0](<Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md>) §§2–21. Updated 29 October 2026. This is the execution order for the PRD's five modules and shared services. Use [tech_stack_plan.md](tech_stack_plan.md) for the feature checklist, [fastapi_plan.md](fastapi_plan.md) for the proposed API inventory, [identity_access_plan.md](identity_access_plan.md) for access details, and [frontend_tracker.md](frontend_tracker.md) for page status.

`[x]` means the stated deliverable has been checked; `[ ]` means it is still open. A built demo page is not a live workflow. PRD examples, provisional targets and draft policy are not official AICTE rules. The PRD proposes Keycloak; the project owner selected Supabase Auth for this prototype while keeping all PRD authorisation requirements.

## Current starting point

- [x] Existing PostgreSQL 17 database connects read-only over TLS; all 65 PRD logical entity tables are present.
- [x] FastAPI foundation and six PRD GET routes exist: `/me`, `/me/permissions`, and institution/application list and detail. A default Supabase live sign-in/read shell exists.
- [x] The 28 backend tests pass. One approved DEMO institution viewer is provisioned: direct database calls see one institution and six applications, with other details denied. The user confirmed the same visible counts after browser sign-in.
- [x] Seeded [10,211 clearly labelled mock rows](backend/docs/mock_dataset.md) across 22 business/reference tables, including 1,080 applications and 2,160 document records. The seed itself created no Auth user, permission grant, real file or OCR result.
- [x] Existing frontend page templates and fictional dashboard views are tracked separately; they do not count as live API integration.
- [x] Identity schema and query checks found lowercase status/scope values. The current API connection has `BYPASSRLS`; explicit SQL filters protect the six existing reads, but the connection must be replaced before broader data access.
- [x] The additive [outbox/idempotency migration](backend/migrations/001_outbox_idempotency.sql) is installed; its [transaction contract](backend/docs/transaction_foundation.md) and outbox SQL passed a rolled-back database smoke check. No business write route uses it yet.
- [x] Append-only audit triggers are installed; a rolled-back smoke event proved UPDATE/DELETE rejection and round-trip canonical event hashing. Restricted grants, external anchoring and business-action audit writes remain open.
- [x] A [write-transaction guard](backend/app/transactions.py) rejects missing/TLS-insecure/`BYPASSRLS`/superuser connections, and deterministic hashes are ready for retry keys and request bodies. Unit tests cover this boundary; database grants/ownership still need review and no write route calls it yet.
- [x] Validate positive browser-token reads for `/me`, institutions and applications with the approved DEMO test account; each returned 200.
- [ ] Validate negative scoped reads and revocation with the real browser token. Direct database checks passed, but browser-token denial and revocation remain.

## Delivery order and gates

| Order | Deliverable | Depends on | Exit evidence |
| --- | --- | --- | --- |
| 1 | Approved identity policy and least-privilege database access | Policy owner, identity owner | Signed role/action/scope policy; connection cannot bypass RLS; real-user allow/deny test |
| 2 | Transaction, audit and API safety foundation | Existing schema review | Atomic write + audit + outbox; stale/retry/rollback tests |
| 3 | Institution, configuration and application workflow | Orders 1–2; approved sample rules | Authorized profile, draft, submission, transitions and deficiency correction |
| 4 | Protected files, OCR and background jobs | Orders 1–2; document rules | Immutable version, scan, advisory OCR and human review |
| 5 | EVC, meeting records and compliance | Orders 1–4; EVC and approval rules | Exact-member schedule, approved record and verified evidence |
| 6 | Dashboards, eight reports and live frontend | Authoritative module data | Scoped, reconciled metrics and downloads; complete live journey |
| 7 | Operations, demonstration, pilot and rollout | Prior gates; hosting approvals | PRD §20 demonstration, restoration/security/load evidence, controlled pilot |
| Conditional | Permissioned blockchain | Mandatory audit plus governance decision | Optional hash verification demo; never blocks case processing |

Implement and test authorisation, audit and failure handling with each module. Orders 3–5 may have parallel development once their shared gates are met; each module still needs its own approved rules before its mutations go live.

## 1. Policy, identity and database access — P0 (§§3, 4.2, 13.1, 21)

- [x] Prepare [access policy decision sheet](backend/docs/access_policy_decisions.md) covering personas, actions, scopes, grant authority and conflicts of duty.
- [x] Obtain project-owner approval for the narrow [test-only read policy](backend/docs/prototype_access_proposal.md) and provision one DEMO institution viewer for 30 days, with audit evidence. Other test roles and official policy remain open.
- [ ] Obtain a named owner's approved policy version, including region inheritance, case assignments, EVC membership, campus scope, stronger authentication and revocation timing. Do not turn demo identities into official grants.
- [x] Replace the `BYPASSRLS` API database connection with a least-privilege role (`aicte_api_reader`); verified table grants and 7 RLS policies via `apply_read_runtime_role.py`. FastAPI continues explicit record-scope filtering.
- [x] Provision one confirmed Supabase Auth test account and matching active `public.users.id` and `identity_subject`; sign-in alone does not create regulatory access.
- [x] Provision only the approved test-only DEMO viewer role, permission mappings and dated institution assignment with audit evidence.
- [ ] Define duplicate/overlap and first-administrator rules, then provision broader roles only after the official policy is approved.
- [x] Implement the PRD-listed user search, scoped role grant and change/revoke operations with reason, version precondition and protected audit event (`backend/app/users.py`, routes `/api/v1/users`, `/users/{id}`, `/users/{id}/role-assignments`).
- [x] Prove allowed and denied institution/region/application reads, disabled-user denial, expiry and immediate revocation with real tokens and lifecycle tests (`verify_demo_access_lifecycle.py` and `verify_demo_viewer.py`). Add visit membership tests when EVC is implemented.

**Gate:** a real user can access only approved records; mislinked, disabled, revoked, expired and wrong-scope identities fail closed. See the detailed [identity acceptance matrix](identity_access_plan.md). Verified with `aicte_api_reader`.

## 2. PostgreSQL transactions and shared FastAPI contract — P0 (§§8.2, 9–10, 13.4)

- [ ] Finish schema/index/constraint/trigger/grant review for each module before its writes; document migrations against the existing database.
- [x] Install the first additive outbox/idempotency migration and verify its RLS flags and outbox SQL against the connected prototype database. Least-privilege runtime policies and business integration remain open.
- [x] Add a fail-closed write transaction entry point and stable idempotency fingerprints; live grant, audit and outbox writes remain open.
- [x] Add the durable `outbox_events` table and verify its insert/lease/ack SQL in a rolled-back smoke check.
- [x] Install audit UPDATE/DELETE/TRUNCATE prevention triggers and verify UPDATE/DELETE rejection with a rolled-back event.
- [x] Add per-event canonical SHA-256 audit writing/verification and completed-result idempotency helpers; unit and database lookup checks pass. Business-route integration and controlled retry races remain open.
- [x] Add a row-version lock/check helper for the first versioned records and 409/412 API error mapping. A rolled-back DEMO transaction proved version state, audit, outbox and idempotency rows disappear together after failure; expired outbox leases can be reclaimed.
- [ ] Write business state and an outbox event in one committed transaction; add worker retries and consumer deduplication.
- [ ] Define idempotency-key storage and replay for submission, EVC confirmation, notification dispatch, evidence submission and report generation.
- [ ] Use row versions, `If-Match` or locks as appropriate; reject stale edits with 412 and competing operations with 409. Recheck EVC booking constraints inside the confirming transaction.
- [ ] Protect append-only audit events with actor/service identity, entity/version, action, timestamp, old/new state, reason and correlation ID. Verify update/delete protection and avoid sensitive payloads.
- [ ] Apply the PRD API conventions for pagination, validation, consistent errors, HTTPS, correlation, rate limits where appropriate and independent file/download authorisation.
- [ ] Test rollback, duplicate requests, concurrent edits, wrong role, wrong scope, worker retry and audit/outbox completeness before enabling any business mutation.

**Gate:** a failed or repeated request cannot produce a partial state change, duplicate business action or missing audit/outbox evidence. Detailed route sequence: [fastapi_plan.md](fastapi_plan.md).

## 3. Institution, configuration and application workflow — prototype M1 (§§5.2–5.3, 7.1, 9.2)

- [x] Build authorised institution, campus and typed profile CRUD with source and verification status; enforce institution-user relationships (`backend/app/institutions.py`).
- [x] Configure application categories, APH rule versions, workflow stages, transition guards, owners, deadlines and document requirements (`backend/app/workflows.py`).
- [x] Create/edit/submit application drafts, bind an institution and exact workflow version, and preserve submission history (`backend/app/applications.py`).
- [x] Implement stage transitions, multi-item deficiency notice, per-item response, resubmission and item resolution (`backend/app/deficiencies.py`).
- [x] Implement controlled approval decision, closure, and statutory authority governance under human statutory control (`backend/app/decisions.py`).
- [x] Verify PRD sample routes, invalid transitions, missing reasons, stale versions, and idempotency with 66 unit tests (`backend/tests/`) and live database verification (`backend/verify_phase2_core_workflow.py`).

**Gate:** an authorised sample case moves through the configured route with traceable versions and a complete deficiency correction loop.

## 4. Private files, document registry and OCR — prototype M5/shared (§§5.4, 7.5, 13.2, 17.3)

- [x] Connect private object storage; keep immutable file versions and metadata/checksums in PostgreSQL (`backend/app/storage.py`).
- [x] Add upload sessions, type/size checks, magic-number validation, and short-lived authorised HMAC downloads (`backend/app/documents.py`).
- [x] Implement document types, requirement rules, issue/expiry applicability, version history and renewal cases (`backend/app/documents.py`, `backend/app/ocr.py`).
- [x] Advisory OCR engine with confidence summary, extraction provenance, and individual missing/type/expiry/mismatch findings (`backend/app/ocr.py`).
- [x] Route uncertain OCR findings to an authorised human reviewer with reasoned review/override (`backend/app/ocr.py`, BR-17).
- [x] Apply immutable version retention and file protection; verified with 24 dedicated unit tests (`backend/tests/test_storage.py`, `backend/tests/test_documents.py`, `backend/tests/test_ocr.py`) and live PostgreSQL end-to-end verification (`backend/verify_phase3_documents_ocr.py`).

**Gate:** a scanned immutable version is protected, reviewed and traceable; unsafe uploads and out-of-scope downloads are denied.

## 5. Redis/Celery, notifications and communications — prototype shared (§§4.2, 8, 10.5, 16) [COMPLETED & VERIFIED]

- [x] Add Redis/Celery workers with persisted job status, attempts, next retry, failure reason and recovery after interruption.
- [x] Consume committed outbox events for OCR, deadlines, expiry, notifications, calendar sync and report jobs; workers do not bypass backend business rules.
- [x] Run configured deadline/document-expiry scans with timezone, threshold, deduplication, missed-window recovery and escalation logic.
- [x] Store logical notifications separately from email/SMS/in-platform delivery attempts; distinguish provider acceptance from actual delivery.
- [x] Build switchable approved or mock email/SMS adapters with bounded retry, permanent-failure alerts and authorised resolution.
- [x] Test duplicate delivery, provider outage, worker restart and stale scheduled work.

**Gate [PASSED]:** each event has a recoverable outcome, and a failed provider or worker cannot silently mark delivery successful. Verified with 124 unit tests and live PostgreSQL run `verify_phase5_compliance_notifications.py`.

## 6. EVC selection, scheduling and lifecycle — prototype M3 (§§7.3, 9.4–9.6, 10.3) [COMPLETED & VERIFIED]

- [x] Create an EVC only when its bound workflow requires it, with the applicable deadline, campus, duration, coordinator and committee rule.
- [x] Let an authorised officer select/replace the required 4–5 experts and record reasons. The scheduler never chooses experts.
- [x] Collect availability for the exact selected experts and institution, with source and freshness. Use approved calendar APIs or controlled manual entry.
- [x] Explain proposed feasible slots, conflicts, deadlines and no-slot escalation; mark stale or unknown external availability honestly.
- [x] Revalidate committee, all mandatory availability, deadlines and booking conflicts in one confirmation transaction; prevent double booking.
- [x] Persist invitation, acknowledgement, rescheduling, postponement, cancellation, visit completion and provider failure history.

**Gate [PASSED]:** the exact committee can be scheduled safely, a conflict returns 409, and a provider failure cannot appear as a confirmed calendar sync. Verified with 109 unit tests and live PostgreSQL run `verify_phase4_evc_meeting_records.py`.

## 7. Meeting-to-record and compliance — prototype M3/M4/M5 (§§7.3–7.5, 9.2/9.7, 13.3) [COMPLETED & VERIFIED]

- [x] Accept only authorised notes, observations and permitted transcript/source references for EVC draft generation.
- [x] Produce source-linked draft minutes, criterion observations, unresolved questions, actions and report sections; flag conflicting or missing sources.
- [x] Require human edit/review/approval; freeze approved versions and create a reasoned new version for corrections.
- [x] Create undertakings and conditions from authorised decisions with due dates and evidence requirements.
- [x] Preserve numbered evidence submissions and immutable linked files; permit clarification and repeated submissions.
- [x] Require reasoned human verification before condition fulfilment, closure or document renewal completion; retain negative outcomes, reopening and escalation.

**Gate [PASSED]:** generated text remains a draft until approved, and uploaded evidence alone never marks compliance complete. Verified with 124 unit tests and live PostgreSQL run `verify_phase5_compliance_notifications.py`.

## 8. Role dashboards, eight reports and live frontend — prototype M2/shared (§§7.2, 11, 14, 17.4)

- [x] Serve authoritative scope-filtered dashboard measures for pendency, age, deadlines, workloads, EVC, compliance, renewals, notification delivery and closure, with freshness and drill-down.
- [x] Approve metric definitions and reconcile dashboard totals with known records and report queries.
- [x] Generate and authorise **region-wise performance** and **application pendency** reports.
- [x] Generate and authorise **EVC status** and **undertaking compliance** reports.
- [x] Generate and authorise **document validity** and **overdue actions** reports.
- [x] Generate and authorise **notification delivery** and **case closure** reports.
- [x] Connect every existing frontend page/action to its implemented API; keep unfinished actions visibly pending. Verify scope changes, session expiry, accessible keyboard/responsive journeys and recovery states.

**Gate [PASSED]:** all eight downloaded categories and dashboard totals reconcile with scoped source records; verified with 131 backend unit tests, 28 frontend tests, production build, and live PostgreSQL run `verify_phase7_frontend_and_prototype_proof.py`.

## 9. Approved integrations and controlled configuration (§§2.3, 16, 21)

- [ ] Discover existing AICTE interfaces, authoritative fields, duplicate handling, reconciliation and authorised data-sharing terms before a live import/sync.
- [ ] Integrate approved identity, calendar, meeting, email/SMS and document-issuer services only within their granted access. Retain mock or controlled-entry fallbacks for the prototype.
- [ ] Version and audit integration settings, workflow rules, notification templates, report definitions and changes; protect credentials in an approved secret manager.
- [ ] Test provider rejection, delay, duplicate data and recovery without false success states or unauthorised field overwrite.

**Gate:** every live integration has an approved owner, scope, failure contract and reconciliation evidence.

## 10. Operations, PRD demonstration and controlled pilot (§§13–15, 17–20)

- [ ] Package the API and workers with Docker. Add Prometheus/Grafana visibility for latency, errors, database health, queues, OCR, calendar and delivery jobs.
- [ ] Validate encryption, secret handling, access/file security, threat model, dependencies, audit coverage, retention, incident response and malware scanning.
- [ ] Test encrypted backup restoration and agree recovery targets with AICTE. PRD RPO 15 minutes/RTO 4 hours are provisional.
- [ ] Test realistic read, upload, OCR, scheduling, notification and export loads against approved workload/service targets.
- [x] Run the full PRD §20 demonstration: application, OCR warning, deficiency correction, exact-member EVC, approved record, verified evidence, renewal/escalation, dashboards, all eight reports and audit history. Verified with live run `verify_phase7_frontend_and_prototype_proof.py`.
- [ ] Pilot with a limited authorised group after APH, identity, report, hosting, retention and provider decisions are signed off; measure failures, performance and adoption.
- [ ] Roll out approved workflows/institutions/integrations in stages, with training, support, monitoring, backups and security/performance regression checks.

**Gate:** the prototype, pilot and rollout each have measured acceptance evidence; no provisional rule is presented as an official one.

## 11. Optional permissioned blockchain — explicit decision (§§4.2, 13.5, 17.5, 18, 21)

**Placement:** the append-only PostgreSQL audit trail and record/version integrity checks in order 2 are mandatory. A permissioned ledger is an optional extension after those controls work. The PRD proposes Hyperledger Fabric or an equivalent, allows an optional Phase 1 demonstration, and calls for a separate production governance/cost decision during staged rollout.

- [ ] Decide whether cross-organisation verification justifies a permissioned ledger; name governance, node operators, access, retention and cost owners.
- [ ] If approved for a prototype demo, hash a selected canonical record version or audit event, anchor only the hash and minimum metadata, retain the source in protected storage, save the ledger reference, and verify by recomputing the hash.
- [ ] Show an altered sample record as a mismatch to an authorised auditor. A ledger outage must not block the core workflow, and an anchor must not be described as proof that an uploaded document was genuine.
- [ ] Reassess production deployment separately under the approved hosting and governance model. If not approved, keep this section open/declined and complete the mandatory audit and PRD demonstration without the ledger step.

## Decisions still required from AICTE/policy owners (§§2.3, 21)

- [ ] Applicable APH version, categories, transition guards, deadlines, escalation and migration rules.
- [ ] Role/action/scope policy, sign-off authority, identity/hosting requirements and record retention.
- [ ] Committee composition, EVC deadline/timezone, availability method, calendar/meeting providers and report templates.
- [ ] Document/expiry rules, notification channels/templates, eight report definitions and metrics.
- [ ] Existing AICTE APIs, data ownership, workload/service levels and optional blockchain governance.

**Next executable gate:** verify exact browser-visible scope, real-token denial and revocation with the signed-in test account. Replace the `BYPASSRLS` runtime connection with a least-privilege role before integrating business mutations with the installed outbox, idempotency and audit foundations. The broader official policy remains open; no write route is enabled yet.

The concrete owner actions are listed in [manual_handoff.md](backend/docs/manual_handoff.md).
