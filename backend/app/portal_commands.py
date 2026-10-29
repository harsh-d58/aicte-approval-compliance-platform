"""Supplemental portal mutations against normalized records, with server scope checks.

This closes UI/API contract gaps without accepting a client-owned snapshot or
simulating successful business actions in browser storage.
"""

from datetime import datetime, timezone
import json
from typing import Any, Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .accounts import _user
from .audit import append_event
from .auth import get_verified_subject
from .authorization import validate_role_grant
from .outbox import enqueue
from .portal_snapshot import snapshot, role as portal_role
from .transactions import write_transaction, UnsafeWriteConnection
from .workflows import validate_graph

router = APIRouter(tags=["portal"])


class PortalCommand(BaseModel):
    kind: str = Field(..., min_length=3, max_length=80)
    id: UUID | None = None
    expectedVersion: int | None = Field(None, ge=1)
    values: dict[str, Any] = Field(default_factory=dict)


def _required(values, key):
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(422, detail=f"{key} is required")
    return value.strip()


def _record(data, collection, record_id):
    record = next((row for row in data[collection] if row["id"] == str(record_id)), None)
    if not record:
        raise HTTPException(404)
    return record


def _permit(roles, *allowed):
    if not roles.intersection(allowed):
        raise HTTPException(403)


@router.post("/portal/commands")
def command_endpoint(payload: PortalCommand, request: Request,
                     subject: Annotated[str, Depends(get_verified_subject)]):
    return execute_command(request, subject, payload)


