# Frontend page inventory and implementation plan

## Post-build PRD recheck — 27 October 2026

All 54 templates exist, but the frontend is **not fully PRD-complete**. The full-document recheck identified F01–F15 in [missing_frontend.md](../../missing_frontend.md). The tracker reopens page rows with partial behaviour. Remaining work includes configuration-driven routing/document rules, per-item deficiencies, scheduling history, generated record outputs, reminders, report date semantics, complete metrics/auditability and application imports. See the current tracker for exact scope. There are 28 passing automated tests; the full §20 single-case browser acceptance is still open.


Current status (27 October 2026): the P01–P54 demonstration inventory and ten-role dashboard upgrade are implemented. See [frontend_tracker.md](../../frontend_tracker.md) and [PROGRESS.md](PROGRESS.md) for checked behaviour, validation and live-service dependencies. Older phase descriptions below are retained as planning history.

> Historical planning detail. The current implementation plan is [../../plan.md](../../plan.md), which retains all 49 templates below and includes the five public information pages. The latest 26 October 2026 navbar update supersedes the navbar rule below: clear glass with no coloured fill, the page gradient visible behind it through the top, dark navy labels and white surfaces with black text on hover.

Based on PRD v1.0, reviewed 26 October 2026. Source: `../../Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md`.

This is a frontend specification and fixture foundation. The pages below have **not** been built in this task. The existing landing page is the only current `page.tsx`. No backend, API routes, database, real identity integration, real OCR, calendar connection, message delivery, or ledger is included.

The PRD specifies capabilities, not page URLs or an official page count. The proposed design uses **49 reusable page templates**. Ten dashboard role views share one template; eight mandatory report categories share one report template. The application wizard and workflow editor each also support a create/edit route variant. Tabs, dialogs and drawers are identified below instead of inflating the page count.

## 1. Pages to build

| ID | Page | Proposed route | Basis |
| --- | --- | --- | --- |
| P01 | Public portal landing | `/` | Existing frontend; entry into the five modules |
| P02 | Sign in | `/login` | PRD 13.1, 18; UX route inferred |
| P03 | Role and scope selection | `/portal/access` | 3.2, 13.1; UX route inferred |
| P04 | Role dashboard: ten views | `/portal` | 7.2 |
| P05 | My tasks and assigned work | `/portal/tasks` | 7.1, 7.2; shared task view inferred |
| P06 | Institution directory | `/portal/institutions` | 5.2, 9.2 |
| P07 | Institution profile and campuses | `/portal/institutions/[institutionId]` | 5.2, 9.2 |
| P08 | Create institution | `/portal/institutions/new` | 9.2; authorised creation only |
| P09 | Application register | `/portal/applications` | 7.1, 9.2 |
| P10 | Application wizard: new/edit | `/portal/applications/new`; `/portal/applications/[applicationId]/edit` | 7.1, 9.2 |
| P11 | Application case workspace | `/portal/applications/[applicationId]` | 5.3, 7.1 |
| P12 | Scrutiny and workflow actions | `/portal/applications/[applicationId]/review` | 7.1 |
| P13 | Deficiency notice and response | `/portal/applications/[applicationId]/deficiencies/[noticeId]` | 7.1 |
| P14 | Decision and case closure | `/portal/applications/[applicationId]/decision` | 5.3, BR-04, BR-24 |
| P15 | Document registry | `/portal/documents` | 5.4, 7.5 |
| P16 | Register/upload document | `/portal/documents/new` | 5.4, 9.2 |
| P17 | Document detail and versions | `/portal/documents/[documentId]` | 5.4, 7.5 |
| P18 | OCR findings and human review | `/portal/documents/[documentId]/checks/[checkId]` | 5.4, BR-17 |
| P19 | Expiry and renewal queue | `/portal/renewals` | 7.5 |
| P20 | Renewal case | `/portal/renewals/[renewalId]` | 5.6, 7.5 |
| P21 | EVC queue | `/portal/evc` | 7.3 |
| P22 | EVC visit workspace | `/portal/evc/[visitId]` | 7.3 |
| P23 | Committee selection | `/portal/evc/[visitId]/committee` | 7.3 step 2 |
| P24 | My/institution availability | `/portal/availability` | 7.3 step 3, 16.2 |
| P25 | Slot recommendations and confirmation | `/portal/evc/[visitId]/schedule` | 7.3 steps 4–7 |
| P26 | EVC calendar | `/portal/evc/calendar` | 7.3 step 8 |
| P27 | Visit observations and completion | `/portal/evc/[visitId]/observations` | 7.3 steps 8–9 |
| P28 | Generate draft meeting records | `/portal/evc/[visitId]/records/new` | 7.3 step 9 |
| P29 | Meeting record editor, review and approval | `/portal/meeting-records/[recordId]` | 7.3 step 9, 13.3 |
| P30 | Undertaking/compliance queue | `/portal/compliance` | 7.4 |
| P31 | Condition, evidence and verification | `/portal/compliance/[conditionId]` | 7.4 |
| P32 | Notification inbox | `/portal/notifications` | 8.1, 9.2 |
| P33 | Notification detail and delivery attempts | `/portal/notifications/[notificationId]` | 8.1–8.2 |
| P34 | Escalation register | `/portal/escalations` | 8.3 |
| P35 | Report catalogue | `/portal/reports` | 11.1 |
| P36 | Report viewer: eight variants | `/portal/reports/[reportCode]` | 11.1–11.3 |
| P37 | Export job and download | `/portal/report-runs/[runId]` | 11.2 |
| P38 | Audit explorer | `/portal/audit` | 13.4 |
| P39 | Record integrity verification | `/portal/audit/verify` | 13.5; ledger optional |
| P40 | User and access directory | `/portal/admin/users` | 3.2, 5.2, 9.2 |
| P41 | User detail and scoped role assignments | `/portal/admin/users/[userId]` | 3.2, 9.2 |
| P42 | Workflow version catalogue | `/portal/admin/workflows` | WF-08, 9.2 |
| P43 | Workflow builder and version review | `/portal/admin/workflows/[workflowId]`; `/portal/admin/workflows/new` | WF-08, 9.2 |
| P44 | Regulatory rules and reference configuration | `/portal/admin/rules` | 5.3–5.5, 12, 21 |
| P45 | Notification rules and templates | `/portal/admin/notification-rules` | 8.2, 9.2 |
| P46 | Escalation rules | `/portal/admin/escalation-rules` | 8.3, 9.2 |
| P47 | Integrations and import/sync status | `/portal/admin/integrations` | 16, 9.2 |
| P48 | Jobs and operational health | `/portal/admin/jobs` | 8.4, 14 |
| P49 | My profile and session settings | `/portal/account` | Identity/scope UX support; inferred |

