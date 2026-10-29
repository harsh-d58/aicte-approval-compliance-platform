"""Canonical per-event audit hashes and same-transaction audit inserts.

This does not replace grant restrictions, backups, or optional external anchoring.
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb


def event_digest(
    *, event_id: UUID, actor_id: UUID | None, action: str, entity_type: str,
    entity_id: UUID, event_at: datetime, correlation_id: UUID | None,
    reason: str | None, metadata: dict, previous_hash: str | None = None,
) -> str:
    """Hash the selected immutable audit fields in a stable UTF-8 representation."""
    if event_at.tzinfo is None or event_at.utcoffset() is None:
        raise ValueError("Audit time must have a timezone")
    if not action or not entity_type or not isinstance(metadata, dict):
        raise ValueError("Audit action, entity type and object metadata are required")
    canonical = {
        "id": str(event_id), "actor_id": str(actor_id) if actor_id else None,
        "action": action, "entity_type": entity_type, "entity_id": str(entity_id),
        "event_at": event_at.astimezone(timezone.utc).isoformat(timespec="microseconds"),
        "correlation_id": str(correlation_id) if correlation_id else None,
        "reason": reason, "metadata": metadata, "previous_hash": previous_hash,
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False,
                         allow_nan=False, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def append_event(
    cursor, *, actor_id: UUID | None, action: str, entity_type: str,
    entity_id: UUID, correlation_id: UUID | None, reason: str | None,
    metadata: dict, previous_hash: str | None = None,
) -> tuple[UUID, str]:
    """Insert audit evidence inside the caller's business transaction."""
    event_id = uuid4()
    # A transaction-scoped lock serializes appends through commit/rollback. Never
    # swallow a failed predecessor read: doing so creates a fork and leaves a
    # PostgreSQL transaction aborted.
    cursor.execute("SELECT pg_advisory_xact_lock(731904226109)")
    cursor.execute("SELECT event_hash, event_at FROM public.audit_events ORDER BY event_at DESC, id DESC LIMIT 1")
    prev_row = cursor.fetchone()
    expected = (prev_row["event_hash"] if isinstance(prev_row, dict) else prev_row[0]) if prev_row else None
    if previous_hash is not None and previous_hash != expected:
        raise ValueError("Audit predecessor differs from the committed chain head")
    previous_hash = expected
    event_at = datetime.now(timezone.utc)
    if prev_row:
        previous_at = prev_row["event_at"] if isinstance(prev_row, dict) else prev_row[1]
        event_at = max(event_at, previous_at + timedelta(microseconds=1))
    digest = event_digest(event_id=event_id, actor_id=actor_id, action=action,
                          entity_type=entity_type, entity_id=entity_id,
                          event_at=event_at, correlation_id=correlation_id,
                          reason=reason, metadata=metadata, previous_hash=previous_hash)
    cursor.execute(
        "INSERT INTO public.audit_events "
        "(id, actor_id, action, entity_type, entity_id, event_at, correlation_id, "
        "reason, metadata, previous_hash, event_hash) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (event_id, actor_id, action, entity_type, entity_id, event_at,
         correlation_id, reason, Jsonb(metadata), previous_hash, digest),
    )
    return event_id, digest


def verify_event(row: dict) -> bool:
    """Recompute one stored event's hash; external anchoring is a separate step."""
    return event_digest(
        event_id=row["id"], actor_id=row["actor_id"], action=row["action"],
        entity_type=row["entity_type"], entity_id=row["entity_id"],
        event_at=row["event_at"], correlation_id=row["correlation_id"],
        reason=row["reason"], metadata=row["metadata"], previous_hash=row["previous_hash"],
    ) == row["event_hash"]


def verify_chain_rows(rows) -> dict:
    """Verify ordered content AND predecessor links; preserve/report legacy gaps.

    A valid prefix cannot prove deletion of its tail without a separately held
    checkpoint. Callers must supply the full ledger, never an arbitrary LIMIT.
    """
    previous = None
    previous_key = None
    errors = []
    count = 0
    for row in rows:
        count += 1
        key = (row["event_at"], str(row["id"]))
        if previous_key is not None and key <= previous_key:
            errors.append({"id": str(row["id"]), "code": "ORDER_INVALID"})
        if not row.get("event_hash"):
            errors.append({"id": str(row["id"]), "code": "LEGACY_UNCHAINED"})
        elif not verify_event(row):
            errors.append({"id": str(row["id"]), "code": "HASH_INVALID"})
        if row.get("previous_hash") != previous:
            errors.append({"id": str(row["id"]), "code": "PREDECESSOR_INVALID"})
        previous, previous_key = row.get("event_hash"), key
    return {"valid": not errors, "count": count, "head_hash": previous, "errors": errors}
