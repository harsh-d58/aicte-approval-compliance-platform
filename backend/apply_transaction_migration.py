"""Apply the reviewed additive Phase 1 migration exactly once.

Usage from repository root:
    .venv/Scripts/python backend/apply_transaction_migration.py --apply
"""

import argparse
from pathlib import Path

from dotenv import dotenv_values
import psycopg


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = Path(__file__).resolve().parent / "migrations" / "001_outbox_idempotency.sql"
TABLES = ("public.outbox_events", "public.api_idempotency_records")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply the additive migration")
    args = parser.parse_args()
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing from the ignored root .env")
    with psycopg.connect(url, sslmode="require", connect_timeout=12,
                         options="-c statement_timeout=30000 -c lock_timeout=5000") as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s), to_regclass(%s)", TABLES)
            present = cursor.fetchone()
            if all(present):
                print("Migration already installed; no changes made")
                connection.rollback()
                return
            if any(present):
                raise RuntimeError("Only part of the migration exists; inspect manually")
            if not args.apply:
                print("Migration pending. Pass --apply to install both tables atomically")
                connection.rollback()
                return
            migration_sql = MIGRATION.read_text(encoding="utf-8")
            for statement in migration_sql.split(";"):
                if statement.strip():
                    cursor.execute(statement)
            cursor.execute(
                "SELECT relname, relrowsecurity FROM pg_class WHERE oid = ANY(ARRAY[%s::regclass,%s::regclass]) ORDER BY relname",
                TABLES,
            )
            installed = cursor.fetchall()
            if len(installed) != 2 or not all(row[1] for row in installed):
                raise RuntimeError("Migration verification failed; transaction will roll back")
        # Connection context commits only after all checks pass.
    print("Installed Phase 1 migration: two RLS-enabled tables and their indexes")


if __name__ == "__main__":
    main()