Shared system screens: unauthenticated/session-expired, access unavailable, record not found, loading, recoverable error, offline/stale data, and unsaved-change confirmation. Implement these through layout boundaries, `loading.tsx`, `error.tsx`, `not-found.tsx`, and shared components rather than assigning each a business page.

Public Help, Website Policies, Accessibility Statement and Sitemap can replace the current footer placeholders if actual approved content is supplied. They are additional content pages, not enumerated PRD business requirements. Self-registration, student applications, payments, admissions, autonomous expert selection and automatic statutory approvals are excluded.

## 2. Shared frontend construction rules

### Shell and visual language

- Preserve the orange-to-white **vertical** landing background, translucent glass navbar, clear logos and Noto Sans. No competition branding or emojis. Use SVG icons.
- Button default: white/translucent with dark text; hover: dark blue `#102e59` with white text. Give keyboard focus equal visibility.
- Authenticated pages: compact topbar, collapsible left navigation, breadcrumb, page title, current role/scope chip, notification badge and account menu. Keep data workspaces on white surfaces for legible tables.
- Desktop: filters above table; detail pages use an approximately 8/4 content/context split. Tablet: one column; mobile: filter drawer, stacked summary cards and a contained horizontally scrollable table.
- Reuse `PortalShell`, `PageHeader`, `ScopeSwitcher`, `MetricCard`, `FilterBar`, `DataTable`, `StatusBadge`, `DeadlineLabel`, `Timeline`, `DocumentPreview`, `VersionSelector`, `UploadPanel`, `ReviewPanel`, `ConfirmActionDialog`, `EmptyState` and `AsyncJobStatus`.
- Status must be text plus icon, not colour alone. Forms require labels, inline errors, error summary and keyboard order. Dialogs trap and restore focus. All actions must have accessible names.

### Data and interaction rules

- Dates display in Asia/Kolkata with timezone labels for EVC intervals. Use the fixed fixture clock in mock mode so expiry and overdue examples remain reproducible.
- Compute cards, queues, charts and exports from the **same scoped collection and filter definitions**. Never hardcode independent dashboard totals.
- Put search, status, date, owner, region, sort and pagination filters in URL search parameters. Preserve them when opening and returning from details.
- Role and scope are separate. The same user can have multiple authorised assignments; switching a label does not grant global visibility. Expert views restrict records to assigned visits; institutional views restrict to assigned institutions; scrutiny views restrict to assigned work.
- Frontend gating demonstrates permitted actions. It is not a substitute for live server authorisation. The future adapter must fetch only authorised data; never ship all real records and hide them client-side.
- Mock writes update a session-local store and derive dependent views. They never edit the seed file. Initially use memory with a reset action; introduce a versioned localStorage adapter only if persistence is actually needed.
- Distinguish success from pending: submitted evidence is not accepted; uploaded renewal is not verified; queued invitation is not delivered; slot recommendation is not reservation; OCR is not authenticity verification; draft record is not approved.
- Every list/detail must cover loading, empty, filtered empty, error/retry, stale data, permission unavailable and missing record. Mutation screens also cover field validation, submitting/duplicate-click prevention, success and conflict/reload.
- A version mismatch keeps unsaved text visible and offers reload/reconcile. A failed transition or slot confirmation leaves the case unchanged.

## 3. Page-by-page build details

### P01 — Public portal landing

**Build:** retain hero/footprint illustration, overview GIF, five module cards, innovations, workflow, roles, CTA and footer. Replace illustrative counters with derived mock counts when the portal is implemented; do not advertise untested operating capacity as a measured fact.

**Actions/navigation:** five cards map through `portalLinks.modules`; innovation cards use `portalLinks.innovations`; login/CTA use `/login`. Before authentication, retain the intended destination and route through sign-in. Role cards preselect a demo role, not privileges. Do not activate links to unbuilt pages.

**Mock/acceptance:** derive institution, module and report counts from fixtures/catalogues. Each card has one meaningful destination and keyboard focus; no `#login` placeholder remains once P02 exists.

### P02 — Sign in

**Build:** logo, portal name, identity-provider sign-in affordance, help/error area, and clearly labelled demo-user selection in mock mode. No invented production password validation or new self-registration flow. Preserve a same-origin `returnTo` destination.

**Actions/states:** choose one of the ten persona types, start a simulated session, continue to P03 if multiple assignments require selection, otherwise enter the permitted destination/P04. Handle identity failure, expired session and an unauthorised deep link. Demo controls must be removed with the mock adapter.

**Mock/acceptance:** `users` and their assignments, default `user-institution`. No real credentials requested, saved or sent; an invalid role cannot enter another user's records.

