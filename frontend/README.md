# AICTE approval and compliance frontend

The default workspace uses live Supabase Auth and the implemented FastAPI read routes. It shows only authorised identity, institution and application records. Other PRD features remain pending until their backend APIs are ready. The fictional demonstration can be enabled explicitly with `NEXT_PUBLIC_PORTAL_MODE=demo` in the single project root `.env`.

## Local setup

1. Copy `../.env.example` to `../.env` if the root `.env` does not already exist. Set `SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `DATABASE_URL`. The anon/publishable key is public; never put a service-role key or database URL in a `NEXT_PUBLIC_` variable.
2. From the project root, start FastAPI with `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload`.
3. From `frontend`, run `npm ci` and `npm run dev`, then open `http://localhost:3000/login`.

The backend requires an active `public.users` identity mapping, approved read permissions and a scoped assignment. Signing in does not provision those records. See the root [FastAPI plan](../fastapi_plan.md) for the PRD implementation order.
