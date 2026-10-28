# FastAPI backend

The backend has the B01 database mapping, B02 Supabase Auth identity boundary, and first scoped read routes. `backend/app/main.py` supplies liveness, dependency readiness, correlation IDs and the PRD §9.1 error envelope. `/api/v1/me` and `/api/v1/me/permissions` validate Supabase Auth access tokens and resolve active application assignments. Read-only institution and application list/detail routes enforce permission and scope in SQL. Business mutations are not exposed yet. The frontend still uses its mock data adapter.

## Local setup

Use Python 3.11 or newer. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Copy `backend/.env.example` to `backend/.env` only if that file does not already exist. Supply `DATABASE_URL` and `SUPABASE_URL` locally. This checkout's ignored `.env` now has the validated project URL. See [access_policy.md](docs/access_policy.md). Never commit credentials or place database secrets in frontend `NEXT_PUBLIC_` variables.

```powershell
.\.venv\Scripts\python.exe backend\check_database.py
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

`GET /health` checks process liveness. `GET /ready` returns 503 until the Supabase project URL exists and a bounded, encrypted, read-only PostgreSQL probe succeeds. It does not certify that business routes have been implemented or Auth is reachable. The diagnostic writes an ignored, sanitised schema report to `backend/docs/database_audit.json`. See [schema_mapping.md](docs/schema_mapping.md) for verified table mappings and outstanding gaps. No replacement database or schema migration is part of this foundation.

See [fastapi_plan.md](../fastapi_plan.md) for implementation order and remaining backend work.