### P03 — Role and scope selection

**Build:** cards for assignments returned for the current user, showing role, institution/region/visit and validity. A user with one assignment can skip this screen. Invalid or expired assignments are unavailable with an explanation.

**Actions/states:** select assignment, confirm context, preserve destination only if permitted; change context later using the shell switcher. Clear the previous context's cached views on switch.

**Mock/acceptance:** institutional scope `inst-001`, west regional scope, expert scopes `visit-001`/`visit-002`, global administrative scope. Tests must show that selecting a role is not equivalent to selecting unrestricted data access.

### P04 — Role dashboard

**Build:** role-specific cards, due/overdue work, a small relevant chart, actionable queue, freshness stamp and scoped report shortcuts. Filters: date range plus authorised institution/region. Each count links to a filtered destination, such as `/portal/applications?status=IN_REVIEW`.

| Role | Required dashboard contents | Principal links |
| --- | --- | --- |
| Institution | Draft/submitted/returned applications, evidence due, renewal dates, upcoming visits | P09, P13, P20, P31 |
| Scrutiny | Assigned queue, stage age, returned/resubmitted cases, blocked guards | P05, P12 |
| Regional | Regional pendency, officer workload, overdue stages, EVC risks, escalations | P09, P23, P25, P34 |
| EVC coordinator | Readiness, missing availability, proposed/confirmed/postponed visits, outstanding reports | P21, P25–P29 |
| EVC expert | Assigned visits, own availability, observations due, draft reviews | P24, P27, P29 |
| Compliance | Evidence awaiting review, overdue conditions, clarification, renewals | P19, P30, P31 |
| Central | Cross-region performance, bottlenecks, EVC/compliance/closure summaries | P35, P36 |
| Policy | Draft/published workflow versions, controlled rules awaiting review | P42–P46 |
| Auditor | Audit events, integrity results, authorised export history | P38, P39, P37 |
| System | Failed/retrying jobs, connector freshness, notification failures, operational health | P33, P47, P48 |

**Mock/acceptance:** compute from `applications`, `tasks`, `visits`, `conditions`, `renewals`, `notifications`, `jobs`; reconcile with report selectors. Show unavailable integration freshness, not fabricated live data. Changing role changes both navigation and records.

### P05 — My tasks and assigned work

**Build:** pending/blocked/completed tabs; task title, case number, institution, owner, due time, overdue duration and next action. Filters: action type, deadline, status, application; sort by urgency/date.

**Actions/states:** open the linked work item; assign/reassign only in a permitted scope using an owner-and-reason dialog. Workflow-driven tasks complete through their source action rather than a generic checkbox bypass.

**Mock/acceptance:** `task-001` → deficiency; `task-002` → scheduling; `task-003` → overdue compliance. Source changes update the task and dashboard consistently. A task link never points to a nonexistent fixture.

### P06 — Institution directory

**Build:** search by name/code, region/type/status filters, table with institution code, official name, region, type, campus count and active application count. Authorised create action opens P08.

**Actions/states:** open P07, filter applications/documents by institution, preserve filters. An institutional user sees only its authorised records, not an unrestricted search form that grants access.

**Mock/acceptance:** `inst-001`/`inst-002` in west and `inst-003` in south exercise regional boundaries. Count active applications using a shared documented status predicate.

### P07 — Institution profile and campuses

**Build:** profile summary plus Overview, Campuses, Profile attributes, Applications, Documents and Authorised users tabs. Fields: official name, institution code/type, region, status; campus name/city/address/primary flag; typed attribute value, verification status and source document version.

**Actions/states:** edit permitted fields; add/edit campus in a drawer; open source document; start application for a selected campus; view access assignments read-only or link P41 for authorised admins. Require a reason for controlled corrections and show ownership of imported fields.

**Mock/acceptance:** `inst-001`, `campus-001`, lease attribute linked to `version-lease-1`. Do not mark profile data verified merely because a user changed it. Display pending verification and version conflict.

### P08 — Create institution

**Build:** institution code, official name, type, region and first campus; optional typed profile attributes. Controlled catalogues populate select inputs. This is an administrative record form, not public onboarding.

**Actions/states:** validate required fields, duplicate institution code, permitted region and primary campus; save to P07 or cancel to P06. Show duplicate/import reconciliation guidance instead of silently creating a second institution.

**Mock/acceptance:** entering `DEMO-INST-001` gives a duplicate example. Creating a sample organisation does not automatically grant the current user institutional representation.

### P09 — Application register

**Build:** counters and table: application number, institution, type/year, current status/stage, owner, submission date, application/stage ages, due date and next action. Filters: role-permitted region/institution, status, stage, officer, type, age band, academic year.

**Actions/states:** start P10, open P11, open assigned review P12; bulk selection is allowed only for explicitly permitted assignment operations, not blanket approvals. Dashboard links prepopulate filters.

**Mock/acceptance:** thirteen application statuses are represented by `app-001`–`app-013`. Draft has no submission-based age; closed cases do not continue accruing active overdue time. Pending counts match P36.

### P10 — Application wizard: new and edit

**Build:** five steps: (1) authorised institution/campus, application type and academic year; (2) institution/profile confirmation; (3) required documents/versions and missing requirements; (4) declaration/checklist; (5) review and submit. Show the resolved sample workflow and pinned rule version read-only.

**Actions/states:** save draft, resume `app-005`, validate each step, back/next, upload/select document, final confirmation, submit once. Edit route uses the same component and allows only mutable draft fields; returned cases use P13 response/version history.

**Mock/acceptance:** `DEMO-APH-v1`, sample `NEW_INSTITUTION`, `2027-28`, `inst-001`/`campus-001`. Required fields and document requirements are configurable examples, not claims about official APH. Successful submission creates one new submission/version, then opens P11.

