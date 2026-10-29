"""Apply Phase 6 grants and RLS policies for reports and dashboards."""

from pathlib import Path
from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[1]
TABLES = [
    "report_definitions",
    "report_runs",
    "regions",
]


def apply():
    env = dotenv_values(ROOT / ".env")
    url = env.get("DATABASE_URL")
    assert url, "DATABASE_URL is required"

    migration_file = ROOT / "backend" / "migrations" / "009_phase6_reports_dashboards.sql"
    sql_text = migration_file.read_text(encoding="utf-8")

    with psycopg.connect(url, sslmode="require", autocommit=True) as conn:
        with conn.cursor() as cur:
            print("==> Applying Phase 6 migration (Grants and RLS policies)...")
            cur.execute(sql_text)
            print("  Migration SQL executed successfully.")

            # Validate grants
            for t in TABLES:
                cur.execute(
                    "SELECT grantee, privilege_type FROM information_schema.role_table_grants "
                    "WHERE table_schema='public' AND table_name=%s AND grantee IN ('aicte_api_writer', 'aicte_api_reader')",
                    (t,),
                )
                grants = cur.fetchall()
                assert len(grants) > 0, f"No grants found on {t}"
                print(f"  Verified grants on {t}: {len(grants)} privilege records")

    print("==> Phase 6 migration successfully applied and verified!")


if __name__ == "__main__":
    apply()
