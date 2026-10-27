# Missing frontend — original 26 October 2026 audit

Reviewed: 26 October 2026. Scope: the main-folder PRD v1.0, current `frontend/app` pages/components, portal data adapter/models, `plan.md` and saved progress. This is an audit; frontend behaviour was not changed.

**Current state: Home plus eight portal page templates exist. Most business workflows remain absent or read-only. Of the 54 templates proposed in our plan, nine have implementations and 45 have no page implementation.** These are planning counts, not an official PRD page count or a feature-completion percentage. Fixtures, types, proposed route constants and descriptive cards do not count as implemented workflows.

Method: source review of every existing page and its control/copy definitions, grouped below by repeated control family; browser checks of Home link targets/styles and demo entry; current automated suite rerun: **8/8 tests pass**. This brief audit is not a fresh exhaustive click-through of every role, responsive breakpoint, error state or accessibility requirement. Previous browser checks are recorded in `frontend/docs/PROGRESS.md`. No new production build was needed for this documentation-only change.

Sources: `Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md`; `plan.md`; `frontend/docs/PROGRESS.md`; `frontend/docs/MOCK_DATA_GUIDE.md`. PRD section numbers below refer to that document. Paths are relative to this project folder.

## 1. Existing pages: features and control coverage

| Plan ID | Page | Present controls/features | Missing or incomplete |
| --- | --- | --- | --- |
| P01 | Home `/` | Logo/Home, About, Modules, Workflow, Innovations, Contact anchors; desktop/mobile login; hamburger; Explore platform/overview links; five Learn more links; seven expandable workflow steps; Request Access/Explore Modules; footer navigation | Four footer placeholders; module destinations not connected; aspirational claims need qualification; actual navbar blur issue below. Innovation/persona cards are informational, without portal shortcuts. |
| P02 | `/login` | Ten fictional role buttons, selected profile, Enter demonstration portal, Continue as current user, Back to home, retry on fixture-load failure | Approved identity-provider entry, identity/session failure and recovery UX. Demo-only access is correctly disclosed; a real password form or public self-registration is **not** required. Role preselection from Home is not wired. |
| P03 | `/portal/access` | Assignment buttons, validity display/disabled expired assignment, Continue to workspace, scoped context switch | More permission/error/expired-assignment scenarios and clear active scope in the persistent shell. No assignment management UI. |
| P04 | `/portal` | Ten role-dependent summaries, fixture-derived cards, application rows/arrows, View applications/View all, task shortcuts, Review application, View associated case, stage/publication bars | Dashboard filters; application/stage age, time remaining and overdue durations; regional comparison/officer workload/bottlenecks; report shortcuts; broad data freshness. Many metrics have no drill-down. Policy/system tables are read-only. |
| P05 | `/portal/tasks` | All/Pending/Blocked/Completed tabs, search, due-date ordering, task dialog, Close/Escape, View application | Assign/reassign, owner/deadline/type/application filters, overdue duration, actual source workflow actions. Review task opens context, not a response/review form. Search uses the internal application ID rather than the visible application number. |
| P09 | `/portal/applications` | Scoped register, search, status filter, priority/number sorting, Clear filters, Previous/Next, case links, retained filters on return | New/Edit/Resume/Submit; assignment controls; institution/region/stage/officer/type/year/age filters; stage/application age, owner and next-action columns. Validate malformed URL filters/pagination. |
| P11 | `/portal/applications/[applicationId]` | Six tabs: Overview, Timeline, Submissions, Documents, Deficiencies, EVC & compliance; back-link; status/context; synthetic document text dialog and close controls; unavailable-record state | All business mutations; workflow-path diagram; individual submission/version navigation; real file preview/download; OCR review; deficiency response; committee/report/evidence workspaces; Decisions and Audit views. Closure authority is not displayed. |
| P32 | `/portal/notifications` | All/Unread tabs, Mark all as read, Mark read/unread, source-case links, reconciled unread badges, delivery-status badges | Notification detail/attempt history; authorised retry; channel/event/date/status filters for operators; escalation navigation. Personal inbox and operator monitoring need separate permissions/views. |
| P49 | `/portal/account` | Identity/status/scope/timezone, Change scope, Reset dialog with cancel/restore, sign-out | Optional user preferences and production identity-provider handoff; session expiry information. Editing official identity fields locally is not appropriate. |

