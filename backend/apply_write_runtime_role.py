"""Install and verify the least-privilege Phase 1 & 2 write database role.

Default is a rolled-back migration dry run. Pass --apply to create the role,
install exact policies, and store its generated URL in the ignored root .env.
The administration DATABASE_URL remains separate for migrations only.
No password, URL, Auth ID or personal data is printed.
"""

import argparse
import os
from pathlib import Path
import re
import secrets
import tempfile
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from dotenv import dotenv_values
import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
MIGRATION = ROOT / "backend" / "migrations" / "004_write_runtime_role.sql"
ROLE = "aicte_api_writer"


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
    if re.search(r"(?m)^DATABASE_WRITE_URL=", existing):
        # Update existing line
        content = re.sub(r"(?m)^DATABASE_WRITE_URL=.*$", "DATABASE_WRITE_URL=" + value, existing)
    else:
        content = existing.rstrip("\r\n") + "\nDATABASE_WRITE_URL=" + value + "\n"
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


def _verify_runtime(write_url: str) -> None:
    with psycopg.connect(write_url, sslmode="require", connect_timeout=10,
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
                raise RuntimeError(f"Runtime role has unexpected privilege flags: {actual}")

        # Test write transaction inside an uncommitted transaction
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    # Test insert into audit_events with valid entity_id
                    cursor.execute(
                        "INSERT INTO public.audit_events (action, entity_type, entity_id, reason, event_hash) "
                        "VALUES ('WRITE_ROLE_VERIFY', 'system', gen_random_uuid(), 'Role verification check', "
                        "'0000000000000000000000000000000000000000000000000000000000000000') "
                        "RETURNING id"
                    )
                    audit_id = cursor.fetchone()[0]
                    # Test that UPDATE on audit_events is blocked by trigger
                    try:
                        cursor.execute(
                            "UPDATE public.audit_events SET reason = 'tamper' WHERE id = %s",
                            (audit_id,),
                        )
                    except psycopg.Error:
                        pass  # Trigger properly blocked it
                    else:
                        raise RuntimeError("Append-only trigger failed to block UPDATE on audit_events")
                # Clean rollback so no test event persists
                raise DryRunRollback()
        except DryRunRollback:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit role/policies and save URL in ignored .env")
    args = parser.parse_args()
    values = dotenv_values(ENV_FILE)
    admin_url = values.get("DATABASE_URL")
    if not admin_url:
        raise SystemExit("DATABASE_URL is missing")
    existing_write = values.get("DATABASE_WRITE_URL")
    if existing_write:
        _verify_runtime(existing_write)
        print("Write runtime role and scoped policies already verified; no changes made")
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
            print("Write role and policies migration dry run passed; no changes made")
            return

    _store_runtime_url(runtime_url)
    _verify_runtime(runtime_url)
    print("Write runtime role installed, scoped and verified; URL saved only in ignored root .env")


if __name__ == "__main__":
    main()
