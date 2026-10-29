"""Install the actual column contracts in existing evaluation report definitions.

Run --apply to commit. Default rolls back. No report output or history is changed.
"""
import argparse
from pathlib import Path
from dotenv import dotenv_values
import psycopg
from psycopg.types.json import Jsonb
from .app.report_catalog import REPORT_COLUMNS, DATE_GRAINS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    apply = parser.parse_args().apply
    config = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    with psycopg.connect(config["DATABASE_URL"], sslmode="require", connect_timeout=8) as connection:
        with connection.transaction(force_rollback=not apply):
            for code, columns in REPORT_COLUMNS.items():
                database_code = "DEMO-" + code.upper().replace("-", "_")
                filters = {"filters": ["date_from", "date_to", "region_id", "status", "query", "column_filters"],
                           "date_grain": DATE_GRAINS[code]}
                connection.execute(
                    "UPDATE report_definitions SET columns_config=%s,filters_config=%s,version=version+1 "
                    "WHERE report_code=%s AND (columns_config IS DISTINCT FROM %s OR filters_config IS DISTINCT FROM %s)",
                    (Jsonb(columns), Jsonb(filters), database_code, Jsonb(columns), Jsonb(filters)))
                row = connection.execute("SELECT columns_config FROM report_definitions WHERE report_code=%s", (database_code,)).fetchone()
                if not row or row[0] != columns:
                    raise RuntimeError("An evaluation report definition is missing or invalid")
    print("Eight evaluation report contracts verified; " + ("committed" if apply else "rolled back"))


if __name__ == "__main__":
    main()
