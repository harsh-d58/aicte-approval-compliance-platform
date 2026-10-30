# SETU hosting optimization and frontend mock migration

Date: 30 October 2026. Status: plan below plus implemented frontend demo mode. See the implementation update at the end for verified behavior and deployment limits. No hosted services or live database records were changed by the optimization.

## 1. Objective and scope

Remove the need to pay for Render backend compute, workers and persistent disks for the first prototype. Keep the portal interactive: a user action must update the corresponding case, dashboard, queue and history. Replace hosted backend operations with a coherent browser mock implementation rather than disconnected hardcoded green badges.

Preserve the existing ten demo personas and Supabase password authentication, as previously requested. Supabase authentication is the exception to the frontend-only target: it remains an external service with its own availability and quotas. Demo persona cards must work without the Python API.

The request changes the earlier requirement that every feature write live Supabase data. In the proposed hosted demo, business actions persist in the browser and **do not update Supabase**. Retain the live implementation as a separate, explicit mode for later use. Do not silently fall back from a failed live request to a fabricated successful result.

Deliverable for this first step: this complete plan. Implementation, production deployment and removal of existing hosted resources are subsequent steps; none is claimed complete here.

## 2. What actually costs money

### Repository evidence

`render.yaml` declares only `aicte-backend`: Python web service, `plan: free`, `pip install -r backend/requirements.txt`, and Uvicorn. There is no declared disk, worker, cron service, Render Postgres or Redis/Key Value instance. The frontend deployment is not declared in that file. A dashboard-created paid service or plan override cannot be inferred from the repository.

**No module automatically upgrades Render or incurs a separate module fee.** Paid compute is a service-plan choice. Resource-heavy components can make the free instance unsuitable; a worker or disk requires separately provisioned infrastructure. Actual charges require checking the Render dashboard and invoice. This audit did not access billing, deployed service settings or production metrics.

| Cost category | Current evidence | Optimization |
|---|---|---|
| Python web compute | One free service declared | Static mock frontend can remove the API dependency entirely |
| Larger CPU/RAM | OCR and report processing need measurement; no larger plan declared | Mock extraction and browser exports remove the server workloads |
| Persistent storage | Uploads, scan sidecars and local keys use the backend filesystem; no disk declared | Store demo uploads in IndexedDB and ship public fixture assets |
| Background workers | Worker code exists, but is absent from the Render blueprint/start command | Run deterministic demo job actions in the browser |
| Cron | Deadline/expiry scanning code exists; no Render cron declared | Recalculate on opening the app and on explicit demo job actions |
| Database | Runtime connects to external Supabase Postgres | Local business state avoids business queries/writes; Auth remains separate |
| Email/SMS | Optional SMTP and HTTPS SMS providers, guarded by explicit send settings | Simulated outbox and delivery receipts; no external sends |
| Paid AI/OCR API | No paid AI API integration identified in the audited application | Existing OCR is local software, not a per-call AI provider bill |
| Build minutes and bandwidth | Python packages/models and frontend assets consume platform resources | Deploy frontend assets only; avoid large fixture files and frequent redeploys |

### Verified platform constraints

Render's free web service sleeps after 15 minutes without inbound traffic, and wake-up takes about a minute. Its filesystem is ephemeral; free web services cannot attach persistent disks. These explain why keeping uploaded documents and runtime keys locally is unsuitable for a durable free deployment. [Render free services](https://render.com/docs/free)

Static sites use Render's CDN without an application server. Bandwidth and build usage still count against workspace allowances; this is not a promise of unlimited zero-cost usage. [Render static sites](https://render.com/docs/static-sites)

