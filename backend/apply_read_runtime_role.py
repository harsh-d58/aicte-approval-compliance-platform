"""Install and verify the approved Phase 1 read-only database role.

Default is a rolled-back migration dry run. Pass --apply to create the role,
install exact read policies, and store its generated URL in the ignored root
.env. The administration DATABASE_URL remains separate for migrations only.
No password, URL, Auth ID or personal data is printed.
"""

import argparse
import os
from pathlib import Path
import re
import secrets
import tempfile
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
MIGRATION = ROOT / "backend" / "migrations" / "003_read_runtime_role.sql"
ROLE = "aicte_api_reader"
READ_TABLES = (
    "users", "roles", "permissions", "role_permissions",
    "user_role_assignments", "institutions", "applications",
)


class DryRunRollback(Exception):
    pass


def _runtime_url(admin_url: str, password: str) -> str:
    parsed = urlsplit(admin_url)
    if parsed.scheme not in ("postgresql", "postgres") or not parsed.hostname:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URI")
    admin_login = unquote(parsed.username or "")
    if admin_login == "postgres":
        login = ROLE
    elif admin_login.startswith("postgres."):
        login = ROLE + admin_login[len("postgres"):]
    else:
        raise RuntimeError("The migration connection must use the known postgres owner")
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    credentials = f"{quote(login, safe='')}:{quote(password, safe='')}"
    return urlunsplit(parsed._replace(netloc=f"{credentials}@{host}{port}"))


def _store_runtime_url(value: str) -> None:
    existing = ENV_FILE.read_text(encoding="utf-8")
    if re.search(r"(?m)^DATABASE_RUNTIME_URL=", existing):
        raise RuntimeError("DATABASE_RUNTIME_URL already exists; refusing to overwrite it")
    content = existing.rstrip("\r\n") + "\nDATABASE_RUNTIME_URL=" + value + "\n"
    handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         prefix=".env.", suffix=".tmp", dir=ROOT,
                                         delete=False)
    try:
        with handle:
            handle.write(content)
        os.replace(handle.name, ENV_FILE)
    finally:
        if os.path.exists(handle.name):
            os.unlink(handle.name)


