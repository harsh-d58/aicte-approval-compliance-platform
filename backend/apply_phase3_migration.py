"""Apply Phase 3 documents and OCR tables grants and RLS policies migration."""

import argparse
from pathlib import Path
from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "backend" / "migrations" / "006_phase3_documents_ocr.sql"
TABLES = [
    "documents",
    "document_versions",
    "document_types",
    "document_requirement_rules",
    "document_extractions",
    "document_check_results",
    "document_renewal_cases",
    "upload_sessions",
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
            print(f"TABLE: {t:28} | RLS={r[0]} | SELECT={r[1]} | INSERT={r[2]} | UPDATE={r[3]} | POLICIES={r[4]}")


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
                print("Dry-run passed: Phase 3 grants and RLS policies valid; rolling back.")
                raise SystemExit(0)
        print("Migration 006_phase3_documents_ocr.sql applied successfully!\n")
        verify_tables(conn)


if __name__ == "__main__":
    main()
