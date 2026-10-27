# Backend development environment

The project has an isolated Python environment at `../.venv`, created with the locally installed Python 3.13.2. FastAPI, Uvicorn, python-dotenv and the psycopg PostgreSQL diagnostic driver are installed there. The FastAPI implementation plan is [fastapi_plan.md](../fastapi_plan.md); business API routes, database-backed application services and workers have not been implemented by this setup.

From the project root (`E:\Harsh\VIT\TY\SIH\PS_IV`), activate it in Command Prompt:

```bat
call .venv\Scripts\activate.bat
```

Or in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activation affects the current terminal only. If script activation is unavailable, use `.venv\Scripts\python.exe` directly; no execution-policy change is required.

Recreate the environment on another checkout, using a compatible Python installation:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
copy backend\.env.example backend\.env
```

Copy the example only when a local `.env` does not already exist; preserve existing credentials. `requirements.in` lists direct dependencies; `requirements.txt` pins the installed environment, including transitive packages. The current environment was checked on Windows with Python 3.13.2; other deployment platforms still need validation.

`backend/.env` is local and ignored by Git. The database owner supplies `DATABASE_URL` there; identity, Redis and storage settings can be filled when their approved services are available. `.env.example` contains blank connection settings and no credentials. During the latest check the supplied database URL was rejected during authentication, so the schema could not be inspected. No database records were changed.

Retry the read-only diagnostic from the project root after correcting the local connection:

```bat
.venv\Scripts\python.exe backend\check_database.py
```

It inspects metadata only after authenticating, uses read-only transaction defaults and a bounded statement timeout, and writes `backend/docs/database_audit.json` locally. The report is ignored by Git. A connection failure does not establish that the schema is incomplete; do not treat an authentication error as a successful database verification.

The environment variable names are a preparation convention, not additional PRD requirements. A future FastAPI settings layer must explicitly load and validate this file; creating it does not activate API integration or authentication. Provider credentials belong in the approved secret-management mechanism. Never place database/service secrets in frontend `NEXT_PUBLIC_` variables.

Verify the Python environment without starting a server:

```bat
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m uvicorn --version
```

No server is started by this setup. OCR, Celery/Redis clients and identity/storage integrations will be added as their PRD work packages are implemented against the actual service contracts. The diagnostic driver does not provide a database-backed business API.

Environment workflow reference: [FastAPI virtual environments](https://fastapi.tiangolo.com/virtual-environments/).
