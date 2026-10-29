"""Statutory decision recording and human authority governance (PRD §§5.3, 7.1, 9.2, BR-04, BR-12)."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .concurrency import RecordMissing, StaleVersion, bump_version, lock_versioned
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid


router = APIRouter(tags=["decisions"])


class CreateDecisionRequest(BaseModel):
    decision_type: str = Field(..., min_length=2, max_length=50)
    decision_status: str = Field(..., pattern=r"^(draft|approved|rejected|withdrawn|superseded)$")
    decision_authority: str = Field(..., min_length=2, max_length=150)
    reason: str = Field(..., min_length=3, max_length=1000)
    record_document_id: UUID | None = None
    expected_version: int = Field(..., ge=1)


@router.post("/applications/{application_id}/decisions", status_code=201)
def record_statutory_decision(
    application_id: UUID,
    payload: CreateDecisionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Record an authoritative statutory decision enforcing human statutory governance (BR-04, BR-12)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "application.record_decision"
    body_dict = payload.model_dump(mode="json")

    expected_version = payload.expected_version
    if if_match is not None:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError:
            raise HTTPException(status_code=400)

    if idempotency_key:
        try:
            with _read_connection(request.app.state.settings.database_url, subject) as read_conn:
                with read_conn.cursor() as cur:
                    cached = find_result(
                        cur,
                        actor_id=caller_uuid,
                        operation=operation,
                        raw_key=idempotency_key,
                        body=body_dict,
                    )
            if cached is not None:
                return cached[1]
        except (IdempotencyConflict, IdempotencyExpired):
            raise HTTPException(status_code=409)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                # 1. Lock and check version
                try:
                    lock_versioned(cur, table="applications", record_id=application_id, expected_version=expected_version)
                    next_version = bump_version(cur, table="applications", record_id=application_id, expected_version=expected_version)
                except StaleVersion:
                    raise HTTPException(status_code=412)
                except RecordMissing:
                    raise HTTPException(status_code=404)

                cur.execute(
                    "SELECT id, application_number, status FROM public.applications WHERE id = %s",
                    (application_id,),
                )
                app = cur.fetchone()
                if app["status"] in ("approved", "rejected", "closed", "withdrawn"):
                    raise HTTPException(status_code=409)

                now = datetime.now(timezone.utc)

                # 2. Insert decision record
                cur.execute(
                    "INSERT INTO public.approval_decisions "
                    "(application_id, decision_type, decision_status, decision_authority, decision_at, reason, record_document_id, created_at, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, application_id, decision_type, decision_status, decision_authority, decision_at, reason, record_document_id, created_at",
                    (application_id, payload.decision_type, payload.decision_status, payload.decision_authority, now, payload.reason, payload.record_document_id, now, caller_uuid),
                )
                decision = cur.fetchone()
                decision_id = decision["id"]

                # 3. Update application status if final
                if payload.decision_status in ("approved", "rejected", "withdrawn"):
                    cur.execute(
                        "UPDATE public.applications "
                        "SET status = %s, closed_at = %s, updated_at = %s, updated_by = %s "
                        "WHERE id = %s",
                        (payload.decision_status, None if payload.decision_status == "approved" else now, now, caller_uuid, application_id),
                    )
                else:
                    cur.execute(
                        "UPDATE public.applications "
                        "SET updated_at = %s, updated_by = %s "
                        "WHERE id = %s",
                        (now, caller_uuid, application_id),
                    )

                # 4. Append audit event
                audit_meta = {
                    "application_number": app["application_number"],
                    "decision_type": payload.decision_type,
                    "decision_status": payload.decision_status,
                    "decision_authority": payload.decision_authority,
                    "old_version": expected_version,
                    "new_version": next_version,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="STATUTORY_DECISION_RECORDED",
                    entity_type="approval_decision",
                    entity_id=decision_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # 5. Enqueue outbox event
                enqueue(
                    cur,
                    event_type="APPLICATION_DECIDED",
                    entity_type="application",
                    entity_id=application_id,
                    entity_version=next_version,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                decision_dict = _serialize(decision)
                decision_dict["application_version"] = next_version

                if idempotency_key:
                    store_result(
                        cur,
                        actor_id=caller_uuid,
                        operation=operation,
                        raw_key=idempotency_key,
                        body=body_dict,
                        http_status=201,
                        response_json=decision_dict,
                        expires_at=now + timedelta(days=1),
                    )

        return decision_dict
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.get("/applications/{application_id}/decisions")
def list_application_decisions(
    application_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List statutory decisions recorded for an application."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, application_id, decision_type, decision_status, decision_authority, "
        "       decision_at, reason, record_document_id, created_at "
        "FROM public.approval_decisions "
        "WHERE application_id = %s ORDER BY created_at DESC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (application_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}
