# Missing frontend — post-build PRD recheck

Reviewed: **27 October 2026**, after the implementation and dashboard pass. Source: the complete 1,700-line **Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md**, v1.0, including functional requirements, business rules, reporting, acceptance criteria and the §20 demonstration. Compared against the current routes, components, models, commands, report selectors and tests.

**All 54 planned page templates now exist. This is page/demo coverage, not full PRD completion.** Several required behaviours remain partial. They are listed below separately from backend/provider dependencies. A route, seeded record or stored configuration is not sufficient evidence that the corresponding requirement is complete.

Current checkboxes: [frontend_tracker.md](frontend_tracker.md). Original pre-build audit: [26 October archive](frontend/docs/audits/2026-10-26-missing_frontend.md). Implementation evidence: [PROGRESS.md](frontend/docs/PROGRESS.md).

## 1. What was built and checked

| Area | Current demonstration behaviour |
| --- | --- |
| Public/shared | Correct Home glass blur and footer/module destinations, qualified prototype copy, animation control, five public pages, ten demo identities, scope selection, loading/error/unavailable handling and responsive navigation. |
| M1 | Draft/save/submit, assignment, sample route transitions, reasoned deficiency return/resubmission, immutable submission references, sample decisions, conditions, closure/reopen and explicit compatible migration. |
| M2 | Ten role-specific domain datasets; white glass and dimensional accents; scope display, filters/chips, status multi-selection, filter/highlight distinction, drill-through/hierarchy, focus/data dialogs, local saved views and filtered CSV export. |
| M3 | Exact officer-selected eligible members, manual availability and corrections, intersections/conflicts/freshness/lead/deadline checks, revalidation, institution/expert invitation acknowledgements, visit actions, observations/actions and template-section drafts with missing-source warnings. |
| M4/M5 | Numbered evidence and clarification links, separate human verification and closure; local files, version selection/preview/download, explicit extraction simulation and review, expiry watchlist and renewal submission/verification. |
| Supporting | Personal inbox versus authorised delivery monitor, attempts/retry, escalation resolution, eight report viewers, frozen CSV/Excel/PDF outputs, audit exploration/local SHA-256 comparison, workflow/configuration editors, user assignments, institution CSV import and job simulations. |

These behaviours use fictional browser-local state. They do not establish production authentication, authoritative issuer verification, actual provider delivery or a protected append-only server log.

## 2. Remaining frontend / local-domain work

P0 = incorrect access/data behaviour; P1 = required workflow/reporting behaviour; P2 = completeness and usability. IDs below are the current backlog and are referenced by the tracker.

