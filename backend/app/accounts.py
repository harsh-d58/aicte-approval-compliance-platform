"""Current identity and scope endpoints backed by the existing public schema."""

from contextlib import contextmanager
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
import psycopg
from psycopg.rows import dict_row

from .auth import get_verified_subject


router = APIRouter(tags=["identity"])


@contextmanager
def _read_connection(url: str | None, subject: str):
    if not url:
        raise HTTPException(status_code=503)
    try:
        with psycopg.connect(
            url, connect_timeout=15, sslmode="require", options="-c statement_timeout=30000", row_factory=dict_row
        ) as connection:
            if not connection.pgconn.ssl_in_use:
                raise HTTPException(status_code=503)
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_user, rolsuper, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
                if cursor.fetchone() != {"current_user": "aicte_api_reader", "rolsuper": False,
                                        "rolbypassrls": False}:
                    raise HTTPException(status_code=503)
                cursor.execute("SELECT set_config('aicte.subject_id', %s, true)",
                               (str(UUID(subject)),))
            yield connection
    except (psycopg.Error, OSError, ValueError):
        raise HTTPException(status_code=503) from None


def _serialize(row: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, (datetime, date)) else str(value) if key.endswith("_id") and value is not None else value
        for key, value in row.items()
    }


def _user(request: Request, subject: str) -> dict:
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, identity_subject, display_name, email, status, last_login_at FROM public.users "
                "WHERE (id::text = %s OR identity_subject = %s) AND status = 'active'",
                (subject, subject),
            )
            row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=403)
    res = _serialize(row)
    res["subject"] = str(res["id"])
    return res


@router.get("/me")
def me(request: Request, subject: Annotated[str, Depends(get_verified_subject)]):
    user = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT a.id, r.role_code, a.scope_type, a.scope_id, a.valid_from, a.valid_until "
                "FROM public.user_role_assignments a "
                "JOIN public.roles r ON r.id = a.role_id "
                "WHERE a.user_id = %s AND a.status = 'active' "
                "AND (a.valid_from IS NULL OR a.valid_from <= CURRENT_TIMESTAMP) "
                "AND (a.valid_until IS NULL OR a.valid_until > CURRENT_TIMESTAMP) "
                "ORDER BY r.role_code, a.id",
                (user["id"],),
            )
            assignments = [_serialize(row) for row in cursor.fetchall()]
    return {"user": user, "assignments": assignments}


@router.get("/me/permissions")
def me_permissions(request: Request, subject: Annotated[str, Depends(get_verified_subject)]):
    user = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT p.permission_code, a.scope_type, a.scope_id "
                "FROM public.user_role_assignments a "
                "JOIN public.role_permissions rp ON rp.role_id = a.role_id "
                "JOIN public.permissions p ON p.id = rp.permission_id "
                "WHERE a.user_id = %s AND a.status = 'active' "
                "AND (a.valid_from IS NULL OR a.valid_from <= CURRENT_TIMESTAMP) "
                "AND (a.valid_until IS NULL OR a.valid_until > CURRENT_TIMESTAMP) "
                "ORDER BY p.permission_code, a.scope_type, a.scope_id",
                (user["id"],),
            )
            permissions = [_serialize(row) for row in cursor.fetchall()]
    return {"data": permissions}