### P11 — Application case workspace

**Build:** header identity/status, current stage/owner/deadline, next responsible role and pinned workflow/APH version. Tabs: Summary, Workflow timeline, Submissions, Deficiencies, Documents, EVC, Compliance, Decisions and Audit. Reuse domain tables rather than copy records.

**Actions/states:** open P12/P13/P14 or linked document/visit/condition; reassign in a dialog with user, due date and reason; authorised cancel/reopen controls require reasons and guard explanations. Show unavailable next transitions disabled with a useful explanation.

**Mock/acceptance:** `app-001` links `notice-001`; `app-002` links `visit-001`; `app-004` links `condition-001`. A workflow draft v2 publication cannot change these cases' v1 history. Old submissions and document-version links remain visible.

### P12 — Scrutiny and workflow actions

**Build:** split review workspace: document/version preview on one side; criterion checklist, reviewer observations, metadata comparisons and transition guard summary on the other. Context panel shows status, assignment, stage age and due date.

**Actions/states:** save observations, resolve deficiency items, draft/issue a notice, recommend next stage, request a permitted transition. Issue dialog collects reason, criterion/item description, related document and response deadline. Confirmations name the destination stage and responsible role.

**Mock/acceptance:** `check-lease-1` flags date mismatch; P13 shows the issued notice. Test missing reason, unresolved guard, duplicated click and version conflict. OCR does not automatically reject the application or issue a statutory decision.

### P13 — Deficiency notice and response

**Build:** notice number, issuing officer/date, reason and response deadline; item-by-item criterion, document/version, description, response text, attachments and resolution status. Separate original submission from response submissions.

**Actions/states:** institution saves draft responses, uploads corrected versions and submits; reviewer resolves items or requests another correction with reasons. Historical issued notice is immutable. View both versions without replacing the original.

**Mock/acceptance:** `notice-001` is open for `app-001`; `notice-002` is responded for `app-009` with `version-lease-2`. Submitting a response is distinct from reviewer resolution; retain all prior notices/submissions.

### P14 — Decision and case closure

**Build:** read-only completed-stage/approved-report summary, allowed decision type, authority, reason, linked decision document, conditions and closure checklist. Show decision records/history beside the form.

**Actions/states:** authorised user saves decision draft, records final outcome, creates linked compliance conditions, or closes under the configured process. Reopen/withdraw/cancel/migrate use separate reason dialogs, only when configured and authorised. Recording approval does not silently close outstanding conditions.

**Mock/acceptance:** `decision-002` draft on `app-010`, conditional `decision-001` on `app-004`, closed `app-006`. Missing authority/reason or incomplete prerequisites blocks final action. No AI-generated approval/rejection.

### P15 — Document registry

**Build:** institution/campus/type/verification/expiry filters; document type, issuer/reference, current version, issue/expiry dates, verification, scan and renewal status. Display Not applicable for non-expiring categories.

**Actions/states:** upload/register P16, open P17, review OCR P18, open renewal P20. File preview/download permission is independent from seeing the parent case.

**Mock/acceptance:** `doc-lease` versioned mismatch, `doc-registration` without expiry, `doc-safety` approaching expiry with a pending renewal. Do not produce a renewal alert for registration.

### P16 — Register/upload document

**Build:** authorised institution/campus/application association, document type, issuer/reference, issue date, conditional expiry date, file picker, progress, metadata preview and scan state. Show configurable file type/size limits.

**Actions/states:** local PDF file selection, client validation, preview, cancel/retry and metadata save. In mock mode do not send files anywhere; sample `previewText` is an explicit placeholder until a real local fixture file or user-selected Blob exists. Never render a fake download URL.

**Mock/acceptance:** 10 MB PDF limit is an illustrative configuration. Missing expiry for a required expiring type, impossible date range, failed scan and pending scan have distinct feedback. Successful upload creates a version record, not a verified document.

### P17 — Document detail and versions

**Build:** preview plus metadata; version selector/table; scan and verification panel; OCR checks; linked institution/application/condition; renewal and audit tabs. Metadata shown must belong to the selected version.

**Actions/states:** add version in drawer, compare versions, open P18/P20, authorised review with result and reason. Read-only historical versions remain accessible within permission. Pending/failed scan blocks file preview appropriately.

**Mock/acceptance:** `doc-lease` keeps v1 and v2; historical submissions still reference v1. `doc-safety` keeps accepted v1 while v2 awaits renewal review. No overwrite/delete action destroys a historical file version.

### P18 — OCR findings and human review

**Build:** selected version preview; extracted/declared values, confidence, engine/provenance/time; check severity, issue details and human review status. Low-confidence or missing fields must be visibly uncertain.

**Actions/states:** reviewer accepts an extraction/check, marks correction required with reason, requests clarification or queues authorised reprocessing. Reprocessing shows queued/processing/failed states. Changing review status does not rewrite the original extracted result.

**Mock/acceptance:** `check-lease-1`: declared `2027-03-31`, extracted `2026-03-31`, confidence `0.62`; `check-safety-2` queued. Text extraction and hash equality are never labelled proof of authenticity.

### P19 — Expiry and renewal queue

**Build:** expiring soon/expired/renewal pending tabs; document, institution, expiry date, days remaining, current version, renewal owner/status and last reminder. Filters: configured expiry window, region, type, verification and status.

**Actions/states:** open renewal, start renewal if applicable, open related document. Advance reminders follow each type's sample configuration; no universal hardcoded threshold.

**Mock/acceptance:** safety expires `2026-11-05`; fixed clock `2026-10-26` yields ten calendar days. A condition's overdue state is independent of its supporting document's expiry.