def _verify_runtime(runtime_url: str, subject: str) -> None:
    with psycopg.connect(runtime_url, sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=5000", autocommit=True) as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("Runtime connection is not encrypted")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_user, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
                "FROM pg_roles WHERE rolname = current_user"
            )
            actual = cursor.fetchone()
            if actual != (ROLE, False, False, False, False):
                raise RuntimeError("Runtime role has unexpected privilege flags")
            cursor.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
            if cursor.fetchone() != (False,):
                raise RuntimeError("Runtime role can create objects in public")
            cursor.execute(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') "
                "AND (has_table_privilege(c.oid, 'INSERT') "
                "OR has_table_privilege(c.oid, 'UPDATE') "
                "OR has_table_privilege(c.oid, 'DELETE') "
                "OR has_table_privilege(c.oid, 'TRUNCATE'))"
            )
            if cursor.fetchone() != (0,):
                raise RuntimeError("Runtime role has a public-table write privilege")
            for table in READ_TABLES:
                cursor.execute(
                    "SELECT count(*) FROM pg_policies WHERE schemaname = 'public' "
                    "AND tablename = %s AND policyname = 'aicte_api_reader_select'",
                    (table,),
                )
                if cursor.fetchone() != (1,):
                    raise RuntimeError("A required read policy is missing")
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM public.users")
                if cursor.fetchone() != (0,):
                    raise RuntimeError("RLS leaked users without a verified subject")
                cursor.execute("SELECT count(*) FROM public.institutions")
                if cursor.fetchone() != (0,):
                    raise RuntimeError("RLS leaked institutions without a verified subject")
                cursor.execute("SELECT count(*) FROM public.applications")
                if cursor.fetchone() != (0,):
                    raise RuntimeError("RLS leaked applications without a verified subject")
                cursor.execute("SELECT set_config('aicte.subject_id', %s, true)", (subject,))
                for table, expected in (
                    ("users", 1), ("roles", 1), ("permissions", 2),
                    ("role_permissions", 2), ("user_role_assignments", 1),
                    ("institutions", 1), ("applications", 6),
                ):
                    cursor.execute(sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(table)))
                    if cursor.fetchone() != (expected,):
                        raise RuntimeError(f"Unexpected scoped count in {table}")
                cursor.execute(
                    "SELECT count(*) FROM public.institutions "
                    "WHERE institution_code <> 'DEMO-INST-0001'"
                )
                if cursor.fetchone() != (0,):
                    raise RuntimeError("Another institution leaked into the DEMO scope")
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM public.institutions")
                if cursor.fetchone() != (0,):
                    raise RuntimeError("The subject persisted across transactions")
                cursor.execute("SELECT set_config('aicte.subject_id', %s, true)", (str(uuid4()),))
                cursor.execute("SELECT count(*) FROM public.applications")
                if cursor.fetchone() != (0,):
                    raise RuntimeError("An unknown subject can read applications")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit role/policies and save URL in ignored .env")
    args = parser.parse_args()
    values = dotenv_values(ENV_FILE)
    admin_url = values.get("DATABASE_URL")
    if not admin_url:
        raise SystemExit("DATABASE_URL is missing")
    existing_runtime = values.get("DATABASE_RUNTIME_URL")
    if existing_runtime:
        with psycopg.connect(admin_url, sslmode="require", connect_timeout=10) as owner:
            owner.read_only = True
            with owner.cursor() as cursor:
                cursor.execute(
                    "SELECT u.id FROM public.users u "
                    "JOIN public.user_role_assignments a ON a.user_id = u.id "
                    "JOIN public.roles r ON r.id = a.role_id "
                    "WHERE r.role_code = 'DEMO_INSTITUTION_VIEWER' AND a.status = 'active'"
                )
                subjects = cursor.fetchall()
        if len(subjects) != 1:
            raise RuntimeError("Expected exactly one approved DEMO test user")
        _verify_runtime(existing_runtime, str(subjects[0][0]))
        print("Read-only runtime role and scoped policies already verified; no changes made")
        return

    secret = secrets.token_urlsafe(48)
    runtime_url = _runtime_url(admin_url, secret)
    with psycopg.connect(admin_url, sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=15000 -c lock_timeout=5000",
                         autocommit=True) as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        with connection.cursor() as cursor:
            cursor.execute("SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_roles WHERE rolname = current_user")
            if cursor.fetchone() != (False, True, True):
                raise RuntimeError("Expected the configured migration owner, not a runtime role")
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
            if cursor.fetchone() is not None:
                raise RuntimeError("Runtime role exists without a saved URL; manual credential review required")
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'api_private'")
            if cursor.fetchone() is not None:
                raise RuntimeError("api_private schema already exists; migration review required")
            cursor.execute(
                "SELECT u.id FROM public.users u "
                "JOIN public.user_role_assignments a ON a.user_id = u.id "
                "JOIN public.roles r ON r.id = a.role_id "
                "WHERE r.role_code = 'DEMO_INSTITUTION_VIEWER' AND a.status = 'active'"
            )
            subjects = cursor.fetchall()
            if len(subjects) != 1:
                raise RuntimeError("Expected exactly one approved DEMO test user")
            subject = str(subjects[0][0])
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(sql.SQL(
                        "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB "
                        "NOCREATEROLE NOBYPASSRLS CONNECTION LIMIT 20 PASSWORD {}"
                    ).format(sql.Identifier(ROLE), sql.Literal(secret)))
                    cursor.execute(MIGRATION.read_text(encoding="utf-8"))
                if not args.apply:
                    raise DryRunRollback()
        except DryRunRollback:
            print("Read-only role and RLS migration dry run passed; no changes made")
            return
    _store_runtime_url(runtime_url)
    _verify_runtime(runtime_url, subject)
    print("Read-only runtime role installed, scoped and verified; URL saved only in ignored root .env")


if __name__ == "__main__":
    main()