Shared shell: Overview/My tasks/Applications/Notifications/account navigation, role-context link, notification bell, sign-out, mobile drawer, loading/retry/error/not-found boundaries and modal focus handling exist. The shell has no navigation entries for institutions, documents, renewals, EVC, compliance, reports, audit or administration because those destinations are not built. The breadcrumb’s Portal link returns to public Home; add an unambiguous workspace breadcrumb if that is intended instead.

## 2. Specific link, text and detail issues already present

These are corrections to existing UI, separate from building the missing modules.

| Priority | Finding and evidence | Required correction |
| --- | --- | --- |
| High | Privacy Policy, Accessibility, Website Policies and Sitemap all use `href="#"`. `frontend/app/components/Footer.tsx:13`. Browser target check confirms all four are placeholders. | Supply the planned content pages and approved copy, then wire the links; do not imply policies exist while they jump to the top. |
| High | All five module Learn more links go to `#workflow`, including dashboards/documents/compliance. `frontend/app/components/ModulesSection.tsx`. | Give each module a meaningful destination or an honest preview/unavailable state. M1/M2 can already lead through sign-in to their implemented read views. |
| High | Home navbar’s computed `backdrop-filter` is **`none`** in the tested Chromium preview despite the intended frosted design. `frontend/app/components/Navbar.module.css:6` puts the WebKit alias after the standard declaration; the generated CSS retains only the alias. | Correct declaration ordering/compatibility and verify actual blur on desktop/mobile. The overview logo blur **does** compute to `blur(6px)` and is working. |
| High | “10,000+ Technical Institutions” is hardcoded and not sourced or measured. `frontend/app/components/StatsBar.tsx:7`; PRD §14 explicitly rejects untested capacity claims. | Cite/label a verified external context statistic, label an illustrative target, or use a fixture-derived count; never present it as supported system capacity. The five/eight/two counts are product-scope counts, not evidence those modules/reports work. |
| High | “APH-compliant workflows”, “Tamper-evident audit trail”, scheduling/report-generation copy and the innovation descriptions read as implemented capabilities. `CTASection.tsx:82`, `ModulesSection.tsx`, `InnovationsSection.tsx`. | Label proposed/prototype capabilities and unapproved sample rules. Optional blockchain must remain optional; OCR/hashes must not imply document authenticity. |
| High | “Government of India Initiative” and the government copyright/branding imply official ownership while the footer also says the portal is not official. `Footer.tsx:41,85,96`. | Make the prototype’s ownership/endorsement status consistent across the page; retain a prominent prototype statement. |
| Medium | Request Access opens demo sign-in; it does not request access. `CTASection.tsx:68`. | Rename to Explore demo/Enter portal or use an approved access-support destination. Do not invent self-registration. |
| Medium | Home’s diagram places “Compliance Pending” before “Approved”, while its own description calls the undertaking post-approval. It also uses `RETURNED` instead of the case status `RETURNED_FOR_DEFICIENCY` and omits resubmission/decision/closure branches. `WorkflowSection.tsx`. | Clearly label the diagram illustrative, show conditional approval → compliance → closure accurately, and align visible status names with configured terminology. The “No submission deadline applies” draft text also needs policy qualification. |
| Medium | About correctly targets `#about`, but that section is statistics; Contact correctly targets the CTA, not a support/contact form. Home anchor targets otherwise exist. | Consider pointing About to the platform overview and make Contact lead to approved contact/help information. These are semantic improvements, not broken-anchor claims. |
| Medium | Dates are fixed to 26 October 2026 and `formatDate` removes the hour/minute. A due time of 17:00 is shown only as a date, sometimes followed by “IST”. `lib/portal/view-models.ts:3,17`; dashboard heading/footer. | Clearly label the fixed demo clock/snapshot; add deadline date/time, timezone, remaining time and overdue duration. Use live time only after adopting a live-data contract. |
| Medium | Current document previews always use `currentVersionId`; submission rows show only a version-reference count. `applications/[applicationId]/page.tsx:32–33`. | Open the exact immutable versions attached to each submission/notice; provide version history and actual file preview/download. Never substitute a later version for evidence originally reviewed. |
| Medium | Case tabs omit decision/approval and audit history; closure text omits the authority, and a missing workflow can silently display fallback version “1.0”. `applications/[applicationId]/page.tsx:27,30,37`. | Expose decision/closure authority and record history. Show unknown/unavailable workflow metadata instead of inventing a version. |
| Medium | Application URL status/sort values are not validated, and `page` is not constrained to an integer. Task search cannot find a case by its displayed application number. `applications/page.tsx:12–21`, `tasks/page.tsx:15`. | Normalise permitted URL values and pagination; search visible case identifiers as well as task text. |
| Medium | “Needs your attention” treats any non-closed condition as a follow-up; case condition cards do not independently flag overdue status. “No urgent items” only tests deficiencies/conditions, even for experts with other outstanding work. Dashboard copy always says “application”/“condition” singular. | Derive urgency by role/action/deadline, retain underlying review status with a separate overdue flag, and pluralise counts correctly. |
| Medium | Persistent context says Committee workspace/EVC expert for both visit assignments; the active visit ID is visible on access/account pages but not as a clear shell scope chip. `PortalShell.tsx`. | Always show the current institution/region/visit beside the role so users can distinguish assignments after switching. |
| Low | Shared badge matching gives `VERIFIED_NON_COMPLIANT` the amber fallback rather than an explicit negative-result treatment. `frontend/app/portal-ui/ui.tsx:24`. | Use an explicit status-to-label/tone mapping and keep textual status independent of colour. |
| Low | The Avaza blur is a display mask; the downloadable source GIF still contains the original logo. `OverviewSection.tsx`/`.module.css`, `public/GIF_1.gif`. | If an unbranded reusable asset is required, sanitise the actual animation frames. Current on-page blur is present, not a missing fix. |