### P20 — Renewal case

**Build:** original accepted version versus renewal submission, validity dates, due date, assigned verifier, evidence/checks and event history. Require a new file version instead of editing the old one.

**Actions/states:** institution adds renewal metadata/version; reviewer accepts or requests correction with reason. Close renewal only after configured verification succeeds; show who accepted it and when.

**Mock/acceptance:** `renewal-001` links safety versions 1 and 2, status UNDER_REVIEW. Merely uploading v2 does not remove expiry/verification work or mark the renewal complete.

### P21 — EVC queue

**Build:** status tabs and deadline risk summary; application, campus, readiness, required-by date, selected/required member count, availability freshness, schedule, coordinator, visit/report status. Filters: region, coordinator, deadline, status.

**Actions/states:** open P22; contextually open committee selection, schedule or report review. Create a work item only for an application whose configured workflow requires EVC, using a guarded action from P11.

**Mock/acceptance:** `visit-001` proposed for `app-002`, `visit-002` completed/report pending for `app-003`. No EVC is forced into an Only Scrutiny route.

### P22 — EVC visit workspace

**Build:** visit summary, campus, expected duration, deadline, coordinator and readiness checklist. Tabs: Committee, Availability, Schedule, Invitations, Observations, Records, Actions and History. Each tab links to its focused page when needed.

**Actions/states:** request availability, open P23/P25/P27/P28/P29, view/resend permitted invitations, postpone/reschedule/cancel with reason. Display delivery response and calendar sync as different statuses.

**Mock/acceptance:** visit-specific committee and version are visible. `invitation-005` is SENT with calendar PENDING, not falsely delivered/synchronised. Visit completion does not imply report approval.

### P23 — Committee selection

**Build:** eligible expert search/filter by expertise; selection panel showing exact selected members, committee role, required count, selected-by/time and composition checks. No algorithm-selected default members.

**Actions/states:** authorised regional/designated officer selects 4–5 members according to the configured rule, saves, or replaces a member with a reason. Prevent duplicates/ineligible choices and over/under-size committees. Other roles see read-only membership.

**Mock/acceptance:** `visit-001` has five explicit `expert-001`–`expert-005` members. Replacement invalidates affected recommendations in session state; the scheduler cannot silently choose an easier expert.

### P24 — My/institution availability

**Build:** calendar plus accessible interval list; date, start/end, available/busy, source and last-confirmed time; relevant visit/deadline context. Experts manage their availability; authorised institutional representatives confirm institution availability.

**Actions/states:** add/edit/remove draft intervals, validate start before end and overlap, confirm availability. Calendar connection status can link to account/integration UI, with manual entry available when connection is absent/stale. Busy event titles are not collected.

**Mock/acceptance:** five experts and `inst-001` confirm 10 November 10:00–13:00 IST; `expert-002` is busy 9 November. `staleAvailability` scenario requires reconfirmation rather than green availability.

### P25 — Slot recommendations and confirmation

**Build:** pinned exact committee, institution availability, duration, horizon, deadline, preparation lead time, freshness policy; recommendation cards/table with interval, rank, mandatory constraint checklist, explanation, snapshot/expiry and blockers. Recommendation and confirmation have separate visual states.

**Actions/states:** generate sample recommendations, compare, select, revalidate then confirm. No feasible slot shows blocking participants, nearest alternatives where supported, deadline risk and escalation link. A 409 invalidates the proposal, keeps visit unconfirmed and offers refreshed options.

**Mock/acceptance:** `slot-001` feasible; `slot-blocked` conflicting; `confirmationConflict`, `staleAvailability` and `noFeasibleSlot` scenarios. Repeated confirm clicks create only one local event. Expired recommendation cannot be treated as a reservation.

### P26 — EVC calendar

**Build:** month/week/agenda views, timezone label and status legend; region/coordinator/status filters. Mobile defaults to agenda. Proposed and confirmed dates have clearly different treatments.

**Actions/states:** event → P22, propose/reschedule → P25, availability → P24. Any drag/drop proposal must open confirmation and revalidation; it cannot commit a move directly. Do not infer external calendar sync from an internal event.

**Mock/acceptance:** completed 22 October visit and proposed 10 November visit. Empty month, postponed visit and stale calendar connector feedback are supported.

### P27 — Visit observations and completion

**Build:** criterion-wise structured observations, author, source, review state and attachments; participant/input completion list; action items with responsible role/due date; separate visit lifecycle controls.

**Actions/states:** assigned experts save/submit observations; coordinator records visit completion/postponement with reason; authorised users maintain action items. Missing evidence can remain unresolved, visibly flagged. Record generation opens P28.

**Mock/acceptance:** `observation-001` lab and `observation-002` lease; `action-001` follow-up. Completing the physical visit does not approve its report or invent missing staffing findings.

### P28 — Generate draft meeting records

**Build:** record type (minutes/EVC report), approved sample template/version, selected authorised source notes/observations, optional permitted transcript reference, source manifest and missing/conflicting-input warnings.

**Actions/states:** preview sources, generate a deterministic sample draft, show queued/processing/failure, open P29. Do not implement AI calls, recording capture or transcript uploads for this frontend task. Draft text must be traceable to selected sample inputs.

**Mock/acceptance:** `visit-002` notes create sections in `record-001`; absent staffing input produces a warning and blank section, not a fabricated observation. New records always begin DRAFT.

### P29 — Meeting record editor, review and approval

**Build:** version selector, section editor, source side panel, review comments, warnings, approval status and action items; approved versions read-only. Compare draft/previous version with clear authorship.