| ID / priority | PRD reference | Present implementation | Remaining work and affected pages |
| --- | --- | --- | --- |
| F01 · P1 | §5.2, §9.2 | Institution profile, campuses and source-linked declarations exist. | Profile attributes still use free-text keys/string values. Add a controlled attribute catalogue with date/number/text validation and provenance; campus address/field ownership editing also needs expansion. **P07/P44**. |
| F02 · P1 | WF-01–03/07–08, BR-02/03/21/23, §10 | Published workflow selection, structural graph validation and a few guarded sample routes work. | Resolve applicability from application/institution/rule version/effective dates; prevent future-effective routes being selected early; execute the configured transition/guard/owner/SLA model. Current progression branches on known stage/status names and does not interpret arbitrary guards published by the builder. Add semantic validation and a safe unsupported-rule state. **P10/P12/P43/P44**. |
| F03 · P1 | §7.1 deficiency flow, §9.2 item resolution | A notice and versioned response can be created and resolved. | The authoring form creates one item; response text/first selected version is applied across items, and resolution is notice-wide. Add multiple items, per-item answers/version references, individual acceptance/return reasons and re-return handling. **P13**. |
| F04 · P1 | §5.4, §7.5, BR-16 | Three sample document types, immutable files/versions and local validation work. | Drive type/expiry/MIME/size/required-document rules from published configuration; add campus/scope linkage. Clarify which logical metadata can change during new-version upload rather than showing editable issuer/reference inputs that the existing-document command ignores. **P16/P44**. |
| F05 · P1 | §5.4, BR-17, §17.3 | One simulated expiry field, findings table, source preview and overall human outcome exist. | Add field/finding-level review, reviewer/time/reason provenance and quality/missing/type checks. Actual OCR/scanning is a service dependency, but its multi-field/provenance/retry states still need a complete frontend contract. **P18**. |
| F06 · P1 | §7.3 steps 4–8, §9.5, §15 | Basic candidates, explanations, no-slot escalation and confirmation revalidation work. | Add controlled scheduling horizon and required location/time constraints; explicit alternative/deadline-risk presentation; retained calculation/failed-attempt history. Recommending again currently replaces proposal rows. Postponement/replacement also needs old-versus-new booking and invitation/cancellation history, explicit reschedule/resend controls and obsolete invitation handling. **P22/P25**. |
| F07 · P1 | §7.3 step 9, BR-12/13, §17.2 | Template-section drafts flag missing sources; current versions can be reviewed/approved and corrected. | Conflicting source inputs are not detected. Questions/unresolved issues/action items are manually authored rather than generated as draft outputs. Add authorised source-type handling and historical approved-version content selection/diff, not only history metadata. Permitted transcripts require a separate approved contract. **P28/P29**. |
| F08 · P1 | §7.4–7.5, §8, §17.3, §20 steps 15–16 | Expiry/overdue views, seeded reminders/escalations, selected event notifications and retry simulations exist. | Add a configuration-driven local rule preview/scenario for reminder thresholds, repeat windows, recipients, resolution and deduplication. A due date passing does not currently execute a scanner. Connect durable scanners/outbox/workers later. Do not call seeded alert rows evidence that timer-driven reminders work. **P19/P45/P46/P48**. |
| F09 · P1 | §11.1–11.3, §17.4 | Eight permitted viewers, common/exact-column filters and real frozen downloads work. | Give each report its correct date grain: closure date, evidence due/verification period, expiry window, visit date and notification event date as applicable. The shared selector currently filters application submission dates for most child reports. Complete named range/age/coordinator/condition/institution-type filters, and join notification region filters to their source records. Reconcile all eight filtered artifacts, not just column shapes and one downloaded category. **P36/P37**. |
| F10 · P1 | §7.2 metric table, §11.3 | Scoped record/status counts, stage-age context, deadlines, overdue counts and comparison controls exist. | Add explicit time remaining/application age measures; EVC readiness-to-confirmation lead time, evidence verification duration, notification-delivery rate with denominator, committee aggregation and integration-delay age. Distinguish active applications from drafts/nonterminal records and terminal outcomes from successful completion in the metric registry. Historical comparisons must stay unavailable until coverage exists. **P04/P09**. |
| F11 · P1 | BR-18/20, §11.2, §13.4–13.5 | Business commands emit local audit rows; explorer/export and a real scoped-workspace SHA-256 baseline comparison exist. | Add target record/version/canonical-source selection, full previous/new state and relevant record-version metadata in the inspector, and audit events for actual file/report/audit downloads. `AuditEvent.version` is currently populated as 1 by new commands rather than consistently identifying the target version. Local placeholder event hashes are not a protected hash chain. **P37/P38/P39**. |
| F12 · P1 | §3.2, §5.2, §13.1 | Grant/revoke/status controls and existing scope IDs are checked. | Add approved role/scope compatibility, duplicate-assignment validation, valid-from/valid-until editing and explicit expired/revoked assignment UX. File permissions must ultimately be independently revalidated by the server. **P41**. |
| F13 · P1 | §2.1, §9.2, §16.1 | Institution CSV mapping, preview and duplicate rejection work. | Application import is absent. Add application mapping, duplicate/update reconciliation, authoritative-field ownership comparisons, review before applying changes and import result/error recovery. Actual portal synchronisation still needs approved APIs. **P47**. |
| F14 · P2 | §14, §17 | Shared errors, form validation, optimistic case/visit versions, duplicate-click blocking and several useful browser checks exist. | Add a reproducible UI scenario/error harness and automated browser journeys covering every action/role/invalid state. Task type/age filters and full stale/offline/session recovery need further work. Native dialogs, phone checks and 28 tests are not a formal WCAG/load/accessibility certification. **P05/P09/shared**. |
| F15 · P2 | §8.3–8.4, §11.2, §15 | Jobs show current status/attempt count/error with local retry/completion; exports show basic states. | Add attempt-level job history, bounded-backoff/max-retry/countdown states and conditional retry controls. Complete scheduled-report configuration and real expired-download lifecycle UI once contracts exist. Some configuration categories are stored/versioned but do not yet drive runtime behaviour. **P37/P44/P45/P46/P48**. |

