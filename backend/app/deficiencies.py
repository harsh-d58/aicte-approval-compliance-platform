"""Deficiency notice issuance, institutional response, and itemized scrutiny resolution (PRD §§5.3, 7.1, 9.2)."""

from datetime import datetime, timedelta, timezone
import secrets
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


router = APIRouter(tags=["deficiencies"])


class CreateDeficiencyItemRequest(BaseModel):
    criterion_code: str | None = Field(None, max_length=100)
    description: str = Field(..., min_length=3, max_length=2000)
    related_document_id: UUID | None = None


class CreateDeficiencyNoticeRequest(BaseModel):
    notice_number: str | None = None
    response_due_days: int = Field(30, ge=1, le=180)
    items: list[CreateDeficiencyItemRequest] = Field(..., min_length=1)
    reason: str = Field("Deficiency notice issued during scrutiny", min_length=3, max_length=500)


class SubmitDeficiencyItemResponse(BaseModel):
    item_id: UUID
    related_document_id: UUID | None = None
    narrative: str = Field("Compliance correction provided", min_length=1, max_length=5000)
    document_version_id: UUID | None = None


class SubmitDeficiencyResponseRequest(BaseModel):
    item_responses: list[SubmitDeficiencyItemResponse] = Field(..., min_length=1, max_length=100)
    reason: str = Field("Institutional response to deficiency notice", min_length=3, max_length=500)


class ResolveDeficiencyItemRequest(BaseModel):
    resolution_status: str = Field(..., pattern=r"^(accepted|rejected|waived)$")
    reason: str = Field(..., min_length=3, max_length=500)


def _generate_notice_number() -> str:
    year = datetime.now(timezone.utc).year
    suffix = secrets.token_hex(4).upper()
    return f"DEF-{year}-{suffix}"


