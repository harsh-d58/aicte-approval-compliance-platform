# FastAPI backend

The backend has the B01 database mapping, B02 Supabase Auth identity boundary, and first scoped read routes. `backend/app/main.py` supplies liveness, dependency readiness, correlation IDs and the PRD §9.1 error envelope. `/api/v1/me` and `/api/v1/me/permissions` validate Supabase Auth access tokens and resolve active application assignments. Read-only institution and application list/detail routes enforce permission and scope in SQL. Business mutations are not exposed yet. The default frontend shell uses these live reads; its separate fictional demo requires an explicit mode setting.

## Local setup

Use Python 3.11 or newer. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Copy the project root `.env.example` to `.env` only if `.env` does not already exist. This single ignored file supplies both applications. Set `DATABASE_URL`, `SUPABASE_URL`, and the Supabase publishable/anon key; keep the database URL server-side. See [access_policy.md](docs/access_policy.md). One confirmed Auth test user and a matching approved DEMO institution read assignment are now provisioned. Browser sign-in reached `/me`, institutions and applications with 200 responses; real-token denial and revocation remain to be checked.

```powershell
.\.venv\Scripts\python.exe backend\check_database.py
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

`GET /health` checks process liveness. `GET /ready` returns 503 until the Supabase project URL exists and a bounded, encrypted, read-only PostgreSQL probe succeeds. It does not certify that business routes have been implemented or Auth is reachable. The diagnostic writes an ignored, sanitised schema report to `backend/docs/database_audit.json`. The latest local diagnostic connected over TLS with a read-only transaction and confirmed all 65 PRD entity tables. See [schema_mapping.md](docs/schema_mapping.md) for remaining constraint and transaction gaps. No replacement database or schema migration is part of this foundation.

See [fastapi_plan.md](../fastapi_plan.md) for implementation order and remaining backend work.

The first additive [outbox/idempotency migration](migrations/001_outbox_idempotency.sql) is installed in the connected prototype database. Its [transaction contract](docs/transaction_foundation.md) and [outbox primitives](app/outbox.py) are available; `python -m backend.verify_outbox` passed insert/lease/retry/ack with a rolled-back smoke event. Business writes remain disabled until the current `BYPASSRLS` runtime connection is replaced with a least-privilege role and tested policies.

The [audit append-only migration](migrations/002_audit_append_only.sql) is also installed. `python -m backend.verify_audit_append_only` checked UPDATE/DELETE rejection and [canonical event hashing](app/audit.py) with a rolled-back event; restricted runtime grants and business-action integration remain open. The [idempotency helper](app/idempotency.py) supports completed-result lookup/conflict checks; its installed-table lookup passed `python -m backend.verify_idempotency`.

The [transaction helper](app/transactions.py) rejects superuser and `BYPASSRLS` database roles before business writes and provides stable retry fingerprints. Database ownership/grants still need review. It is not yet called by a mutation endpoint.

Phase 2 adds [version guards](app/concurrency.py) for the first versioned records and a rolled-back [atomic action check](verify_atomic_action.py). `python -m backend.verify_atomic_action` verified that a DEMO application version update, audit event, outbox event and idempotency result appear together inside a transaction and vanish together on rollback. `python -m backend.verify_outbox` also checked expired-lease recovery. All 28 backend unit tests pass. These checks use the migration credential only for smoke testing; no business write route is enabled.

For UI and query development, [seed_mock_data.py](seed_mock_data.py) has inserted a deterministic [10,211-row DEMO dataset](docs/mock_dataset.md) in 22 tables. It creates no Auth users, grants, real files or OCR output. Run without arguments for a preview; `--apply` is idempotent for the same dataset namespace.

See [manual_handoff.md](docs/manual_handoff.md) for the policy, database and identity actions needed before live write routes.
