"""Institution profile, campus, and typed attributes management (PRD §§5.2, 7.1, 9.2)."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator
from psycopg.rows import dict_row

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .concurrency import RecordMissing, StaleVersion, bump_version, lock_versioned
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .records import _cursor_id, _next_cursor
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid
from .authorization import role_name


router = APIRouter(tags=["institutions"])


class UpdateInstitutionRequest(BaseModel):
    official_name: str | None = Field(None, min_length=2, max_length=255)
    institution_type: str | None = Field(None, min_length=2, max_length=100)
    region_id: UUID | None = None
    expected_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3, max_length=500)


class CreateCampusRequest(BaseModel):
    campus_name: str = Field(..., min_length=2, max_length=200)
    address: dict[str, Any] = Field(default_factory=dict)
    region_id: UUID | None = None
    is_primary: bool = False
    reason: str = Field(..., min_length=3, max_length=500)


class ProfileAttributeItem(BaseModel):
    attribute_key: str = Field(..., min_length=1, max_length=100)
    value_text: str | None = None
    value_date: date | None = None
    value_number: float | None = None
    source_document_id: UUID | None = None
    source_document_version_id: UUID | None = None
    verified_status: str = Field("pending", pattern=r"^(pending|unverified|verified|rejected|not_applicable)$")

    @model_validator(mode="after")
    def typed_value(self):
        if sum(v is not None for v in (self.value_text, self.value_date, self.value_number)) != 1:
            raise ValueError("Exactly one typed attribute value is required")
        if self.verified_status == "unverified": self.verified_status = "pending"
        return self


class UpdateProfileAttributesRequest(BaseModel):
    attributes: list[ProfileAttributeItem] = Field(..., min_length=1)
    reason: str = Field(..., min_length=3, max_length=500)


@router.patch("/institutions/{institution_id}")
def update_institution(
    institution_id: UUID,
    payload: UpdateInstitutionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Controlled update of institution profile with optimistic locking and audit logging."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "institution.update"
    body_dict = payload.model_dump(mode="json")

    # Match header version if present
    expected_version = payload.expected_version
    if if_match is not None:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError:
            raise HTTPException(status_code=400)

    # Idempotency lookup
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
                # 1. Lock and check expected version
                try:
                    lock_versioned(cur, table="institutions", record_id=institution_id, expected_version=expected_version)
                    next_version = bump_version(cur, table="institutions", record_id=institution_id, expected_version=expected_version)
                except StaleVersion:
                    raise HTTPException(status_code=412)
                except RecordMissing:
                    raise HTTPException(status_code=404)

                # 2. Get current record
                cur.execute("SELECT * FROM public.institutions WHERE id = %s", (institution_id,))
                current = cur.fetchone()
                if current is None:
                    raise HTTPException(status_code=404)

                new_name = payload.official_name or current["official_name"]
                new_type = payload.institution_type or current["institution_type"]
                new_region = payload.region_id if payload.region_id is not None else current["region_id"]
                now = datetime.now(timezone.utc)

                # 3. Update institution
                cur.execute(
                    "UPDATE public.institutions "
                    "SET official_name = %s, institution_type = %s, region_id = %s, updated_at = %s, updated_by = %s "
                    "WHERE id = %s "
                    "RETURNING id, official_name, institution_code, institution_type, status, region_id, updated_at, version",
                    (new_name, new_type, new_region, now, caller_uuid, institution_id),
                )
                updated = cur.fetchone()

                # 4. Append audit event
                audit_metadata = {
                    "old_version": expected_version,
                    "new_version": next_version,
                    "official_name": new_name,
                    "institution_type": new_type,
                    "region_id": str(new_region) if new_region else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="INSTITUTION_UPDATED",
                    entity_type="institution",
                    entity_id=institution_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_metadata,
                )

                # 5. Enqueue outbox event
                enqueue(
                    cur,
                    event_type="INSTITUTION_UPDATED",
                    entity_type="institution",
                    entity_id=institution_id,
                    entity_version=next_version,
                    payload=audit_metadata,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(updated)
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


@router.get("/institutions/{institution_id}/campuses")
def list_campuses(
    institution_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
):
    """List campuses belonging to the specified institution."""
    _ = _user(request, subject)
    after = _cursor_id(cursor)
    sql = (
        "SELECT id, institution_id, campus_name, address, region_id, is_primary, created_at, updated_at, version "
        "FROM public.institution_campuses WHERE institution_id = %s "
    )
    params: list[Any] = [institution_id]
    if after is not None:
        sql += " AND id > %s "
        params.append(after)
    sql += " ORDER BY is_primary DESC, id ASC LIMIT %s"
    params.append(limit + 1)

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = [_serialize(row) for row in cur.fetchall()]

    has_more = len(rows) > limit
    data = rows[:limit]
    return {
        "data": data,
        "page": {
            "limit": limit,
            "next_cursor": _next_cursor(data[-1]["id"]) if has_more else None,
        },
    }


@router.post("/institutions/{institution_id}/campuses", status_code=201)
def create_campus(
    institution_id: UUID,
    payload: CreateCampusRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Add a campus location to an institution within an atomic transaction."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "campus.create"
    body_dict = payload.model_dump(mode="json")

    # Idempotency lookup
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
                # 1. Verify institution exists
                cur.execute("SELECT id FROM public.institutions WHERE id = %s", (institution_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404)

                now = datetime.now(timezone.utc)
                # If is_primary, clear existing primary
                if payload.is_primary:
                    cur.execute(
                        "UPDATE public.institution_campuses SET is_primary = false "
                        "WHERE institution_id = %s AND is_primary = true",
                        (institution_id,),
                    )

                # 2. Insert campus
                from psycopg.types.json import Jsonb
                cur.execute(
                    "INSERT INTO public.institution_campuses "
                    "(institution_id, campus_name, address, region_id, is_primary, created_at, created_by, updated_at, updated_by, version) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1) "
                    "RETURNING id, institution_id, campus_name, address, region_id, is_primary, created_at, updated_at, version",
                    (institution_id, payload.campus_name, Jsonb(payload.address), payload.region_id, payload.is_primary, now, caller_uuid, now, caller_uuid),
                )
                campus = cur.fetchone()
                campus_id = campus["id"]

                # 3. Append audit event
                audit_meta = {
                    "campus_name": payload.campus_name,
                    "is_primary": payload.is_primary,
                    "region_id": str(payload.region_id) if payload.region_id else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="CAMPUS_CREATED",
                    entity_type="institution_campus",
                    entity_id=campus_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # 4. Enqueue outbox event
                enqueue(
                    cur,
                    event_type="CAMPUS_CREATED",
                    entity_type="institution_campus",
                    entity_id=campus_id,
                    entity_version=1,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(campus)
                if idempotency_key:
                    store_result(
                        cur,
                        actor_id=caller_uuid,
                        operation=operation,
                        raw_key=idempotency_key,
                        body=body_dict,
                        http_status=201,
                        response_json=response_data,
                        expires_at=now + timedelta(days=1),
                    )

        return response_data
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.get("/institutions/{institution_id}/attributes")
def list_profile_attributes(
    institution_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List typed profile attributes for an institution."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, institution_id, attribute_key, value_text, value_date, value_number, "
        "source_document_id, source_document_version_id, verified_status, created_at, updated_at, version "
        "FROM public.institution_profile_attributes "
        "WHERE institution_id = %s ORDER BY attribute_key ASC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (institution_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.put("/institutions/{institution_id}/attributes")
def update_profile_attributes(
    institution_id: UUID,
    payload: UpdateProfileAttributesRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Batch upsert typed profile attributes with provenance tracking."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    now = datetime.now(timezone.utc)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                # 1. Verify institution exists
                cur.execute("SELECT id FROM public.institutions WHERE id = %s", (institution_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404)

                updated_items = []
                for attr in payload.attributes:
                    if attr.verified_status != "pending":
                        cur.execute("SELECT r.role_code FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id WHERE a.user_id=%s AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (caller_uuid,))
                        if not {role_name(r["role_code"]) for r in cur.fetchall()}.intersection({"REGIONAL", "CENTRAL", "SCRUTINY", "COMPLIANCE"}):
                            raise HTTPException(403, detail="Profile verification requires a regulatory reviewer")
                    if attr.source_document_version_id:
                        cur.execute("SELECT d.id FROM public.document_versions v JOIN public.documents d ON d.id=v.document_id WHERE v.id=%s AND d.institution_id=%s", (attr.source_document_version_id, institution_id))
                        source = cur.fetchone()
                        if not source or (attr.source_document_id and attr.source_document_id != source["id"]):
                            raise HTTPException(422, detail="Attribute source must belong to this institution")
                        attr.source_document_id = source["id"]
                    elif attr.source_document_id:
                        raise HTTPException(422, detail="Choose an exact source document version")
                    if attr.verified_status == "verified" and not attr.source_document_version_id:
                        raise HTTPException(422, detail="Verified attributes require exact source evidence")
                    val_date = attr.value_date
                    cur.execute(
                        "INSERT INTO public.institution_profile_attributes "
                        "(institution_id, attribute_key, value_text, value_date, value_number, source_document_id, source_document_version_id, verified_status, created_at, created_by, updated_at, updated_by, version) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1) "
                        "ON CONFLICT (institution_id, attribute_key) DO UPDATE "
                        "SET value_text = EXCLUDED.value_text, "
                        "    value_date = EXCLUDED.value_date, "
                        "    value_number = EXCLUDED.value_number, "
                        "    source_document_id = EXCLUDED.source_document_id, "
                        "    source_document_version_id = EXCLUDED.source_document_version_id, "
                        "    verified_status = EXCLUDED.verified_status, "
                        "    updated_at = EXCLUDED.updated_at, "
                        "    updated_by = EXCLUDED.updated_by, "
                        "    version = public.institution_profile_attributes.version + 1 "
                        "RETURNING id, institution_id, attribute_key, value_text, value_date, value_number, source_document_id, verified_status, version",
                        (institution_id, attr.attribute_key, attr.value_text, val_date, attr.value_number, attr.source_document_id, attr.source_document_version_id, attr.verified_status, now, caller_uuid, now, caller_uuid),
                    )
                    saved = cur.fetchone()
                    updated_items.append(_serialize(saved))

                # Append audit event
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="INSTITUTION_ATTRIBUTES_UPDATED",
                    entity_type="institution",
                    entity_id=institution_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata={"attributes_count": len(payload.attributes)},
                )

                # Enqueue outbox event
                enqueue(
                    cur,
                    event_type="INSTITUTION_ATTRIBUTES_UPDATED",
                    entity_type="institution",
                    entity_id=institution_id,
                    payload={"attributes_count": len(payload.attributes)},
                    correlation_id=corr_uuid,
                )

        return {"data": updated_items}
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)
