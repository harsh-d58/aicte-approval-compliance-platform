# AICTE Platform — Codebase Fine-Tuning & Dynamicism Inventory

> **Document Purpose:** Detailed technical analysis of all architectural changes, backend routes, frontend state adaptations, and dynamic data pipelines implemented by ChatGPT sol 6.1 to transform the platform from a client-side mock prototype into a live, database-backed application.
> **Date:** 29 October 2026
> **Workspace:** `e:\Harsh\VIT\TY\SIH\PS_IV`

---

## Table of Contents
1. [Executive Summary of Changes](#1-executive-summary-of-changes)
2. [The Core Dynamic Architecture](#2-the-core-dynamic-architecture)
3. [File-by-File Breakdown: Backend Changes](#3-file-by-file-breakdown-backend-changes)
4. [File-by-File Breakdown: Frontend Changes](#4-file-by-file-breakdown-frontend-changes)
5. [How Dynamicism Was Implemented](#5-how-dynamicism-was-implemented)
   - [5.1 Live Snapshot Projection (`/portal/snapshot`)](#51-live-snapshot-projection-portalsnapshot)
   - [5.2 Live Mutation Bridge (`/portal/commands` & `executeLiveCommand`)](#52-live-mutation-bridge-portalcommands--executelivecommand)
   - [5.3 Auto-Polling & Focus Refresh Engine](#53-auto-polling--focus-refresh-engine)
   - [5.4 Advancing Analytical Clock (`setPortalNow`)](#54-advancing-analytical-clock-setportalnow)
   - [5.5 1-Click Prototype Persona JWT Auth (`/prototype/session`)](#55-1-click-prototype-persona-jwt-auth-prototypesession)
   - [5.6 Binary File Upload & SHA-256 Storage (`/portal/documents`)](#56-binary-file-upload--sha-256-storage-portaldocuments)
6. [Database Schema Migrations & Infrastructure Scripts](#6-database-schema-migrations--infrastructure-scripts)
7. [Current Test Coverage & Health Matrix](#7-current-test-coverage--health-matrix)
8. [Pending Items & Recommendations for Next Steps](#8-pending-items--recommendations-for-next-steps)

---

## 1. Executive Summary of Changes

Prior to these modifications, the rich Power-BI analytics dashboard and the 16 portal sub-pages operated on deterministic, in-memory fixtures defined in [frontend/lib/portal/mock-data.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/portal/mock-data.ts). User mutations (approving applications, issuing deficiency notices, verifying documents) were handled purely in browser memory by a synchronous reducer (`applyCommand` in [frontend/lib/portal/commands.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/portal/commands.ts)) and saved to `sessionStorage`.

**ChatGPT sol 6.1 built a complete dynamic bridge** connecting the existing rich Next.js frontend to the live PostgreSQL/Supabase database and FastAPI backend:

1. **Eliminated In-Memory Mutation Reducer:** All UI mutations now execute via asynchronous REST calls (`executeLiveCommand`) against real FastAPI endpoints, which run within guarded PostgreSQL transactions and append to `public.audit_events` and `public.outbox_events`.
2. **Created Universal Live Snapshot API:** Added `GET /api/v1/portal/snapshot` which extracts, scopes, and normalizes 56 PostgreSQL tables in a single composite query and projects them into the exact `PortalCollections` interface expected by the UI.
3. **Dynamic Frontend Hydration:** Rewrote [DemoProvider.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/DemoProvider.tsx) to fetch live data from `/portal/snapshot`, poll the database every 30 seconds, auto-refresh on window focus, and advance the analytical clock (`setPortalNow`) to real-time IST.
4. **1-Click Prototype Persona Authentication:** Implemented `/prototype/session` so that developers and evaluators can still click any of the 10 demonstration role cards on `/login` and immediately receive a cryptographically signed JWT mapped to a deterministic PostgreSQL user with assigned RLS scopes.
5. **Binary Document Uploads:** Implemented `/portal/documents` accepting base64 file payloads from the browser, calculating SHA-256 digests, checking MIME types and file sizes, enforcing optimistic version locking (`If-Match`), and storing binary files on disk.
6. **Preserved UI Aesthetics & Verification:** Maintained 100% of the Power-BI charts, cross-filters, cross-highlighting, and record inspectors without breaking any visual components or tests (166/166 backend tests passing, 28/28 frontend tests passing).

---

## 2. The Core Dynamic Architecture

The diagram below illustrates how data and mutations now flow between the user interface and the database:

```
[ Next.js 16 UI Pages ] (AnalyticsDashboard, Applications, Documents, EVC, Compliance, Reports)
        |
        | 1. Reads 'data' (scoped) & 'allData'
        v
[ DemoProvider.tsx ] <======================================================+
        |                                                                    |
        | 2. Action executed: execute(command)                               | 7. Re-fetches
        v                                                                    |    Live Snapshot
[ executeLiveCommand() ] (frontend/lib/live/commands.ts)                     |    (auto-polling
        |                                                                    |     & on-focus)
        | 3. Translates UI command to REST API request                       |
        |    (with Idempotency-Key & If-Match version headers)               |
        v                                                                    |
+-------------------------------------------------------------------------+  |
|                         FastAPI Backend Engine                          |  |
|                                                                         |  |
|  * Standard Endpoints: /applications, /institutions, /evc, etc.         |  |
|  * Supplemental Engine: /portal/commands (portal_commands.py)           |  |
|  * Binary Documents:    /portal/documents (portal_files.py)             |  |
|  * Snapshot Engine:     /portal/snapshot (portal_snapshot.py) ----------+--+
+-------------------------------------------------------------------------+
                                    |
                                    | 4. Explicit PostgreSQL TLS Transaction
                                    |    (pg_advisory_xact_lock serialized)
                                    | 5. Row version checked & RLS validated
                                    | 6. Writes state + audit_events + outbox
                                    v
+-------------------------------------------------------------------------+
|                  PostgreSQL 17 Database (Supabase)                      |
|  - 56 Normalized Relational Tables                                      |
|  - Append-Only Audit Trigger (blocks UPDATE/DELETE on audit_events)     |
|  - Outbox Events & Idempotency Keys with Unique Hashes                  |
+-------------------------------------------------------------------------+
```

---

## 3. File-by-File Breakdown: Backend Changes

| File Link | Status | Key Symbols / Components | What ChatGPT sol 6.1 Implemented |
| :--- | :--- | :--- | :--- |
| [backend/app/portal_snapshot.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal_snapshot.py) | **NEW** | `snapshot()`, `map_snapshot()`, `scoped_tables()` | Runs an atomic SQL statement aggregating 56 PostgreSQL tables via `jsonb_build_object()`. Applies server-side scope filtering based on active `user_role_assignments` and maps normalized rows into the `PortalCollections` shape. |
| [backend/app/portal.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal.py) | **NEW** | `router`, `portal_snapshot()` | Exposes `GET /api/v1/portal/snapshot`. Verifies the user subject from the Bearer JWT, opens a write transaction, and serves the snapshot with `Cache-Control: no-store`. |
| [backend/app/portal_commands.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal_commands.py) | **NEW** | `router`, `command_endpoint()`, `execute_command()` | Exposes `POST /api/v1/portal/commands`. Handles 22+ supplemental mutation kinds directly against PostgreSQL. Employs `pg_advisory_xact_lock(72844116)`, validates role permissions, appends audit events, and writes outbox rows. |
| [backend/app/portal_files.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal_files.py) | **NEW** | `router`, `upload_document()` | Exposes `POST /api/v1/portal/documents`. Handles base64 binary document uploads, validates MIME types, checks size limits (10MB), checks document type expiration support, computes SHA-256 hashes, and registers versions. |
| [backend/app/prototype.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/prototype.py) | **NEW** | `router`, `prototype_session()`, `verify_prototype_token()` | Exposes `POST /api/v1/prototype/session`. Provides 1-click token issuance for the 10 role personas, generating deterministic UUIDv5 user subjects and signing HS256 tokens using `.secrets/prototype-session.key`. |
| [backend/app/main.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/main.py) | **MODIFIED** | Router mounts, CORS middleware | Mounted `portal_router`, `portal_files_router`, `portal_commands_router`, and `prototype_router`. Added CORS support for `localhost:3000` with headers `Authorization`, `Idempotency-Key`, `If-Match`. Added 409 Conflict and 412 Precondition Failed status handling. |
| [backend/app/concurrency.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/concurrency.py) | **NEW** | `check_and_advance_version()` | Optimistic locking helper that verifies row versions for applications, institutions, and documents, raising HTTP 412 if stale. |
| [backend/app/transactions.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/transactions.py) | **NEW** | `write_transaction()` | Context manager that ensures TLS-encrypted connection, sets RLS session variables (`aicte.subject_id`), rejects superuser/bypass-RLS accounts, and rolls back cleanly on exception. |
| [backend/seed_mock_data.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/seed_mock_data.py) | **NEW** | `build_rows()`, `ROWS` | Comprehensive synthetic generator producing 180 institutions, 1,080 applications, 2,160 documents, EVC visits, and compliance conditions matching all PRD constraints. |
| [backend/seed_live_prototype.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/seed_live_prototype.py) | **NEW** | `main()` | Database population script that seeds the connected PostgreSQL instance with the synthetic prototype dataset. |
| [backend/provision_prototype_personas.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/provision_prototype_personas.py) | **NEW** | `main()` | Provisions the 10 canonical UUIDv5 persona users into `public.users` and assigns their statutory roles in `public.user_role_assignments`. |
| [backend/tests/test_portal_snapshot.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/tests/test_portal_snapshot.py) | **NEW** | `PortalSnapshotTests` | 6 unit tests verifying that all seeded records project cleanly, child RLS policies are properly scoped, and data contracts match the frontend shape. |
| [backend/tests/test_portal_commands.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/tests/test_portal_commands.py) | **NEW** | `PortalCommandTests` | 7 unit tests verifying permission denials, out-of-scope modifications, stale version rejections, and audit event insertions. |
| [backend/tests/test_transactions.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/tests/test_transactions.py) | **NEW** | `TransactionTests` | Unit tests verifying transaction rollbacks, advisory locking, and connection safety guards. |

---

## 4. File-by-File Breakdown: Frontend Changes

| File Link | Status | Key Symbols / Components | What ChatGPT sol 6.1 Implemented |
| :--- | :--- | :--- | :--- |
| [frontend/app/portal-ui/DemoProvider.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/DemoProvider.tsx) | **REWRITTEN** | `DemoProvider`, `useDemo` | Replaced the local fixture loader with a live polling engine. Fetches `/portal/snapshot`, sets up a 30s polling interval and window focus listener, dispatches commands through `executeLiveCommand()`, and re-fetches the snapshot on completion. |
| [frontend/lib/live/commands.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/live/commands.ts) | **NEW** | `executeLiveCommand()`, `LiveCommandClient` | Translates frontend `Command` objects into HTTP requests directed to `/portal/commands`, `/applications`, `/portal/documents`, `/institutions`, etc., attaching `Idempotency-Key` and `If-Match` version headers. |
| [frontend/app/portal-ui/LiveProvider.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/LiveProvider.tsx) | **MODIFIED** | `signInDemo()`, `LiveContext` | Added `signInDemo(personaId)` which calls `POST /prototype/session`, stores the returned prototype token in `sessionStorage`, and fetches `/me` to establish a live identity. |
| [frontend/app/portal-ui/PortalShell.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/PortalShell.tsx) | **MODIFIED** | Topbar badge, footer metadata | Added a live refresh button in the topbar (`Live data · Refresh`) that shows the IST timestamp of the last database fetch. Updated footer to cite "Supabase PostgreSQL · IST". |
| [frontend/app/portal-ui/AnalyticsDashboard.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/AnalyticsDashboard.tsx) | **MODIFIED** | Footer badge, text labels | Changed footer caption from "Fictional source snapshot" to "Live database snapshot". Preserved all interactive bar charts, KPI cards, and cross-filter logic. |
| [frontend/app/portal-ui/DocumentPages.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/DocumentPages.tsx) | **MODIFIED** | `DocumentPages` | Added "Human document verification" panel with `ReasonAction` triggering `document.verify` against the live backend. |
| [frontend/app/portal-ui/ReportPages.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/ReportPages.tsx) | **MODIFIED** | `ReportPages` | Converted synchronous report creation/completion calls to `await execute(...)`. Updated table caption to "live database snapshot". |
| [frontend/app/portal-ui/domain-ui.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/domain-ui.tsx) | **MODIFIED** | `ActionForm` | Converted internal form submission handler to `await execute(command)` to properly wait for server persistence. |
| [frontend/lib/portal/view-models.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/portal/view-models.ts) | **MODIFIED** | `demoNow`, `setPortalNow()` | Made `demoNow` mutable via `setPortalNow(isoString)` so the frontend analytical clock advances in sync with live database snapshot timestamps. |
| [frontend/lib/portal/report-rows.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/portal/report-rows.ts) | **MODIFIED** | `getReportRows()` | Added safe fallback defaults for documents where versions are not yet uploaded, preventing runtime null reference errors. |

---

## 5. How Dynamicism Was Implemented

### 5.1 Live Snapshot Projection (`/portal/snapshot`)
Instead of making dozens of REST calls to fetch applications, institutions, documents, visits, and users separately, [backend/app/portal_snapshot.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal_snapshot.py) builds a single PostgreSQL query:
```sql
SELECT jsonb_build_object(
  'regions', (SELECT COALESCE(jsonb_agg(to_jsonb(projection)), '[]'::jsonb) FROM public.regions AS projection),
  'applications', (SELECT COALESCE(jsonb_agg(to_jsonb(projection)), '[]'::jsonb) FROM public.applications AS projection),
  ...
) AS snapshot;
```
This is wrapped in [backend/app/portal.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal.py) under the route `GET /api/v1/portal/snapshot`. The server verifies the token subject and filters the snapshot in `scoped_tables()` using the user's active `public.user_role_assignments`.

### 5.2 Live Mutation Bridge (`/portal/commands` & `executeLiveCommand`)
When a user clicks "Submit Application", "Verify Document", or "Schedule Visit":
1. The UI dispatches an action object like `{ kind: "document.verify", id: "...", values: { result: "VERIFIED", reason: "Approved" } }`.
2. [frontend/lib/live/commands.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/live/commands.ts) intercepts the action in `executeLiveCommand()`.
3. It generates an `Idempotency-Key` header and an `If-Match` version header.
4. It sends an HTTP POST to `/api/v1/portal/commands` (or the specific REST route).
5. [backend/app/portal_commands.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal_commands.py) opens a database transaction, obtains `pg_advisory_xact_lock`, verifies permissions, updates the tables, inserts an audit log into `public.audit_events`, enqueues outbox events, and commits.
6. The frontend receives the success response and immediately re-queries `/portal/snapshot`, refreshing the UI with the newly committed state.

### 5.3 Auto-Polling & Focus Refresh Engine
In [frontend/app/portal-ui/DemoProvider.tsx](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/app/portal-ui/DemoProvider.tsx), dynamicism is kept active without requiring manual user refreshes:
```typescript
// Background polling every 30 seconds
const timer = window.setInterval(() => {
  if (document.visibilityState === "visible") void refresh().catch(() => {});
}, 30_000);

// Auto-refresh when the browser tab regains focus
const focus = () => { void refresh().catch(() => {}); };
window.addEventListener("focus", focus);
```

### 5.4 Advancing Analytical Clock (`setPortalNow`)
The Power-BI dashboard computes overdue durations and deadline SLA breaches using `demoNow`. Previously, `demoNow` was a hardcoded string (`"2026-10-26T12:00:00+05:30"`). ChatGPT sol 6.1 introduced `setPortalNow()` in [frontend/lib/portal/view-models.ts](file:///e:/Harsh/VIT/TY/SIH/PS_IV/frontend/lib/portal/view-models.ts), which `DemoProvider.tsx` calls on every database snapshot:
```typescript
setPortalNow(new Date().toISOString());
```
This ensures deadlines and overdue counters are calculated relative to the current real-world time.

### 5.5 1-Click Prototype Persona JWT Auth (`/prototype/session`)
To preserve passwordless login for hackathon evaluation:
- [backend/app/prototype.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/prototype.py) assigns deterministic UUIDv5 identifiers to each of the 10 role cards (e.g., `user-institution`, `user-regional`, `user-scrutiny`).
- Calling `POST /prototype/session` returns an access token containing:
  ```json
  {
    "sub": "00000000-0000-0000-0000-000000000001",
    "role": "INSTITUTION",
    "iss": "aicte-prototype-v1",
    "exp": 1793230000
  }
  ```
- This token is validated on all requests, giving the user access to `/portal/snapshot` and `/portal/commands` scoped strictly to that role.

### 5.6 Binary File Upload & SHA-256 Storage (`/portal/documents`)
In [backend/app/portal_files.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/app/portal_files.py):
- Accepts base64 encoded document files from the browser.
- Validates the binary payload, computing its SHA-256 checksum.
- Rejects files larger than 10MB or unsupported MIME types.
- Enforces document expiration rules based on `document_types.supports_expiry`.
- Writes the file to physical storage (`storage/`) and records the version in `public.document_versions`.

---

## 6. Database Schema Migrations & Infrastructure Scripts

ChatGPT sol 6.1 authored several additive migrations and runtime scripts to support these dynamic capabilities:

1. **`backend/migrations/001_outbox_idempotency.sql`**:
   - Creates `public.outbox_events` for transactional outbox dispatching with lease management (`FOR UPDATE SKIP LOCKED`).
   - Creates `public.idempotency_keys` storing hashed keys (`key_hash`) and request fingerprints (`request_hash`).
2. **`backend/migrations/002_audit_append_only.sql`**:
   - Creates triggers `prevent_audit_update` and `prevent_audit_delete` on `public.audit_events` to enforce immutable append-only compliance.
3. **`backend/migrations/010_institution_availability.sql`**:
   - Creates table `public.institution_availability` for institution-side availability windows during EVC scheduling.
4. **`backend/apply_read_runtime_role.py` & `apply_write_runtime_role.py`**:
   - Scripts configuring least-privilege PostgreSQL roles (`aicte_api_reader` and `aicte_api_writer`) to prevent running under superuser credentials.

---

## 7. Current Test Coverage & Health Matrix

| Test Suite | Previous Status | Current Status | Coverage Details |
| :--- | :---: | :---: | :--- |
| **Backend Unit Tests** | 131 passing | **166 passing** | Added 35 tests covering portal snapshots, portal commands, transactional safety, concurrency locks, and prototype auth. |
| **Frontend Unit Tests** | 28 passing | **28 passing** | All 28 scoped security, EVC scheduling, audit, and SLA tests continue to pass. |
| **TypeScript Typecheck** | 0 errors | **0 errors** | `npx tsc --noEmit` exits with code 0 across the entire Next.js codebase. |
| **Live Database Acceptance** | Untested | **100% PASS** | [backend/verify_live_portal.py](file:///e:/Harsh/VIT/TY/SIH/PS_IV/backend/verify_live_portal.py) exercised all 10 roles, draft creation, submit, unauthorized approval denial (403), and all 8 statutory reports against remote PostgreSQL. |
| **FastAPI OpenAPI Schema** | Valid | **Valid** | All routes mount cleanly at `http://localhost:8000/docs`. |

---

## 8. Pending Items & Recommendations for Next Steps

While ChatGPT sol 6.1 built a comprehensive foundation, the following fine-tuning opportunities remain:

1. **Supabase Realtime WebSockets:**
   - *Current State:* Frontend polls every 30 seconds via `setInterval`.
   - *Enhancement:* Subscribe to `postgres_changes` on Supabase channels for instant push updates when other officers modify records.
2. **Remote Database Timeout Resilience:**
   - *Observation:* Querying all 56 tables across the internet from Tokyo Supabase pooler can occasionally experience TCP/SSL timeouts under heavy load.
   - *Enhancement:* Add query connection retry logic or optimize `portal_snapshot.py` to cache semi-static tables (`regions`, `workflow_definitions`, `document_types`).
3. **Background Worker Execution:**
   - *Observation:* `outbox_events` and `notifications` are enqueued in PostgreSQL, but background consumption is handled on-demand rather than via a standing Celery/Redis daemon.
   - *Enhancement:* Add a lightweight asyncio outbox processor loop in FastAPI lifespan.
4. **OCR Service Connection:**
   - *Observation:* Document uploads extract text via deterministic fallback when Tesseract is not installed locally.
   - *Enhancement:* Wire Tesseract CLI or cloud vision API if automated text verification on uploaded PDFs is evaluated live.
