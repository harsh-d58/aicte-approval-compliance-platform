"""Completed API idempotency results, stored with the business transaction."""

from datetime import datetime, timezone
import json
from uuid import UUID

from psycopg.types.json import Jsonb

from .transactions import idempotency_key_hash, request_hash


class IdempotencyConflict(ValueError):
    """A retry key was reused with a different request."""


class IdempotencyExpired(ValueError):
    """An old key cannot be treated as a new request while its row remains."""


def find_result(cursor, *, actor_id: UUID, operation: str, raw_key: str, body: dict):
    """Return a completed result or None; caller rechecks access on replay.

    An expired row still reserves its key. Treating it as a miss would let a
    retry repeat a business action after any later retention cleanup.
    """
    key_hash = idempotency_key_hash(raw_key)
    fingerprint = request_hash(operation, body)
    cursor.execute(
        "SELECT request_hash, http_status, response_json, expires_at "
        "FROM public.api_idempotency_records "
        "WHERE actor_id = %s AND operation = %s AND key_hash = %s",
        (actor_id, operation, key_hash),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        row = (row["request_hash"], row["http_status"], row["response_json"], row["expires_at"])
    if row[0] != fingerprint:
        raise IdempotencyConflict("Retry key was used for a different request")
    if row[3] <= datetime.now(timezone.utc):
        raise IdempotencyExpired("Retry key expired; use a new key for a new action")
    return row[1], row[2]


def store_result(
    cursor, *, actor_id: UUID, operation: str, raw_key: str,
    body: dict, http_status: int, response_json: dict,
    expires_at: datetime,
) -> None:
    """Insert a completed result before the caller commits the business action.

    Unique-key conflicts must roll back the whole action; the caller then reads
    the winner's completed result in a new transaction and rechecks access.
    """
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError("Idempotency expiry must have a timezone")
    if expires_at <= datetime.now(timezone.utc) or not 200 <= http_status <= 599:
        raise ValueError("Invalid idempotency expiry or HTTP status")
    if not isinstance(response_json, dict):
        raise ValueError("The stored response must be a JSON object")
    cursor.execute(
        "INSERT INTO public.api_idempotency_records "
        "(actor_id, operation, key_hash, request_hash, http_status, response_json, expires_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (actor_id, operation, idempotency_key_hash(raw_key), request_hash(operation, body),
         http_status, Jsonb(json.loads(json.dumps(response_json, default=str))), expires_at),
    )
