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
from .decision_lifecycle import decision_outcome, check_decision_prerequisites


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
    decision_type, outcome = decision_outcome(payload.decision_type, payload.decision_status)
    body_dict = {"application_id": str(application_id), **payload.model_dump(mode="json")}

    expected_version = payload.expected_version
    if if_match is not None:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError:
            raise HTTPException(status_code=400)
        if expected_version < 1:
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
                except StaleVersion:
                    raise HTTPException(status_code=412)
                except RecordMissing:
                    raise HTTPException(status_code=404)

                cur.execute(
                    "SELECT a.id,a.application_number,a.status,a.workflow_definition_id,a.institution_id,s.stage_type "
                    "FROM public.applications a LEFT JOIN public.application_stage_instances si ON si.id=a.current_stage_instance_id "
                    "LEFT JOIN public.workflow_stages s ON s.id=si.workflow_stage_id WHERE a.id = %s",
                    (application_id,),
                )
                app = cur.fetchone()
                if not app:
                    raise HTTPException(404)
                check_decision_prerequisites(cur, app, decision_type, outcome)
                if payload.record_document_id:
                    cur.execute('SELECT id FROM public.documents WHERE id=%s AND institution_id=%s AND (application_id IS NULL OR application_id=%s)', (payload.record_document_id, app['institution_id'], application_id))
                    if not cur.fetchone():
                        raise HTTPException(422, detail='Decision document must belong to this application or institution')
                next_version = bump_version(cur, table="applications", record_id=application_id, expected_version=expected_version)

                now = datetime.now(timezone.utc)

                # 2. Insert decision record
                cur.execute(
                    "INSERT INTO public.approval_decisions "
                    "(application_id, decision_type, decision_status, decision_authority, decision_at, reason, record_document_id, created_at, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, application_id, decision_type, decision_status, decision_authority, decision_at, reason, record_document_id, created_at",
                    (application_id, decision_type, payload.decision_status, payload.decision_authority, now, payload.reason, payload.record_document_id, now, caller_uuid),
                )
                decision = cur.fetchone()
                decision_id = decision["id"]

                # 3. Update application status if final
                if outcome:
                    cur.execute(
                        "UPDATE public.applications "
                        "SET status = %s, closed_at = %s, updated_at = %s, updated_by = %s "
                        "WHERE id = %s",
                        (outcome, None if outcome == "approved" else now, now, caller_uuid, application_id),
                    )
                else:
                    cur.execute(
                        "UPDATE public.applications "
                        "SET updated_at = %s, updated_by = %s "
                        "WHERE id = %s",
                        (now, caller_uuid, application_id),
                    )
                if outcome == 'approved':
                    cur.execute('UPDATE public.compliance_conditions SET source_approval_id=%s,updated_at=%s,updated_by=%s,version=version+1 WHERE application_id=%s AND source_approval_id IS NULL', (decision_id, now, caller_uuid, application_id))
                if outcome in ('closed', 'rejected', 'withdrawn'):
                    cur.execute("UPDATE public.application_stage_instances SET status='completed',completed_at=%s WHERE id=(SELECT current_stage_instance_id FROM public.applications WHERE id=%s) AND status<>'completed'", (now, application_id))
                    cur.execute("UPDATE public.assignments SET status='completed' WHERE application_id=%s AND status='active'", (application_id,))

                # 4. Append audit event
                audit_meta = {
                    "application_number": app["application_number"],
                    "decision_type": decision_type,
                    "application_status": outcome or app['status'],
                    "decision_status": payload.decision_status,
                    "decision_authority": payload.decision_authority,
                    "old_version": expected_version,
                    "new_version": next_version,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="APPLICATION_CLOSED" if outcome == 'closed' else "STATUTORY_DECISION_RECORDED",
                    entity_type="approval_decision",
                    entity_id=decision_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # 5. Enqueue outbox event
                enqueue(
                    cur,
                    event_type="APPLICATION_CLOSED" if outcome == 'closed' else "APPLICATION_DECIDED",
                    entity_type="application",
                    entity_id=application_id,
                    entity_version=next_version,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                decision_dict = _serialize(decision)
                decision_dict["application_version"] = next_version
                decision_dict["application_status"] = outcome or app['status']

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
