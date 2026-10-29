"""Communications, delivery attempts, retries, and escalation rules (PRD §§7.5, 8, 9.2, 15)."""

from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import time

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .communications.jobs import queue_jobs, refresh_notification
from .authorization import RESOURCES, role_name, within
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid


router = APIRouter(tags=["notifications"])


@contextmanager
def notification_transaction(url, subject=None):
    with write_transaction(url, subject) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def notification_authority(cur, caller, notification=None, *, global_only=False):
    cur.execute("SELECT a.*,r.role_code FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id JOIN public.users u ON u.id=a.user_id WHERE a.user_id=%s AND u.status='active' AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (caller['id'],))
    assignments = cur.fetchall()
    allowed = [a for a in assignments if role_name(a['role_code']) in ('SYSTEM','CENTRAL','REGIONAL')]
    if any(a['scope_type']=='global' and role_name(a['role_code']) in ('SYSTEM','CENTRAL') for a in allowed):
        return
    if global_only or not notification:
        raise HTTPException(403, detail='Global notification administration required')
    kind = notification.get('related_entity_type')
    table = {'application':'applications','institution':'institutions','document':'documents','compliance_condition':'compliance-conditions','deficiency_notice':'deficiency-notices','evc_visit':'evc-visits'}.get(kind)
    if table and notification.get('related_entity_id'):
        cur.execute(RESOURCES[table], (notification['related_entity_id'],))
        row = cur.fetchone()
        if row and any(within(row,a) for a in allowed):
            return
    raise HTTPException(403, detail='Notification outside current authority')


class CreateNotificationRequest(BaseModel):
    event_code: str = Field(..., min_length=2, max_length=100)
    recipient_user_id: UUID
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RetryNotificationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    channel: str = Field("email", pattern=r"^(email|sms)$")



class CreateEscalationRuleRequest(BaseModel):
    event_code: str = Field(..., min_length=2, max_length=100)
    threshold_minutes: int = Field(..., ge=0)
    recipient_role_id: UUID
    action_type: str = Field(..., min_length=2, max_length=50)


class ResolveEscalationRequest(BaseModel):
    resolution_status: str = Field(..., pattern=r"^(resolved|dismissed|superseded)$")
    reason: str = Field(..., min_length=3, max_length=1000)


class ProviderReceipt(BaseModel):
    job_id: UUID
    provider_event_id: str = Field(min_length=1, max_length=160, pattern=r'^[A-Za-z0-9_.:-]+$')
    provider_reference: str = Field(min_length=1, max_length=200)
    outcome: str = Field(pattern=r'^(delivered|failed)$')


@router.post('/notification-provider-receipts')
async def provider_receipt(request: Request):
    from .communications.receipts import authenticate_receipt, apply_receipt
    from pydantic import ValidationError
    secret = os.getenv('NOTIFICATION_RECEIPT_SECRET', '')
    # Read with a hard bound before buffering a body supplied by a third party.
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > 16384:
            raise HTTPException(413)
    raw = bytes(chunks)
    try:
        authenticate_receipt(raw, request.headers.get('X-Receipt-Timestamp',''), request.headers.get('X-Receipt-Signature',''), secret)
    except RuntimeError:
        raise HTTPException(503, detail='Receipt provider unavailable') from None
    except ValueError:
        raise HTTPException(401, detail='Invalid receipt authentication') from None
    try:
        receipt = ProviderReceipt.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(422, detail='Invalid receipt') from None
    with notification_transaction(request.app.state.settings.database_write_url) as cur:
        try:
            changed = apply_receipt(cur, **receipt.model_dump())
        except ValueError:
            raise HTTPException(409, detail='Receipt conflicts with stored delivery') from None
        if changed:
            append_event(cur,actor_id=None,action='NOTIFICATION_PROVIDER_RECEIPT',entity_type='notification_delivery_job',entity_id=receipt.job_id,correlation_id=None,reason='Authenticated provider delivery receipt',metadata={'outcome':receipt.outcome,'provider_event_id':receipt.provider_event_id})
    return {'recorded':changed}


@router.post("/notifications", status_code=201)
def queue_notification(
    payload: CreateNotificationRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Queue a logical notification for dispatch distinguishing logical intent from delivery attempts (PRD §8.1)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "notifications.queue_notification"
    body_dict = payload.model_dump(mode="json")
    now = datetime.now(timezone.utc)
    notification_id = uuid4()

    try:
        with notification_transaction(write_url, caller["subject"]) as cur:
            notification_authority(cur, caller, body_dict)
            if idempotency_key:
                try:
                    prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                    if prior:
                        return prior[1]
                except (IdempotencyConflict, IdempotencyExpired) as e:
                    raise HTTPException(status_code=409)

            # Ensure recipient user exists
            cur.execute(
                "SELECT id FROM public.users WHERE id = %s",
                (payload.recipient_user_id,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Recipient user not found")

            cur.execute(
                "INSERT INTO public.notifications "
                "(id, event_code, recipient_user_id, related_entity_type, related_entity_id, created_at, status, payload) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'queued', %s) "
                "RETURNING id, event_code, recipient_user_id, related_entity_type, related_entity_id, created_at, status, payload",
                (
                    notification_id,
                    payload.event_code,
                    payload.recipient_user_id,
                    payload.related_entity_type,
                    payload.related_entity_id,
                    now,
                    Jsonb(payload.payload),
                ),
            )
            created = cur.fetchone()

            audit_meta = {
                "event_code": payload.event_code,
                "recipient_user_id": str(payload.recipient_user_id),
                "related_entity_type": payload.related_entity_type,
                "related_entity_id": str(payload.related_entity_id) if payload.related_entity_id else None,
            }
            append_event(
                cur,
                actor_id=caller_uuid,
                action="NOTIFICATION_QUEUED",
                entity_type="notification",
                entity_id=notification_id,
                correlation_id=corr_uuid,
                reason="Queued communication notification",
                metadata=audit_meta,
            )
            enqueue(
                cur,
                event_type="NOTIFICATION_DISPATCH_REQUIRED",
                entity_type="notification",
                entity_id=notification_id,
                payload=audit_meta,
                correlation_id=corr_uuid,
            )

            res = _serialize(dict(created))
            if idempotency_key:
                store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=201, response_json=res, expires_at=now + timedelta(days=1))
            return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.get("/notifications")
def list_notifications(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    recipient_user_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query()] = None,
):
    """List notifications with cursor pagination."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    query = (
        "SELECT id, event_code, recipient_user_id, related_entity_type, related_entity_id, "
        "created_at, status, payload "
        "FROM public.notifications WHERE 1=1 "
    )
    params: list[Any] = []

    if recipient_user_id:
        query += "AND recipient_user_id = %s "
        params.append(recipient_user_id)
    if status:
        query += "AND status = %s "
        params.append(status)
    if cursor:
        query += "AND id > %s "
        params.append(cursor)

    query += "ORDER BY id ASC LIMIT %s"
    params.append(limit + 1)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = str(items[-1]["id"]) if has_more and items else None

    return {
        "data": [_serialize(dict(r)) for r in items],
        "page": {
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.get("/notifications/{notification_id}")
def get_notification(
    notification_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve details of a notification and its delivery attempts history (PRD §8.2)."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, event_code, recipient_user_id, related_entity_type, related_entity_id, "
                "created_at, status, payload "
                "FROM public.notifications WHERE id = %s",
                (notification_id,),
            )
            notification = cur.fetchone()
            if not notification:
                raise HTTPException(status_code=404, detail="Notification not found")

            cur.execute(
                "SELECT id, notification_id, channel, attempt_number, attempted_at, result, "
                "provider_reference, failure_reason, created_at, provider_status, delivery_job_id "
                "FROM public.notification_attempts "
                "WHERE notification_id = %s "
                "ORDER BY attempt_number ASC, channel ASC",
                (notification_id,),
            )
            attempts = cur.fetchall()

            res = _serialize(dict(notification))
            res["attempts"] = [_serialize(dict(a)) for a in attempts]
            cur.execute('SELECT id,channel,status,attempt_count,available_at,provider_reference,last_error,accepted_at,delivered_at FROM public.notification_delivery_jobs WHERE notification_id=%s ORDER BY channel', (notification_id,))
            res['delivery_jobs'] = [_serialize(dict(j)) for j in cur.fetchall()]
            return res


@router.post('/notifications/{notification_id}/retry', status_code=202)
def retry_notification_delivery(notification_id: UUID, payload: RetryNotificationRequest, request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None):
    """Queue a failed/blocked channel. Never fabricate an attempt or send in HTTP."""
    caller = _user(request, subject)
    url = request.app.state.settings.database_write_url
    body = {'notification_id':str(notification_id), **payload.model_dump(mode='json')}
    with notification_transaction(url, caller['subject']) as cur:
        cur.execute('SELECT * FROM public.notifications WHERE id=%s FOR UPDATE', (notification_id,))
        notification = cur.fetchone()
        if not notification:
            raise HTTPException(404)
        notification_authority(cur, caller, notification)
        if idempotency_key:
            try:
                prior = find_result(cur, actor_id=_to_uuid(caller['id']), raw_key=idempotency_key, operation='notifications.retry_delivery', body=body)
            except (IdempotencyConflict, IdempotencyExpired):
                raise HTTPException(409) from None
            if prior:
                return prior[1]
        queue_jobs(cur, notification_id, [payload.channel])
        cur.execute('SELECT * FROM public.notification_delivery_jobs WHERE notification_id=%s AND channel=%s FOR UPDATE', (notification_id,payload.channel))
        job = cur.fetchone()
        if job['status'] in ('accepted','delivered','sending','unknown') or job['attempt_count']>=8:
            raise HTTPException(409, detail='Delivery requires reconciliation or has exhausted retries')
        cur.execute("UPDATE public.notification_delivery_jobs SET status='queued',available_at=now(),last_error=NULL WHERE id=%s", (job['id'],))
        refresh_notification(cur, notification_id)
        res={'id':str(job['id']),'notification_id':str(notification_id),'channel':payload.channel,'status':'queued'}
        append_event(cur, actor_id=_to_uuid(caller['id']), action='NOTIFICATION_RETRY_QUEUED',entity_type='notification',entity_id=notification_id,correlation_id=_to_uuid(getattr(request.state,'correlation_id',None)),reason='Requested durable channel retry',metadata={'channel':payload.channel,'job_id':str(job['id'])})
        if idempotency_key:
            store_result(cur, actor_id=_to_uuid(caller['id']), raw_key=idempotency_key, operation='notifications.retry_delivery', body=body,http_status=202,response_json=res,expires_at=datetime.now(timezone.utc)+timedelta(days=1))
        return res


@router.post('/notifications/process-outbox', status_code=202)
def process_notification_outbox(request: Request, subject: Annotated[str, Depends(get_verified_subject)],
    limit: Annotated[int, Query(ge=1,le=50)] = 10):
    """Repair missing durable handoffs; supervised workers perform dispatch."""
    caller = _user(request, subject)
    with notification_transaction(request.app.state.settings.database_write_url,caller['subject']) as cur:
        notification_authority(cur,caller,global_only=True)
        cur.execute("SELECT id FROM public.notifications WHERE status='queued' ORDER BY created_at,id LIMIT %s FOR UPDATE SKIP LOCKED", (limit,))
        ids=[row['id'] for row in cur.fetchall()]
        for ident in ids:
            queue_jobs(cur,ident)
        if ids:
            append_event(cur,actor_id=_to_uuid(caller['id']),action='NOTIFICATION_HANDOFFS_REPAIRED',entity_type='user',entity_id=_to_uuid(caller['id']),correlation_id=None,reason='Queued missing notification channel jobs',metadata={'notification_ids':[str(i) for i in ids]})
    return {'queued_count':len(ids),'notification_ids':[str(i) for i in ids]}


@router.post("/escalation-rules", status_code=201)
def create_escalation_rule(
    payload: CreateEscalationRuleRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Create an escalation rule for unresponded deficiencies or pending statutory milestones."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    now = datetime.now(timezone.utc)
    rule_id = uuid4()

    try:
        with notification_transaction(write_url, caller["subject"]) as cur:
            notification_authority(cur, caller, global_only=True)
            cur.execute(
                "SELECT id FROM public.roles WHERE id = %s",
                (payload.recipient_role_id,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Recipient role not found")

            cur.execute(
                "INSERT INTO public.escalation_rules "
                "(id, event_code, threshold_minutes, recipient_role_id, action_type, enabled, version, created_at, created_by, updated_at, updated_by) "
                "VALUES (%s, %s, %s, %s, %s, true, 1, %s, %s, %s, %s) "
                "RETURNING id, event_code, threshold_minutes, recipient_role_id, action_type, enabled, version, created_at",
                (
                    rule_id,
                    payload.event_code,
                    payload.threshold_minutes,
                    payload.recipient_role_id,
                    payload.action_type,
                    now,
                    caller_uuid,
                    now,
                    caller_uuid,
                ),
            )
            row = cur.fetchone()

            append_event(
                cur,
                actor_id=caller_uuid,
                action="ESCALATION_RULE_CREATED",
                entity_type="escalation_rule",
                entity_id=rule_id,
                correlation_id=corr_uuid,
                reason="Created escalation rule",
                metadata={"event_code": payload.event_code, "threshold_minutes": payload.threshold_minutes},
            )

            return _serialize(dict(row))
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.get("/escalation-rules")
def list_escalation_rules(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List configured escalation rules."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, event_code, threshold_minutes, recipient_role_id, action_type, enabled, version, created_at "
                "FROM public.escalation_rules ORDER BY event_code ASC, version DESC"
            )
            rows = cur.fetchall()

    return {"data": [_serialize(dict(r)) for r in rows]}


@router.get("/escalation-events")
def list_escalation_events(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    resolution_status: Annotated[str | None, Query()] = None,
):
    """List triggered escalation events."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    query = (
        "SELECT id, rule_id, related_entity_type, related_entity_id, triggered_at, "
        "recipient_user_id, resolution_status, resolved_at, created_at "
        "FROM public.escalation_events WHERE 1=1 "
    )
    params: list[Any] = []
    if resolution_status:
        query += "AND resolution_status = %s "
        params.append(resolution_status)

    query += "ORDER BY triggered_at DESC"

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    return {"data": [_serialize(dict(r)) for r in rows]}


@router.post("/escalation-events/{event_id}/resolve")
def resolve_escalation_event(
    event_id: UUID,
    payload: ResolveEscalationRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Authorised officer resolves or dismisses an escalation event."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    now = datetime.now(timezone.utc)

    try:
        with notification_transaction(write_url, caller["subject"]) as cur:
            cur.execute(
                "SELECT * FROM public.escalation_events WHERE id = %s FOR UPDATE",
                (event_id,),
            )
            ev = cur.fetchone()
            if not ev:
                raise HTTPException(status_code=404, detail="Escalation event not found")

            notification_authority(cur, caller, ev)
            cur.execute(
                "UPDATE public.escalation_events "
                "SET resolution_status = %s, resolved_at = %s "
                "WHERE id = %s "
                "RETURNING id, rule_id, resolution_status, resolved_at",
                (payload.resolution_status, now, event_id),
            )
            updated = cur.fetchone()

            append_event(
                cur,
                actor_id=caller_uuid,
                action="ESCALATION_EVENT_RESOLVED",
                entity_type="escalation_event",
                entity_id=event_id,
                correlation_id=corr_uuid,
                reason=payload.reason,
                metadata={"resolution_status": payload.resolution_status},
            )

            return _serialize(dict(updated))
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)