## 3. Concrete defects fixed during this recheck

- **Frozen report scope:** new runs now retain the requesting role and exact assignment scope. The same expert cannot open/complete a visit-001 snapshot after switching to visit-002. Legacy unscoped seeded runs are limited to global assignments. Added a regression test; this is separate from needing real server enforcement.
- **Renewal downgrade:** both the selector and command now require a strictly newer version number. Choosing an older or equal version is rejected. Added a regression test.

These fixes do not close the broader report semantics or configurable verification gaps above.

## 4. Service, data and policy dependencies — not missing page routes

- **Identity/API security:** the user-selected Supabase Auth prototype integration, approved future SSO, server-side permissions, independent file access, transaction/idempotency/concurrency enforcement, rate limits and signed downloads (§§3,9,10,13). The live read-only shell is built, but account/grant verification remains open.
- **Files/OCR:** protected durable storage, hashing/scanning, real OCR provenance, approved issuer verification, retention and authorised transcript handling (§§5.4,13,15,16).
- **Workers/providers:** transactional outbox, deadline/expiry scanners, delivery/calendar adapters, real provider references/receipts, durable jobs and scheduled exports (§§8,10,16).
- **Audit/infrastructure:** protected append-only history, authoritative canonical hashes, optional anchoring, monitoring, approved hosting, backup/restore and security/load validation (§§13–15).
- **Approved policy and data:** applicable APH/categories, complete route/guard/SLA mapping, sign-off/composition, templates, expiry/reminder rules, metrics, retention and historical coverage (§21). These open decisions must not be replaced by invented official values.
- **Publication output:** current CSV/Excel retain Unicode; PDF uses a basic Latin font/simple layout. Multilingual publication output still needs an appropriate font/layout implementation.

## 5. §20 demonstration and verification limits

The local command test now completes a draft → scrutiny → EVC selection/scheduling → source-linked approved report → approval → condition/evidence verification → closure journey. Deficiency/version handling has separate tests. Browser checks cover draft submission, a real fictional PDF upload/preview, all ten dashboards on desktop/phone, every page family, all permitted report variants, saved views, actual Excel/PDF downloads and local integrity match/mismatch.

**The complete 20-step single-case acceptance scenario is not yet proven.** The current long command test does not combine the deficiency/OCR mismatch, timer-triggered renewal alert/escalation, generated questions/actions and all eight artifact downloads into the same coherent case. Seeded examples and separate passing tests must not be substituted for that evidence. Add the full browser journey and fixture/scenario controls after closing F02/F03/F06–F11.

Current automated evidence: **28 passing tests**, TypeScript, lint and production build. They prove their stated cases, not every transition generated by arbitrary configuration or real external-service behaviour. Broader assistive-technology/cross-browser/performance/security acceptance remains open.

## 6. Next implementation order

1. F02/F03/F04: make published configuration drive the sample workflows, document rules and per-item deficiency flow.
2. F06/F07/F08: retain scheduling history, complete meeting-record outputs and demonstrate real local timer/rule evaluation.
3. F09/F10/F11: correct date grains/metric definitions and download/source-version auditability; reconcile every exported report.
4. F01/F12/F13/F15: finish controlled institution/access data, application imports and operational retry/configuration behaviour.
5. F14 and §20: automate the complete coherent browser demonstration, then carry out broader accessibility and device acceptance.

The new frontend and dashboard work is substantial, but these open behaviours must remain visible until implemented and verified.