def execute_command(request, subject, payload: PortalCommand):
    caller = _user(request, subject)
    actor = UUID(str(caller["id"]))
    values = payload.values
    kind = payload.kind
    target = payload.id
    now = datetime.now(timezone.utc)
    reason = str(values.get("reason") or "Prototype portal action")
    if len(reason) > 2000:
        raise HTTPException(422)
    try:
        with write_transaction(request.app.state.settings.database_write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                # Serialize supplemental commands before taking a consistent snapshot.
                cur.execute("SELECT pg_advisory_xact_lock(72844116)")
                data = snapshot(connection, subject)
                user = _record(data, "users", actor)
                cur.execute("SELECT r.role_code FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id WHERE a.user_id=%s AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from <= CURRENT_TIMESTAMP) AND (a.valid_until IS NULL OR a.valid_until > CURRENT_TIMESTAMP)", (actor,))
                raw_roles = [r["role_code"] for r in cur.fetchall()]
                # Read-only aliases never acquire write access via their UI label.
                roles = {portal_role(code) for code in raw_roles if not code.endswith("_VIEWER")}
                if not roles:
                    raise HTTPException(403)

                if kind == "document.verify":
                    _permit(roles, "SCRUTINY", "COMPLIANCE", "REGIONAL")
                    document=next((d for d in data["documents"] if any(v["id"]==str(target) for v in d["versions"])),None)
                    if not document:raise HTTPException(404)
                    result=_required(values,"result")
                    if result not in ("VERIFIED","REJECTED"):raise HTTPException(422)
                    if len(reason.strip())<3:raise HTTPException(422)
                    cur.execute("SELECT status FROM public.document_file_scans WHERE document_version_id=%s ORDER BY scanned_at DESC LIMIT 1", (target,))
                    scan = cur.fetchone()
                    if not scan or scan["status"] != "clean": raise HTTPException(409, detail="A clean file scan is required before verification")
                    cur.execute("UPDATE public.document_versions SET verification_status=%s WHERE id=%s",(result.lower(),target))

                elif kind == "notification.read":
                    notification = _record(data, "notifications", target)
                    if notification["recipientId"] != str(actor):
                        raise HTTPException(403)
                    cur.execute("UPDATE public.notifications SET payload = COALESCE(payload, '{}'::jsonb) || %s WHERE id = %s AND recipient_user_id = %s",
                                (Jsonb({"read": bool(values.get("read"))}), target, actor))

                elif kind == "availability.save":
                    from .evc import _aware, _scheduling_lock
                    _scheduling_lock(cur)
                    pt=_required(values,"participantType")
                    pid=_required(values,"participantId")
                    if pt=="INSTITUTION":
                        _permit(roles,"INSTITUTION")
                        item=_record(data,"institutions",pid)
                        table,column,owner="institution_availability","institution_id",item["id"]
                    elif pt=="EXPERT":
                        _permit(roles,"EVC_EXPERT","EVC_COORDINATOR","REGIONAL")
                        item=_record(data,"experts",pid)
                        if roles=={"EVC_EXPERT"} and item["userId"]!=str(actor):raise HTTPException(403)
                        table,column,owner="expert_availability","expert_user_id",item["userId"]
                    else:raise HTTPException(422)
                    start,end=_aware(_required(values,"startAt")),_aware(_required(values,"endAt"))
                    if end<=start or values.get("state") not in ("AVAILABLE","BUSY"):raise HTTPException(422)
                    prior=target
                    if prior:
                        previous=_record(data,"availability",prior)
                        if previous["participantId"]!=pid or previous["participantType"]!=pt or previous.get("supersededAt"):raise HTTPException(409)
                        cur.execute(f"UPDATE public.{table} SET superseded_at=%s WHERE id=%s AND superseded_at IS NULL",(now,prior))
                        if cur.rowcount!=1:raise HTTPException(409)
                    target=uuid4()
                    cur.execute(f"INSERT INTO public.{table}(id,{column},start_at,end_at,availability_status,source,last_confirmed_at,created_by,supersedes_id) VALUES(%s,%s,%s,%s,%s,'manual_entry',%s,%s,%s)",(target,owner,start,end,"available" if values["state"]=="AVAILABLE" else "unavailable",now,actor,prior))

                elif kind == "application.assign":
                    _permit(roles, "REGIONAL", "CENTRAL")
                    application = _record(data, "applications", target)
                    if payload.expectedVersion != application["version"]:
                        raise HTTPException(412)
                    owner = UUID(_required(values, "ownerId"))
                    _record(data, "users", owner)
                    cur.execute("SELECT current_stage_instance_id,version,status,institution_id FROM public.applications WHERE id = %s FOR UPDATE", (target,))
                    current = cur.fetchone()
                    if current["version"] != payload.expectedVersion: raise HTTPException(412)
                    if current["status"] not in ("submitted", "under_review", "resubmitted", "deficiency_returned") or not current["current_stage_instance_id"]: raise HTTPException(409)
                    cur.execute("SELECT 1 FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id JOIN public.users u ON u.id=a.user_id JOIN public.institutions i ON i.id=%s WHERE a.user_id=%s AND u.status='active' AND a.status='active' AND r.role_code IN ('SCRUTINY','SCRUTINY_OFFICER','DEMO_SCRUTINY') AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now()) AND ((a.scope_type='region' AND a.scope_id=i.region_id) OR (a.scope_type='application' AND a.scope_id=%s))", (current["institution_id"], owner, target))
                    if not cur.fetchone(): raise HTTPException(422, detail="Assignee must be an active scrutiny officer in this case scope")
                    deadline = datetime.fromisoformat(_required(values,"dueAt"))
                    if deadline.tzinfo is None or deadline <= now: raise HTTPException(422, detail="Assignment deadline must be in the future and include a time zone")
                    stage = current["current_stage_instance_id"]
                    cur.execute("UPDATE public.assignments SET status='completed' WHERE application_id=%s AND status='active'", (target,))
                    cur.execute("INSERT INTO public.assignments (application_id,stage_instance_id,assigned_user_id,assigned_at,due_at,status,created_by) VALUES (%s,%s,%s,%s,%s,'active',%s)",
                                (target, stage, owner, now, _required(values, "dueAt"), actor))
                    cur.execute("UPDATE public.applications SET version=version+1,updated_at=%s,updated_by=%s WHERE id=%s", (now, actor, target))

                elif kind in ("institution.save", "institution.import"):
                    _permit(roles, "SYSTEM", "CENTRAL", "REGIONAL")
                    rows = values.get("rows") if kind == "institution.import" else [values]
                    if not isinstance(rows, list) or not rows or len(rows) > 200:
                        raise HTTPException(422)
                    for row in rows:
                        if not isinstance(row, dict):
                            raise HTTPException(422)
                        region_id = UUID(_required(row, "regionId"))
                        if not any(a["scope"]["type"] == "GLOBAL" or (a["scope"]["type"] == "REGION" and a["scope"]["id"] == str(region_id)) for a in user["assignments"]):
                            raise HTTPException(403)
                        target = uuid4()
                        cur.execute("INSERT INTO public.institutions (id,institution_code,official_name,institution_type,status,region_id,created_by) VALUES (%s,%s,%s,%s,'active',%s,%s)",
                                    (target, _required(row, "code"), _required(row, "name"), _required(row, "type"), region_id, actor))
                        cur.execute("INSERT INTO public.institution_campuses (institution_id,campus_name,address,region_id,is_primary,created_by) VALUES (%s,%s,%s,%s,true,%s)",
                                    (target, _required(row, "campusName"), Jsonb({"city": _required(row, "city")}), region_id, actor))

                elif kind == "application.migrate":
                    _permit(roles, "POLICY", "CENTRAL")
                    application = _record(data, "applications", target)
                    if payload.expectedVersion != application["version"]:
                        raise HTTPException(412)
                    if application["status"] in ("APPROVED", "REJECTED", "CLOSED", "WITHDRAWN"):
                        raise HTTPException(409, detail="Terminal cases cannot migrate workflows")
                    workflow = _record(data, "workflows", _required(values, "workflowId"))
                    if workflow["status"] != "PUBLISHED":
                        raise HTTPException(409)
                    cur.execute("SELECT application_type_id FROM public.workflow_definitions WHERE id=%s AND status='published'", (workflow["id"],))
                    definition = cur.fetchone()
                    if not definition: raise HTTPException(409, detail="Target workflow is not effective")
                    workflow_type = definition["application_type_id"]
                    cur.execute("SELECT application_type_id,workflow_definition_id,current_stage_instance_id,version FROM public.applications WHERE id=%s FOR UPDATE", (target,))
                    current = cur.fetchone()
                    if current["version"] != payload.expectedVersion: raise HTTPException(412)
                    if current["application_type_id"] != workflow_type:
                        raise HTTPException(422)
                    if len(reason.strip()) < 3: raise HTTPException(422, detail="Migration requires a reason")
                    old_stage, new_stage = None, None
                    if current["current_stage_instance_id"]:
                        cur.execute("SELECT workflow_stage_id FROM public.application_stage_instances WHERE id=%s", (current["current_stage_instance_id"],))
                        old_stage = cur.fetchone()["workflow_stage_id"]
                        mapped = _required(values, "stageCode")
                        cur.execute("SELECT id,default_sla_days FROM public.workflow_stages WHERE workflow_definition_id=%s AND stage_code=%s", (workflow["id"], mapped))
                        destination = cur.fetchone()
                        if not destination: raise HTTPException(422, detail="An explicit target stage mapping is required")
                        new_stage = destination["id"]
                        cur.execute("UPDATE public.application_stage_instances SET status='completed',completed_at=%s WHERE id=%s", (now,current["current_stage_instance_id"]))
                        cur.execute("INSERT INTO public.application_stage_instances(application_id,workflow_stage_id,status,entered_at,due_at,created_by) VALUES(%s,%s,'in_progress',%s,%s,%s) RETURNING id", (target,new_stage,now,now+__import__('datetime').timedelta(days=destination["default_sla_days"] or 0),actor))
                        current["current_stage_instance_id"] = cur.fetchone()["id"]
                        cur.execute("UPDATE public.assignments SET status='completed' WHERE application_id=%s AND status='active'", (target,))
                        cur.execute("INSERT INTO public.stage_history(application_id,from_stage_id,to_stage_id,actor_user_id,reason,event_at,correlation_id) VALUES(%s,%s,%s,%s,%s,%s,%s)", (target,old_stage,new_stage,actor,reason,now,getattr(request.state,"correlation_id",None)))
                    values["migration"] = {"oldWorkflowId":str(current["workflow_definition_id"]),"newWorkflowId":workflow["id"],"fromStageId":str(old_stage) if old_stage else None,"toStageId":str(new_stage) if new_stage else None}
                    cur.execute("UPDATE public.applications SET workflow_definition_id=%s,version=version+1,updated_at=%s,updated_by=%s WHERE id=%s AND version=%s",
                                (workflow["id"], now, actor, target, payload.expectedVersion))
                    if cur.rowcount != 1:
                        raise HTTPException(412)
                    cur.execute("UPDATE public.applications SET current_stage_instance_id=%s WHERE id=%s", (current["current_stage_instance_id"],target))

                elif kind in ("workflow.save", "workflow.publish"):
                    _permit(roles, "POLICY", "CENTRAL")
                    source = _record(data, "workflows", target) if target else None
                    if kind == "workflow.publish":
                        if not source or source["status"] != "DRAFT" or not source["stages"] or not source["transitions"]:
                            raise HTTPException(409)
                        validate_graph(source["stages"], source["transitions"])
                        effective = _required(values,"effectiveFrom")
                        datetime.strptime(effective,"%Y-%m-%d")
                        cur.execute("UPDATE public.workflow_definitions SET status='published',effective_from=%s,updated_at=%s,updated_by=%s WHERE id=%s AND status='draft'", (effective,now, actor, target))
                        if not cur.rowcount:
                            raise HTTPException(409)
                    else:
                        stages, transitions = values.get("stages"), values.get("transitions")
                        validate_graph(stages, transitions)
                        if not isinstance(stages, list) or not stages or not isinstance(transitions, list):
                            raise HTTPException(422)
                        stage_codes = {s.get("code") for s in stages if isinstance(s, dict)}
                        if len(stage_codes) != len(stages) or any(not isinstance(t, dict) or t.get("from") not in stage_codes or t.get("to") not in stage_codes for t in transitions):
                            raise HTTPException(422)
                        if source:
                            cur.execute("SELECT application_type_id,aph_rule_version_id,version_number FROM public.workflow_definitions WHERE id=%s", (target,))
                            metadata = cur.fetchone()
                        else:
                            cur.execute("SELECT id AS application_type_id FROM public.application_types WHERE id=%s AND status='active'", (UUID(_required(values,"applicationTypeId")),))
                            metadata = cur.fetchone()
                            if not metadata:
                                raise HTTPException(409)
                            cur.execute("SELECT id FROM public.aph_rule_versions WHERE id=%s AND approved_by IS NOT NULL", (UUID(_required(values,"aphRuleVersionId")),))
                            aph = cur.fetchone()
                            if not aph: raise HTTPException(422, detail="Select an approved APH rule version")
                            metadata.update({"aph_rule_version_id": aph["id"], "version_number": 0})
                        cur.execute("SELECT COALESCE(MAX(version_number),0)+1 AS next_version FROM public.workflow_definitions WHERE application_type_id=%s", (metadata["application_type_id"],))
                        metadata["version_number"] = cur.fetchone()["next_version"] - 1
                        # Every save creates a draft version, preserving all bound published workflows.
                        target = uuid4()
                        cur.execute("INSERT INTO public.workflow_definitions (id,name,application_type_id,aph_rule_version_id,status,version_number,created_by) VALUES (%s,%s,%s,%s,'draft',%s,%s)",
                                    (target, _required(values, "name"), metadata["application_type_id"], metadata["aph_rule_version_id"], metadata["version_number"] + 1, actor))
                        ids = {}
                        for position, stage in enumerate(stages, 1):
                            stage_id = uuid4()
                            ids[stage["code"]] = stage_id
                            stage_type = stage["code"].lower()
                            if stage_type not in ("intake", "scrutiny", "deficiency", "evc", "decision", "compliance", "closure"):
                                stage_type = "other"
                            cur.execute("INSERT INTO public.workflow_stages (id,workflow_definition_id,stage_code,stage_name,stage_order,stage_type,default_sla_days,created_by,owner_role_code) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                        (stage_id, target, _required(stage, "code"), _required(stage, "name"), position, stage_type, stage["slaDays"], actor,stage["ownerRole"]))
                        for transition in transitions:
                            guards = transition.get("guards") or []
                            guard = {"required_roles":[next(s["ownerRole"] for s in stages if s["code"]==transition["from"]),"REGIONAL","CENTRAL"]}
                            if any(g in guards for g in ("NO_OPEN_DEFICIENCIES","deficiencies_resolved")): guard["require_all_deficiencies_resolved"] = True
                            if "COMPLETED_EVC" in guards: guard["require_completed_evc"] = True
                            if "APPROVED_MEETING_RECORD" in guards: guard["require_approved_meeting_record"] = True
                            cur.execute("INSERT INTO public.workflow_transitions (workflow_definition_id,from_stage_id,to_stage_id,transition_type,guard_rule,requires_authorisation,created_by) VALUES (%s,%s,%s,'forward',%s,true,%s)",
                                        (target, ids[transition["from"]], ids[transition["to"]], Jsonb(guard), actor))

                elif kind in ("config.save", "config.publish"):
                    _permit(roles, "POLICY", "CENTRAL")
                    source = _record(data, "configurations", target) if target else None
                    if kind == "config.publish":
                        if not source or source["status"] != "DRAFT":
                            raise HTTPException(409)
                        if source["category"] == "COMMITTEE":
                            cur.execute("UPDATE public.committees SET status='active',updated_at=%s,updated_by=%s WHERE id=%s", (now, actor, target))
                        else:
                            cur.execute("UPDATE public.system_settings SET approved_by=%s,effective_at=%s,updated_at=%s,updated_by=%s WHERE id=%s", (actor, now, now, actor, target))
                        if not cur.rowcount:
                            raise HTTPException(422, detail="This reference catalogue is managed by its dedicated module")
                    else:
                        config_values = values.get("values")
                        if not isinstance(config_values, dict):
                            raise HTTPException(422)
                        category = source["category"] if source else _required(values, "category")
                        if category not in ("SETTINGS", "RETENTION", "TEMPLATE", "COMMITTEE"):
                            raise HTTPException(422, detail="This reference catalogue needs a dedicated typed configuration endpoint")
                        target = uuid4()
                        if category == "COMMITTEE":
                            if int(config_values.get("memberCount", 0)) not in (4, 5) or int(config_values.get("durationMinutes", 0)) <= 0 or int(config_values.get("availabilityFreshnessHours", 0)) <= 0:
                                raise HTTPException(422)
                            cur.execute("SELECT committee_type_id FROM public.committees WHERE id=%s", (source["id"] if source else None,))
                            committee_type = cur.fetchone()
                            if not committee_type:
                                cur.execute("SELECT id AS committee_type_id FROM public.committee_types ORDER BY code LIMIT 1")
                                committee_type = cur.fetchone()
                            if not committee_type:
                                cur.execute("INSERT INTO public.committee_types(code,name,description,created_by) VALUES('AICTE-STATUTORY-EVC','AICTE Statutory EVC','Illustrative prototype composition; not an official statutory rule',%s) ON CONFLICT(code) DO UPDATE SET name=EXCLUDED.name RETURNING id AS committee_type_id",(actor,))
                                committee_type=cur.fetchone()
                            cur.execute("INSERT INTO public.committees (id,committee_type_id,name,status,configuration,version,created_by) VALUES (%s,%s,%s,'inactive',%s,%s,%s)",
                                        (target, committee_type["committee_type_id"], _required(values, "name"), Jsonb(config_values), (source["version"] + 1) if source else 1, actor))
                        else:
                            cur.execute("INSERT INTO public.system_settings (id,setting_key,setting_value,version,created_by) VALUES (%s,%s,%s,%s,%s)",
                                        (target, _required(values, "name") + ':' + str(target), Jsonb(config_values), (source["version"] + 1) if source else 1, actor))

                elif kind in ("application.cancel", "application.reopen"):
                    application = _record(data, "applications", target)
                    if payload.expectedVersion != application["version"]:
                        raise HTTPException(412)
                    if kind == "application.cancel":
                        _permit(roles, "INSTITUTION", "REGIONAL")
                        if application["status"] in ("APPROVED", "REJECTED", "CLOSED", "WITHDRAWN"):
                            raise HTTPException(409)
                        status = "withdrawn"
                    else:
                        _permit(roles, "REGIONAL")
                        if application["status"] != "CLOSED":
                            raise HTTPException(409)
                        status = "under_review"
                    cur.execute("UPDATE public.applications SET status=%s,closed_at=%s,version=version+1,updated_at=%s,updated_by=%s WHERE id=%s AND version=%s",
                                (status, now if status == "withdrawn" else None, now, actor, target, payload.expectedVersion))
                    if cur.rowcount != 1:
                        raise HTTPException(412)

                elif kind in ("renewal.submit", "renewal.verify"):
                    renewal = _record(data, "renewals", target)
                    document = _record(data, "documents", renewal["documentId"])
                    if kind == "renewal.submit":
                        _permit(roles, "INSTITUTION")
                        version_id = _required(values, "versionId")
                        version = next((v for v in document["versions"] if v["id"] == version_id), None)
                        prior = next((v for v in document["versions"] if v["id"] == renewal["previousVersionId"]), None)
                        if not version or not prior or version["number"] <= prior["number"] or renewal["status"] == "VERIFIED":
                            raise HTTPException(409)
                        cur.execute("UPDATE public.document_renewal_cases SET submitted_version_id=%s,status='submitted' WHERE id=%s", (version_id, target))
                    else:
                        _permit(roles, "COMPLIANCE", "REGIONAL")
                        if renewal["status"] not in ("SUBMITTED", "UNDER_REVIEW"):
                            raise HTTPException(409)
                        version = next((v for v in document["versions"] if v["id"] == renewal["submittedVersionId"]), None)
                        if not version or version["verification"] != "VERIFIED":
                            raise HTTPException(409, detail="Verify the submitted document version before closing its renewal")
                        cur.execute("UPDATE public.document_renewal_cases SET status='completed',closed_at=%s WHERE id=%s", (now, target))

                elif kind in ("visit.postpone", "visit.cancel"):
                    _permit(roles, "REGIONAL", "EVC_COORDINATOR")
                    visit = _record(data, "visits", target)
                    if visit["status"] in ("COMPLETED", "CANCELLED"):
                        raise HTTPException(409)
                    status = "postponed" if kind == "visit.postpone" else "cancelled"
                    cur.execute("UPDATE public.evc_visits SET status=%s,confirmed_start_at=NULL,confirmed_end_at=NULL,updated_at=%s,updated_by=%s WHERE id=%s", (status, now, actor, target))
                    cur.execute("INSERT INTO public.evc_visit_events (evc_visit_id,event_type,event_at,actor_user_id,reason,details) VALUES (%s,%s,%s,%s,%s,%s)",
                                (target, status, now, actor, reason, Jsonb({})))

                elif kind == "invitation.respond":
                    invitation = _record(data, "invitations", target)
                    if invitation["recipientId"] != str(actor):
                        raise HTTPException(403)
                    response = _required(values, "response").lower()
                    if response not in ("accepted", "declined"):
                        raise HTTPException(422)
                    cur.execute("UPDATE public.evc_invitations SET response_status=%s WHERE id=%s", (response, target))

                elif kind == "observation.save":
                    _permit(roles, "EVC_EXPERT")
                    if not target:
                        visit = _record(data,"visits",_required(values,"visitId"))
                        target=uuid4()
                        cur.execute("INSERT INTO public.evc_observations (id,evc_visit_id,criterion_code,observation_text,source_type,review_status,created_by) VALUES (%s,%s,%s,%s,'site_inspection',%s,%s)",(target,visit["id"],_required(values,"criterion"),_required(values,"text"),"submitted" if values.get("submit") else "draft",actor))
                    else:
                        observation = _record(data, "observations", target)
                        if observation["authorId"] != str(actor) or observation["status"] != "DRAFT":
                            raise HTTPException(403)
                        cur.execute("UPDATE public.evc_observations SET criterion_code=%s,observation_text=%s,review_status=%s,updated_at=%s WHERE id=%s",
                                    (_required(values, "criterion"), _required(values, "text"), "submitted" if values.get("submit") else "draft", now, target))


                elif kind in ("actionitem.save", "actionitem.complete"):
                    _permit(roles, "EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL")
                    if kind == "actionitem.save":
                        visit = _record(data, "visits", _required(values, "visitId"))
                        observation = _record(data, "observations", _required(values, "observationId"))
                        if observation["visitId"] != visit["id"]:
                            raise HTTPException(422)
                        cur.execute("SELECT id FROM public.roles WHERE role_code IN (%s,%s) ORDER BY role_code LIMIT 1",
                                    (_required(values, "responsibleRole"), "DEMO_" + _required(values, "responsibleRole")))
                        responsible = cur.fetchone()
                        if not responsible:
                            raise HTTPException(422)
                        target = uuid4()
                        cur.execute("INSERT INTO public.action_items (id,evc_visit_id,description,responsible_role_id,due_at,status,source_observation_id,created_by) VALUES (%s,%s,%s,%s,%s,'open',%s,%s)",
                                    (target, visit["id"], _required(values, "description"), responsible["id"], _required(values, "dueAt"), observation["id"], actor))
                    else:
                        _record(data, "actionItems", target)
                        cur.execute("UPDATE public.action_items SET status='completed' WHERE id=%s AND status <> 'completed'", (target,))
                        if not cur.rowcount:
                            raise HTTPException(409)

                elif kind == "record.save":
                    _permit(roles, "EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL")
                    record = _record(data, "meetingRecords", target)
                    if payload.expectedVersion is not None and payload.expectedVersion != record["currentVersion"]:
                        raise HTTPException(412)
                    current = next(v for v in record["versions"] if v["number"] == record["currentVersion"])
                    sections = values.get("sections")
                    sources = {o["id"] for o in data["observations"] if o["visitId"] == record["visitId"] and o["status"] == "SUBMITTED"}
                    if not isinstance(sections, list) or not sections or any(not isinstance(s, dict) or not s.get("title") or not s.get("text") or not s.get("sourceIds") or not set(s["sourceIds"]).issubset(sources) for s in sections):
                        raise HTTPException(422)
                    if current["status"] == "IN_REVIEW":
                        raise HTTPException(409)
                    number = record["currentVersion"] + 1
                    version_id = uuid4()
                    from hashlib import sha256
                    manifest = {"sections": sections, "correction_reason": reason,
                                "sources": [{"id": source} for source in sorted({source for section in sections for source in section["sourceIds"]})]}
                    manifest["content_sha256"] = sha256(json.dumps(sections, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
                    cur.execute("INSERT INTO public.meeting_record_versions (id,evc_report_id,record_type,version_number,content_reference,source_manifest,created_by,approval_status) VALUES (%s,%s,%s,%s,%s,%s,%s,'draft')",
                                (version_id, target, record["type"].lower(), number, f"urn:meeting-record-version:{version_id}", Jsonb(manifest), actor))
                    for section in sections:
                        for source in section["sourceIds"]:
                            cur.execute("INSERT INTO public.meeting_record_sources (meeting_record_version_id,source_type,source_id,section_reference) VALUES (%s,'evc_observation',%s,%s)",
                                        (version_id, source, section["title"]))
                    cur.execute("UPDATE public.evc_reports SET current_version_id=%s,report_status='draft',approved_by=NULL,approved_at=NULL WHERE id=%s", (version_id, target))

                elif kind == "user.status":
                    _permit(roles, "SYSTEM")
                    user_target = _record(data, "users", target)
                    if target == actor:
                        raise HTTPException(403)
                    cur.execute("UPDATE public.users SET status=%s,updated_at=%s,updated_by=%s,version=version+1 WHERE id=%s",
                                ("disabled" if user_target["status"] == "ACTIVE" else "active", now, actor, target))

                elif kind == "user.assignment":
                    _permit(roles, "SYSTEM")
                    if not any(a["role"] == "SYSTEM" and a["scope"]["type"] == "GLOBAL" for a in user["assignments"]):
                        raise HTTPException(403)
                    assigned_user = _record(data, "users", target)
                    if values.get("action") == "revoke":
                        if target == actor:
                            raise HTTPException(403)
                        assignment_index = int(values.get("assignmentIndex", -1))
                        if assignment_index < 0 or assignment_index >= len(assigned_user["assignments"]):
                            raise HTTPException(422)
                        selected = assigned_user["assignments"][assignment_index]
                        cur.execute("SELECT a.id,r.role_code,a.scope_type,a.scope_id FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id WHERE a.user_id=%s AND a.status='active'", (target,))
                        matches = [a for a in cur.fetchall() if portal_role(a["role_code"]) == selected["role"] and a["scope_type"].upper() == selected["scope"]["type"] and str(a["scope_id"] or "all") == selected["scope"]["id"]]
                        if not matches:
                            raise HTTPException(409)
                        for assignment in matches:
                            cur.execute("UPDATE public.user_role_assignments SET status='revoked',version=version+1,updated_at=%s,updated_by=%s WHERE id=%s", (now, actor, assignment["id"]))
                    else:
                        role_code = _required(values, "role")
                        scope_type = _required(values, "scopeType").lower()
                        scope_id = None if scope_type == "global" else UUID(_required(values, "scopeId"))
                        allowed_scopes = {"institution": "institutions", "region": "regions", "application": "applications"}
                        if scope_type != "global":
                            if scope_type not in allowed_scopes:
                                raise HTTPException(422)
                            _record(data, allowed_scopes[scope_type], scope_id)
                        cur.execute("SELECT id,role_code FROM public.roles ORDER BY role_code")
                        role_row = next((r for r in cur.fetchall() if portal_role(r["role_code"]) == role_code), None)
                        if not role_row or not role_row["role_code"].startswith("DEMO_") or role_row["role_code"].endswith("_VIEWER"):
                            raise HTTPException(422)
                        valid_until = datetime.fromisoformat(values["validUntil"]) if values.get("validUntil") else None
                        if valid_until and valid_until.tzinfo is None:
                            raise HTTPException(422, detail="Role expiry needs a time zone")
                        validate_role_grant(cur, actor, target, role_row["role_code"], scope_type, scope_id, now, valid_until)
                        cur.execute("SELECT 1 FROM public.user_role_assignments WHERE user_id=%s AND role_id=%s AND scope_type=%s AND scope_id IS NOT DISTINCT FROM %s AND status='active' AND (valid_until IS NULL OR valid_until > %s)",
                                    (target, role_row["id"], scope_type, scope_id, now))
                        if cur.fetchone():
                            raise HTTPException(409)
                        cur.execute("INSERT INTO public.user_role_assignments (user_id,role_id,scope_type,scope_id,valid_from,valid_until,status,created_by) VALUES (%s,%s,%s,%s,%s,%s,'active',%s)",
                                    (target, role_row["id"], scope_type, scope_id, now, values.get("validUntil") or None, actor))

                elif kind == "job.retry":
                    _permit(roles, "SYSTEM")
                    job = _record(data, "jobs", target)
                    if job["status"] not in ("FAILED", "RETRY_PENDING"):
                        raise HTTPException(409)
                    cur.execute("UPDATE public.background_jobs SET status='queued',next_attempt_at=%s,updated_at=%s WHERE id=%s", (now, now, target))

                elif kind in ("integration.disable", "integration.test"):
                    _permit(roles, "SYSTEM")
                    _record(data, "integrations", target)
                    if kind == "integration.test":
                        raise HTTPException(422, detail="Connector health requires a configured provider; no simulated success is recorded")
                    cur.execute("UPDATE public.integration_endpoints SET status='disabled',updated_at=%s,updated_by=%s,version=version+1 WHERE id=%s", (now, actor, target))

                else:
                    raise HTTPException(422, detail=f"Live action {kind} is not implemented")

                entity_id = target or uuid4()
                action = "PORTAL_" + kind.upper().replace(".", "_")
                correlation = UUID(getattr(request.state, "correlation_id", str(uuid4())))
                metadata = {"command": kind}
                if values.get("migration"): metadata["migration"] = values["migration"]
                append_event(cur, actor_id=actor, action=action, entity_type=kind.split(".")[0], entity_id=entity_id,
                             correlation_id=correlation, reason=reason, metadata=metadata)
                enqueue(cur, event_type=action, entity_type=kind.split(".")[0], entity_id=entity_id,
                        correlation_id=correlation, payload=metadata)
        return {"id": str(entity_id), "message": "Saved to the live database."}
    except UnsafeWriteConnection:
        raise HTTPException(503) from None
    except (ValueError, TypeError):
        raise HTTPException(422) from None