**Actions/states:** save draft, submit review, request changes with comments, approve only for designated role, create correction version with reason. Approval freezes the selected version; edits never mutate an approved record. Surface conflicting edits through 412 flow.

**Mock/acceptance:** `record-001` IN_REVIEW with unresolved sources; `record-002` approved minutes. Source links open authorised observations only. Approval is a human action, independent of the generator.

### P30 — Undertaking/compliance queue

**Build:** open/evidence submitted/review/clarification/verified/closed tabs and a separate overdue filter. Columns: condition, application/institution, source decision, due date, evidence status, verification state, reviewer, overdue days and escalation.

**Actions/states:** open P31; authorised create-condition drawer from a decision captures description/code, evidence required, due date and verification role. Institutional views are limited to their own conditions.

**Mock/acceptance:** `condition-001` remains CLARIFICATION_REQUIRED and also overdue; `condition-002` CLOSED. Crossing a deadline does not erase the underlying review state.

### P31 — Condition, evidence and verification

**Build:** condition/source approval, evidence requirements, due date, responsible institution/reviewer and status. Tabs: Evidence submissions, Verification, Timeline; each submission links immutable document versions and any prior clarification.

**Actions/states:** institution submits evidence/clarification as a new numbered submission; authorised reviewer records compliant/noncompliant/clarification with comments; authorised close/reopen requires configured criteria and reason. Show closure authority/time and retained history.

**Mock/acceptance:** `evidence-001` with safety v2 was returned for missing declaration by `verification-001`. `evidence-002` accepted supports the closed condition. Uploading more files alone never closes a condition.

### P32 — Notification inbox

**Build:** unread/all tabs with subject/event, related entity, creation time and read state. Personal notifications differ from operator delivery monitoring; channel/status filters appear only where relevant to the role.

**Actions/states:** open associated case/condition/visit, mark read/unread locally, open P33 for authorised details. A read receipt is not the same as external provider delivery evidence.

**Mock/acceptance:** `notification-001` → app deficiency, `notification-002` → condition. Empty inbox, unread badge reconciliation and role-filtered recipients are covered.

### P33 — Notification detail and attempts

**Build:** event/recipient category/channel, linked entity, logical status, attempt timeline, failure reason, retryability and last/next attempt. Minimise personal recipient information in broad operator views.

**Actions/states:** authorised retry of retryable failures; retry creates a new attempt and pending job, retaining previous failures. Non-operators cannot dispatch/retry messages just by viewing their notification.

**Mock/acceptance:** notification 2 has two failed attempts and RETRY_PENDING; notification 3 SENT means provider accepted, with no evidence of delivery. All sends/retries are simulated; no email/SMS tool is called.

### P34 — Escalation register

**Build:** entity/case, triggering deadline, overdue duration, rule/version, level, owner, reason, triggered time and resolution status. Filters: region, role, action/entity type, level and open/resolved.

**Actions/states:** row opens a detail drawer and source record; authorised user acknowledges/reassigns/resolves with reason. Resolution should reflect the configured source condition, not simply hide the alert.

**Mock/acceptance:** `escalation-001` → condition 1 and `rule-escalation-001`. Prevent duplicate active events for the same rule/window in the simulation. Never resolve the underlying evidence review automatically.

### P35 — Report catalogue

**Build:** eight report cards grouped as workflow/EVC/compliance/operations, descriptions and permitted formats; recent runs with status, requester and generated time. Show only authorised categories for the active scope.

**Actions/states:** card opens P36 with stable report code; recent run opens P37. All eight categories exist in the catalogue even when an individual user is authorised for a subset.

**Mock/acceptance:** `reportDefinitions` has exactly the eight categories in PRD 11.1. Global access does not imply every role may export every category.

### P36 — Report viewer: eight variants

**Build:** one reusable renderer with definition-driven columns/filters, summary counts, table, reporting-period controls, live-query/snapshot label, generation time and data freshness. Report names/columns/filters/roles are listed in section 4 below.

**Actions/states:** apply/reset/share permitted filters, drill into a case/visit/condition, request CSV/XLSX/PDF as supported, then follow P37. Large mock exports simulate queued/processing/completed or failed. Never present an HTML/text file as a genuine XLSX or PDF.

**Mock/acceptance:** `getMockReportRows` derives all eight outputs from the same collections used by dashboards; CSV may be generated client-side from these rows. Actual XLSX/PDF renderers are future frontend dependencies; until built, show an honest unavailable state. Export permission and scope are applied before row construction, and snapshot metadata travels with the output.

### P37 — Export job and download

**Build:** definition, reporting period, filters, requester, format, generation/snapshot times, job status/progress, row count and download expiry. Keep source filters available so the user can rerun the same report.

**Actions/states:** queued → processing → completed download; failed → retry; expired → regenerate. Mock downloads use a real browser-generated Blob containing derived sample rows; if a format is not generated, no fake download button.

**Mock/acceptance:** `run-001` completed; `run-007` failed; `expiredDownload` scenario. A completed run's row count is derived in `data-source.ts`. Permission unavailable can revoke a download even if the job was previously visible.

### P38 — Audit explorer

**Build:** actor, action, entity, timestamp, version, correlation ID and controlled-action reason; filters by entity/case, actor, action and time. Drawer shows previous/new states where available, version references, hash chain and optional anchor status.

**Actions/states:** inspect source entity within permissions; export authorised redacted history; open P39. Audit is read-only; corrections are subsequent events rather than edit/delete operations.

**Mock/acceptance:** `audit-001` deficiency, `audit-002` committee selection. Audit hashes are explicitly illustrative strings. Never put source documents, transcripts, tokens or full sensitive payloads in audit metadata.

### P39 — Record integrity verification

