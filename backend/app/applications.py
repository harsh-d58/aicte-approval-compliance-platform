"""Application draft intake, editing, submission, and stage transition engine (PRD §§5.3, 7.1, 9.2)."""

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
from .workflows import evaluate_guard
from .authorization import role_name


router = APIRouter(tags=["applications"])


class CreateApplicationRequest(BaseModel):
    institution_id: UUID
    application_type_id: UUID
    workflow_definition_id: UUID
    campus_id: UUID | None = None
    reason: str = Field("Initial application draft creation", min_length=3, max_length=500)


class UpdateApplicationDraftRequest(BaseModel):
    campus_id: UUID | None = None
    expected_version: int = Field(..., ge=1)
    reason: str = Field("Draft application update", min_length=3, max_length=500)


class SubmitApplicationRequest(BaseModel):
    expected_version: int = Field(..., ge=1)
    reason: str = Field("Application submitted for regulatory review", min_length=3, max_length=500)


class TransitionApplicationRequest(BaseModel):
    to_stage_id: UUID
    expected_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3, max_length=500)


def _generate_app_number() -> str:
    year = datetime.now(timezone.utc).year
    suffix = secrets.token_hex(4).upper()
    return f"APP-{year}-{suffix}"


@router.post("/applications", status_code=201)
def create_application_draft(
    payload: CreateApplicationRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Create a new draft application bound to an institution, application type, and workflow."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "application.create_draft"
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
                cur.execute("SELECT id FROM public.institutions WHERE id = %s", (payload.institution_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404)

                # 2. Verify application type exists
                cur.execute("SELECT id FROM public.application_types WHERE id = %s AND status='active'", (payload.application_type_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=400)

                # 3. Verify workflow definition exists and matches type
                cur.execute(
                    "SELECT id FROM public.workflow_definitions WHERE id = %s AND application_type_id = %s AND status='published'",
                    (payload.workflow_definition_id, payload.application_type_id),
                )
                if cur.fetchone() is None:
                    raise HTTPException(status_code=400)

                if payload.campus_id:
                    cur.execute("SELECT id FROM public.institution_campuses WHERE id=%s AND institution_id=%s", (payload.campus_id, payload.institution_id))
                    if not cur.fetchone(): raise HTTPException(422, detail="Campus must belong to this institution")

                app_number = _generate_app_number()
                now = datetime.now(timezone.utc)

                cur.execute(
                    "INSERT INTO public.applications "
                    "(application_number, institution_id, campus_id, application_type_id, "
                    " workflow_definition_id, status, created_at, created_by, updated_at, updated_by, version) "
                    "VALUES (%s, %s, %s, %s, %s, 'draft', %s, %s, %s, %s, 1) "
                    "RETURNING id, application_number, institution_id, campus_id, application_type_id, "
                    "          workflow_definition_id, status, created_at, updated_at, version",
                    (app_number, payload.institution_id, payload.campus_id, payload.application_type_id,
                     payload.workflow_definition_id, now, caller_uuid, now, caller_uuid),
                )
                app = cur.fetchone()
                app_id = app["id"]

                # Append audit event
                audit_meta = {
                    "application_number": app_number,
                    "institution_id": str(payload.institution_id),
                    "application_type_id": str(payload.application_type_id),
                    "workflow_definition_id": str(payload.workflow_definition_id),
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="APPLICATION_DRAFT_CREATED",
                    entity_type="application",
                    entity_id=app_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # Enqueue outbox event
                enqueue(
                    cur,
                    event_type="APPLICATION_DRAFT_CREATED",
                    entity_type="application",
                    entity_id=app_id,
                    entity_version=1,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(app)
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


@router.get("/applications/{application_id}/history")
@router.get("/applications/{application_id}/workflow-history")
def application_history(application_id: UUID, request: Request,
                        subject: Annotated[str, Depends(get_verified_subject)]):
    _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM public.stage_history WHERE application_id=%s ORDER BY event_at,id", (application_id,))
            return {"data": [_serialize(row) for row in cur.fetchall()]}


@router.get("/applications/{application_id}/assignments")
def application_assignments(application_id: UUID, request: Request,
                            subject: Annotated[str, Depends(get_verified_subject)]):
    _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM public.assignments WHERE application_id=%s ORDER BY assigned_at,id", (application_id,))
            return {"data": [_serialize(row) for row in cur.fetchall()]}


class AssignmentRequest(BaseModel):
    assigned_user_id: UUID
    due_at: datetime
    expected_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3, max_length=500)


@router.post("/applications/{application_id}/assignments", status_code=201)
def assign_application(application_id: UUID, payload: AssignmentRequest, request: Request,
                       subject: Annotated[str, Depends(get_verified_subject)]):
    from .portal_commands import PortalCommand, execute_command
    return execute_command(request, subject, PortalCommand(kind="application.assign", id=application_id,
        expectedVersion=payload.expected_version, values={"ownerId":str(payload.assigned_user_id),
        "dueAt":payload.due_at.isoformat(), "reason":payload.reason}))


@router.patch("/applications/{application_id}")
@router.put("/applications/{application_id}")
def update_application_draft(
    application_id: UUID,
    payload: UpdateApplicationDraftRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Update sections of an application draft with optimistic version check."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "application.update_draft"
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

                # 2. Check draft status
                cur.execute("SELECT status FROM public.applications WHERE id = %s", (application_id,))
                current = cur.fetchone()
                if current["status"] != "draft":
                    raise HTTPException(status_code=409)
                if payload.campus_id:
                    cur.execute("SELECT c.id FROM public.institution_campuses c JOIN public.applications a ON a.institution_id=c.institution_id WHERE c.id=%s AND a.id=%s", (payload.campus_id, application_id))
                    if not cur.fetchone(): raise HTTPException(422, detail="Campus must belong to this institution")

                now = datetime.now(timezone.utc)
                cur.execute(
                    "UPDATE public.applications "
                    "SET campus_id = %s, updated_at = %s, updated_by = %s "
                    "WHERE id = %s "
                    "RETURNING id, application_number, institution_id, campus_id, application_type_id, status, updated_at, version",
                    (payload.campus_id, now, caller_uuid, application_id),
                )
                updated = cur.fetchone()

                audit_meta = {
                    "old_version": expected_version,
                    "new_version": next_version,
                    "campus_id": str(payload.campus_id) if payload.campus_id else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="APPLICATION_DRAFT_UPDATED",
                    entity_type="application",
                    entity_id=application_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="APPLICATION_DRAFT_UPDATED",
                    entity_type="application",
                    entity_id=application_id,
                    entity_version=next_version,
                    payload=audit_meta,
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


@router.post("/applications/{application_id}/submit")
def submit_application(
    application_id: UUID,
    payload: SubmitApplicationRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Atomic submission of an application draft, starting workflow and stage tracking."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "application.submit"
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
                try:
                    lock_versioned(cur, table="applications", record_id=application_id, expected_version=expected_version)
                    next_version = bump_version(cur, table="applications", record_id=application_id, expected_version=expected_version)
                except StaleVersion:
                    raise HTTPException(status_code=412)
                except RecordMissing:
                    raise HTTPException(status_code=404)

                cur.execute(
                    "SELECT id, status, workflow_definition_id, application_number FROM public.applications WHERE id = %s",
                    (application_id,),
                )
                app = cur.fetchone()
                if app["status"] != "draft":
                    raise HTTPException(status_code=409)

                # Find initial stage (order = 1)
                cur.execute(
                    "SELECT id, stage_code, stage_name, default_sla_days FROM public.workflow_stages "
                    "WHERE workflow_definition_id = %s AND EXISTS (SELECT 1 FROM public.workflow_definitions w WHERE w.id=workflow_definition_id AND w.status='published') ORDER BY stage_order ASC LIMIT 1",
                    (app["workflow_definition_id"],),
                )
                first_stage = cur.fetchone()
                if first_stage is None:
                    raise HTTPException(409, detail="A published effective workflow is required")

                first_stage_id = first_stage["id"]
                now = datetime.now(timezone.utc)
                due_at = now + timedelta(days=first_stage["default_sla_days"]) if first_stage.get("default_sla_days") else None

                # 1. Insert application submission record (submission #1)
                cur.execute(
                    "INSERT INTO public.application_submissions "
                    "(application_id, submission_number, submitted_by, submitted_at, submission_status, created_at) "
                    "VALUES (%s, 1, %s, %s, 'submitted', %s) RETURNING id",
                    (application_id, caller_uuid, now, now),
                )

                submission_id = cur.fetchone()["id"]

                # 2. Insert initial stage instance
                cur.execute(
                    "INSERT INTO public.application_stage_instances "
                    "(application_id, workflow_stage_id, status, entered_at, due_at, created_at, created_by) "
                    "VALUES (%s, %s, 'in_progress', %s, %s, %s, %s) RETURNING id",
                    (application_id, first_stage_id, now, due_at, now, caller_uuid),
                )
                stage_instance_id = cur.fetchone()["id"]

                # 3. Update application status and current stage instance
                cur.execute(
                    "UPDATE public.applications "
                    "SET status = 'submitted', current_stage_instance_id = %s, submitted_at = %s, updated_at = %s, updated_by = %s "
                    "WHERE id = %s "
                    "RETURNING id, application_number, status, current_stage_instance_id, submitted_at, version",
                    (stage_instance_id, now, now, caller_uuid, application_id),
                )
                submitted_app = cur.fetchone()

                # 4. Record stage history
                cur.execute(
                    "INSERT INTO public.stage_history "
                    "(application_id, from_stage_id, to_stage_id, actor_user_id, reason, event_at, correlation_id, created_at) "
                    "VALUES (%s, NULL, %s, %s, %s, %s, %s, %s)",
                    (application_id, first_stage_id, caller_uuid, payload.reason, now, corr_uuid, now),
                )

                # 5. Append audit event
                audit_meta = {
                    "application_number": app["application_number"],
                    "submission_id": str(submission_id),
                    "stage_instance_id": str(stage_instance_id),
                    "first_stage_id": str(first_stage_id),
                    "old_version": expected_version,
                    "new_version": next_version,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="APPLICATION_SUBMITTED",
                    entity_type="application",
                    entity_id=application_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # 6. Enqueue outbox event
                enqueue(
                    cur,
                    event_type="APPLICATION_SUBMITTED",
                    entity_type="application",
                    entity_id=application_id,
                    entity_version=next_version,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(submitted_app)
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


@router.post("/applications/{application_id}/transitions")
def transition_application(
    application_id: UUID,
    payload: TransitionApplicationRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Execute an authorised stage transition with guard evaluation and full audit."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "application.transition"
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
                try:
                    lock_versioned(cur, table="applications", record_id=application_id, expected_version=expected_version)
                    next_version = bump_version(cur, table="applications", record_id=application_id, expected_version=expected_version)
                except StaleVersion:
                    raise HTTPException(status_code=412)
                except RecordMissing:
                    raise HTTPException(status_code=404)

                cur.execute(
                    "SELECT a.id, a.status, a.current_stage_instance_id, a.workflow_definition_id, a.application_number, "
                    "       si.workflow_stage_id as current_stage_id "
                    "FROM public.applications a "
                    "LEFT JOIN public.application_stage_instances si ON si.id = a.current_stage_instance_id "
                    "WHERE a.id = %s",
                    (application_id,),
                )
                app = cur.fetchone()
                if not app or not app["current_stage_instance_id"]:
                    raise HTTPException(status_code=400)
                if app["status"] in {"draft", "approved", "rejected", "closed", "withdrawn"}:
                    raise HTTPException(409, detail="This application cannot transition")

                current_stage_id = app["current_stage_id"]

                # 1. Check transition exists
                cur.execute(
                    "SELECT id, guard_rule, transition_type, requires_authorisation "
                    "FROM public.workflow_transitions "
                    "WHERE workflow_definition_id = %s AND from_stage_id = %s AND to_stage_id = %s",
                    (app["workflow_definition_id"], current_stage_id, payload.to_stage_id),
                )
                transition = cur.fetchone()
                if transition is None:
                    raise HTTPException(status_code=400)

                # 2. Evaluate guard
                # Check unresolved deficiencies
                cur.execute(
                    "SELECT count(*) FROM public.deficiency_notices dn "
                    "JOIN public.deficiency_items di ON di.deficiency_notice_id = dn.id "
                    "WHERE dn.application_id = %s AND di.resolution_status NOT IN ('accepted','waived')",
                    (application_id,),
                )
                unresolved = cur.fetchone()["count"]

                # Fetch caller roles
                cur.execute(
                    "SELECT r.role_code FROM public.user_role_assignments a "
                    "JOIN public.roles r ON r.id = a.role_id "
                    "WHERE a.user_id = %s AND a.status = 'active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())",
                    (caller_uuid,),
                )
                caller_roles = [row["role_code"] for row in cur.fetchall()]

                if unresolved:
                    raise HTTPException(409, detail="Resolve every deficiency item before advancing")

                context = {
                    "caller_roles": caller_roles,
                    "current_status": app["status"],
                    "unresolved_deficiency_count": unresolved,
                }
                guard = transition["guard_rule"] or {}
                if guard.get("require_completed_evc"):
                    cur.execute("SELECT EXISTS(SELECT 1 FROM public.evc_visits WHERE application_id=%s AND status='completed') AS ok", (application_id,))
                    context["completed_evc"] = cur.fetchone()["ok"]
                if guard.get("require_approved_meeting_record"):
                    cur.execute("SELECT EXISTS(SELECT 1 FROM public.evc_reports r JOIN public.evc_visits v ON v.id=r.evc_visit_id WHERE v.application_id=%s AND r.report_status='approved') AS ok", (application_id,))
                    context["approved_meeting_record"] = cur.fetchone()["ok"]
                passed, reason = evaluate_guard(transition["guard_rule"], context)
                if not passed:
                    raise HTTPException(status_code=403)

                # 3. Get destination stage info
                cur.execute(
                    "SELECT id, stage_code, stage_type, default_sla_days FROM public.workflow_stages WHERE id = %s AND workflow_definition_id=%s",
                    (payload.to_stage_id, app["workflow_definition_id"]),
                )
                target_stage = cur.fetchone()
                if not target_stage:
                    raise HTTPException(status_code=400)
                stage_role_map = {
                    "INTAKE": "INSTITUTION", "SCRUTINY": "SCRUTINY", "DEFICIENCY": "INSTITUTION",
                    "EVC": "EVC_COORDINATOR", "COMPLIANCE": "COMPLIANCE", "DECISION": "REGIONAL"
                }
                owner_role = stage_role_map.get((target_stage.get("stage_type") or "").upper(), "REGIONAL")
                if transition["requires_authorisation"] and owner_role:
                    if not {role_name(r) for r in caller_roles}.intersection({"REGIONAL", "CENTRAL", "SCRUTINY", owner_role}):
                        raise HTTPException(403)

                now = datetime.now(timezone.utc)
                due_at = now + timedelta(days=target_stage["default_sla_days"]) if target_stage.get("default_sla_days") else None

                # Complete current stage instance
                cur.execute(
                    "UPDATE public.application_stage_instances "
                    "SET status = 'completed', completed_at = %s "
                    "WHERE id = %s",
                    (now, app["current_stage_instance_id"]),
                )

                # Create new stage instance
                cur.execute(
                    "INSERT INTO public.application_stage_instances "
                    "(application_id, workflow_stage_id, status, entered_at, due_at, created_at, created_by) "
                    "VALUES (%s, %s, 'in_progress', %s, %s, %s, %s) RETURNING id",
                    (application_id, payload.to_stage_id, now, due_at, now, caller_uuid),
                )
                new_stage_instance_id = cur.fetchone()["id"]
                if target_stage["stage_type"] == "scrutiny":
                    cur.execute("INSERT INTO public.assignments(application_id,stage_instance_id,assigned_user_id,assigned_at,due_at,status,created_by) "
                                "SELECT application_id,%s,assigned_user_id,%s,%s,'active',%s FROM public.assignments "
                                "WHERE application_id=%s AND status='active'", (new_stage_instance_id, now, due_at, caller_uuid, application_id))
                cur.execute("UPDATE public.assignments SET status='completed' WHERE application_id=%s AND status='active' AND stage_instance_id<>%s", (application_id,new_stage_instance_id))

                # Derive new application status from stage type
                stage_type = target_stage["stage_type"]
                status_map = {
                    "intake": "submitted",
                    "scrutiny": "under_review",
                    "deficiency": "deficiency_returned",
                    "evc": "under_review",
                    "decision": "under_review",
                }
                new_status = status_map.get(stage_type, "under_review")

                # Update application
                cur.execute(
                    "UPDATE public.applications "
                    "SET status = %s, current_stage_instance_id = %s, updated_at = %s, updated_by = %s "
                    "WHERE id = %s "
                    "RETURNING id, application_number, status, current_stage_instance_id, updated_at, version",
                    (new_status, new_stage_instance_id, now, caller_uuid, application_id),
                )
                updated_app = cur.fetchone()
                if stage_type == "evc":
                    cur.execute("INSERT INTO public.evc_visits(application_id,campus_id,status,required_by,created_at,created_by,updated_at,updated_by) "
                                "SELECT id,campus_id,'required',%s,%s,%s,%s,%s FROM public.applications a WHERE a.id=%s "
                                "AND NOT EXISTS(SELECT 1 FROM public.evc_visits v WHERE v.application_id=a.id AND v.status NOT IN ('cancelled','completed'))",
                                (due_at or now+timedelta(days=30),now,caller_uuid,now,caller_uuid,application_id))

                # Stage history
                cur.execute(
                    "INSERT INTO public.stage_history "
                    "(application_id, from_stage_id, to_stage_id, actor_user_id, reason, event_at, correlation_id, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (application_id, current_stage_id, payload.to_stage_id, caller_uuid, payload.reason, now, corr_uuid, now),
                )

                # Audit event
                audit_meta = {
                    "from_stage_id": str(current_stage_id),
                    "to_stage_id": str(payload.to_stage_id),
                    "stage_instance_id": str(new_stage_instance_id),
                    "new_status": new_status,
                    "old_version": expected_version,
                    "new_version": next_version,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="STAGE_TRANSITIONED",
                    entity_type="application",
                    entity_id=application_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )

                # Outbox event
                enqueue(
                    cur,
                    event_type="APPLICATION_STAGE_TRANSITIONED",
                    entity_type="application",
                    entity_id=application_id,
                    entity_version=next_version,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(updated_app)
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
