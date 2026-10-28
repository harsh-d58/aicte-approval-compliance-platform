"""Scoped, read-only institution and application records from the existing schema."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .accounts import _read_connection, _user
from .auth import get_verified_subject


router = APIRouter(tags=["records"])

# Internal granular permission codes. The policy owner must approve and provision
# these codes and their role grants before any business record is visible.
INSTITUTION_READ = "institution.read"
APPLICATION_READ = "application.read"

ACTIVE_GRANT = (
    "JOIN public.role_permissions rp ON rp.role_id = a.role_id "
    "JOIN public.permissions p ON p.id = rp.permission_id "
    "WHERE a.user_id = %s AND a.status = 'ACTIVE' "
    "AND (a.valid_from IS NULL OR a.valid_from <= CURRENT_TIMESTAMP) "
    "AND (a.valid_until IS NULL OR a.valid_until > CURRENT_TIMESTAMP) "
    "AND p.permission_code = %s AND ("
)

INSTITUTION_SCOPE = (
    "(a.scope_type = 'GLOBAL' AND a.scope_id IS NULL) "
    "OR (a.scope_type = 'INSTITUTION' AND a.scope_id = i.id) "
    "OR (a.scope_type = 'REGION' AND a.scope_id = i.region_id)"
)

APPLICATION_SCOPE = (
    "(a.scope_type = 'GLOBAL' AND a.scope_id IS NULL) "
    "OR (a.scope_type = 'INSTITUTION' AND a.scope_id = app.institution_id) "
    "OR (a.scope_type = 'REGION' AND a.scope_id = i.region_id) "
    "OR (a.scope_type = 'APPLICATION' AND a.scope_id = app.id)"
)


def _cursor_id(cursor: str | None) -> UUID | None:
    if cursor is None:
        return None
    try:
        if len(cursor) != 22:
            raise ValueError
        value = UUID(bytes=urlsafe_b64decode(cursor + "=="))
        if _next_cursor(value) != cursor:
            raise ValueError
        return value
    except (ValueError, TypeError, Base64Error):
        raise HTTPException(status_code=400) from None


def _next_cursor(value: UUID) -> str:
    return urlsafe_b64encode(value.bytes).decode("ascii").rstrip("=")


def _page(rows: list[dict], limit: int) -> dict:
    has_more = len(rows) > limit
    data = rows[:limit]
    return {
        "data": data,
        "page": {
            "limit": limit,
            "next_cursor": _next_cursor(data[-1]["id"]) if has_more else None,
        },
    }


@router.get("/institutions")
def institutions(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
    status: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
):
    user = _user(request, subject)
    after = _cursor_id(cursor)
    sql = (
        "SELECT i.id, i.official_name, i.institution_code, i.institution_type, "
        "i.status, i.region_id, i.created_at, i.updated_at, i.version "
        "FROM public.institutions i WHERE EXISTS ("
        "SELECT 1 FROM public.user_role_assignments a "
        + ACTIVE_GRANT + INSTITUTION_SCOPE + "))"
    )
    params: list = [user["id"], INSTITUTION_READ]
    if after is not None:
        sql += " AND i.id > %s"
        params.append(after)
    if status is not None:
        sql += " AND i.status = %s"
        params.append(status)
    sql += " ORDER BY i.id LIMIT %s"
    params.append(limit + 1)
    with _read_connection(request.app.state.settings.database_url) as connection:
        with connection.cursor() as db:
            db.execute(sql, params)
            return _page(db.fetchall(), limit)


@router.get("/institutions/{institution_id}")
def institution(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    institution_id: UUID,
):
    user = _user(request, subject)
    sql = (
        "SELECT i.id, i.official_name, i.institution_code, i.institution_type, "
        "i.status, i.region_id, i.created_at, i.updated_at, i.version "
        "FROM public.institutions i WHERE i.id = %s AND EXISTS ("
        "SELECT 1 FROM public.user_role_assignments a "
        + ACTIVE_GRANT + INSTITUTION_SCOPE + "))"
    )
    with _read_connection(request.app.state.settings.database_url) as connection:
        with connection.cursor() as db:
            db.execute(sql, (institution_id, user["id"], INSTITUTION_READ))
            row = db.fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    return row


@router.get("/applications")
def applications(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
    status: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
):
    user = _user(request, subject)
    after = _cursor_id(cursor)
    sql = (
        "SELECT app.id, app.application_number, app.institution_id, app.campus_id, "
        "app.application_type_id, app.workflow_definition_id, app.status, "
        "app.current_stage_instance_id, app.submitted_at, app.closed_at, "
        "app.created_at, app.updated_at, app.version "
        "FROM public.applications app "
        "JOIN public.institutions i ON i.id = app.institution_id WHERE EXISTS ("
        "SELECT 1 FROM public.user_role_assignments a "
        + ACTIVE_GRANT + APPLICATION_SCOPE + "))"
    )
    params: list = [user["id"], APPLICATION_READ]
    if after is not None:
        sql += " AND app.id > %s"
        params.append(after)
    if status is not None:
        sql += " AND app.status = %s"
        params.append(status)
    sql += " ORDER BY app.id LIMIT %s"
    params.append(limit + 1)
    with _read_connection(request.app.state.settings.database_url) as connection:
        with connection.cursor() as db:
            db.execute(sql, params)
            return _page(db.fetchall(), limit)


@router.get("/applications/{application_id}")
def application(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    application_id: UUID,
):
    user = _user(request, subject)
    sql = (
        "SELECT app.id, app.application_number, app.institution_id, app.campus_id, "
        "app.application_type_id, app.workflow_definition_id, app.status, "
        "app.current_stage_instance_id, app.submitted_at, app.closed_at, "
        "app.created_at, app.updated_at, app.version "
        "FROM public.applications app "
        "JOIN public.institutions i ON i.id = app.institution_id "
        "WHERE app.id = %s AND EXISTS ("
        "SELECT 1 FROM public.user_role_assignments a "
        + ACTIVE_GRANT + APPLICATION_SCOPE + "))"
    )
    with _read_connection(request.app.state.settings.database_url) as connection:
        with connection.cursor() as db:
            db.execute(sql, (application_id, user["id"], APPLICATION_READ))
            row = db.fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    return row
