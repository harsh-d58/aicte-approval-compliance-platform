# Frontend progress — 27 October 2026

## Fresh PRD recheck result

All 54 page templates are implemented, but several required behaviours remain partial. This is not full PRD completion. The complete PRD was reread after the build; F01–F15 in [missing_frontend.md](../../missing_frontend.md) now list concrete remaining UI/local-domain work separately from service dependencies. Corresponding tracker rows were reopened. The full §20 single-case browser scenario remains open. Two review defects were fixed: export runs are now bound to role and exact assignment scope, and renewals reject older/equal versions. The regression suite now has **28 passing tests**.


Current checklist: [frontend_tracker.md](../../frontend_tracker.md). Product inventory: [plan.md](../../plan.md). Historical gap audit: [missing_frontend.md](../../missing_frontend.md). Dashboard contract: [dashboards_upgrade.md](../../dashboards_upgrade.md).

## Implemented demonstration

All P01–P54 templates are present; new/edit variants share components. This is a frontend demonstration with fictional records and a fixed source clock of 26 October 2026, 12:00 IST.

| Area | Current behaviour |
| --- | --- |
| Home/public | Approved orange-to-white direction and white frosted navigation preserved; computed blur fixed; real public/help/policy/sitemap pages; linked modules; qualified prototype claims; corrected illustrative workflow; animation pause/reduced-motion treatment. |
| Institutions/applications | Scoped directory, create/profile/campuses/attributes, source verification, draft/save/submit, assignment, scrutiny, deficiencies/responses/resolution, guarded progression, reasoned decisions/conditions/closure/reopen and explicit compatible workflow migration. |
| Documents | Local PDF/PNG/JPEG validation and IndexedDB storage, preview/download, immutable versions and exact submission/evidence links, declared/extracted comparison and human assessment, renewal creation/submission/verification. Extraction is an explicit local simulation. |
| EVC/records | Officer-selected eligible committee, versioned corrections to manual availability, fresh exact-participant interval intersections, conflict/lead/deadline checks, recommendations, confirmation/invitations, acknowledgement, lifecycle actions, draft/submitted observations, source-linked questions/actions, template-bound missing-source warnings and human-reviewed immutable record corrections. |
| Compliance/communications | Numbered evidence/clarification submissions, reasoned verification, separate explicit closure/reopen, linked tasks, personal inbox, authorised delivery monitor/attempts/retry, source-linked escalations and operational job simulations. |
| Reports/audit | Eight role-permitted filtered report variants, source drill-through, frozen run snapshots and actual CSV/Excel/PDF downloads; audit explorer/export and real local SHA-256 baseline comparison, clearly separate from an authoritative ledger. |
| Administration | Scoped user assignments/status, immutable workflow clone/validation/publication, typed versioned configuration creation/edit/publication, connector status/local simulation, CSV mapping/preview/duplicate validation and local import, job retry/completion simulation. |
| Dashboards | Ten domain-specific datasets, white glass surfaces and dimensional accents, filters/chips, filter/highlight distinction, multi-select status bars, hierarchy, data/focus/record dialogs, scoped saved views, CSV export, snapshot semantics, responsive/collapsible navigation and low-effects fallback. |

## Data lifecycle

`DemoProvider` loads the adapter, then restores `aicte.demo.records.v2` from sessionStorage. Shared commands clone data and check the canonical actor, active assignment, scope, permissions, optimistic version and action guards before committing. Late actions from a changed identity/scope are rejected. Historical documents/submissions/approved records remain versioned.

Identity uses `aicte.demo.session.v1`. Refresh and role switching retain local demo records. Sign-out clears identity; it retains local records so another demo persona can continue the same journey. Account reset restores seed records and a valid baseline assignment; it clears stale action notices. Local IndexedDB files and saved analytical views remain until the browser site data is cleared. These facts are disclosed in the privacy/help pages.

## Verification

- `npm test`: 28 passing checks. They cover scope, safe routes, pending route children, permissions, canonical disabled actors, stale versions, duplicate submission, deficiencies, immutable evidence/record versions, availability corrections, scheduling, missing template sources, policy binding, compliance closure, all eight report column contracts, frozen export formats and same-user scope isolation, strictly newer renewal versions, analytics reconciliation and a coherent EVC-to-closure journey.
- `npx tsc --noEmit`, ESLint and production build pass; the build contains every planned route.
- Browser: all ten role dashboards at desktop and a 390px phone viewport, without viewport-level horizontal overflow; exact scope display; filter/highlight reconciliation; saved view save/load; data/focus dialogs; drawer Escape/focus return; low-effects computed blur fallback.
- Browser: representative draft/save/submit, real fictional PDF upload/preview, every new page family, all eight report variants under their permitted personas, real Excel/PDF export downloads, SHA-256 match and mismatch after reset, public pages and Home computed blur/footer targets. Export bytes were inspected for valid Excel ZIP/XML and PDF cross-reference/EOF with the expected records.
- These checks are representative functional validation, not a formal WCAG, penetration, load or device-lab certification. Continuous historical coverage is unavailable and is labelled accordingly.

## Preserved fixes

The overview GIF retains its responsive Avaza blur mask. Its original animation is unchanged. PendingPortal keeps nested route children mounted inside a hidden inert container during session loading/errors/redirects; Next instant-navigation validation remains enabled, with an SSR regression check.

## Remaining dependencies and limits

Production identity/server enforcement, transactional storage/outbox, approved policy, scanning/OCR, calendar/delivery providers, durable workers and authoritative audit verification require real services. Sample configuration is not approved APH policy. Historical trends/comparison require complete event coverage. Seeded report runs are metadata-only; generate a new snapshot for a real file. PDF uses a simple paginated basic Latin font; CSV/Excel preserve Unicode. Broader accessibility, cross-browser and representative-device performance validation remain external acceptance work. No current action sends real messages or changes an official record.
