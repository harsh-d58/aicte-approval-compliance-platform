"""Read/write smoke check inside a transaction that is always rolled back."""

from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
import psycopg

from backend.app.outbox import claim_due, enqueue, mark_processed, schedule_retry


ROOT = Path(__file__).resolve().parents[1]
url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing")

with psycopg.connect(url, sslmode="require", connect_timeout=10) as connection:
    if not connection.pgconn.ssl_in_use:
        raise RuntimeError("TLS is required")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.outbox_events WHERE processed_at IS NULL")
            if cursor.fetchone()[0]:
                raise RuntimeError("Pending outbox work exists; refusing to claim it in a smoke test")
            event_id = enqueue(cursor, event_type="DEMO_OUTBOX_SMOKE", entity_type="demo",
                               entity_id=uuid4(), payload={"demo_only": True})
            claims = claim_due(cursor, limit=10)
            matching = [row for row in claims if row[0] == event_id]
            assert len(matching) == 1
            first_token = matching[0][5]
            cursor.execute(
                "UPDATE public.outbox_events SET claimed_until = CURRENT_TIMESTAMP - INTERVAL '1 second' "
                "WHERE id = %s AND claim_token = %s",
                (event_id, first_token),
            )
            recovered_claims = claim_due(cursor, limit=10)
            recovered = [row for row in recovered_claims if row[0] == event_id]
            assert len(recovered) == 1 and recovered[0][6] == 2
            recovered_token = recovered[0][5]
            assert recovered_token != first_token
            assert not mark_processed(cursor, event_id, first_token)
            assert schedule_retry(cursor, event_id, recovered_token,
                                  delay_seconds=0, error_code="DEMO_RETRY")
            retry_claims = claim_due(cursor, limit=10)
            retried = [row for row in retry_claims if row[0] == event_id]
            assert len(retried) == 1 and retried[0][6] == 3
            token = retried[0][5]
            assert not mark_processed(cursor, event_id, first_token)
            assert not mark_processed(cursor, event_id, uuid4())
            assert mark_processed(cursor, event_id, token)
            assert not mark_processed(cursor, event_id, token)
    finally:
        connection.rollback()
print("Outbox insert, expired-lease recovery, retry and acknowledgement passed; smoke event rolled back")
