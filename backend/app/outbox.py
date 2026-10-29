"""Transactional outbox primitives; callers own commit and permission checks."""

from uuid import UUID

from psycopg.types.json import Jsonb


def enqueue(
    cursor,
    *,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    payload: dict,
    correlation_id: UUID | None = None,
    entity_version: int | None = None,
) -> UUID:
    """Insert an event inside the caller's business transaction."""
    if not event_type or not entity_type or not isinstance(payload, dict):
        raise ValueError("An event type, entity type and object payload are required")
    cursor.execute(
        "INSERT INTO public.outbox_events "
        "(event_type, entity_type, entity_id, entity_version, payload, correlation_id) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (event_type, entity_type, entity_id, entity_version, Jsonb(payload), correlation_id),
    )
    row = cursor.fetchone()
    return row["id"] if isinstance(row, dict) else row[0]


def claim_due(cursor, *, limit: int = 50, lease_seconds: int = 60) -> list[tuple]:
    """Lease due events with row locks; concurrent workers skip locked rows."""
    if not 1 <= limit <= 100 or not 1 <= lease_seconds <= 3600:
        raise ValueError("Invalid claim limit or lease")
    cursor.execute(
        "WITH due AS ("
        "SELECT id FROM public.outbox_events "
        "WHERE processed_at IS NULL AND dead_lettered_at IS NULL AND attempt_count < 8 AND available_at <= CURRENT_TIMESTAMP "
        "AND (claimed_until IS NULL OR claimed_until <= CURRENT_TIMESTAMP) "
        "ORDER BY available_at, created_at, id FOR UPDATE SKIP LOCKED LIMIT %s"
        ") UPDATE public.outbox_events AS e "
        "SET claim_token = gen_random_uuid(), "
        "claimed_until = CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'), "
        "attempt_count = attempt_count + 1 "
        "FROM due WHERE e.id = due.id "
        "RETURNING e.id, e.event_type, e.entity_type, e.entity_id, "
        "e.payload, e.claim_token, e.attempt_count",
        (limit, lease_seconds),
    )
    return cursor.fetchall()


def mark_processed(cursor, event_id: UUID, claim_token: UUID) -> bool:
    """Acknowledge only the worker holding the current claim token."""
    cursor.execute(
        "UPDATE public.outbox_events SET processed_at = CURRENT_TIMESTAMP, "
        "claim_token = NULL, claimed_until = NULL, last_error = NULL "
        "WHERE id = %s AND claim_token = %s AND processed_at IS NULL "
        "RETURNING id",
        (event_id, claim_token),
    )
    return cursor.fetchone() is not None


def schedule_retry(
    cursor, event_id: UUID, claim_token: UUID, *,
    delay_seconds: int, error_code: str,
) -> bool:
    """Release the current claim and make the event due after bounded backoff."""
    if not 0 <= delay_seconds <= 86400:
        raise ValueError("Invalid retry delay")
    if not error_code or len(error_code) > 128 or any(character.isspace() for character in error_code):
        raise ValueError("Use a short non-sensitive error code")
    cursor.execute(
        "UPDATE public.outbox_events "
        "SET claim_token = NULL, claimed_until = NULL, "
        "dead_lettered_at = CASE WHEN attempt_count >= 8 THEN CURRENT_TIMESTAMP ELSE NULL END, "
        "available_at = CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'), "
        "last_error = %s "
        "WHERE id = %s AND claim_token = %s AND processed_at IS NULL "
        "RETURNING id",
        (delay_seconds, error_code, event_id, claim_token),
    )
    return cursor.fetchone() is not None
