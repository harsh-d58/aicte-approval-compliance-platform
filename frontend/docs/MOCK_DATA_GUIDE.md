# Demonstration data and session guide

All records are fictional. The fixed source clock is `2026-10-26T12:00:00+05:30`; displays use Asia/Kolkata. Current implementation evidence is in [PROGRESS.md](PROGRESS.md).

## Source ownership

| File | Responsibility |
| --- | --- |
| `lib/portal/types.ts` | Frontend domain models, including immutable versions and snapshot rows. |
| `lib/portal/data-source.ts` | Adapter used by the provider; clones the baseline. |
| `lib/portal/mock-data.ts` | Clearly fictional baseline and sample policy. |
| `lib/portal/commands.ts` | Local transactional action validation and downstream state/history updates. |
| `lib/portal/view-models.ts` | Fixed clock, display labels, safe routes and scope selection. |
| `lib/portal/analytics.ts` | Ten domain datasets and validated coordinated dashboard queries. |
| `lib/portal/report-rows.ts` | Eight report selectors consuming supplied scoped data, including local edits. |
| `lib/portal/mock-reports.ts` | Baseline-only adapter convenience wrapper. |
| `lib/portal/exports.ts` | Real CSV, OOXML ZIP workbook and simple paginated PDF writers. |
| `lib/portal/files.ts` | Browser-local file storage and object-URL downloads. |
| `app/portal-ui/DemoProvider.tsx` | Canonical identity/scope context, shared records, persistence/reset and guarded command dispatch. |
| `tests/portal-scope.test.mjs` | 28 pure/domain and rendering regression checks. |

## Sessions, scopes and persistence

Choose one of ten fictional roles at `/login`. Experts have separately selectable visit assignments. Institution, region, owned scrutiny case and visit scope selectors run before display. Expert views exclude institution-wide documents/evidence. Personal inboxes remain recipient-only; authorised global delivery monitoring is separate. Export runs are bound to requester, role and exact scope, so another identity or another assignment cannot open a broader frozen snapshot. Legacy unscoped runs are visible only to global assignments. Operational queues require the system persona.

Session identity is stored at `aicte.demo.session.v1`. Local record state uses `aicte.demo.records.v2` and survives refresh/role switching in the tab. Sign-out removes identity, while records remain available for a demonstration journey across roles. Account reset removes the local record snapshot and restores the seed with a valid baseline assignment. File blobs are stored in IndexedDB; analytical view definitions use versioned per-user/role/scope localStorage keys. Clear this site’s browser data to remove files/preferences. No real credentials or records should be supplied.

## Supported local actions

Forms exercise actual local draft/submission, review/deficiency/decision, document versions, scheduling/availability, observations/approved records, evidence/verification/closure, workflow/configuration versions, imports, retries and export snapshots. Failed permission/version/guard checks leave the shared record unchanged and retain input. Upload never verifies evidence, completes renewal or closes compliance automatically.

File metadata checks are local type/size validation, not malware scans. OCR forms explicitly accept simulated extracted text. Connector tests, queue completion and invitation delivery are labelled local simulations. No email/SMS/calendar provider or authoritative ledger is contacted. Local SHA-256 comparison checks the chosen browser baseline only. Approved meeting-record versions are retained when creating a reasoned correction.

Report exports capture filtered rows before completion. Seeded completed runs have metadata only; create a new run to obtain actual files. CSV escapes formula-like values, Excel uses inline strings, and PDF currently uses a basic Latin font/simple paginated layout. Continuous historical coverage is not present; historical performance comparisons remain unavailable.

## Replacing the adapter

Retain typed UI models and selectors where useful. Replace fixture/session controls with the approved identity provider and scoped server queries; enforce authorisation, assignment validity and versions on the server. Do not deliver all real institutions to the browser and filter them client-side. Replace commands with transactional mutations, storage/scanning/OCR/provider contracts, durable outbox/workers and audit services. Replace the fixed clock and sample APH configuration with approved contracts. Remove mock data, identities and local simulations only after their live replacements are ready.

The post-build PRD recheck found further UI/local-domain gaps F01–F15; consult `../../missing_frontend.md` rather than assuming every stored configuration drives execution or every route completes its PRD behaviour.
