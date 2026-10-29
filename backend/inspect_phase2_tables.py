"""Inspect Phase 2 table schemas from the existing PostgreSQL database."""

from pathlib import Path
from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[1]
TABLES = [
    "institutions",
    "institution_campuses",
    "institution_profile_attributes",
    "applications",
    "application_types",
    "application_submissions",
    "aph_rule_sets",
    "aph_rule_versions",
    "workflow_definitions",
    "workflow_stages",
    "workflow_transitions",
    "application_stage_instances",
    "stage_history",
    "assignments",
    "deficiency_notices",
    "deficiency_items",
    "approval_decisions",
]


def main():
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    with psycopg.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            for table in TABLES:
                cur.execute(
                    "SELECT c.relrowsecurity, "
                    "has_table_privilege('aicte_api_writer', c.oid, 'SELECT'), "
                    "has_table_privilege('aicte_api_writer', c.oid, 'INSERT'), "
                    "has_table_privilege('aicte_api_writer', c.oid, 'UPDATE'), "
                    "(SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = %s) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relname = %s",
                    (table, table),
                )
                res = cur.fetchone()
                rls, sel, ins, upd, pols = res if res else (None, None, None, None, None)
                print(f"TABLE: {table:30} | RLS={rls} | SELECT={sel} | INSERT={ins} | UPDATE={upd} | POLICIES={pols}")


if __name__ == "__main__":
    main()
