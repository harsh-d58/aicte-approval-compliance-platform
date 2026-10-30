# Frontend hosting implementation status

Policy: compact dependency plan; parallel bounded adapter, direct-page and static
hosting work; parent owns auth/providers and integration verification.

The default is now `NEXT_PUBLIC_PORTAL_MODE=demo`. Set it to `live` explicitly to
retain the Python/Supabase business API. Real Supabase password sign-in is retained
in demo mode and validates directly against Supabase; it opens the synthetic
institutional demo profile. Persona cards remain local and require no API token.
Demo credentials and live credentials use separate browser session keys.

Implemented:
- Shared IndexedDB business state across personas, expected versions, atomic
  revision comparison and cross-tab notifications; no API polling in demo.
- Existing workflow reducer, conditions/checklists, approval linking and separate
  evidence verification/closure; dashboard/report views derive from that state.
- Local file storage/preview/download and immutable version references.
- Explicit manual/sample OCR simulation; real file checksum, no server inference.
- Frozen report rows with genuine CSV/XLSX/PDF downloads in the browser.
- Web Crypto hashes for local audit events, tamper-copy verification and explicit
  local trust boundary. No claims of PostgreSQL protection in demo mode.
- Account page reset now actually resets data; record-only export explicitly
  excludes uploaded bytes. Full state+file backup/import is not implemented.
- Separate static build staging and Render demo blueprint; live deployment files
  and all existing database records are preserved.

Verification so far:
- All59frontend tests passed, including repository persistence/tamper checks,
  local page actions, provider races and static URL mapping.
- Browser test with every `/api/v1`/port8000 request blocked passed: all ten
  personas, new institution save/navigation/full reload, local audit verification
  and tamper simulation, frozen report CSV/XLSX/PDF downloads, and file upload
  whose blob survives reload. Zero attempted business API requests/page errors.
- Evidence: tmp/hosting-tests.log and tmp/hosting-browser.log.

Static validation passed: build:demo exported all60static/SSG pages. The same
backend-blocked browser test passed on the static preview at port4173, including
newly generated IDs carried by exported placeholder routes, hard reload, legacy
report deep links, file persistence, three export formats and all ten personas.
Evidence:tmp/static-demo-build.log and tmp/static-demo-browser.log.
The exported HTML/JS was checked for configured private credential values; none
were present. Static route unit tests cover nested notice IDs and fixed routes.

Preview command:from frontend, npm run preview:demo. Deployment blueprint:
render-demo.yaml, publishing frontend/out from npm run build:demo.
No hosted
services have been deleted, downgraded or deployed by this implementation.
Supabase Auth usage and static-site bandwidth/build usage retain their own quotas.

Limitations: synthetic seed data replaces the shared live dataset, local changes
are not shared across devices, reminders cannot run while the browser is closed,
and simulations are not real external delivery, OCR or security certification.

VERDICT: PASS
