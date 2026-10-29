"""User administration and scoped role assignment routes (PRD §9.2)."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from .accounts import _read_connection, _serialize, _user
from .records import _cursor_id, _next_cursor
from .audit import append_event
from .auth import get_verified_subject
from .authorization import validate_role_grant
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .transactions import UnsafeWriteConnection, write_transaction


router = APIRouter(tags=["users"])


class CreateRoleAssignmentRequest(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=64)
    scope_type: str = Field(..., pattern=r"^(global|institution|region|application|campus)$")
    scope_id: UUID | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    reason: str = Field(..., min_length=3, max_length=500)


class UpdateRoleAssignmentRequest(BaseModel):
    status: str | None = Field(None, pattern=r"^(active|revoked|expired|pending)$")
    valid_until: datetime | None = None
    reason: str = Field(..., min_length=3, max_length=500)


def _to_uuid(val: Any) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


def _page_users(rows: list[dict], limit: int) -> dict:
    has_more = len(rows) > limit
    data = rows[:limit]
    return {
        "data": data,
        "page": {
            "limit": limit,
            "next_cursor": _next_cursor(data[-1]["id"]) if has_more else None,
        },
    }


@router.get("/users")
def list_users(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
    status: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    role_code: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
):
    """List application users with role assignments and cursor pagination."""
    caller = _user(request, subject)
    after = _cursor_id(cursor)
    sql = (
        "SELECT u.id, u.display_name, u.email, u.status, u.last_login_at, "
        "COALESCE(array_agg(r.role_code) FILTER (WHERE r.role_code IS NOT NULL AND a.status = 'active'), '{}') AS active_roles "
        "FROM public.users u "
        "LEFT JOIN public.user_role_assignments a ON a.user_id = u.id AND a.status = 'active' "
        "LEFT JOIN public.roles r ON r.id = a.role_id "
        "WHERE 1=1 "
    )
    params: list[Any] = []
    if after is not None:
        sql += " AND u.id > %s "
        params.append(after)
    if status is not None:
        sql += " AND u.status = %s "
        params.append(status)
    if search is not None:
        sql += " AND (u.display_name ILIKE %s OR u.email ILIKE %s) "
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard])

    sql += " GROUP BY u.id, u.display_name, u.email, u.status, u.last_login_at "
    if role_code is not None:
        sql += " HAVING %s = ANY(array_agg(r.role_code)) "
        params.append(role_code)

    sql += " ORDER BY u.id ASC LIMIT %s"
    params.append(limit + 1)

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = [_serialize(row) for row in cur.fetchall()]
    return _page_users(rows, limit)


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve user details and active role assignments."""
    _ = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, display_name, email, status, last_login_at "
                "FROM public.users WHERE id = %s",
                (user_id,),
            )
            target = cur.fetchone()
            if target is None:
                raise HTTPException(status_code=404)
            cur.execute(
                "SELECT a.id, r.role_code, r.role_name, a.scope_type, a.scope_id, "
                "a.valid_from, a.valid_until, a.status "
                "FROM public.user_role_assignments a "
                "JOIN public.roles r ON r.id = a.role_id "
                "WHERE a.user_id = %s "
                "ORDER BY a.status ASC, r.role_code ASC, a.id ASC",
                (user_id,),
            )
            assignments = [_serialize(row) for row in cur.fetchall()]
    return {
        "user": _serialize(target),
        "assignments": assignments,
    }