The Home workflow buttons do expand descriptions; hero/overview links, login links and the main section anchors are not dead controls. Do not classify informational persona/innovation cards as broken buttons: they are currently plain content, although their planned portal shortcuts are absent.

## 3. PRD features still missing behind the UI

| PRD area | Current coverage | Missing frontend actions and states |
| --- | --- | --- |
| Institution master, §§5.2,9.2 | Names/campuses in fixtures and case summaries | Directory/search; authorised create/edit institution; campuses; typed profile attributes; source verification; imported-field ownership; duplicate handling; scoped user links. |
| M1 workflow, §7.1, WF-01–10 | Read-only status, owner, workflow reference and a small seeded timeline | Create/save/resume/submit drafts; resolve/present sample route; review criteria; assign/reassign; guarded transition actions; reasons; deficiency notices/responses/item resolution; cancellation/reopen/migration; optimistic conflicts and duplicate-submit protection; decisions and authorised closure. |
| M2 dashboards, §7.2 | Scoped counters, stage bars and basic case/task links | Date/region/institution/type/officer/committee filters; age/time-left/overdue metrics; workload/bottlenecks; completed/blocked trends; scheduling/report status drill-down; report shortcuts; source freshness and sync delay. |
| M3 EVC, §7.3 | Visit status, selected-member count and deadline in case tab; role-specific summary cards | Queue/readiness; officer selects configured 4–5 eligible experts, prevents duplicates and records replacement reason; manual expert/institution availability; freshness/conflicts; ranked explainable slots; no-slot escalation; revalidation/confirmation; reschedule/postpone/cancel; calendar/invitations/acknowledgements; observations and visit completion. |
| Meeting-to-record innovation, §7.3 step 9 | Draft/approved source fixtures; a dashboard count | Authorised input/source selection; draft minutes, criterion observations, questions, action items and report sections; missing/conflicting-source warnings; editor; review/request changes/approve; immutable approved versions and reasoned corrections. |
| M4 compliance, §7.4 | Condition description/status/due date and required-evidence text | Create condition from decision; evidence upload/version links; numbered submissions/clarification responses; reviewer verification with reason; verified compliant/non-compliant results; close/reopen/history; reminders and escalations. Upload must not auto-close. |
| M5 documents/renewal, §7.5 and document model | Current synthetic text previews and renewal counters | Registry/metadata/upload/scan progress; type/size validation; immutable versions; supported-expiry versus non-expiring categories; expiry windows; renewal queue/cases; human verification and retained history. Upload must not auto-complete renewal. |
| OCR shared capability, §§5.4,12 BR-17 | Extraction/confidence/mismatch fixtures only | Queue/check view, source preview, declared/extracted comparison, confidence, field findings, manual resolution and retry. Low-confidence OCR must not auto-reject cases. |
| Notifications/escalations/jobs, §8 | Personal read/unread inbox; seeded delivery badge; system job table | Event-triggered demo notifications; channel/recipient rules; attempt/failure/retry detail; reminder/escalation register, acknowledge/reassign/resolve; job detail/retry; no false sent-versus-delivered claims. |
| Eight reports, §11 | Definitions and row helpers in `mock-data.ts`/`mock-reports.ts` | Catalogue, filtered report viewers, scoped rows/drill-downs, reporting period/freshness/snapshot labels; real CSV/XLSX/PDF output as supported; async progress/failure/retry/expired downloads; export metadata and reconciliation checks. No downloadable report UI exists. |
| Audit/integrity, §§13.4–13.5 | Illustrative events/hashes and auditor counters | Audit explorer, actor/action/time/reason/version/correlation details, authorised history export; local/authoritative verification distinction; match/mismatch/source/anchor status. Real blockchain remains optional and must not block cases. |
| Configuration/access/integrations, §§3.2,7.1 WF-08,9.2,16 | Demo role choices, scope filtering, readonly workflow/job snippets | Scoped user/role assignments; workflow build/validate/clone/publish/effective dates; APH/document/committee/template rules; notification/escalation rules; import preview/mapping/duplicates; connector test/freshness/ownership/failures and manual fallback. |