Persistent disks require paid eligible services. Render cron has a minimum monthly charge of $1 per cron service, plus usage rules. Neither is needed for the proposed demo. [Persistent disks](https://render.com/docs/disks), [cron billing](https://render.com/docs/cronjobs)

No monthly savings figure is asserted without the actual bill. Intended topology: one static frontend, existing Supabase Auth, zero Render API/worker/disk/cron services required by the demo. Avoid replacing the removed API with an always-on Next.js server and calling that a static deployment.

## 3. Complete backend component disposition

All paths below are under `backend/app/`. Modules grouped in one row share a replacement boundary. CPU/RAM pressure is a qualitative assessment from implementation, not a benchmark or a confirmed paid deployment.

| Components | Present responsibility / hosting pressure | Hosted prototype replacement |
|---|---|---|
| `main.py`, `settings.py`, `__init__.py` | FastAPI routes, middleware, CORS, health/readiness and server config; base Python process | Static app bootstrap, explicit demo mode and local readiness state; no health pings |
| `database.py`, `accounts.py` | PostgreSQL connectivity, active account/profile and permission reads | Bundled synthetic users/grants; Supabase Auth maps authenticated subject to a local demo profile |
| `auth.py` | JWT/JWKS validation | Keep Supabase sign-in/session lifecycle; remove dependency on Python `/me` for demo navigation; backend validation stays in live mode |
| `prototype.py` | Server-issued development persona tokens and local signing key | Stable local persona IDs and selected role/scope; no server token/key needed for demo cards |
| `authorization.py` | Scoped server authorization and role rules | Client role/scope filtering for demonstration only; not real data protection |
| `transactions.py`, `concurrency.py`, `idempotency.py` | Atomic writes, optimistic versions, request replay protection | Atomic local state reducer, expected-version checks and persisted command IDs |
| `institutions.py`, `users.py` | Institution/campus/profile management, grants and account status | Local records, linked updates, local role permissions; cannot edit real Supabase accounts |
| `applications.py`, `workflows.py`, `configurations.py` | Applications, configured transitions, published policy versions | Browser state machine preserving the current workflow and transition guards |
| `deficiencies.py` | Itemized notices, exact-version responses and resolution | Same notices/items/version relationships and role-specific queues in the reducer |
| `evc.py` | Expert membership, availability, conflict checks, ranked slots and visits | Deterministic browser slot calculation, persisted confirmation and visit lifecycle |
| `meeting_records.py` | Source-backed report drafts, versioning, review and approval | Local immutable source manifests and report versions; human actions remain explicit |
| `decisions.py`, `decision_lifecycle.py` | Authorized decisions and closure prerequisites | Local Approve/Reject/Close transitions; keep conditions open after approval |
| `compliance.py` | Undertakings, evidence versions, verification and closure | Local submissions/verifications with independent persona actions and linked history |
| `documents.py`, `portal_files.py` | Document registration, immutable versions and uploaded bytes | IndexedDB blobs and document metadata; preserve exact version IDs and preview/download |
| `storage.py` | Files, signed downloads, checksums, ClamAV/Defender scan status and HMAC key | Blob URLs and SHA-256 checksums in browser; simulated scan status clearly identified |
| `ocr.py`, `ocr_engine.py`, `ocr_fixtures.py` | PDF rendering, Tesseract/RapidOCR inference, source extraction and comparison | Fixture extraction for sample files; editable simulated extraction for arbitrary files; no server inference |
| `portal.py`, `portal_snapshot.py`, `portal_commands.py` | Full projection, scoped snapshots and portal command bridge | Single browser repository and command adapter; dashboards derive from the same state |
| `dashboards.py`, `report_projection.py`, `report_catalog.py` | Role dashboards and report projections/filter rules | Existing TypeScript metrics and report-row functions over local state |
| `reports.py`, `report_exports.py` | Report runs, frozen snapshots and CSV/XLSX/PDF bytes | Local report snapshots and actual supported browser downloads; never fake a file extension |
| `notifications.py`, `outbox.py`, `outbox_worker.py` | Notifications, queues, retries, deadline/renewal scans and dispatch | In-app notices, explicit simulated processing and deterministic due-date evaluation |
| `communications/dispatcher.py`, `email_provider.py`, `sms_provider.py` | Optional external message submissions | Local previews and simulated outcomes only; remove credentials from demo deployment |
| `communications/jobs.py`, `policy.py`, `receipts.py`, `__init__.py` | Delivery leases, approved send policy and receipt validation | Local job history; simulated accepted/delivered/failure states, no provider webhooks |
| `audit.py`, `records.py` | Hash-chained audit append, ledger verification, scoped reads and trigger inspection | Browser-local event chain and Web Crypto verification; explicit demo trust boundary and unavailable database-trigger check |

Backend migrations, seeding, recording-preparation and acceptance scripts remain development/live tooling. Do not run them from frontend hosting, ship their credentials, or delete their historical migrations to reduce runtime cost.

## 4. Highest-priority resource and deployment issues

1. **OCR dependency weight.** `requirements.txt` includes ONNX Runtime, OpenCV, NumPy, RapidOCR, Pillow, PDFium, Tesseract bindings, Shapely and related native packages. `ocr_engine.py` caches an OCR engine and executes local recognition/rendering. This increases build size, startup and runtime resource needs. Tesseract bindings do not themselves install the native Tesseract binary. Mocking this domain removes the entire Python OCR stack from the demo deployment.
2. **Runtime file persistence.** `storage.py` writes under `backend/storage/documents`; generated secret files and scan sidecars also depend on local persistence. A free Render restart can leave database metadata pointing to missing bytes. Browser files avoid this server/disk mismatch for the demo. Download availability remains limited to that browser unless assets are bundled.
3. **Scanning is a separate dependency.** Defender is Windows-specific; ClamAV requires a working scanner endpoint. Do not claim a file is actually malware-clean because a demo timer completed. A lightweight mock scan replaces infrastructure, not the security guarantee.
4. **Worker is not part of Uvicorn.** `outbox_worker.py` is a separate loop/process. Uploading it with the web app does not schedule reminders or deliver queued notifications. Use local demo processing instead of adding a paid worker/cron.
5. **Broad repeated reads.** `portal_snapshot.py` aggregates the projection tables; the frontend polls and refreshes this snapshot. In demo mode there should be no snapshot requests or repeated database TLS connections at all. Use state subscriptions after mutations, not 30-second API polling.
6. **Audit and exports grow with data.** Full-ledger verification and report generation use CPU/memory; the code does not establish that either individually requires a paid plan. Local verification and bounded sample data remove this server load.
7. **Startup settings and signing keys.** The Render blueprint sets `APP_ENV=development` and does not declare every optional scanner/prototype/signing setting. Do not treat a working local environment as a complete deployed configuration. A static demo needs no backend database URLs or signing secrets.

## 5. Target architecture

```text
Static portal assets on Render CDN
  +-- Supabase Auth adapter: real password sign-in, refresh, sign-out
  +-- Demo persona adapter: original ten cards, no API token
  +-- Portal repository: synthetic seed + persisted local changes
  +-- Commands: validated local transitions -> one atomic next snapshot
  +-- Views: scoped dashboards, registers, detail pages, reports
  +-- IndexedDB: state, blobs, immutable versions, export snapshots
  +-- Browser workers / Web Crypto: optional hashing and simulated job processing
```

Local data should be versioned and namespaced by demo dataset, not by persona: changing Ananya to Nisha must show the evidence Ananya just submitted. Derive role views from one shared local state. Partition separate demo installations/datasets explicitly; changing real accounts must not expose imported private data. Ship synthetic public-safe fixtures only.

Keep runtime boundaries explicit: proposed `NEXT_PUBLIC_PORTAL_MODE=demo|live` selects an adapter. Never place `DATABASE_URL`, runtime/write URLs, service-role keys, SMTP/SMS credentials or signing secrets in public configuration. Demo mode makes no business API calls. Live mode continues using the existing backend and its server authorization.

### Existing implementation to reuse

- `frontend/lib/portal/types.ts`: collection and relationship contracts.
- `frontend/lib/portal/mock-data.ts`: existing seed, after scenario/ID validation.
- `frontend/lib/portal/data-source.ts`: seed reader contract; currently reads fresh clones, so it is not a persistent mutable repository yet.
- `frontend/lib/portal/commands.ts`: existing `applyCommand`, role rules and domain transitions. Review parity with recent backend repairs before connecting it.
- `frontend/lib/portal/view-models.ts`, `dashboard-metrics.ts`, `analytics.ts`, `report-rows.ts`: scope, filtering and derived data.
- `frontend/lib/portal/files.ts`: existing IndexedDB blob store. Its comment says files stay local, but current live document commands subsequently upload them; comments are not proof of network isolation.
- `frontend/lib/portal/exports.ts`: inspect actual supported formats and reuse them where correct.

Do not simply change `DemoProvider` to import a static seed. That would leave direct API consumers broken and lose changes between navigation/reloads.

### Frontend changes required

| Boundary | Required change |
|---|---|
| `LiveProvider.tsx`, `LiveLogin.tsx`, login page | Separate real Supabase session from business profile loading; demo persona login must not call `/prototype/session` or `/me` |
| `DemoProvider.tsx` | Use selected data adapter; remove polling in demo; persist local mutations; preserve role switching and loading/error recovery |
| `lib/live/commands.ts` and local command reducer | Keep live adapter; route demo commands to validated local reducer with parity for all command kinds |
| `DocumentPages.tsx`, `CorrectionEvidencePicker.tsx` | Local immutable blob versions and exact-version evidence links; no download-token endpoint in demo |
| `OcrTester.tsx` | Browser file selection, sample-based simulated extraction and honest status/field comparisons |
| `ReportPages.tsx` | Browser report runs, frozen scoped data and valid downloadable formats; no Python export endpoint |
| `AuditPages.tsx`, `AuditVerification.tsx` | Local chain verifier and separate tamper copy; show local provenance, not server/database protection |
| `LivePortal.tsx` | Audit legacy route usage and either adapt or exclude it from demo navigation; no hidden live requests |
| `PortalShell.tsx` and login copy | Replace “Live Cloud Workspace”, “saved to Supabase” and similar claims with “Demo workspace / saved in this browser” in demo mode |
| `next.config.ts`, dynamic route pages, Render blueprint | Produce a genuinely static deployment with working deep links and newly created local IDs |

## 6. Preserve the full workflow, not only screen appearance

| Demo phase | Minimum working browser behavior |
|---|---|
| Intake | Create/edit/submit application, attach actual local files, update institution dashboard |
| Scrutiny | Issue itemized notice; bind it to this application and exact document types |
| Rectification | Attach selected new versions; save narrative; update notice and scrutiny queue |
| EVC referral | Resolve the items; apply the configured stage transition |
| Scheduling | Select five experts, show conflicts/availability, generate and confirm a valid slot |
| Inspection | Save/submit observations under the assigned expert scope |
| Report | Generate source-backed version, submit, approve, update the same application's stage |
| Decision | Add condition, preserve evidence checklist, manually approve/reject; do not equate approval with closure |
| Compliance | Institution evidence -> Nisha verification -> explicit condition closure; independent steps |
| Reporting | Dynamic counts/filtering from the updated state, frozen run snapshot and real file download |
| Audit | Append actual demo commands; recalculate chain digests; simulation detects an altered copy |
| Policy | Draft/publish versioned workflow and guards; preserve existing case workflow references |
| Administration | Local demo role/job/integration controls that update local data, without changing real Auth users |

Use one coherent institution/application/visit/report/condition chain for the recording scenario. The existing Phase07/08 script uses conflicting application captions: fix the seed and guide together, rather than silently moving historic live records. Preserve the live demo database as-is.

## 7. Persistence, files, exports and trust limits

- Persist state and blobs in IndexedDB, with schema version, dataset ID, revision and migration. Handle quota/denied-storage errors without reporting a successful save.
- Offer Export demo state, Import demo state and Reset demo. Include file blobs in backups or explicitly report omitted files; validate imports and references before replacing state.
- Use same-origin cross-tab change notifications and revisions; prevent concurrent tabs overwriting newer state. Cross-device/shared-user collaboration is not provided by a local mock.
- Keep local uploaded PDF/PNG/JPEG bytes available for previews and downloads, validate size/type, and revoke object URLs when done.
- Mock OCR must distinguish known sample results from arbitrary uploads. Do not invent extracted text as actual recognition or issuer verification. Optional real browser OCR is a separate, larger enhancement with its own download/performance cost.
- Browser CSV is straightforward; XLSX and PDF must be genuine formats or be marked unsupported until implemented. Keep scope/filter/run snapshots consistent with the displayed report. Do not rename JSON/HTML as XLSX/PDF.
- A browser SHA-256 chain can demonstrate tamper detection, but the browser owner can rewrite both data and hashes. It is not a regulator's immutable ledger, PostgreSQL trigger protection or independently anchored verification. Show this limitation near demo verification.
- Client role filtering is demonstration behavior, not authorization for confidential records. Real Supabase Auth does not make a fully editable local store trusted.
- Deadlines/reminders can evaluate while the site is open or on next load. They cannot promise delivery while the browser is closed. Simulated email/SMS is visible in-app and never sent externally.

## 8. Static hosting: necessary route work

The current Next.js configuration enables cache components/partial prefetching and default image optimization; it does not specify `output: 'export'`. The current build's partial prerender output is not proof that a static site works. There are 21 dynamic detail route patterns, including nested application notices, visits, documents and records, and no `generateStaticParams` implementation was found in the route scan.

Next.js static export requires handling dynamic paths and unsupported server features. Its default image optimizer is not available as a static service; use unoptimized images or an appropriate loader. Check the installed Next16 documentation before changing cache/partial-render options. [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports)

Preferred prototype route strategy: fixed exported shell routes with query-string IDs for mutable records, or a deliberate client-side route dispatcher behind a static shell. Preserve existing recording URLs through explicit redirects/rewrites where feasible. Choose and test one approach before changing navigation globally. Pre-generating only known fixture IDs fails when a user creates a new application/document; a blanket fallback to `/index.html` does not automatically provide Next dynamic-route semantics.

Target Render configuration after the export is proven: static runtime, frontend build command, publish the actual static `out` directory, no Python install/start command and no database secrets. Derive exact blueprint syntax from Render documentation during implementation. Do not overwrite the live deployment blueprint until the static preview passes.

## 9. Implementation sequence and completion gates

| Step | Work | Completion evidence |
|---|---|---|
| 0 | Record bill/deployment inventory, baseline live/demo workflows and public-safe seed | Service list and baseline artifacts; unknown billing values remain unknown |
| 1 | Add explicit demo/live adapter and local repository; preserve Auth and persona keys | Demo login + reload + role change work while API is stopped |
| 2 | Wire all command kinds, persistence, scope and expected versions | One command updates register, dashboard, task and history; stale changes rejected |
| 3 | Complete documents, file preview, mock OCR, scheduling, reports and local audit adapters | Zero hidden live endpoint dependencies; valid file downloads |
| 4 | Validate one full recording scenario and update UI provenance/script | All thirteen phases navigate coherently with state carried across personas |
| 5 | Resolve static routes/export/images and build a separate static preview | Direct deep links, reloads and newly created local IDs work on preview |
| 6 | Deploy validated static frontend and validate browser/network behavior | Static publish artifact; no Uvicorn/Next server required |
| 7 | Retire unnecessary hosted backend resources after cutover | Actual dashboard inventory confirms intended services stopped/removed and billing checked |

Keep existing backend files/migrations and the live adapter. Removing code is not required to stop hosted compute. Do not delete Supabase data, revoke live credentials or remove hosted resources before preserving rollback and validating the frontend replacement.

## 10. Acceptance checklist

- [ ] Original ten cards work with no Python API; real Supabase password Auth remains available.
- [ ] API-blocked browser test completes the demo workflow; network log has no `/api/v1` business requests, local API defaults, provider sends or external OCR calls.
- [ ] Selecting a different persona keeps the same dataset and the correct role/scope view.
- [ ] Application, deficiency, exact evidence versions, visit, report, decision and condition links all refer to the correct records.
- [ ] Approve/Reject/Close remain distinct. No unconditional green/accepted overrides.
- [ ] Dashboard counts, reports and tasks react immediately to changes and survive reload.
- [ ] Upload bytes survive reload; missing blobs/quota failure are actionable; reset/import behavior is verified.
- [ ] Report downloads open in their advertised file formats and retain frozen filters/scope.
- [ ] Audit verification checks real local events, simulation fails separately, and UI discloses demo provenance.
- [ ] No UI claims a demo mutation was saved to Supabase or a simulated notification was externally delivered.
- [ ] New record URLs, direct navigation, refresh and back/forward work on the deployed static origin.
- [ ] Static build, targeted command/persistence tests and one end-to-end scenario pass. No repeated full tests without a change or unresolved failure.
- [ ] Bundle/deploy artifacts contain no backend credentials or private dataset exports.
- [ ] Actual Render service/billing inventory confirms no unintended paid API, worker, disk or cron remains. Account-level usage and Supabase charges remain separately monitored.

## 11. Expected outcome and rollback

Expected: remove Python hosting and server OCR/storage/worker requirements for the hosted demo, avoid backend cold-start waits, and keep a consistent interactive recording experience. No guaranteed invoice reduction is claimed until actual deployed services and usage are inspected.

Trade-offs: local data instead of shared Supabase business state; simulated OCR/scanning/notifications/integrations; browser-limited storage and scheduling; no trusted server authorization or immutable audit guarantee for demo records.

Rollback: preserve the live build/configuration, current database and document storage. Use a separate demo preview and mode-specific datasets; returning to live mode reconnects to the unchanged backend. Local demo commands are never automatically replayed into the live database.

Audit evidence: `render.yaml`, `backend/requirements.txt`, every `backend/app/*.py` and `communications/*.py` component group above, frontend providers and direct API consumers, existing local reducer/data/files/report helpers, Next config and route-pattern inventory. Platform facts were checked against the official linked sources on the audit date. The document is a plan, not evidence that the mock migration or static export has already been implemented.

## 12. Implementation update

The browser mock migration is implemented. Default mode is `demo`; set
`NEXT_PUBLIC_PORTAL_MODE=live` to retain the existing live business API. Supabase
password authentication remains real and directly validated; in demo mode it
opens a synthetic institutional profile. The ten persona cards are entirely local.

Implemented shared IndexedDB records and files, atomic revision checks and
cross-tab notifications, domain commands, conditions and independent verification,
frozen CSV/XLSX/PDF report downloads, explicit OCR simulation and real local audit
hashing. Account settings provide a working reset and records-only JSON export.
Complete file-inclusive backup/import remains unimplemented; the export explains
that uploaded bytes are omitted.

`npm run build:demo` now creates a separate static build under `frontend/out`.
The build generates all60pages with static/SSG output; it needs neither Python
nor a Next.js runtime server. Dynamic IDs use static placeholder pages with
original IDs carried in the query. A small static opening page converts legacy
deep links using the Render rewrite in `render-demo.yaml`. Live source routes
and `render.yaml` remain available and are not rewritten by this build.

Verified: all59frontend tests and TypeScript pass. The development browser test
passes all ten personas with every backend request blocked; it covers mutation
persistence/new IDs/reload, file bytes after reload, frozen report downloads and
audit verification/tamper simulation. The same checks passed on the exported
static preview, including new-ID deep links and reloads. Details are recorded in
`completion/HOSTING_OPTIMIZATION_IMPLEMENTATION.md`.

Deployment commands, from `frontend`:

```text
npm ci
npm run build:demo
npm run preview:demo
```

Preview serves static files on port4173 and is a local test tool, not a production
application server requirement. Deploy `frontend/out` using the separate
`render-demo.yaml` blueprint. Supply only the Supabase URL and public anon key if
real password sign-in is required. Do not provide database URLs or private keys.
Hosted cutover and paid-service retirement have not been performed; existing
charges do not stop merely because this repository implementation exists.
