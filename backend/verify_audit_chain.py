"""Verify the cryptographic hash-chain integrity of the append-only audit trail (PRD §1.4 Innovation 1, §13.5).

Traverses audit_events in chronological order, verifies that each event's hash
correctly seals its canonical payload and binds to the previous event's hash.
"""

from pathlib import Path
from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row

from backend.app.audit import verify_chain_rows


ROOT = Path(__file__).resolve().parents[1]


def verify_chain():
    env = dotenv_values(ROOT / ".env")
    url = env.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")

    print('Verifying complete audit ledger, including predecessor linkage...')
    with psycopg.connect(url, sslmode="require", autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, actor_id, action, entity_type, entity_id, event_at, correlation_id, "
                "       reason, metadata, previous_hash, event_hash "
                "FROM public.audit_events "
                "ORDER BY event_at ASC, id ASC",
            )
            rows = cur.fetchall()
            if not rows:
                print("No audit events found.")
                return True

            result = verify_chain_rows(rows)
            print(result)
            print('VERDICT: PASS' if result['valid'] else 'VERDICT: FAIL -- ledger hash/linkage gaps')
            print('Tail deletion requires an independent previously retained head checkpoint.')
            return result['valid']


if __name__ == "__main__":
    raise SystemExit(0 if verify_chain() else 1)

