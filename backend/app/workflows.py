"""Workflow definitions, stages, transitions, and guard evaluation (PRD §§5.3, 7.1, 9.2)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .accounts import _read_connection, _serialize, _user
from .auth import get_verified_subject
from .authorization import role_name


router = APIRouter(tags=["workflows"])


def evaluate_guard(guard_rule: dict[str, Any] | None, context: dict[str, Any]) -> tuple[bool, str | None]:
    """Evaluate a workflow transition guard against current execution context."""
    if not guard_rule:
        return True, None
    known = {"required_roles", "required_status", "require_all_deficiencies_resolved", "require_approved_meeting_record", "require_completed_evc", "approved", "demo_only"}
    if set(guard_rule) - known:
        return False, "Unsupported guard rule; policy correction is required"

    # Role guard
    required_roles = guard_rule.get("required_roles")
    if required_roles:
        caller_roles = context.get("caller_roles", [])
        if not {role_name(role) for role in required_roles}.intersection(role_name(role) for role in caller_roles):
            return False, f"Transition requires one of roles: {', '.join(required_roles)}"

    # Status guard
    required_status = guard_rule.get("required_status")
    if required_status:
        current_status = context.get("current_status")
        if current_status != required_status:
            return False, f"Application must be in status '{required_status}', current is '{current_status}'"

    # Deficiency resolution guard
    if guard_rule.get("require_all_deficiencies_resolved"):
        unresolved_count = context.get("unresolved_deficiency_count")
        if unresolved_count is None: return False, "Deficiency state unavailable"
        if unresolved_count > 0:
            return False, f"Cannot transition while {unresolved_count} deficiency items remain unresolved"

    for key, field in (("require_completed_evc", "completed_evc"), ("require_approved_meeting_record", "approved_meeting_record")):
        if guard_rule.get(key) and not context.get(field):
            return False, f"Transition requires {field.replace('_', ' ')}"

    return True, None


def validate_graph(stages, transitions):
    """Validate executable graph input before saving or publishing."""
    import re
    if not isinstance(stages, list) or len(stages) < 2 or not isinstance(transitions, list) or not transitions:
        raise HTTPException(422, detail="A workflow needs at least two stages and a transition")
    codes = []
    roles = {"INSTITUTION", "SCRUTINY", "REGIONAL", "CENTRAL", "COMPLIANCE", "EVC_COORDINATOR", "EVC_EXPERT"}
    for stage in stages:
        if not isinstance(stage, dict) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(stage.get("code", ""))) or not str(stage.get("name", "")).strip():
            raise HTTPException(422, detail="Stages require unique codes and names")
        if stage.get("ownerRole") not in roles or type(stage.get("slaDays")) is not int or not 0 <= stage["slaDays"] <= 3650:
            raise HTTPException(422, detail="Stages require an operational owner role and a nonnegative SLA")
        codes.append(stage["code"])
    if len(set(codes)) != len(codes): raise HTTPException(422, detail="Duplicate stage code")
    seen, edges = set(), {}
    known = {"NO_OPEN_DEFICIENCIES", "deficiencies_resolved", "COMPLETED_EVC", "APPROVED_MEETING_RECORD", "AUTHORIZED_ROLE", "authorised"}
    for edge in transitions:
        if not isinstance(edge, dict) or edge.get("from") not in codes or edge.get("to") not in codes or edge["from"] == edge["to"]:
            raise HTTPException(422, detail="Transition endpoints must be distinct stages in this workflow")
        pair = (edge["from"], edge["to"])
        if pair in seen: raise HTTPException(422, detail="Duplicate transition")
        seen.add(pair); edges.setdefault(edge["from"], []).append(edge["to"])
        guards = edge.get("guards")
        if not isinstance(guards, list) or any(g not in known for g in guards):
            raise HTTPException(422, detail="Unknown transition guard")
    reached = {codes[0]}
    for _ in codes:
        reached.update(destination for origin, destinations in edges.items() if origin in reached for destination in destinations)
    if reached != set(codes): raise HTTPException(422, detail="Every stage must be reachable from the first stage")
    if not any(code not in edges for code in codes): raise HTTPException(422, detail="Workflow requires a terminal stage")


@router.get("/application-types")
def list_application_types(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    status: Annotated[str | None, Query()] = None,
):
    """List valid application types."""
    _ = _user(request, subject)
    sql = "SELECT id, code, name, description, status, version FROM public.application_types WHERE 1=1 "
    params: list[Any] = []
    if status is not None:
        sql += " AND status = %s "
        params.append(status)
    sql += " ORDER BY code ASC"

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.get("/workflows")
def list_workflows(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    application_type_id: Annotated[UUID | None, Query()] = None,
):
    """List published workflow definitions."""
    _ = _user(request, subject)
    sql = (
        "SELECT w.id, w.name, w.application_type_id, w.aph_rule_version_id, w.status, w.version_number, "
        "t.name as application_type_name, t.code as application_type_code "
        "FROM public.workflow_definitions w "
        "JOIN public.application_types t ON t.id = w.application_type_id "
        "WHERE 1=1 "
    )
    params: list[Any] = []
    if application_type_id is not None:
        sql += " AND w.application_type_id = %s "
        params.append(application_type_id)
    sql += " ORDER BY w.name ASC, w.version_number DESC"

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.get("/workflows/{workflow_id}")
def get_workflow_detail(
    workflow_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Get workflow definition details with stages and allowed transitions."""
    _ = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT w.id, w.name, w.application_type_id, w.aph_rule_version_id, w.status, w.version_number, "
                "t.name as application_type_name, t.code as application_type_code "
                "FROM public.workflow_definitions w "
                "JOIN public.application_types t ON t.id = w.application_type_id "
                "WHERE w.id = %s",
                (workflow_id,),
            )
            wf = cur.fetchone()
            if wf is None:
                raise HTTPException(status_code=404)

            # Stages
            cur.execute(
                "SELECT id, stage_code, stage_name, stage_order, stage_type, default_sla_days "
                "FROM public.workflow_stages WHERE workflow_definition_id = %s ORDER BY stage_order ASC",
                (workflow_id,),
            )
            stages = [_serialize(row) for row in cur.fetchall()]

            # Transitions
            cur.execute(
                "SELECT id, from_stage_id, to_stage_id, transition_type, guard_rule, requires_authorisation "
                "FROM public.workflow_transitions WHERE workflow_definition_id = %s",
                (workflow_id,),
            )
            transitions = [_serialize(row) for row in cur.fetchall()]

    return {
        "workflow": _serialize(wf),
        "stages": stages,
        "transitions": transitions,
    }
