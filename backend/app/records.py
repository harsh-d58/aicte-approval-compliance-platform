"""Scoped, read-only institution and application records from the existing schema."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from copy import deepcopy
from binascii import Error as Base64Error
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .accounts import _read_connection, _user
from .auth import get_verified_subject
from datetime import datetime, timezone
from psycopg.rows import dict_row
from .audit import verify_chain_rows


router = APIRouter(tags=["records"])


def _require_audit_access(cursor, subject):
    cursor.execute("SELECT 1 FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id "
                   "WHERE a.user_id=%s AND a.status='active' AND a.scope_type='global' "
                   "AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now()) "
                   "AND r.role_code IN ('AUDITOR','CENTRAL','CENTRAL_OFFICER','SYSTEM','SYSTEM_ADMIN','DEMO_AUDITOR','DEMO_CENTRAL','DEMO_SYSTEM') LIMIT 1", (subject,))
    if not cursor.fetchone():
        raise HTTPException(403)

# Internal granular permission codes. The policy owner must approve and provision
# these codes and their role grants before any business record is visible.
INSTITUTION_READ = "institution.read"
APPLICATION_READ = "application.read"

ACTIVE_GRANT = (
    "JOIN public.role_permissions rp ON rp.role_id = a.role_id "
    "JOIN public.permissions p ON p.id = rp.permission_id "
    "WHERE a.user_id = %s AND a.status = 'active' "
    "AND (a.valid_from IS NULL OR a.valid_from <= CURRENT_TIMESTAMP) "
    "AND (a.valid_until IS NULL OR a.valid_until > CURRENT_TIMESTAMP) "
    "AND p.permission_code = %s AND ("
)

INSTITUTION_SCOPE = (
    "(a.scope_type = 'global' AND a.scope_id IS NULL) "
    "OR (a.scope_type = 'institution' AND a.scope_id = i.id) "
    "OR (a.scope_type = 'region' AND a.scope_id = i.region_id)"
)

APPLICATION_SCOPE = (
    "(a.scope_type = 'global' AND a.scope_id IS NULL) "
    "OR (a.scope_type = 'institution' AND a.scope_id = app.institution_id) "
    "OR (a.scope_type = 'region' AND a.scope_id = i.region_id) "
    "OR (a.scope_type = 'application' AND a.scope_id = app.id)"
)

# The institution join below is LEFT: an application-scoped reader may have
# application.read without institution.read, so institution RLS hides i while
# the exact application grant must remain usable.


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
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
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
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
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
        "LEFT JOIN public.institutions i ON i.id = app.institution_id WHERE EXISTS ("
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
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
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
        "LEFT JOIN public.institutions i ON i.id = app.institution_id "
        "WHERE app.id = %s AND EXISTS ("
        "SELECT 1 FROM public.user_role_assignments a "
        + ACTIVE_GRANT + APPLICATION_SCOPE + "))"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as db:
            db.execute(sql, (application_id, user["id"], APPLICATION_READ))
            row = db.fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    return row



@router.get("/audit/verify-chain")
def verify_audit_chain(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    limit_recent: Annotated[int, Query(ge=1, le=50)] = 10,
    simulate: bool = False,
):
    """Cryptographic SHA-256 verification of the full PostgreSQL audit ledger (PRD §13.4, BR-18, BR-22)."""
    _ = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, subject) as connection:
        with connection.cursor(row_factory=dict_row) as cur:
            _require_audit_access(cur, subject)
            # 1. Fetch full ordered audit chain
            cur.execute(
                "SELECT id, actor_id, action, entity_type, entity_id, event_at, correlation_id, "
                "       reason, metadata, previous_hash, event_hash "
                "FROM public.audit_events "
                "ORDER BY event_at ASC, id ASC"
            )
            rows = cur.fetchall()

            # 2. Check active PostgreSQL trigger immutability
            cur.execute(
                "SELECT tgname "
                "FROM pg_trigger "
                "WHERE tgrelid = 'public.audit_events'::regclass AND NOT tgisinternal AND tgenabled <> 'D'"
            )
            trigger_rows = cur.fetchall()
            active_triggers = [t["tgname"] for t in trigger_rows]
            immutable_triggers_active = any("no_update" in t for t in active_triggers)

            # Simulation changes only an in-memory copy, then runs the same verifier.
            simulated_event_id = None
            if simulate:
                rows = deepcopy(rows)
                target = next((row for row in reversed(rows) if row.get("event_hash")), None)
                if target is None:
                    raise HTTPException(409, detail="No hashed audit event available for simulation")
                simulated_event_id = str(target["id"])
                target["reason"] = (target.get("reason") or "") + " [simulation altered payload]"
            # 3. Cryptographic chain verification
            check_result = verify_chain_rows(rows)

            # 4. Extract genesis, head, and recent blocks
            genesis_hash = rows[0]["event_hash"] if rows else None
            head_hash = rows[-1]["event_hash"] if rows else None
            recent_rows = rows[-limit_recent:] if rows else []

            recent_blocks = [
                {
                    "id": str(r["id"]),
                    "action": r["action"],
                    "actor_id": str(r["actor_id"]) if r.get("actor_id") else None,
                    "entity_type": r["entity_type"],
                    "entity_id": str(r["entity_id"]),
                    "event_at": r["event_at"].isoformat() if hasattr(r["event_at"], "isoformat") else str(r["event_at"]),
                    "previous_hash": r.get("previous_hash"),
                    "event_hash": r.get("event_hash"),
                    "valid": not any(e["id"] == str(r["id"]) for e in check_result["errors"]),
                }
                for r in recent_rows
            ]

            return {
                "valid": check_result["valid"],
                "simulation": simulate,
                "simulated_event_id": simulated_event_id,
                "total_events": check_result["count"],
                "genesis_hash": genesis_hash,
                "head_hash": head_hash,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "errors": check_result.get("errors", []),
                "immutable_triggers_active": immutable_triggers_active,
                "active_triggers": list(set(active_triggers)),
                "recent_blocks": recent_blocks,
            }
