"""Apply PRD §13.4 append-only audit triggers once, transactionally."""

import argparse
from pathlib import Path

from dotenv import dotenv_values
import psycopg


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = Path(__file__).resolve().parent / "migrations" / "002_audit_append_only.sql"
TRIGGERS = ("audit_events_no_update_delete", "audit_events_no_truncate")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")
    with psycopg.connect(url, sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=30000 -c lock_timeout=5000") as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.audit_events'::regclass "
                "AND tgname = ANY(%s)", (list(TRIGGERS),))
            present = {row[0] for row in cursor.fetchall()}
            if present == set(TRIGGERS):
                print("Audit append-only triggers already installed")
                connection.rollback()
                return
            if present:
                raise RuntimeError("Partial audit migration detected")
            if not args.apply:
                print("Audit append-only migration pending. Pass --apply to install")
                connection.rollback()
                return
            cursor.execute(MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(
                "SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.audit_events'::regclass "
                "AND tgname = ANY(%s)", (list(TRIGGERS),))
            if {row[0] for row in cursor.fetchall()} != set(TRIGGERS):
                raise RuntimeError("Audit trigger verification failed")
    print("Installed audit append-only triggers")


if __name__ == "__main__":
    main()
