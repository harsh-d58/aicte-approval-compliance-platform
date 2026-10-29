"""Apply Phase 5 grants and RLS policies for compliance and communications."""

from pathlib import Path
from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[1]
TABLES = [
    "compliance_conditions",
    "compliance_verifications",
    "evidence_submissions",
    "evidence_submission_files",
    "notifications",
    "notification_attempts",
    "notification_rules",
    "escalation_rules",
    "escalation_events",
]


def apply():
    env = dotenv_values(ROOT / ".env")
    url = env.get("DATABASE_URL")
    assert url, "DATABASE_URL is required"

    migration_file = ROOT / "backend" / "migrations" / "008_phase5_compliance_notifications.sql"
    sql_text = migration_file.read_text(encoding="utf-8")

    with psycopg.connect(url, sslmode="require", autocommit=True) as conn:
        with conn.cursor() as cur:
            print("==> Applying Phase 5 migration (Grants and RLS policies)...")
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

    print("==> Phase 5 migration successfully applied and verified!")


if __name__ == "__main__":
    apply()
