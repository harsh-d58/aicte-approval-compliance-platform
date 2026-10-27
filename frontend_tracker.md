# Frontend implementation tracker

This file tracks all 54 planned page templates and the dashboard upgrade. It covers the missing frontend work first, then the glassmorphism, dimensional visuals and interactive analytics requested for all dashboards.

**Checked = the stated frontend item is implemented and checked. Unchecked page rows below already have a working template, but still have identified PRD behaviour left.** All 54 page templates exist; this is not a feature-completion percentage. Fresh full-PRD recheck: 27 October 2026. See F01–F15 in [missing_frontend.md](missing_frontend.md).

## Public pages

- [x] **P01 · Home** — Platform overview, modules, workflow, innovations and entry into the demo.
- [x] **P50 · Help & support** — Explain how to use the demo and where production support information belongs.
- [x] **P51 · Privacy** — Explain prototype data storage and handling without claiming an approved official policy.
- [x] **P52 · Accessibility** — Describe keyboard access, motion controls and known limitations.
- [x] **P53 · Website policies** — Explain prototype ownership, external links and sample content.
- [x] **P54 · Sitemap** — Provide working navigation to the public pages and portal modules.

## Access and shared workspace

- [x] **P02 · Sign in** — Choose one of ten fictional demo roles and enter an authorised scope.
- [x] **P03 · Role & scope** — Review assignments and switch the active institution, region or visit.
- [ ] **P04 · Dashboard** — Show role-dependent counts, priorities and links from scoped data. Upgrade tracked below. **Partial:** F10 — remaining metric definitions/time/denominators and freshness detail.
- [ ] **P05 · My tasks** — Search assigned tasks, review status and inspect task context. **Partial:** F14 — task type/age filtering and full failure/recovery coverage.
- [x] **P32 · Notifications** — Personal inbox with read/unread controls and linked source cases.
- [x] **P33 · Notification detail** — Recipient, channel, delivery attempts, failures and authorised retry.
- [x] **P34 · Escalations** — Review overdue or blocked work and resolve escalations after the source issue is resolved.
- [x] **P49 · Account & session** — Identity, assignments, demo reset and sign-out.

## Institutions and applications

- [x] **P06 · Institution directory** — Search institutions, regions and campuses within the current scope.
- [ ] **P07 · Institution profile** — View and edit profile details, campuses and source-linked attributes. **Partial:** F01 — controlled typed profile attributes and expanded campus/ownership fields.
- [x] **P08 · Create institution** — Create an authorised institution and primary campus with duplicate validation.
- [ ] **P09 · Application register** — Search, filter, sort and page through scoped applications. **Partial:** F10/F14 — complete age/time filtering and validated recovery cases.
- [ ] **P10 · New / edit application** — Save and resume drafts, choose a sample workflow and submit a declaration. **Partial:** F02 — applicable/effective workflow resolution, not just a manual published-route choice.
- [x] **P11 · Application detail** — Inspect case status, timeline, submissions, documents and linked EVC/compliance records.
- [ ] **P12 · Scrutiny & workflow actions** — Review documents, assign ownership and make guarded stage transitions. **Partial:** F02 — execute configured guards, owners and SLAs for arbitrary supported routes.
- [ ] **P13 · Deficiency notice & response** — Issue corrections, submit exact evidence versions and resolve reviewed items. **Partial:** F03 — per-item authoring, responses/version links, resolution and re-return.
- [x] **P14 · Decision & closure** — Record authority/reasons, create approval conditions, close or reopen an eligible case.

## Documents and renewals

- [x] **P15 · Document registry** — Search document metadata, verification, versions and declared expiry dates.
- [ ] **P16 · Register / upload document** — Validate local files and declared metadata; preserve immutable versions. **Partial:** F04 — configuration-driven document rules, campus/scope linkage and metadata behaviour.
- [x] **P17 · Document detail** — Preview/download available files and inspect exact historical versions.
- [ ] **P18 · Document checks** — Compare declared/extracted fields and record reasoned human review. **Partial:** F05 — field/finding-level review and full extraction/provenance states.
- [ ] **P19 · Expiry & renewal queue** — Track expiring documents and renewal cases separately from non-expiring categories. **Partial:** F08 — threshold-driven reminder/scanner preview and event generation.
- [x] **P20 · Renewal case** — Submit a newer document version and obtain explicit human verification.

## Expert visits and meeting records

- [x] **P21 · EVC queue** — List visit readiness, selected committee size, coordinator and deadline.
- [ ] **P22 · EVC visit workspace** — Bring together committee, schedule, invitations, records and event history. **Partial:** F06 — retained scheduling/invitation/reschedule history.
- [x] **P23 · Committee selection** — Let the officer select the required eligible experts and record replacement reasons.
- [x] **P24 · Availability** — Record expert/institution availability and busy periods with freshness information.
- [ ] **P25 · Slot recommendations** — Explain feasible/blocked slots, revalidate availability and confirm a chosen slot. **Partial:** F06 — scheduling horizon/constraints, alternatives and failed-attempt history.
- [x] **P26 · EVC calendar** — View confirmed visits and proposals by month with clear sync status.
- [x] **P27 · Observations & completion** — Submit authorised criterion observations and record visit completion.
- [ ] **P28 · Generate draft meeting record** — Generate minutes or EVC-report drafts from submitted source observations. **Partial:** F07 — conflicting inputs and generated questions/actions.
- [ ] **P29 · Meeting-record editor** — Edit source-linked sections, request changes, approve and preserve correction versions. **Partial:** F07 — historical approved-version content selection/diff.