@router.post("/applications/{application_id}/deficiency-notices", status_code=201)
def create_deficiency_notice(
    application_id: UUID,
    payload: CreateDeficiencyNoticeRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Issue a formal deficiency notice with itemized compliance gaps (PRD §5.3)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "deficiency.create_notice"
    body_dict = payload.model_dump(mode="json")

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
                # 1. Fetch application and verify not closed
                cur.execute(
                    "SELECT id, status, current_stage_instance_id, version FROM public.applications WHERE id = %s FOR UPDATE",
                    (application_id,),
                )
                app = cur.fetchone()
                if app is None:
                    raise HTTPException(status_code=404)
                if app["status"] not in ("submitted", "under_review", "resubmitted", "deficiency_returned") or not app["current_stage_instance_id"]:
                    raise HTTPException(status_code=409)

                now = datetime.now(timezone.utc)
                due_at = now + timedelta(days=payload.response_due_days)
                notice_number = payload.notice_number or _generate_notice_number()

                # 2. Insert deficiency notice
                cur.execute(
                    "INSERT INTO public.deficiency_notices "
                    "(application_id, stage_instance_id, notice_number, issued_by, issued_at, response_due_at, status, created_at, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'open', %s, %s) "
                    "RETURNING id, application_id, stage_instance_id, notice_number, issued_by, issued_at, response_due_at, status, created_at",
                    (application_id, app["current_stage_instance_id"], notice_number, caller_uuid, now, due_at, now, caller_uuid),
                )
                notice = cur.fetchone()
                notice_id = notice["id"]

                # 3. Insert items
                created_items = []
                for item in payload.items:
                    if item.related_document_id:
                        cur.execute("SELECT d.id FROM public.documents d JOIN public.applications a ON a.institution_id=d.institution_id WHERE d.id=%s AND a.id=%s", (item.related_document_id, application_id))
                        if not cur.fetchone(): raise HTTPException(422, detail="Related document must belong to this application or institution")
                    cur.execute(
                        "INSERT INTO public.deficiency_items "
                        "(deficiency_notice_id, criterion_code, description, related_document_id, resolution_status, created_at, created_by) "
                        "VALUES (%s, %s, %s, %s, 'pending', %s, %s) "
                        "RETURNING id, deficiency_notice_id, criterion_code, description, related_document_id, resolution_status, created_at",
                        (notice_id, item.criterion_code, item.description, item.related_document_id, now, caller_uuid),
                    )
                    created_items.append(_serialize(cur.fetchone()))

                # 4. Update application status to deficiency_returned
                cur.execute(
                    "UPDATE public.applications "
                    "SET status = 'deficiency_returned', version=version+1, updated_at = %s, updated_by = %s "
                    "WHERE id = %s",
                    (now, caller_uuid, application_id),
                )

                # 5. Append audit event
                audit_meta = {
                    "notice_number": notice_number,
                    "items_count": len(payload.items),
                    "response_due_at": due_at.isoformat(),
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DEFICIENCY_NOTICE_ISSUED",
                    entity_type="deficiency_notice",
                    entity_id=notice_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # 6. Enqueue outbox event
                enqueue(
                    cur,
                    event_type="DEFICIENCY_NOTICE_ISSUED",
                    entity_type="deficiency_notice",
                    entity_id=notice_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                notice_dict = _serialize(notice)
                notice_dict["items"] = created_items

                if idempotency_key:
                    store_result(
                        cur,
                        actor_id=caller_uuid,
                        operation=operation,
                        raw_key=idempotency_key,
                        body=body_dict,
                        http_status=201,
                        response_json=notice_dict,
                        expires_at=now + timedelta(days=1),
                    )

        return notice_dict
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.get("/applications/{application_id}/deficiency-notices")
def list_deficiency_notices(
    application_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List deficiency notices and their nested items for an application."""
    _ = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, application_id, stage_instance_id, notice_number, issued_by, issued_at, response_due_at, status, created_at "
                "FROM public.deficiency_notices WHERE application_id = %s ORDER BY issued_at DESC",
                (application_id,),
            )
            notices = [_serialize(row) for row in cur.fetchall()]

            for notice in notices:
                cur.execute(
                    "SELECT id, deficiency_notice_id, criterion_code, description, related_document_id, resolution_status, created_at "
                    "FROM public.deficiency_items WHERE deficiency_notice_id = %s ORDER BY created_at ASC",
                    (notice["id"],),
                )
                notice["items"] = [_serialize(row) for row in cur.fetchall()]

    return {"data": notices}


@router.post("/deficiency-notices/{notice_id}/resubmit")
@router.post("/deficiency-notices/{notice_id}/responses")
def submit_deficiency_response(
    notice_id: UUID,
    payload: SubmitDeficiencyResponseRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Institutional representative uploads itemized deficiency responses with document evidence."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "deficiency.submit_response"
    body_dict = payload.model_dump(mode="json")

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
                # 1. Fetch notice
                cur.execute(
                    "SELECT id, application_id, status FROM public.deficiency_notices WHERE id = %s FOR UPDATE",
                    (notice_id,),
                )
                notice = cur.fetchone()
                if notice is None:
                    raise HTTPException(status_code=404)
                if notice["status"] not in ("open", "responded", "under_review"):
                    raise HTTPException(status_code=409)

                now = datetime.now(timezone.utc)
                if len({item.item_id for item in payload.item_responses}) != len(payload.item_responses):
                    raise HTTPException(422, detail="An item may appear only once per response")
                cur.execute("SELECT id,status,institution_id FROM public.applications WHERE id=%s FOR UPDATE", (notice["application_id"],))
                application = cur.fetchone()
                if application["status"] not in ("deficiency_returned", "resubmitted", "under_review"):
                    raise HTTPException(409)
                cur.execute("INSERT INTO public.application_submissions(application_id,submission_number,submitted_by,submitted_at,submission_status,created_at) SELECT %s,COALESCE(MAX(submission_number),0)+1,%s,%s,'submitted',%s FROM public.application_submissions WHERE application_id=%s RETURNING id,submission_number", (notice["application_id"], caller_uuid, now, now, notice["application_id"]))
                submission = cur.fetchone()
                updated_items = []
                for resp in payload.item_responses:
                    cur.execute("SELECT id,resolution_status FROM public.deficiency_items WHERE id=%s AND deficiency_notice_id=%s FOR UPDATE", (resp.item_id, notice_id))
                    current = cur.fetchone()
                    if not current: raise HTTPException(422, detail="Response item does not belong to this notice")
                    if current["resolution_status"] in ("accepted", "waived"):
                        raise HTTPException(409, detail="Resolved items cannot be overwritten")
                    if resp.related_document_id and not resp.document_version_id:
                        raise HTTPException(422, detail="Select the exact evidence version")
                    document_id = None
                    if resp.document_version_id:
                        cur.execute("SELECT d.id FROM public.document_versions v JOIN public.documents d ON d.id=v.document_id WHERE v.id=%s AND d.institution_id=%s AND (d.application_id IS NULL OR d.application_id=%s)", (resp.document_version_id, application["institution_id"], notice["application_id"]))
                        document = cur.fetchone()
                        if not document or (resp.related_document_id and document["id"] != resp.related_document_id):
                            raise HTTPException(422, detail="Evidence version must belong to this application or institution")
                        document_id = document["id"]
                    cur.execute("INSERT INTO public.deficiency_item_responses(deficiency_item_id,submission_id,narrative,document_version_id,submitted_by,submitted_at) VALUES(%s,%s,%s,%s,%s,%s)", (resp.item_id, submission["id"], resp.narrative.strip(), resp.document_version_id, caller_uuid, now))
                    cur.execute(
                        "UPDATE public.deficiency_items "
                        "SET resolution_status = 'submitted', related_document_id = COALESCE(%s, related_document_id) "
                        "WHERE id = %s AND deficiency_notice_id = %s "
                        "RETURNING id, deficiency_notice_id, criterion_code, description, related_document_id, resolution_status",
                        (document_id, resp.item_id, notice_id),
                    )
                    item_row = cur.fetchone()
                    updated_items.append(_serialize(item_row))

                cur.execute("SELECT count(*) AS count FROM public.deficiency_items WHERE deficiency_notice_id=%s AND resolution_status IN ('pending','rejected')", (notice_id,))
                complete = cur.fetchone()["count"] == 0

                # 2. Update notice status
                cur.execute(
                    "UPDATE public.deficiency_notices SET status = %s WHERE id = %s",
                    ("responded" if complete else "open", notice_id),
                )

                # 3. Update application status to resubmitted
                cur.execute(
                    "UPDATE public.applications SET status = %s, version=version+1, updated_at = %s, updated_by = %s WHERE id = %s",
                    ("resubmitted" if complete else "deficiency_returned", now, caller_uuid, notice["application_id"]),
                )

                # 4. Audit & Outbox
                audit_meta = {
                    "notice_id": str(notice_id),
                    "items_responded": len(updated_items),
                    "submission_id": str(submission["id"]),
                    "submission_number": submission["submission_number"],
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DEFICIENCY_RESPONSE_SUBMITTED",
                    entity_type="deficiency_notice",
                    entity_id=notice_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DEFICIENCY_RESPONSE_SUBMITTED",
                    entity_type="deficiency_notice",
                    entity_id=notice_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = {"status": "responded" if complete else "open", "updated_items": updated_items, "submission_number": submission["submission_number"]}
                if idempotency_key:
                    store_result(
                        cur,
                        actor_id=caller_uuid,
                        operation=operation,
                        raw_key=idempotency_key,
                        body=body_dict,
                        http_status=200,
                        response_json=response_data,
                        expires_at=now + timedelta(days=1),
                    )

        return response_data
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.post("/deficiency-items/{item_id}/resolve")
def resolve_deficiency_item(
    item_id: UUID,
    payload: ResolveDeficiencyItemRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Scrutiny officer resolves an individual deficiency item (PRD §5.3)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "deficiency.resolve_item"
    body_dict = {"item_id": str(item_id), **payload.model_dump(mode="json")}

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
                # 1. Fetch item and parent notice
                cur.execute(
                    "SELECT id, deficiency_notice_id, resolution_status FROM public.deficiency_items WHERE id = %s FOR UPDATE",
                    (item_id,),
                )
                item = cur.fetchone()
                if item is None:
                    raise HTTPException(status_code=404)
                if item["resolution_status"] != "submitted" and payload.resolution_status != "waived":
                    raise HTTPException(409, detail="Review a submitted response before accepting or returning it")

                notice_id = item["deficiency_notice_id"]

                # 2. Update resolution status
                cur.execute(
                    "UPDATE public.deficiency_items SET resolution_status = %s WHERE id = %s "
                    "RETURNING id, deficiency_notice_id, criterion_code, description, related_document_id, resolution_status",
                    (payload.resolution_status, item_id),
                )
                updated_item = cur.fetchone()

                # 3. Check if all items for the notice are accepted or waived
                cur.execute(
                    "SELECT count(*) FROM public.deficiency_items "
                    "WHERE deficiency_notice_id = %s AND resolution_status NOT IN ('accepted', 'waived')",
                    (notice_id,),
                )
                remaining_unresolved = cur.fetchone()["count"]

                notice_resolved = False
                if payload.resolution_status == "rejected":
                    cur.execute("UPDATE public.deficiency_notices SET status='open' WHERE id=%s", (notice_id,))
                    cur.execute("UPDATE public.applications SET status='deficiency_returned',version=version+1,updated_at=now(),updated_by=%s WHERE id=(SELECT application_id FROM public.deficiency_notices WHERE id=%s)", (caller_uuid, notice_id))
                if remaining_unresolved == 0:
                    cur.execute(
                        "UPDATE public.deficiency_notices SET status = 'resolved' WHERE id = %s",
                        (notice_id,),
                    )
                    notice_resolved = True

                # 4. Audit & Outbox
                audit_meta = {
                    "item_id": str(item_id),
                    "resolution_status": payload.resolution_status,
                    "notice_resolved": notice_resolved,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DEFICIENCY_ITEM_RESOLVED",
                    entity_type="deficiency_item",
                    entity_id=item_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DEFICIENCY_ITEM_RESOLVED",
                    entity_type="deficiency_item",
                    entity_id=item_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = {
                    "item": _serialize(updated_item),
                    "notice_resolved": notice_resolved,
                }
                if idempotency_key:
                    store_result(
                        cur,
                        actor_id=caller_uuid,
                        operation=operation,
                        raw_key=idempotency_key,
                        body=body_dict,
                        http_status=200,
                        response_json=response_data,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                    )

        return response_data
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)