All eight missing report variants: **region performance, application pendency, EVC status, undertaking compliance, document validity, overdue actions, notification delivery, case closure**. They share one proposed viewer template; they are eight required outputs, not eight completed pages.

Role-specific gaps remain for all ten personas: institution submission/response, scrutiny review, regional assignment/oversight, coordinator scheduling, expert availability/observations, compliance verification, central regional analytics, policy editors, auditor explorer and system job/integration operations. A different welcome title and four counters do not complete each role’s dashboard.

## 4. All proposed pages with no implementation

The following 45 templates have no `page.tsx` equivalent. IDs match `plan.md`; create/edit variants count as one reusable template. Public information pages P50–P54 are additions from our plan, not five separately enumerated PRD modules.

| Plan ID | Missing page | Proposed route |
| --- | --- | --- |
| P06 | Institution directory | `/portal/institutions` |
| P07 | Institution profile/campuses | `/portal/institutions/[institutionId]` |
| P08 | Create institution | `/portal/institutions/new` |
| P10 | Application wizard, new/edit | `/portal/applications/new`; `/portal/applications/[applicationId]/edit` |
| P12 | Scrutiny/workflow action workspace | `/portal/applications/[applicationId]/review` |
| P13 | Deficiency notice/response | `/portal/applications/[applicationId]/deficiencies/[noticeId]` |
| P14 | Decision/case closure | `/portal/applications/[applicationId]/decision` |
| P15 | Document registry | `/portal/documents` |
| P16 | Document registration/upload | `/portal/documents/new` |
| P17 | Document detail/version history | `/portal/documents/[documentId]` |
| P18 | OCR findings/human review | `/portal/documents/[documentId]/checks/[checkId]` |
| P19 | Expiry/renewal queue | `/portal/renewals` |
| P20 | Renewal case | `/portal/renewals/[renewalId]` |
| P21 | EVC queue | `/portal/evc` |
| P22 | EVC visit workspace | `/portal/evc/[visitId]` |
| P23 | Officer committee selection | `/portal/evc/[visitId]/committee` |
| P24 | Expert/institution availability | `/portal/availability` |
| P25 | Slot recommendation/confirmation | `/portal/evc/[visitId]/schedule` |
| P26 | EVC calendar | `/portal/evc/calendar` |
| P27 | Visit observations/completion | `/portal/evc/[visitId]/observations` |
| P28 | Generate draft meeting record | `/portal/evc/[visitId]/records/new` |
| P29 | Meeting-record edit/review/approval | `/portal/meeting-records/[recordId]` |
| P30 | Undertaking/compliance queue | `/portal/compliance` |
| P31 | Condition/evidence/verification | `/portal/compliance/[conditionId]` |
| P33 | Notification detail/delivery attempts | `/portal/notifications/[notificationId]` |
| P34 | Escalation register | `/portal/escalations` |
| P35 | Report catalogue | `/portal/reports` |
| P36 | Report viewer, all eight variants | `/portal/reports/[reportCode]` |
| P37 | Export job/download | `/portal/report-runs/[runId]` |
| P38 | Audit explorer | `/portal/audit` |
| P39 | Record integrity verification | `/portal/audit/verify` |
| P40 | User/access directory | `/portal/admin/users` |
| P41 | User/scoped role assignments | `/portal/admin/users/[userId]` |
| P42 | Workflow version catalogue | `/portal/admin/workflows` |
| P43 | Workflow builder/version review, new/edit | `/portal/admin/workflows/new`; `/portal/admin/workflows/[workflowId]` |
| P44 | Regulatory/reference configuration | `/portal/admin/rules` |
| P45 | Notification rules/templates | `/portal/admin/notification-rules` |
| P46 | Escalation rules | `/portal/admin/escalation-rules` |
| P47 | Integration/import/sync status | `/portal/admin/integrations` |
| P48 | Jobs/operational health | `/portal/admin/jobs` |
| P50 | Help/support | `/help` |
| P51 | Privacy policy | `/privacy` |
| P52 | Accessibility statement | `/accessibility` |
| P53 | Website policies | `/website-policies` |
| P54 | Sitemap | `/sitemap` |

