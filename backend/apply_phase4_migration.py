"""Apply Phase 4 EVC and meeting record tables grants and RLS policies migration."""

import argparse
from pathlib import Path
from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "backend" / "migrations" / "007_phase4_evc_meeting_records.sql"
TABLES = [
    "evc_visits",
    "evc_committee_members",
    "expert_profiles",
    "expert_availability",
    "slot_recommendations",
    "evc_invitations",
    "evc_visit_events",
    "evc_observations",
    "evc_reports",
    "meeting_record_versions",
    "meeting_record_sources",
    "committee_types",
    "committees",
]


def verify_tables(conn):
    with conn.cursor() as cur:
        for t in TABLES:
            cur.execute(
                "SELECT c.relrowsecurity, "
                "has_table_privilege('aicte_api_writer', c.oid, 'SELECT'), "
                "has_table_privilege('aicte_api_writer', c.oid, 'INSERT'), "
                "has_table_privilege('aicte_api_writer', c.oid, 'UPDATE'), "
                "(SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = %s) "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = %s",
                (t, t),
            )
            r = cur.fetchone()
            print(f"TABLE: {t:26} | RLS={r[0]} | SELECT={r[1]} | INSERT={r[2]} | UPDATE={r[3]} | POLICIES={r[4]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit migration")
    args = parser.parse_args()

    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")

    with psycopg.connect(url, sslmode="require", autocommit=True) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(MIGRATION.read_text(encoding="utf-8"))
            if not args.apply:
                print("Dry-run passed: Phase 4 grants and RLS policies valid; rolling back.")
                raise SystemExit(0)
        print("Migration 007_phase4_evc_meeting_records.sql applied successfully!\n")
        verify_tables(conn)


if __name__ == "__main__":
    main()