@router.post("/users/{user_id}/role-assignments", status_code=201)
def assign_user_role(
    user_id: UUID,
    payload: CreateRoleAssignmentRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Assign a scoped role to a user within an atomic transaction with audit and outbox."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    # Validate scope constraints
    if payload.scope_type == "global" and payload.scope_id is not None:
        raise HTTPException(status_code=400)
    if payload.scope_type != "global" and payload.scope_id is None:
        raise HTTPException(status_code=400)
    if payload.valid_from and payload.valid_until and payload.valid_from >= payload.valid_until:
        raise HTTPException(status_code=400)

    now = datetime.now(timezone.utc)
    valid_from = payload.valid_from or now
    correlation_id = getattr(request.state, "correlation_id", None)
    operation = "user.role_assign"
    body_dict = payload.model_dump(mode="json")

    caller_uuid = _to_uuid(caller["id"])
    corr_uuid = _to_uuid(correlation_id)

    # Check Idempotency Key cache if supplied
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
        except IdempotencyConflict:
            raise HTTPException(status_code=409)
        except IdempotencyExpired:
            raise HTTPException(status_code=409)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                # 1. Verify target user exists
                cur.execute("SELECT id, status FROM public.users WHERE id = %s", (user_id,))
                user_row = cur.fetchone()
                if user_row is None:
                    raise HTTPException(status_code=404)

                # 2. Verify role exists
                cur.execute("SELECT id, role_code FROM public.roles WHERE role_code = %s", (payload.role_code,))
                role_row = cur.fetchone()
                if role_row is None:
                    raise HTTPException(status_code=400)
                role_id = role_row["id"]

                validate_role_grant(cur, caller_uuid, user_id, role_row["role_code"],
                                    payload.scope_type, payload.scope_id, valid_from, payload.valid_until)

                # validate_role_grant holds the target-user lock and checks
                # overlapping validity intervals. A second unbounded duplicate
                # check would incorrectly reject a later, nonoverlapping grant.
                # 4. Insert assignment
                cur.execute(
                    "INSERT INTO public.user_role_assignments "
                    "(user_id, role_id, scope_type, scope_id, valid_from, valid_until, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'active') "
                    "RETURNING id, user_id, role_id, scope_type, scope_id, valid_from, valid_until, status",
                    (user_id, role_id, payload.scope_type, payload.scope_id, valid_from, payload.valid_until),
                )
                assignment = cur.fetchone()
                assignment_id = assignment["id"]

                # 5. Append append-only audit event
                audit_metadata = {
                    "role_code": payload.role_code,
                    "scope_type": payload.scope_type,
                    "scope_id": str(payload.scope_id) if payload.scope_id else None,
                    "valid_from": valid_from.isoformat(),
                    "valid_until": payload.valid_until.isoformat() if payload.valid_until else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="ROLE_ASSIGNED",
                    entity_type="user_role_assignment",
                    entity_id=assignment_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_metadata,
                )

                # 6. Enqueue outbox event for downstream workers
                enqueue(
                    cur,
                    event_type="USER_ROLE_ASSIGNED",
                    entity_type="user_role_assignment",
                    entity_id=assignment_id,
                    payload=audit_metadata,
                    correlation_id=corr_uuid,
                )

                # 7. Store idempotency result if key was provided
                response_data = _serialize(assignment)
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


@router.patch("/users/{user_id}/role-assignments/{assignment_id}")
def update_user_role_assignment(
    user_id: UUID,
    assignment_id: UUID,
    payload: UpdateRoleAssignmentRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Revoke or modify an existing role assignment within an atomic transaction."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    now = datetime.now(timezone.utc)
    correlation_id = getattr(request.state, "correlation_id", None)
    operation = "user.role_update"
    body_dict = payload.model_dump(mode="json")

    caller_uuid = _to_uuid(caller["id"])
    corr_uuid = _to_uuid(correlation_id)

    # Check Idempotency Key cache if supplied
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
        except IdempotencyConflict:
            raise HTTPException(status_code=409)
        except IdempotencyExpired:
            raise HTTPException(status_code=409)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT id, user_id, role_id, scope_type, scope_id, valid_from, valid_until, status "
                    "FROM public.user_role_assignments "
                    "WHERE id = %s AND user_id = %s FOR UPDATE",
                    (assignment_id, user_id),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise HTTPException(status_code=404)

                new_status = payload.status or existing["status"]
                new_until = payload.valid_until if payload.valid_until is not None else existing["valid_until"]
                if new_until and existing["valid_from"] and new_until <= existing["valid_from"]:
                    raise HTTPException(422, detail="Role validity must be a nonempty interval")
                if new_status == "active":
                    cur.execute("SELECT role_code FROM public.roles WHERE id=%s", (existing["role_id"],))
                    role = cur.fetchone()
                    validate_role_grant(cur, caller_uuid, user_id, role["role_code"],
                                        existing["scope_type"], existing["scope_id"],
                                        existing["valid_from"], new_until, assignment_id)

                cur.execute(
                    "UPDATE public.user_role_assignments "
                    "SET status = %s, valid_until = %s "
                    "WHERE id = %s "
                    "RETURNING id, user_id, role_id, scope_type, scope_id, valid_from, valid_until, status",
                    (new_status, new_until, assignment_id),
                )
                updated = cur.fetchone()

                action_code = "ROLE_REVOKED" if new_status == "revoked" else "ROLE_UPDATED"
                metadata = {
                    "old_status": existing["status"],
                    "new_status": new_status,
                    "old_valid_until": existing["valid_until"].isoformat() if existing["valid_until"] else None,
                    "new_valid_until": new_until.isoformat() if new_until else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action=action_code,
                    entity_type="user_role_assignment",
                    entity_id=assignment_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=metadata,
                )
                enqueue(
                    cur,
                    event_type=f"USER_{action_code}",
                    entity_type="user_role_assignment",
                    entity_id=assignment_id,
                    payload=metadata,
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
