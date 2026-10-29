"""Read-only check of the installed idempotency lookup SQL."""

from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
import psycopg

from backend.app.idempotency import find_result


ROOT = Path(__file__).resolve().parents[1]
url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing")
with psycopg.connect(url, sslmode="require", connect_timeout=10) as connection:
    connection.read_only = True
    with connection.cursor() as cursor:
        result = find_result(cursor, actor_id=uuid4(), operation="DEMO_SMOKE",
                             raw_key="lookup-only", body={"demo_only": True})
        assert result is None
        cursor.execute(
            "SELECT count(*) FROM public.api_idempotency_records "
            "WHERE operation IN ('DEMO_ATOMIC_SMOKE', 'DEMO_RETRY_RACE_SMOKE')"
        )
        assert cursor.fetchone() == (0,), "A rolled-back smoke result was retained"
    connection.rollback()
print("Idempotency lookup SQL passed against the installed table; no data changed")
