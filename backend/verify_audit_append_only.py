"""Check audit mutation guards using a synthetic event that is rolled back."""

from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row

from backend.app.audit import append_event, verify_event


ROOT = Path(__file__).resolve().parents[1]
url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing")


class SmokeRollback(Exception):
    pass


with psycopg.connect(url, sslmode="require", connect_timeout=10,
                     autocommit=True, row_factory=dict_row) as connection:
    if not connection.pgconn.ssl_in_use:
        raise RuntimeError("TLS is required")
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                event_id, _ = append_event(
                    cursor, actor_id=None, action="DEMO_AUDIT_SMOKE", entity_type="demo",
                    entity_id=uuid4(), correlation_id=uuid4(), reason="rolled-back smoke test",
                    metadata={"demo_only": True},
                )
                cursor.execute("SELECT * FROM public.audit_events WHERE id = %s", (event_id,))
                assert verify_event(cursor.fetchone())
                statements = (
                    ("UPDATE", "UPDATE public.audit_events SET reason = 'changed' WHERE id = %s", (event_id,)),
                    ("DELETE", "DELETE FROM public.audit_events WHERE id = %s", (event_id,)),
                    ("TRUNCATE", "TRUNCATE public.audit_events", None),
                )
                for name, statement, parameters in statements:
                    try:
                        with connection.transaction():
                            cursor.execute(statement, parameters)
                    except psycopg.Error as error:
                        # The audit-anchor FK can reject TRUNCATE before its trigger runs.
                        if error.sqlstate != "55000" and not (name == "TRUNCATE" and error.sqlstate == "0A000"):
                            raise RuntimeError(f"{name} failed for another reason: {error.sqlstate}") from None
                    else:
                        raise AssertionError(f"{name} was not blocked")
            raise SmokeRollback()
    except SmokeRollback:
        pass
print("Audit UPDATE/DELETE triggers blocked edits; TRUNCATE was rejected; synthetic event rolled back")