## Compliance

- [x] **P30 · Compliance queue** — Review approval conditions, deadlines and separate overdue flags.
- [x] **P31 · Condition & evidence** — Submit versioned evidence, respond to clarification, verify and explicitly close/reopen.

## Reports and audit

- [x] **P35 · Report catalogue** — List permitted report outputs and export runs.
- [ ] **P36 · Report viewer** — Filter scoped rows, inspect source records and generate a snapshot. All eight variants below are required. **Partial:** F09 — correct per-report date grains, named range filters and reconciliation.
  - [x] Region performance
  - [x] Application pendency
  - [x] EVC status
  - [x] Undertaking compliance
  - [x] Document validity
  - [x] Overdue actions
  - [x] Notification delivery
  - [x] Case closure
- [ ] **P37 · Export run & download** — Show job state, snapshot metadata and usable CSV, Excel and PDF downloads. **Partial:** F09/F11/F15 — report semantics, audited downloads and scheduled/expired lifecycle.
- [ ] **P38 · Audit explorer** — Search actor/action/reason/time/version/correlation history and export permitted events. **Partial:** F11 — full target-version/state metadata and export auditability.
- [ ] **P39 · Integrity verification** — Demonstrate local fingerprint match/mismatch and distinguish it from an authoritative audit service. **Partial:** F11 — exact record/version canonical verification, beyond a whole-scope baseline.

## Administration

- [x] **P40 · User directory** — Inspect demo users, status and assignments.
- [ ] **P41 · User & scoped assignments** — Grant/revoke authorised role assignments with explicit scope and reason. **Partial:** F12 — role/scope compatibility, assignment dates, duplicate/revoked states.
- [x] **P42 · Workflow catalogue** — Inspect published/draft versions and preserve existing case bindings.
- [ ] **P43 · Workflow builder** — Edit stages/transitions, validate a draft and publish a version with an effective date. **Partial:** F02 — semantic validation that matches the executable workflow engine.
- [ ] **P44 · Regulatory & reference rules** — Edit versioned sample APH, document, committee, template and retention settings. **Partial:** F01/F02/F04/F15 — configuration schemas and runtime binding.
- [ ] **P45 · Notification rules** — Configure sample events, channels, recipients and templates. **Partial:** F08/F15 — template/rule preview and configuration-driven dispatch.
- [ ] **P46 · Escalation rules** — Configure sample thresholds and escalation levels. **Partial:** F08/F15 — repeat/window/channel/resolution rules and execution preview.
- [ ] **P47 · Integrations & imports** — Inspect freshness, failures and field ownership; exercise explicit local integration simulations. **Partial:** F13 — application import and authoritative update reconciliation.
- [ ] **P48 · Jobs & operational health** — Inspect queued/failed jobs and exercise authorised retry operations. **Partial:** F08/F15 — attempt history and bounded retry/scanner execution states.

## Open PRD behaviour backlog

Each item below remains unchecked even though its page templates exist. Full evidence and PRD references are in `missing_frontend.md`.

- [ ] **F01** Controlled typed institution attributes, campus fields and ownership.
- [ ] **F02** Applicable/effective workflow resolution and executable configured guards/owners/SLAs.
- [ ] **F03** Multiple deficiency items with individual responses, version links and resolutions.
- [ ] **F04** Configuration-driven document requirements/type limits and campus/scope metadata.
- [ ] **F05** Per-field/finding review, provenance and full extraction/retry states.
- [ ] **F06** Scheduling constraints, alternatives, retained attempts and booking/invitation history.
- [ ] **F07** Conflicting-source detection, generated questions/actions and historical record content.
- [ ] **F08** Threshold/recipient/repeat/deduplication rule preview and timer-triggered demonstration.
- [ ] **F09** Correct report date grains, named range filters and all-eight artifact reconciliation.
- [ ] **F10** Complete dashboard time/lead/verification/delivery/committee/freshness metric definitions.
- [ ] **F11** Canonical record/version verification, target audit metadata and audited downloads.
- [ ] **F12** Role/scope compatibility, assignment validity/duplicate/revocation controls.
- [ ] **F13** Application import, authoritative update mapping and reconciliation.
- [ ] **F14** Error/scenario harness, remaining filters and complete automated browser acceptance.
- [ ] **F15** Attempt-level job history, bounded retry states and scheduled/expired export lifecycle.
- [ ] **PRD §20** One coherent browser journey covering all 20 steps, including triggered renewal/escalation and all eight downloads.