**Build:** choose authorised record/version or event; expected fingerprint, comparison result, verification time, source and optional anchor metadata. Explain that integrity comparison is not a finding of authenticity.

**Actions/states:** simulate match/mismatch, inspect source version, show ledger disabled/pending/unavailable without blocking case work. Do not claim real blockchain transactions or cryptographic verification from the placeholder hashes.

**Mock/acceptance:** `integrityMismatch` deliberately compares two labelled sample fingerprints. If a future frontend hashes a user-selected file with Web Crypto, label it local hashing and keep it distinct from a real authoritative/ledger verification response.

### P40 — User and access directory

**Build:** name, synthetic email, status, roles, scopes, assignment validity; search/status/role/region filters. Include enabled/disabled and expiring-access examples when extending fixtures.

**Actions/states:** open P41; authorised access review/revoke dialogs require context and confirmation. No password, provider token or secret appears in the table.

**Mock/acceptance:** nine staff personas plus five expert users cover all ten role types. Integration service is a non-human actor, not an eleventh dashboard persona or public login option.

### P41 — User detail and scoped assignments

**Build:** identity-provider reference/display profile read-only where authoritative; assignments table with role, scope type/ID, valid from/until and status. Show effective action permissions and access history in separate panels.

**Actions/states:** grant/change/revoke an assignment using permitted roles/scopes/dates; confirm revocation and refresh local navigation/data context. Do not equate entering an institution code with gaining representation.

**Mock/acceptance:** institutional assignment only `inst-001`; expert scoped to the two sample visits. Invalid dates, expired scope and attempted global grant without authority have visible validation.

### P42 — Workflow version catalogue

**Build:** workflow name, application type, APH version, workflow version, draft/published/retired status, effective dates and approval information. Provide route comparison and impacted-application counts.

**Actions/states:** open P43, create a draft, clone a published version. Published definitions are read-only. Retiring a route does not rewrite historical applications.

**Mock/acceptance:** `workflow-evc-v1`, `workflow-scrutiny-v1`, draft `workflow-evc-v2`. The UI demonstrates both Only Scrutiny and EVC-containing routes with version pinning.

### P43 — Workflow builder and version review

**Build:** accessible stage list with optional visual diagram; stage code/name/order/type, owner role, SLA, transition from/to/type, guards, required authority, rule reference and effective date. Tabs: Stages, Transitions, Validation, Version history/impact.

**Actions/states:** add/reorder stages, configure transitions, validate, preview a sample case, submit/publish under authorised policy. New route uses the same editor. Published changes create another version; controlled migration requires explicit policy and reason.

**Mock/acceptance:** incomplete v2 fails validation; stage references must belong to the same workflow and required guards must be specified. Publishing v2 does not change `app-001`'s workflow ID. No backend rule engine is implemented here.

### P44 — Regulatory rules and reference configuration

**Build:** versioned tabbed editors for APH references/versions; application categories; institution/region catalogues; document categories/requirements/expiry reminders; committee composition/freshness/duration; report/meeting templates; controlled timezone/retention settings. Distinguish approved values from unresolved policy decisions.

**Actions/states:** create draft, edit typed values, validate, compare, publish with approved-by/effective date and change reason. Rows open drawers rather than separate CRUD pages for every catalogue. No arbitrary secret field or unstructured executable rule input.

**Mock/acceptance:** `configurations` covers each tab, including non-expiring registration and five-member sample committee. Retention policy remains pending; do not invent official durations, APH deadlines or approved sign-off roles. Unsupported published values remain read-only.

### P45 — Notification rules and templates

**Build:** event, channel, recipient role/scope rule, template/version, enabled status and approved/effective metadata. Detail drawer/editor previews a message using synthetic event data.

**Actions/states:** create/edit draft, validate required placeholders, preview, publish/enable under configuration permission. Any 'test' action shows a local preview only; it must not contact a real recipient.

**Mock/acceptance:** `rule-notification-001` deficiency/in-app/institution. Unknown placeholders and missing recipient mapping fail validation. Changing a template never rewrites historical delivery attempts.

### P46 — Escalation rules

**Build:** triggering event/entity, overdue threshold, recipient role/scope, channel, repeat interval, maximum level, resolution condition, informational/action-required classification and version status.

**Actions/states:** edit a draft, preview which sample records would trigger, validate threshold and recipient, publish approved version. Display duplicate prevention rule and change impact.

**Mock/acceptance:** `rule-escalation-001` uses illustrative 60 minutes, regional recipient, max level 2. It is a demo policy, not an official SLA. Simulation creates one event per configured entity/rule/window.

### P47 — Integrations and import/sync status

**Build:** connector cards for identity/calendar/email/SMS/import/document issuer/optional ledger where configured; status/freshness, permitted capabilities and field ownership. Drawer shows last sync, failed jobs, mapping and retry history. Controlled sample-import wizard previews mapping, duplicates and validation before local import.

**Actions/states:** simulate connection test, inspect errors, select manual-availability fallback, preview/import synthetic records with duplicate handling. No real OAuth, credentials, network calls or assumed existing government APIs. Unconfigured connectors show unavailable/pending approval.

**Mock/acceptance:** calendar STALE, email FAILED, legacy MOCK, ledger DISABLED. A test success cannot be presented as an external connection unless a real authorised integration exists. Credentials remain outside frontend data models.

### P48 — Jobs and operational health

**Build:** tabs for async jobs/queues, notification delivery, OCR, calendar/import sync, report generation and optional anchoring. Columns: job type, source record, state, attempts, last error and next retry. Health cards are explicitly mock observations, not production uptime claims.

