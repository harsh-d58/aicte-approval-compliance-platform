"""Apply Phase 2 core workflow tables grants and RLS policies migration."""

import argparse
from pathlib import Path
from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "backend" / "migrations" / "005_phase2_core_workflow.sql"


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
                print("Dry-run passed: Phase 2 grants and RLS policies valid; rolling back.")
                raise SystemExit(0)
    print("Migration 005_phase2_core_workflow.sql applied successfully!")


if __name__ == "__main__":
    main()