## Existing-page improvements and shared checks

These checkboxes describe the completed implementation pass. They do not close the F01–F15 PRD gaps above.

- [x] Correct Home navigation blur, footer links, module destinations, prototype claims and workflow sequence.
- [x] Expand navigation and make the active institution/region/visit clear throughout the portal.
- [x] Connect case/task/inbox links to the new action workspaces and exact evidence versions.
- [x] Add validated filters, deadline times, age and overdue durations where relevant.
- [x] Verify role/action permissions, version conflicts, guarded transitions and immutable histories.
- [x] Verify local upload/preview, scheduling collisions, evidence verification and export reconciliation.
- [x] Check responsive layouts, keyboard navigation, focus, reduced motion and readable contrast.
- [x] Run TypeScript, lint, automated tests and production build; fix failures.
- [x] Update progress and dependency notes to match actual implemented behaviour.

## Dashboard upgrade — shared visual/interaction pass

The visual and interaction foundation below is built. P04 remains unchecked for the additional business metrics and reconciliation in F10.

The dashboard upgrade follows `dashboards_upgrade.md`: translucent white surfaces, restrained depth and interactive analytics that reconcile with the underlying records.

- [x] Shared glassmorphism design tokens, readable white surfaces and consistent navigation.
- [x] Dimensional decorative elements and restrained motion with reduced-motion support.
- [x] Shared date, region, institution, type, owner and status filters with clear reset behaviour.
- [x] Interactive charts, chart selection/cross-filtering and source-record drill-through.
- [x] Saved views scoped to the demo identity/role/assignment.
- [x] Accessible data-table alternatives, chart focus view and usable exports.
- [x] Honest snapshot/freshness labels, empty states and reconciled metrics.
- [x] **Institution dashboard** — Applications, deficiencies, evidence obligations and document validity.
- [x] **Scrutiny dashboard** — Assigned review queue, stage age, deadlines and review workload.
- [x] **Regional dashboard** — Regional pendency, officer workload, EVC readiness and escalation priorities.
- [x] **EVC coordinator dashboard** — Availability, slot blockers, confirmations and record preparation.
- [x] **EVC expert dashboard** — Assigned visits, invitations, availability and observations/review work.
- [x] **Compliance dashboard** — Evidence submissions, overdue conditions, verification and closure.
- [x] **Central dashboard** — Regional comparisons, bottlenecks, performance and report drill-through.
- [x] **Policy dashboard** — Workflow publication, configuration versions and validation work.
- [x] **Auditor dashboard** — Event history, case traceability and integrity inspection.
- [x] **System dashboard** — Job failures, delivery attempts, integration freshness and retries.
- [x] Check all ten desktop/mobile layouts; verify shared keyboard controls and low-effects fallback; implement reduced-motion styling. Formal assistive-technology/device-lab acceptance remains below.

## Remaining service and validation work

- [ ] Connect approved production identity, scoped server APIs and transactional mutations.
- [ ] Connect approved file storage/scanning, real OCR, calendars, delivery providers and durable export workers.
- [ ] Replace sample APH rules, authority mappings, deadlines, templates and retention with approved policy.
- [ ] Supply complete historical coverage before enabling reliable trends and prior-period comparisons.
- [ ] Conduct formal accessibility, assistive-technology, cross-browser and representative-device performance validation.
- [ ] Extend PDF export beyond its current basic Latin font/layout when multilingual publication output is required.

## Service dependencies

Production identity, server-side authorisation, transactional storage, malware scanning, OCR execution, external calendars/messaging, durable export workers and authoritative audit verification remain external dependencies. Sample policy values require approved PRD/APH decisions. They are not marked complete merely because the frontend offers a clearly labelled local demonstration.

## Latest verification — 27 October 2026

- `npm test`: 28 checks pass, including a coherent draft → scrutiny → EVC → approved record → decision → evidence verification → closure journey.
- TypeScript, ESLint and production build pass. All planned routes are included in the build.
- Browser: all ten dashboards on desktop and 390px phone viewport; no viewport-level horizontal overflow; filter/highlight reconciliation; focus/data dialogs; saved-view save/load; mobile drawer Escape/focus restoration; low-effects blur fallback.
- Browser: new draft/save/submit; real fictional PDF upload and local preview; every new page family; all eight report variants under permitted roles; real Excel/PDF downloads; SHA-256 match/mismatch after local data reset; public pages and Home blur/link correction.
- Export inspection: Excel ZIP CRCs/XML/rows and PDF header/xref/EOF/rows verified. Full formal accessibility and performance certification remains unchecked above.

## Fresh PRD recheck

The full PRD was reread after implementation. Page rows with remaining behaviour have been reopened rather than claiming completion from route existence. Use F01–F15 in `missing_frontend.md` as the next build backlog. The original complete §20 single-case browser demonstration is still an acceptance task; separate passing examples do not replace it. Scope-bound frozen exports and strictly newer renewal versions were fixed during the recheck, bringing the suite to 28 tests.