**Actions/states:** inspect a job drawer, open linked P18/P33/P37/P47, simulate retry for permitted job types. Optional backup/retention read-only summaries can be added after their operational contracts are agreed; no deploy/restore/security-setting actions in this frontend.

**Mock/acceptance:** queued `job-002`, retrying `job-001`, failed `job-003`. Retry preserves attempt history and source state; failed optional anchoring never blocks normal applications.

### P49 — My profile and session settings

**Build:** current user, authorised assignments, active scope, timezone display, session status and calendar-availability method. User-managed preferences can include notification display choices where policy permits; mandated notifications cannot be opted out without a specified policy.

**Actions/states:** switch scope via P03, update permitted local preferences, sign out, reset mock session. Production identity/password changes redirect to the approved identity provider; this page does not invent a credential system.

**Mock/acceptance:** show synthetic profile and manual/calendar source distinction. Reset restores fixed baseline fixtures; sign-out clears session-local data/context.

## 4. All eight report-page variants

Each row below uses P36 and the `ReportDefinition` record with matching code. Columns and filters are seeded in `mock-data.ts`; report output is derived in `mock-reports.ts`.

| Code | Columns to build | Filters | Typical roles |
| --- | --- | --- | --- |
| `region-performance` | Region, received/completed counts, stage pendency, processing time, overdue, EVC completion, compliance | Date range, region, application type, institution type | Central, regional |
| `application-pendency` | Application, institution, stage, stage/application age, deadline, overdue duration, owner, next action | Region, stage, age band, officer, status | Regional, scrutiny, central |
| `evc-status` | Application, selected committee, proposed/confirmed date, scheduling status, deadline, conflicts, visit/report status | Region, coordinator, date range, status | Regional, coordinator, scoped expert |
| `undertaking-compliance` | Condition, due date, evidence/verification status, overdue days, reviewer, escalation | Region, condition type, status, due period | Compliance, regional |
| `document-validity` | Institution, type, issue/expiry, version, verification, renewal | Type, region, expiry window, status | Compliance, regional |
| `overdue-actions` | Entity type, case, action, owner, due date, overdue duration, escalation level, resolution | Region, role, action type, overdue range | Supervisors, authorised admins |
| `notification-delivery` | Event, recipient category, channel, logical delivery status, attempts, failure reason, last attempt | Date range, channel, event, delivery status | Administrators, scoped auditors |
| `case-closure` | Application, closure date, final status, authority, reason, duration, reopen status | Region, date range, type, outcome | Central, regional, auditors |

The listed roles are a starting view of PRD 'typical authorised users', not a final statutory permission matrix. Designated decision/record sign-off and export permissions must remain configurable. Scope applies to every row and drill-down.

## 5. Linking portal cards and records

`lib/portal/routes.ts` centralises future destinations. Keep it independent of fixtures so it stays when mock files are deleted.

| Existing element | Destination once built |
| --- | --- |
| Workflow Automation Engine (M1) | `/portal/applications` |
| Role-Based Dashboards (M2) | `/portal` |
| EVC Scheduling & Management (M3) | `/portal/evc` |
| Undertaking & Compliance Tracker (M4) | `/portal/compliance` |
| Document Expiry & Renewal Alerts (M5) | `/portal/renewals` |
| Audit innovation | `/portal/audit/verify` |
| EVC coordination innovation | `/portal/evc` |
| Login / request access | `/login`, then permitted intended destination |
| Pending/overdue dashboard card | Matching register plus URL filters |
| Institution / application / document row | Its ID-based detail route |
| EVC row / calendar event | Visit detail; next-action shortcut can open scheduling/report |
| Compliance card / reminder | Matching condition detail |
| Report card / generated export | Report code route / run ID route |

Use `next/link` for internal route navigation once pages exist. Use normal download affordances only for actual files/Blobs. Avoid attaching an entire clickable card around nested links/buttons. Current landing links are intentionally unchanged until their target routes are implemented.

## 6. Frontend build order and completion checks

1. **Foundation:** shared shell/design components, session context and selected role/scope, data-source boundary, list filters, error/loading boundaries. P01–P05, P49.
2. **Institution/application:** P06–P14, including draft persistence, versioned submissions, scrutiny, deficiency loop, stage guards, decision/closure. Verify Only Scrutiny and EVC routes.
3. **Documents:** P15–P20, reusable uploads/version previews/OCR review, conditional expiry and renewal verification.
4. **EVC:** P21–P29. Officer explicitly selects five experts; display all five plus institution; conflict/no-slot/stale scenarios; confirmation revalidation; observations → source-linked draft → human review → approved immutable version.
5. **Compliance/communications:** P30–P34, evidence versus verification, reminders/escalations and delivery attempts.
6. **Reporting/audit:** P35–P39. All eight categories, derived counts, actual client CSV export, export lifecycle, redacted audit and labelled integrity demonstration.
7. **Administration:** P40–P48, draft/published configuration, scoped assignments, integration/job previews. Review all role navigation paths.

For each page: build normal/empty/error/forbidden states, responsive keyboard-accessible UI, all specified links and mock interactions. Validate intended state changes and retained histories; a screenshot alone cannot establish those behaviours. Type-check/build/lint; add meaningful interaction checks for permission boundaries, version preservation, scheduling conflict, human approval and report reconciliation.

## 7. Mock-data separation and go-live replacement

See `MOCK_DATA_GUIDE.md` for the data dictionary, usage, scenarios and deletion steps. Keep `types.ts` and `routes.ts`; replace `data-source.ts`; delete `mock-data.ts` and `mock-reports.ts` after removing their imports. No page may import those mock files directly.

Do not wire a real API or implement backend services during this frontend scope. Any later adapter must preserve the UI distinction between pending and verified/approved outcomes and must use authorised, scoped responses.
