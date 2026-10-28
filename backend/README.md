# FastAPI backend

The backend is at the **B01 foundation** stage. `backend/app/main.py` supplies liveness, dependency readiness, correlation IDs and the PRD §9.1 error envelope. Business endpoints are not exposed yet. The frontend still uses its mock data adapter.

## Local setup

Use Python 3.11 or newer. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Copy `backend/.env.example` to `backend/.env` only if that file does not already exist. Supply `DATABASE_URL`, `IDENTITY_ISSUER_URL` and `IDENTITY_AUDIENCE` locally. Never commit credentials or place them in frontend `NEXT_PUBLIC_` variables.

```powershell
.\.venv\Scripts\python.exe backend\check_database.py
.\.venv\Scripts\python.exe -m unittest backend.tests.test_foundation
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

`GET /health` checks process liveness. `GET /ready` returns 503 until identity settings exist and a bounded read-only PostgreSQL probe succeeds. It does not certify that business routes have been implemented. The diagnostic writes an ignored, sanitised schema report to `backend/docs/database_audit.json`; inspect the report before mapping existing tables to the PRD. No replacement database or schema migration is part of this foundation.

See [fastapi_plan.md](../fastapi_plan.md) for implementation order and remaining backend work.