## 5. Shared behaviour and verification still needed

- **States:** consistent per-page loading, filtered/unfiltered empty, recoverable errors, forbidden/unavailable records, offline/stale data, session expiry and unsaved-change confirmation. Loading/error boundaries exist, but most failure/scenario controls are not wired for validation.
- **Forms/mutations:** labels, field validation/error summary, draft persistence, submitting/duplicate-click prevention, success feedback, permission guards, concurrency conflict/reconcile and retained histories. Most do not exist because the underlying action forms are absent.
- **Accessibility:** keep the existing skip link, focus styles, tab keyboard navigation, portal drawer focus management and native dialogs. Still verify WCAG 2.1 AA contrast/zoom/reading order, small low-contrast portal text, touch targets, live result announcements, Home hamburger Escape/focus return, and association of workflow expanders with their detail panel. CSS reduced-motion rules do not stop the JavaScript counters or animated GIF; provide a suitable pause/static/reduced-motion treatment where needed. No formal accessibility pass is evidenced by the eight tests.
- **Data completeness:** fixture case histories/documents are sparse; “No recorded stage events” on a submitted case means absent sample history, not proof no activity occurred. Expand coherent sample journeys instead of filling missing history with invented events. Global/regional datasets should support real filter combinations and all important outcomes.
- **Regression coverage:** the eight passing tests cover scope/return destinations/fixture preservation and retaining route children. Add browser interaction tests, role-action permission tests, workflow/deficiency/version/conflict/scheduling/verification/export reconciliation tests as those features are implemented. They do not currently prove the PRD §20 end-to-end demonstration.
- **Existing fixes to retain:** the on-page Avaza blur and the dropped-route loading-state fix are present. The latter has an SSR regression test; do not “fix” future warnings by disabling navigation validation wholesale.

## 6. Frontend gaps versus external dependencies

Missing UI can first be built against the existing mock adapter: forms, queues, version selection, scheduling explanations, human review/approval, report generation/download simulations, retry/conflict states and navigation. This does not require inventing approved government integrations.

Production authentication, backend authorisation/permissions, transactional transitions/outbox, storage/scanning, OCR execution, calendar/provider delivery, durable export jobs and authoritative audit verification are separate service dependencies. The current adapter imports the complete **fictional** dataset into the browser; that is acceptable for this labelled demo, but cannot be reused as real-data authorisation. Use scoped server responses before connecting real records.

PRD §21 policy inputs remain open: applicable APH/version/stages, official status names, deadlines, document/expiry rules, committee composition, sign-off roles, templates, metrics, retention, identity/hosting and approved providers/APIs. Frontend controls should label sample values and support configuration rather than present assumptions as approved rules.

Not missing requirements: student admission/application flows, payments, automatic expert selection, AI statutory approval/rejection, public self-registration and mandatory production blockchain. The PRD excludes or does not require these.

## 7. Recommended order

1. Correct existing links/copy/glass blur and expose the active role/scope clearly.
2. Build institution profiles and the complete draft → scrutiny → deficiency → resubmission → decision/closure flow; add actual document upload/version/OCR-review interfaces.
3. Build the officer-selected committee → exact-member availability → explainable slots/conflict → confirmed visit → observations → human-approved record journey.
4. Build conditions/evidence/verification, renewal queues, reminders, notification attempts and escalation actions.
5. Build all eight usable report outputs and the audit explorer/integrity demonstration; reconcile counts with the same source records.
6. Complete administration, approved public content, accessibility/error/responsive checks and the PRD §20 demonstration from one coherent case.

Completion means that an authorised user can perform the specified action and see consistent downstream state/history—not merely read a description or click through to a placeholder.
