"""Meeting-to-Record Assistant, committee observations, draft generation, and human approval (PRD §§5.5, 7.3, 9.2, BR-12, BR-13)."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid
from .workflows import evaluate_guard
from .authorization import role_name


router = APIRouter(tags=["meeting-records"])


class CreateObservationRequest(BaseModel):
    criterion_code: str = Field(..., min_length=2, max_length=100)
    observation_text: str = Field(..., min_length=5, max_length=3000)
    source_type: str = Field("site_inspection", pattern=r"^(site_inspection|interview|document_check|facility_audit)$")
    reason: str = Field("Record on-site committee observation", min_length=3, max_length=500)
    review_status: str = Field("draft", pattern=r"^(draft|submitted)$")


class GenerateMeetingDraftRequest(BaseModel):
    template_version: str = Field("EVC-2026.1", max_length=50)
    record_type: str = Field("minutes", pattern=r"^(minutes|evc_report|observations_summary)$")
    reason: str = Field("Generate draft meeting record from verified visit observations", min_length=3, max_length=500)
    source_ids: list[UUID] | None = Field(None, max_length=500)


class ApproveMeetingRecordRequest(BaseModel):
    reason: str = Field("Convener statutory approval of meeting minutes and EVC report", min_length=3, max_length=500)


class RequestChangesRequest(BaseModel):
    comments: str = Field(..., min_length=5, max_length=2000)
    reason: str = Field("Request corrections to draft meeting record", min_length=3, max_length=500)


def _lock_current_record(cur, report_id):
    cur.execute('SELECT r.*,v.record_type,v.approval_status,v.source_manifest FROM public.evc_reports r JOIN public.meeting_record_versions v ON v.id=r.current_version_id WHERE r.id=%s FOR UPDATE OF r,v', (report_id,))
    row=cur.fetchone()
    if not row:
        raise HTTPException(404)
    return row


def _require_record_reviewer(cur, report, caller_id):
    # Resource scope is checked by authorize_request. Within an expert committee,
    # only its selected convener may issue the formal human approval.
    cur.execute("SELECT r.role_code FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id WHERE a.user_id=%s AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (caller_id,))
    roles={role_name(row['role_code']) for row in cur.fetchall()}
    if roles.intersection({'REGIONAL','CENTRAL','EVC_COORDINATOR'}):
        return
    cur.execute("SELECT EXISTS(SELECT 1 FROM public.evc_committee_members m WHERE m.evc_visit_id=%s AND m.committee_role='convener' AND m.selection_status='selected' AND m.expert_user_id=%s) AS authorised", (report['evc_visit_id'],caller_id))
    if 'EVC_EXPERT' not in roles or not cur.fetchone()['authorised']:
        raise HTTPException(403,detail='Formal review requires an authorised regulatory reviewer or selected convener')


def _advance_evc_to_decision(cur, report, caller_id, now, reason, correlation_id):
    """Use only a configured EVC-to-decision edge, inside the approval transaction."""
    cur.execute('SELECT a.*,si.workflow_stage_id,s.stage_type FROM public.evc_visits v JOIN public.applications a ON a.id=v.application_id LEFT JOIN public.application_stage_instances si ON si.id=a.current_stage_instance_id LEFT JOIN public.workflow_stages s ON s.id=si.workflow_stage_id WHERE v.id=%s FOR UPDATE OF a', (report['evc_visit_id'],))
    app=cur.fetchone()
    if not app or app['status'] in ('draft','approved','rejected','closed','withdrawn'):
        raise HTTPException(409,detail='Application cannot advance from its current state')
    if app['stage_type']=='decision':
        return
    if app['stage_type']!='evc':
        raise HTTPException(409,detail='EVC report approval requires an EVC stage')
    cur.execute("SELECT t.*,s.default_sla_days FROM public.workflow_transitions t JOIN public.workflow_stages s ON s.id=t.to_stage_id WHERE t.workflow_definition_id=%s AND t.from_stage_id=%s AND s.workflow_definition_id=t.workflow_definition_id AND s.stage_type='decision'", (app['workflow_definition_id'],app['workflow_stage_id']))
    edges=cur.fetchall()
    if len(edges)!=1:
        raise HTTPException(409,detail='A unique configured transition to the decision stage is required')
    edge=edges[0]
    cur.execute("SELECT count(*) AS count FROM public.deficiency_items di JOIN public.deficiency_notices dn ON dn.id=di.deficiency_notice_id WHERE dn.application_id=%s AND di.resolution_status NOT IN ('accepted','waived')", (app['id'],))
    unresolved=cur.fetchone()['count']
    cur.execute("SELECT r.role_code FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id WHERE a.user_id=%s AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (caller_id,))
    roles=[r['role_code'] for r in cur.fetchall()]
    cur.execute("SELECT status='completed' AS completed FROM public.evc_visits WHERE id=%s", (report['evc_visit_id'],))
    completed=cur.fetchone()['completed']
    passed,_=evaluate_guard(edge['guard_rule'],{'caller_roles':roles,'current_status':app['status'],
        'unresolved_deficiency_count':unresolved,'completed_evc':completed,'approved_meeting_record':True})
    if unresolved or not passed or not completed:
        raise HTTPException(409,detail='Configured EVC transition prerequisites are not satisfied')
    cur.execute("UPDATE public.application_stage_instances SET status='completed',completed_at=%s WHERE id=%s", (now,app['current_stage_instance_id']))
    due_at=now+timedelta(days=edge['default_sla_days']) if edge.get('default_sla_days') else None
    cur.execute("INSERT INTO public.application_stage_instances(application_id,workflow_stage_id,status,entered_at,due_at,created_at,created_by) VALUES(%s,%s,'in_progress',%s,%s,%s,%s) RETURNING id", (app['id'],edge['to_stage_id'],now,due_at,now,caller_id))
    instance_id=cur.fetchone()['id']
    cur.execute("UPDATE public.applications SET status='under_review',current_stage_instance_id=%s,version=version+1,updated_at=%s,updated_by=%s WHERE id=%s", (instance_id,now,caller_id,app['id']))
    cur.execute("UPDATE public.assignments SET status='completed' WHERE application_id=%s AND status='active'", (app['id'],))
    cur.execute('INSERT INTO public.stage_history(application_id,from_stage_id,to_stage_id,actor_user_id,reason,event_at,correlation_id,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)', (app['id'],app['workflow_stage_id'],edge['to_stage_id'],caller_id,reason,now,correlation_id,now))
    metadata={'from_stage_id':str(app['workflow_stage_id']),'to_stage_id':str(edge['to_stage_id']),'report_id':str(report['id'])}
    append_event(cur,actor_id=caller_id,action='STAGE_TRANSITIONED',entity_type='application',entity_id=app['id'],correlation_id=correlation_id,reason=reason,metadata=metadata)
    enqueue(cur,event_type='APPLICATION_STAGE_TRANSITIONED',entity_type='application',entity_id=app['id'],payload=metadata,correlation_id=correlation_id)


@router.post("/evc-visits/{visit_id}/observations", status_code=201)
def record_committee_observation(
    visit_id: UUID,
    payload: CreateObservationRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Record verified on-site committee observations against regulatory criteria (PRD §7.3)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "evc.record_observation"
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
                # Verify visit exists
                cur.execute("SELECT id, status FROM public.evc_visits WHERE id = %s FOR UPDATE", (visit_id,))
                visit = cur.fetchone()
                if visit is None:
                    raise HTTPException(status_code=404)
                if visit['status'] not in ('scheduled','confirmed','completed'):
                    raise HTTPException(409, detail='Observations require a confirmed or completed visit')

                now = datetime.now(timezone.utc)
                cur.execute(
                    "INSERT INTO public.evc_observations "
                    "(evc_visit_id, criterion_code, observation_text, source_type, created_by, review_status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, evc_visit_id, criterion_code, observation_text, source_type, review_status, created_at",
                    (visit_id, payload.criterion_code, payload.observation_text, payload.source_type, caller_uuid, payload.review_status, now, now),
                )
                obs = cur.fetchone()
                obs_id = obs["id"]

                audit_meta = {
                    "visit_id": str(visit_id),
                    "criterion_code": payload.criterion_code,
                    "source_type": payload.source_type,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="EVC_OBSERVATION_RECORDED",
                    entity_type="evc_observation",
                    entity_id=obs_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="EVC_OBSERVATION_RECORDED",
                    entity_type="evc_observation",
                    entity_id=obs_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(obs)
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


@router.get("/evc-visits/{visit_id}/observations")
def list_committee_observations(
    visit_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve all observations recorded for an EVC visit."""
    _ = _user(request, subject)
    sql = (
        "SELECT o.id, o.evc_visit_id, o.criterion_code, o.observation_text, o.source_type, "
        "       o.review_status, o.created_at, u.display_name as expert_name "
        "FROM public.evc_observations o "
        "JOIN public.users u ON u.id = o.created_by "
        "WHERE o.evc_visit_id = %s ORDER BY o.created_at ASC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (visit_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.post("/evc-visits/{visit_id}/meeting-record-drafts", status_code=201)
def generate_meeting_record_draft(
    visit_id: UUID,
    payload: GenerateMeetingDraftRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Meeting-to-Record Assistant compiles draft report and minutes from verified observations (BR-12, BR-13)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "meeting_record.generate_draft"
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
                # 1. Fetch visit and verify
                cur.execute("SELECT id, status FROM public.evc_visits WHERE id = %s FOR UPDATE", (visit_id,))
                visit = cur.fetchone()
                if visit is None:
                    raise HTTPException(status_code=404)
                if visit['status'] not in ('scheduled','confirmed','completed'):
                    raise HTTPException(409, detail='Records require a confirmed or completed visit')

                # 2. Fetch observations
                cur.execute(
                    "SELECT id, criterion_code, observation_text, source_type, created_by, created_at, review_status FROM public.evc_observations WHERE evc_visit_id = %s AND review_status='submitted' ORDER BY created_at,id FOR SHARE",
                    (visit_id,),
                )
                observations = cur.fetchall()
                if payload.source_ids is not None:
                    selected=set(payload.source_ids)
                    if not selected or len(selected)!=len(payload.source_ids) or not selected.issubset({o['id'] for o in observations}):
                        raise HTTPException(422, detail='Every selected source must be a submitted observation of this visit')
                    observations=[o for o in observations if o['id'] in selected]
                if not observations:
                    raise HTTPException(409, detail='Submit at least one observation before generating a record')

                now = datetime.now(timezone.utc)

                # 3. Create or fetch evc_reports row
                cur.execute("SELECT id FROM public.evc_reports WHERE evc_visit_id = %s FOR UPDATE", (visit_id,))
                report = cur.fetchone()
                if report is None:
                    cur.execute(
                        "INSERT INTO public.evc_reports "
                        "(evc_visit_id, report_status, template_version, created_at, created_by) "
                        "VALUES (%s, 'draft', %s, %s, %s) RETURNING id",
                        (visit_id, payload.template_version, now, caller_uuid),
                    )
                    report = cur.fetchone()

                report_id = report["id"]

                # 4. Determine next version number for this record_type
                cur.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver "
                    "FROM public.meeting_record_versions WHERE evc_report_id = %s AND record_type = %s",
                    (report_id, payload.record_type),
                )
                ver_num = cur.fetchone()["next_ver"]

                # 5. Build source manifest & content reference
                sections=[{'criterion':o['criterion_code'],'text':o['observation_text'],'source_id':str(o['id']),
                           'source_type':o.get('source_type'),'created_by':str(o.get('created_by')) if o.get('created_by') else None,
                           'source_created_at':o['created_at'].isoformat() if hasattr(o.get('created_at'),'isoformat') else o.get('created_at'),
                           'source_status':'submitted'} for o in observations]
                manifest = {
                    "template_version": payload.template_version,
                    "observations_count": len(observations),
                    "generated_at": now.isoformat(),
                    "sources": [{"criterion": o["criterion_code"], "id": str(o["id"])} for o in observations],
                    "sections": sections,
                    "content_sha256":hashlib.sha256(json.dumps(sections,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
                }
                stored_version_id=uuid4()
                content_ref = f"urn:meeting-record-version:{stored_version_id}"

                # 6. Insert meeting_record_versions
                cur.execute(
                    "INSERT INTO public.meeting_record_versions "
                    "(id, evc_report_id, record_type, version_number, content_reference, source_manifest, created_by, approval_status, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft', %s) "
                    "RETURNING id, evc_report_id, record_type, version_number, content_reference, source_manifest, approval_status, created_at",
                    (stored_version_id, report_id, payload.record_type, ver_num, content_ref, Jsonb(manifest), caller_uuid, now),
                )
                record_version = cur.fetchone()
                version_id = record_version["id"]

                # 7. Insert meeting_record_sources linkages
                for obs in observations:
                    cur.execute(
                        "INSERT INTO public.meeting_record_sources "
                        "(meeting_record_version_id, source_type, source_id, section_reference, created_at) "
                        "VALUES (%s, 'evc_observation', %s, %s, %s)",
                        (version_id, obs["id"], obs["criterion_code"], now),
                    )

                # 8. Link current_version_id on evc_reports
                cur.execute(
                    "UPDATE public.evc_reports SET current_version_id = %s, report_status = 'draft',approved_by=NULL,approved_at=NULL WHERE id = %s",
                    (version_id, report_id),
                )

                # 9. Audit & Outbox
                audit_meta = {
                    "report_id": str(report_id),
                    "version_id": str(version_id),
                    "version_number": ver_num,
                    "record_type": payload.record_type,
                    "observations_count": len(observations),
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="MEETING_RECORD_DRAFT_GENERATED",
                    entity_type="meeting_record_version",
                    entity_id=version_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="MEETING_RECORD_DRAFT_GENERATED",
                    entity_type="meeting_record_version",
                    entity_id=version_id,
                    entity_version=ver_num,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = {
                    "report_id": report_id,
                    "record_version": _serialize(record_version),
                }
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


@router.get("/meeting-records/{report_id}")
def get_meeting_record(
    report_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve EVC meeting record and its active version."""
    _ = _user(request, subject)
    sql = (
        "SELECT r.id, r.evc_visit_id, r.report_status, r.template_version, r.current_version_id, "
        "       r.approved_by, r.approved_at, r.created_at, "
        "       v.record_type, v.version_number, v.content_reference, v.source_manifest, v.approval_status "
        "FROM public.evc_reports r "
        "LEFT JOIN public.meeting_record_versions v ON v.id = r.current_version_id "
        "WHERE r.id = %s"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (report_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404)
    return _serialize(row)


@router.post("/meeting-records/{report_id}/submit-review")
def submit_meeting_record_for_review(
    report_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Submit draft meeting record for formal committee review."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                report = _lock_current_record(cur,report_id)
                if report['approval_status']!='draft':
                    raise HTTPException(409,detail='Only a draft record can be submitted for review')
                if not (report.get('source_manifest') or {}).get('sections'):
                    raise HTTPException(409,detail='Generate a record with persisted source sections first')

                cur.execute(
                    "UPDATE public.meeting_record_versions SET approval_status = 'pending_approval' WHERE id = %s RETURNING id, approval_status",
                    (report["current_version_id"],),
                )
                updated = cur.fetchone()
                cur.execute("UPDATE public.evc_reports SET report_status='submitted' WHERE id=%s", (report_id,))
                append_event(cur,actor_id=_to_uuid(caller['id']),action='MEETING_RECORD_SUBMITTED',entity_type='meeting_record_version',entity_id=report['current_version_id'],correlation_id=_to_uuid(getattr(request.state,'correlation_id',None)),reason='Submitted record for human review',metadata={'report_id':str(report_id)})
        return _serialize(updated)
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.post("/meeting-records/{report_id}/approve")
def approve_meeting_record(
    report_id: UUID,
    payload: ApproveMeetingRecordRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Convener statutory approval freezing the meeting record version (PRD BR-12, BR-13)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "meeting_record.approve"
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
                report = _lock_current_record(cur,report_id)
                if report['approval_status']!='pending_approval':
                    raise HTTPException(409, detail='Submit the current draft for review before approval')
                _require_record_reviewer(cur,report,caller_uuid)
                manifest=report.get('source_manifest') or {}
                if not manifest.get('sections') or not manifest.get('sources'):
                    raise HTTPException(409,detail='Record has no persisted authorised source content')
                digest=hashlib.sha256(json.dumps(manifest['sections'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                if digest!=manifest.get('content_sha256'):
                    raise HTTPException(409,detail='Record source content changed; generate a new version')

                now = datetime.now(timezone.utc)
                version_id = report["current_version_id"]

                # 1. Freeze approved version
                cur.execute(
                    "UPDATE public.meeting_record_versions "
                    "SET approval_status = 'approved', approved_by = %s, approved_at = %s "
                    "WHERE id = %s "
                    "RETURNING id, approval_status, approved_by, approved_at",
                    (caller_uuid, now, version_id),
                )
                version_approved = cur.fetchone()

                # 2. Update parent report status
                cur.execute(
                    "UPDATE public.evc_reports "
                    "SET report_status = 'approved', approved_by = %s, approved_at = %s "
                    "WHERE id = %s",
                    (caller_uuid, now, report_id),
                )
                if report['record_type']=='evc_report':
                    _advance_evc_to_decision(cur,report,caller_uuid,now,payload.reason,corr_uuid)

                # 3. Audit & Outbox
                audit_meta = {
                    "report_id": str(report_id),
                    "version_id": str(version_id),
                    "approved_by": str(caller_uuid),
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="MEETING_RECORD_APPROVED",
                    entity_type="evc_report",
                    entity_id=report_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="MEETING_RECORD_APPROVED",
                    entity_type="evc_report",
                    entity_id=report_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(version_approved)
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


@router.post("/meeting-records/{report_id}/request-changes")
def request_meeting_record_changes(
    report_id: UUID,
    payload: RequestChangesRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Return meeting record draft for corrections with reviewer comments."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                report = _lock_current_record(cur,report_id)
                if report['approval_status']!='pending_approval':
                    raise HTTPException(409,detail='Only a record pending review can be returned for changes')
                _require_record_reviewer(cur,report,_to_uuid(caller['id']))

                cur.execute(
                    "UPDATE public.meeting_record_versions SET approval_status = 'draft' WHERE id = %s RETURNING id, approval_status",
                    (report["current_version_id"],),
                )
                updated = cur.fetchone()
                cur.execute("UPDATE public.meeting_record_versions SET source_manifest=source_manifest || %s WHERE id=%s", (Jsonb({'review_feedback':payload.comments,'reviewed_by':str(caller['id'])}),report['current_version_id']))
                cur.execute("UPDATE public.evc_reports SET report_status='draft',approved_by=NULL,approved_at=NULL WHERE id=%s", (report_id,))
                append_event(cur,actor_id=_to_uuid(caller['id']),action='MEETING_RECORD_CHANGES_REQUESTED',entity_type='meeting_record_version',entity_id=report['current_version_id'],correlation_id=_to_uuid(getattr(request.state,'correlation_id',None)),reason=payload.reason,metadata={'comments':payload.comments,'report_id':str(report_id)})
        return _serialize(updated)
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.get("/meeting-records/{report_id}/sources")
def list_meeting_record_sources(
    report_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Inspect observation sources and section linkages for an approved or draft meeting record."""
    _ = _user(request, subject)
    sql = (
        "SELECT s.id, s.meeting_record_version_id, s.source_type, s.source_id, s.section_reference, "
        "       o.observation_text, o.criterion_code "
        "FROM public.evc_reports r "
        "JOIN public.meeting_record_sources s ON s.meeting_record_version_id = r.current_version_id "
        "LEFT JOIN public.evc_observations o ON o.id = s.source_id "
        "WHERE r.id = %s"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (report_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}
