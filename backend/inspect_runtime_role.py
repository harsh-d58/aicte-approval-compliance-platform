"""Read-only database privilege inventory for the Phase 1 runtime-role gate.

Prints role flags and table-policy counts, never connection details or secrets.
Run from the repository root: python -m backend.inspect_runtime_role
"""

from pathlib import Path

from dotenv import dotenv_values
import psycopg
from psycopg.conninfo import conninfo_to_dict


ROOT = Path(__file__).resolve().parents[1]
TABLES = (
    "users", "roles", "permissions", "role_permissions", "user_role_assignments",
    "institutions", "applications", "audit_events", "outbox_events",
    "api_idempotency_records",
)


def main() -> None:
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")
    conninfo = conninfo_to_dict(url)
    print("Connection string is URI: " + str(url.startswith(("postgresql://", "postgres://"))))
    print("Connection kind: " + ("shared pooler" if "pooler" in conninfo.get("host", "")
                                   else "direct or dedicated"))
    print("Username has pooler tenant suffix: " + str("." in conninfo.get("user", "")))
    with psycopg.connect(url, sslmode="require", connect_timeout=8,
                         options="-c statement_timeout=5000") as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
                "FROM pg_roles WHERE rolname = current_user"
            )
            role = cursor.fetchone()
            if role is None:
                raise RuntimeError("Current role is unavailable")
            print("Current role flags: " + ", ".join(
                f"{name}={value}" for name, value in zip(
                    ("name", "superuser", "bypassrls", "createrole", "createdb"), role
                )
            ))
            for table in TABLES:
                cursor.execute(
                    "SELECT c.relrowsecurity, c.relforcerowsecurity, "
                    "pg_get_userbyid(c.relowner), "
                    "(SELECT count(*) FROM pg_policies p "
                    "WHERE p.schemaname = 'public' AND p.tablename = %s) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relname = %s AND c.relkind IN ('r', 'p')",
                    (table, table),
                )
                result = cursor.fetchone()
                if result is None:
                    print(f"{table}: absent")
                    continue
                rls, forced, owner, policies = result
                print(f"{table}: rls={rls}, forced={forced}, owner={owner}, policies={policies}")


if __name__ == "__main__":
    main()
