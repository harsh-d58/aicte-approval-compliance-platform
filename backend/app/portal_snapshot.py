"""Project normalized PostgreSQL records into the existing portal view models.

The connection belongs to the caller and must already have its RLS subject set.
No fixture imports, browser state, credentials, object keys or download tokens are
included. Child collections are intersected with visible parent IDs because the
early prototype's child-table RLS policies are broader than its parent policies.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from psycopg import sql
from psycopg.rows import dict_row


TABLES = (
    "regions", "users", "roles", "user_role_assignments", "institutions",
    "institution_campuses", "institution_profile_attributes", "applications",
    "application_types", "application_submissions", "workflow_definitions",
    "workflow_stages", "workflow_transitions", "aph_rule_versions", "aph_rule_sets",
    "application_stage_instances", "stage_history", "assignments",
    "deficiency_notices", "deficiency_items", "documents", "document_versions",
    "document_types", "document_extractions", "document_check_results",
    "document_renewal_cases", "expert_profiles", "expert_availability", "evc_visits",
    "evc_committee_members", "slot_recommendations", "evc_invitations",
    "evc_visit_events", "evc_observations", "evc_reports", "meeting_record_versions",
    "meeting_record_sources", "action_items", "approval_decisions",
    "compliance_conditions", "evidence_submissions", "evidence_submission_files",
    "compliance_verifications", "notifications", "notification_attempts",
    "escalation_events", "escalation_rules", "notification_rules",
    "report_definitions", "report_runs", "audit_events", "audit_anchors",
    "committees", "system_settings", "integration_endpoints", "background_jobs",
    "institution_availability", "deficiency_item_responses", "document_file_scans",
    "configuration_revisions",
)

ROLES = {"INSTITUTION", "SCRUTINY", "REGIONAL", "EVC_COORDINATOR", "EVC_EXPERT",
         "COMPLIANCE", "CENTRAL", "POLICY", "AUDITOR", "SYSTEM"}
ROLE_ALIASES = {
    "DEMO_INSTITUTION_VIEWER": "INSTITUTION", "DEMO_REGION_VIEWER": "REGIONAL",
    "DEMO_APPLICATION_VIEWER": "SCRUTINY", "INSTITUTION_USER": "INSTITUTION",
    "SCRUTINY_OFFICER": "SCRUTINY", "REGIONAL_OFFICER": "REGIONAL",
    "COMPLIANCE_OFFICER": "COMPLIANCE", "CENTRAL_OFFICER": "CENTRAL",
    "POLICY_ADMIN": "POLICY", "SYSTEM_ADMIN": "SYSTEM",
}
APPLICATION_STATUSES = {"UNDER_REVIEW": "IN_REVIEW", "DEFICIENCY_RETURNED": "RETURNED_FOR_DEFICIENCY",
                        "EVC_REQUIRED": "AWAITING_EVC", "EVC_SCHEDULED": "AWAITING_EVC"}
VISIT_STATUSES = {"REQUIRED": "READY", "COMMITTEE_SELECTION": "READY", "SCHEDULING": "AWAITING_AVAILABILITY",
                  "SCHEDULED": "CONFIRMED"}


def serial(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: serial(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(item) for item in value]
    return value


def upper(value, default=""):
    return str(value or default).upper()


def role(value):
    code = upper(value).removeprefix("DEMO_")
    return ROLE_ALIASES.get(upper(value), ROLE_ALIASES.get(code, code))


def report_code(value):
    return str(value or "").removeprefix("DEMO-").lower().replace("_", "-")

def clean_text(val):
    if not isinstance(val, str):
        return val
    v = re.sub(r"^DEMO\s+ONLY\s+[^\w\s]+\s*", "", val, flags=re.IGNORECASE)
    v = v.replace("DEMO-LIVE-", "AICTE-2026-").replace("DEMO-APP-", "AICTE-APP-")
    v = v.replace("DEMO-COND-", "COND-2026-").replace("DEMO-DEF-", "DEF-2026-").replace("DEMO-INST-", "INST-")
    v = re.sub(r"^DEMO[\s_-]+", "", v, flags=re.IGNORECASE)
    v = re.sub(r"\bDEMO\b", "", v, flags=re.IGNORECASE).strip()
    return v


def index(rows):
    return {row["id"]: row for row in rows}


def grouped(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[row.get(key)].append(row)
    return result


def snapshot(connection, subject):
    """Read all projection tables in one statement and one PostgreSQL snapshot.

    A single SQL statement avoids dozens of network round trips and provides
    cross-table consistency even at the default READ COMMITTED isolation level.
    Secrets are excluded from integration projections before aggregation.
    """
    entries = []
    for table in TABLES:
        if table == "integration_endpoints":
            source = sql.SQL("(SELECT id, system_name, integration_type, status, configuration, updated_at FROM public.{})").format(sql.Identifier(table))
        else:
            source = sql.SQL("public.{}").format(sql.Identifier(table))
        entries.append(sql.SQL("{}, (SELECT COALESCE(jsonb_agg(to_jsonb(projection)), '[]'::jsonb) FROM {} AS projection)").format(sql.Literal(table), source))
    # jsonb_build_object accepts at most 100 arguments. Bounded chunks keep the
    # statement valid when new tables are added to the projection allowlist.
    objects = [sql.SQL("jsonb_build_object({})").format(sql.SQL(", ").join(entries[offset:offset + 24])) for offset in range(0, len(entries), 24)]
    statement = sql.SQL("SELECT {} AS snapshot").format(sql.SQL(" || ").join(objects))
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(statement)
        tables = cursor.fetchone()["snapshot"]
    return map_snapshot(tables, str(subject))


def map_snapshot(tables, subject):
    """Pure mapping boundary used by live reads and deterministic contract tests."""
    tables = scoped_tables(tables, subject)
    t = lambda name: tables.get(name, [])
    institutions = index(t("institutions"))
    apps = index(t("applications"))
    institution_ids, app_ids = set(institutions), set(apps)
    users = index(t("users"))
    roles = index(t("roles"))
    stages = index(t("workflow_stages"))
    stage_instances = index(t("application_stage_instances"))
    instances_by_app = grouped(t("application_stage_instances"), "application_id")
    application_types = index(t("application_types"))
    assignments = grouped(t("assignments"), "application_id")
    grant_rows = grouped(t("user_role_assignments"), "user_id")
    campuses = grouped(t("institution_campuses"), "institution_id")
    attributes = grouped(t("institution_profile_attributes"), "institution_id")
    workflow_stages = grouped(t("workflow_stages"), "workflow_definition_id")
    workflow_transitions = grouped(t("workflow_transitions"), "workflow_definition_id")
    rule_versions = index(t("aph_rule_versions"))
    rule_sets = index(t("aph_rule_sets"))
    now = datetime.now(timezone.utc)

    def current_grant(g):
        def parse(value):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result
        return (g.get("status") == "active" and
                (not g.get("valid_from") or parse(g["valid_from"]) <= now) and
                (not g.get("valid_until") or parse(g["valid_until"]) > now))

    result = {"regions": [{"id": r["id"], "name": r["name"], "code": r["code"]} for r in t("regions")],
              "users": [], "institutions": [], "applications": [], "workflows": []}
    for u in users.values():
        grants = []
        for g in grant_rows[u["id"]]:
            r = role(roles.get(g["role_id"], {}).get("role_code"))
            if current_grant(g) and r in ROLES:
                grants.append({"role": r, "scope": {"type": upper(g["scope_type"]), "id": g.get("scope_id") or "all"}, "validUntil": g.get("valid_until")})
        result["users"].append({"id": u["id"], "displayName": u["display_name"], "email": u.get("email") or "", "status": "ACTIVE" if u["status"] == "active" else "DISABLED", "assignments": grants})
    for i in institutions.values():
        result["institutions"].append({"id": i["id"], "code": clean_text(i.get("institution_code") or ""), "name": clean_text(i["official_name"]), "type": i["institution_type"], "regionId": i.get("region_id") or "", "status": upper(i["status"]),
            "campuses": [{"id": c["id"], "name": clean_text(c["campus_name"]), "city": (c.get("address") or {}).get("city", ""), "primary": c["is_primary"]} for c in campuses[i["id"]]],
            "attributes": [{"key": a["attribute_key"], "value": str(next((a[k] for k in ("value_text", "value_date", "value_number") if a.get(k) is not None), "")), "verification": "VERIFIED" if a.get("verified_status") == "verified" else "PENDING", "sourceVersionId": None} for a in attributes[i["id"]]]})
    for a in apps.values():
        instance = stage_instances.get(a.get("current_stage_instance_id")) or next(iter(sorted(instances_by_app[a["id"]], key=lambda s: s.get("entered_at", ""), reverse=True)), {})
        stage = stages.get(instance.get("workflow_stage_id"), {})
        status = APPLICATION_STATUSES.get(upper(a["status"]), upper(a["status"]))
        if status in ("SUBMITTED", "IN_REVIEW"):
            status = {"evc": "AWAITING_EVC", "decision": "DECISION_PENDING"}.get(stage.get("stage_type"), status)
        owner = next((g.get("assigned_user_id") for g in reversed(assignments[a["id"]]) if g.get("status") in ("active", "assigned", "pending")), None)
        result["applications"].append({"id": a["id"], "number": clean_text(a["application_number"]), "institutionId": a["institution_id"], "campusId": a.get("campus_id") or "", "type": application_types.get(a["application_type_id"], {}).get("code", "").removeprefix("DEMO-"), "academicYear": a.get("academic_year") or str((a.get("submitted_at") or a.get("created_at") or "")[:4]), "status": status, "workflowId": a["workflow_definition_id"], "currentStage": stage.get("stage_code", "").removeprefix("DEMO-"), "stageEnteredAt": instance.get("entered_at"), "submittedAt": a.get("submitted_at"), "dueAt": instance.get("due_at"), "ownerId": owner, "nextAction": {"DRAFT": "Complete and submit application", "RETURNED_FOR_DEFICIENCY": "Respond to deficiency notice", "CLOSED": "Case closed"}.get(status, "Review current workflow stage"), "version": a.get("version", 1), "closure": {"at": a["closed_at"], "authorityId": a.get("updated_by") or "", "reason": "See approval decision and audit history", "reopened": False} if a.get("closed_at") else None})
    for w in t("workflow_definitions"):
        rv = rule_versions.get(w.get("aph_rule_version_id"), {})
        rs = rule_sets.get(rv.get("rule_set_id"), {})
        result["workflows"].append({"id": w["id"], "name": w["name"], "version": str(w.get("version_number", 1)), "aphVersion": str(rv.get("version_number", "")), "status": upper(w["status"]), "effectiveFrom": rs.get("effective_from"), "stages": [{"code": s["stage_code"].removeprefix("DEMO-"), "name": s["stage_name"], "slaDays": s.get("default_sla_days") or 0, "ownerRole": {"INTAKE": "INSTITUTION", "SCRUTINY": "SCRUTINY", "DEFICIENCY": "INSTITUTION", "EVC": "EVC_COORDINATOR", "COMPLIANCE": "COMPLIANCE"}.get(upper(s.get("stage_type")), "REGIONAL")} for s in sorted(workflow_stages[w["id"]], key=lambda s: s.get("stage_order", 0))], "transitions": [{"from": stages.get(x["from_stage_id"], {}).get("stage_code", "").removeprefix("DEMO-"), "to": stages.get(x["to_stage_id"], {}).get("stage_code", "").removeprefix("DEMO-"), "guards": list((x.get("guard_rule") or {}).keys())} for x in workflow_transitions[w["id"]]]})
    result["submissions"] = [{"id": s["id"], "applicationId": s["application_id"], "number": s["submission_number"], "submittedAt": s["submitted_at"], "submittedBy": s.get("submitted_by") or "", "noticeId": s.get("deficiency_notice_id"), "documentVersionIds": s.get("document_version_ids") or []} for s in t("application_submissions") if s["application_id"] in app_ids]
    result["stageEvents"] = [{"id": s["id"], "applicationId": s["application_id"], "at": s["event_at"], "actorId": s.get("actor_user_id") or "", "from": stages.get(s.get("from_stage_id"), {}).get("stage_code", "").removeprefix("DEMO-"), "to": stages.get(s.get("to_stage_id"), {}).get("stage_code", "").removeprefix("DEMO-"), "reason": s.get("reason") or "", "workflowId": apps[s["application_id"]]["workflow_definition_id"]} for s in t("stage_history") if s["application_id"] in app_ids]
    items = grouped(t("deficiency_items"), "deficiency_notice_id")
    # Project the latest persisted per-item response, never a browser-only narrative.
    responses = {}
    for response in sorted(t("deficiency_item_responses"), key=lambda r: (r.get("submitted_at", ""), r["id"])):
        responses[response["deficiency_item_id"]] = response
    for notice_items in items.values():
        for position, item in enumerate(notice_items):
            response = responses.get(item["id"])
            if response:
                item = item.copy()
                item["response_text"] = response["narrative"]
                item["response_document_version_id"] = response.get("document_version_id")
                notice_items[position] = item
    def item_status(value):
        return {"PENDING": "OPEN", "RESPONSE_SUBMITTED": "RESPONDED", "SUBMITTED": "RESPONDED", "ACCEPTED": "RESOLVED", "WAIVED": "RESOLVED"}.get(upper(value), upper(value, "OPEN"))
    result["deficiencies"] = [{"id": n["id"], "number": clean_text(str(n["notice_number"])), "applicationId": n["application_id"], "issuedBy": n.get("issued_by") or "", "issuedAt": n["issued_at"], "responseDueAt": n.get("response_due_at") or "", "reason": n.get("reason") or "Deficiency notice", "status": item_status(n["status"]), "items": [{"id": i["id"], "criterion": i.get("criterion_code") or "", "description": i["description"], "documentId": i.get("related_document_id"), "status": item_status(i["resolution_status"]), "response": i.get("response_text"), "responseVersionId": i.get("response_document_version_id")} for i in items[n["id"]]]} for n in t("deficiency_notices") if n["application_id"] in app_ids]
    for application in result["applications"]:
        application["applicationTypeId"] = apps[application["id"]]["application_type_id"]
        stage_instance = stage_instances.get(apps[application["id"]].get("current_stage_instance_id"), {})
        application["stageType"] = stages.get(stage_instance.get("workflow_stage_id"), {}).get("stage_type", "")
    for workflow in result["workflows"]:
        persisted_workflow = next(w for w in t("workflow_definitions") if w["id"] == workflow["id"])
        workflow["applicationTypeId"] = persisted_workflow.get("application_type_id")
        workflow["effectiveFrom"] = persisted_workflow.get("effective_from") or workflow["effectiveFrom"]
        for stage in workflow["stages"]:
            stage["id"] = next((s["id"] for s in workflow_stages[workflow["id"]] if s["stage_code"].removeprefix("DEMO-") == stage["code"]), "")
            persisted_stage = stages.get(stage["id"], {})
            stage["type"] = persisted_stage.get("stage_type")
            stage["ownerRole"] = role(persisted_stage.get("owner_role_code")) or stage["ownerRole"]
    _documents(result, tables, institution_ids, app_ids)
    _visits(result, tables, app_ids)
    _compliance(result, tables, app_ids)
    _shared(result, tables, subject, app_ids, institution_ids)
    return result


def scoped_tables(tables, subject):
    """Scope parents even when the writer's RLS intentionally permits all rows.

    A client-selected persona never affects this filter. Only persisted, active,
    unexpired assignments belonging to the server-verified subject are used.
    Child projection helpers then intersect every entity with these parents.
    """
    now = datetime.now(timezone.utc)
    def moment(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    active = [g for g in tables.get("user_role_assignments", [])
              if g.get("user_id") == subject and g.get("status") == "active"
              and (not g.get("valid_from") or moment(g["valid_from"]) <= now)
              and (not g.get("valid_until") or moment(g["valid_until"]) > now)]
    enabled = any(u["id"] == subject and u.get("status") == "active" for u in tables.get("users", []))
    if not enabled:
        active = []
    scopes = {(g["scope_type"], g.get("scope_id")) for g in active}
    role_index = index(tables.get("roles", []))
    prototype = bool(active) and all(role_index.get(g["role_id"], {}).get("role_code", "").startswith("DEMO_") for g in active)
    prototype_subjects = {g["user_id"] for g in tables.get("user_role_assignments", [])
                          if role_index.get(g["role_id"], {}).get("role_code", "").startswith("DEMO_")}
    all_institutions = index(tables.get("institutions", []))
    if prototype:
        all_institutions = {key: value for key, value in all_institutions.items()
                            if str(value.get("institution_code") or "").startswith(("DEMO-", "INST-"))
                            or value.get("created_by") in prototype_subjects}
    campuses = index(tables.get("institution_campuses", []))
    def permitted(app):
        institution = all_institutions.get(app["institution_id"], {})
        return bool(institution) and (("global", None) in scopes or ("institution", app["institution_id"]) in scopes
                or ("application", app["id"]) in scopes
                or ("region", institution.get("region_id")) in scopes
                or ("campus", app.get("campus_id")) in scopes)
    apps = [a for a in tables.get("applications", []) if permitted(a)]
    institution_ids = {a["institution_id"] for a in apps}
    for institution in all_institutions.values():
        if (("global", None) in scopes or ("institution", institution["id"]) in scopes
                or ("region", institution.get("region_id")) in scopes
                or any(scope == "campus" and campuses.get(identifier, {}).get("institution_id") == institution["id"] for scope, identifier in scopes)):
            institution_ids.add(institution["id"])
    scoped = {**tables, "institutions": [i for i in all_institutions.values() if i["id"] in institution_ids], "applications": apps}
    actor_roles = {role(role_index.get(g["role_id"], {}).get("role_code")) for g in active}
    if actor_roles == {"SCRUTINY"}:
        assigned_apps = {a["application_id"] for a in tables.get("assignments", []) if a.get("assigned_user_id") == subject}
        scoped["applications"] = [a for a in scoped["applications"] if a["id"] in assigned_apps]
        permitted_institutions = {a["institution_id"] for a in scoped["applications"]}
        scoped["institutions"] = [i for i in scoped["institutions"] if i["id"] in permitted_institutions]
    if "SYSTEM" not in actor_roles:
        # Keep a minimal directory for visible owners, committee experts and the
        # caller. Never return unrelated users' identity subjects or contacts.
        relevant_users = {subject}
        app_ids = {a["id"] for a in apps}
        visit_ids = {v["id"] for v in tables.get("evc_visits", []) if v["application_id"] in app_ids}
        relevant_users.update(e["user_id"] for e in tables.get("expert_profiles", []))
        relevant_users.update(a.get("assigned_user_id") for a in tables.get("assignments", []) if a["application_id"] in app_ids)
        relevant_users.update(v.get("coordinator_user_id") for v in tables.get("evc_visits", []) if v["id"] in visit_ids)
        scoped["users"] = [u for u in tables.get("users", []) if u["id"] in relevant_users]
        scoped["user_role_assignments"] = [g for g in tables.get("user_role_assignments", []) if g["user_id"] == subject]
        scoped["integration_endpoints"] = []
        scoped["background_jobs"] = []
    if not actor_roles.intersection({"SYSTEM", "POLICY", "CENTRAL"}):
        scoped["system_settings"] = []
        scoped["notification_rules"] = []
        scoped["escalation_rules"] = []
    return scoped


def _documents(result, tables, institution_ids, app_ids):
    t = lambda name: tables.get(name, [])
    types = index(t("document_types"))
    versions = grouped(t("document_versions"), "document_id")
    docs = [d for d in t("documents") if (d.get("application_id") in app_ids or (not d.get("application_id") and d["institution_id"] in institution_ids))]
    doc_ids = {d["id"] for d in docs}
    version_ids = {v["id"] for vs in versions.values() for v in vs if v["document_id"] in doc_ids}
    result["documents"] = []
    for d in docs:
        kind = types.get(d["document_type_id"], {})
        result["documents"].append({"id": d["id"], "institutionId": d["institution_id"], "applicationId": d.get("application_id"), "campusId": d.get("campus_id"), "type": kind.get("document_type_code", "").removeprefix("DEMO-"), "issuer": d.get("issuer") or "", "reference": d.get("reference") or "", "supportsExpiry": kind.get("supports_expiry", False), "currentVersionId": d.get("current_version_id") or "", "versions": [{"id": v["id"], "number": v["version_number"], "fileName": v["file_name"], "mimeType": v["mime_type"], "sizeBytes": v["size_bytes"], "issuedAt": v.get("issue_date"), "expiryDate": v.get("expiry_date"), "uploadedAt": v["uploaded_at"], "uploadedBy": v.get("uploaded_by") or "", "verification": "VERIFIED" if v["verification_status"] == "verified" else "REJECTED" if v["verification_status"] == "rejected" else "PENDING", "scan": upper(v.get("scan_status"), "PENDING"), "previewText": "Metadata record only; use an authorised file download when available." if str(v.get("object_key", "")).startswith("demo/metadata-only/") else "File preview requires an authorised download."} for v in sorted(versions[d["id"]], key=lambda v: v["version_number"])]})
        result["documents"][-1]["documentTypeId"] = d["document_type_id"]
        result["documents"][-1]["version"] = d.get("version", 1)
    scans = {}
    for scan in sorted(t("document_file_scans"), key=lambda row: (row.get("created_at", ""), row["id"])):
        scans[scan["document_version_id"]] = scan
    for document in result["documents"]:
        for version in document["versions"]:
            scan = scans.get(version["id"])
            if scan:
                version["scan"] = {"clean": "CLEAN", "infected": "INFECTED", "error": "QUARANTINED", "unavailable": "QUARANTINED"}[scan["status"]]
    version_index = index(t("document_versions"))
    checks = grouped(t("document_check_results"), "document_version_id")
    result["documentChecks"] = []
    for e in t("document_extractions"):
        if e["document_version_id"] not in version_ids:
            continue
        extracted = e.get("extracted_fields") or {}
        confidence = (e.get("confidence_summary") or {}).get("overall_confidence"); fields = [{"name": name, "declared": "", "extracted": str(value) if value is not None else None, "confidence": confidence} for name, value in extracted.items() if name not in ("demo_only", "file_processed")]
        result["documentChecks"].append({"id": e["id"], "documentId": version_index[e["document_version_id"]]["document_id"], "versionId": e["document_version_id"], "engine": e["engine_name"], "processedAt": e.get("completed_at"), "status": "FAILED" if e["status"] == "failed" else "COMPLETED" if e["status"] in ("completed", "needs_review") else "QUEUED", "fields": fields, "findings": [{"code": c["check_code"], "severity": upper(c["severity"]), "description": (c.get("details") or {}).get("note") or str(c.get("result") or ""), "review": {"ACCEPTED": "ACCEPTED", "CORRECTION_REQUIRED": "CORRECTION_REQUIRED", "REJECTED":"CORRECTION_REQUIRED", "OVERRIDDEN":"ACCEPTED"}.get(upper(c.get("review_status")), "PENDING")} for c in checks[e["document_version_id"]]]})
        if checks[e["document_version_id"]]:
            result["documentChecks"][-1]["id"] = checks[e["document_version_id"]][0]["id"]
    extracted_versions = {c["versionId"] for c in result["documentChecks"]}
    for version_id, findings in checks.items():
        if version_id not in version_ids or version_id in extracted_versions:
            continue
        first = findings[0]
        result["documentChecks"].append({"id": first["id"], "documentId": version_index[version_id]["document_id"], "versionId": version_id, "engine": "Metadata validation (no OCR extraction)", "processedAt": first.get("created_at"), "status": "COMPLETED", "fields": [], "findings": [{"code": c["check_code"], "severity": upper(c["severity"]), "description": (c.get("details") or {}).get("note") or str(c.get("result") or ""), "review": {"ACCEPTED": "ACCEPTED", "CORRECTION_REQUIRED": "CORRECTION_REQUIRED", "REJECTED":"CORRECTION_REQUIRED", "OVERRIDDEN":"ACCEPTED"}.get(upper(c.get("review_status")), "PENDING")} for c in findings]})
    result["renewals"] = [{"id": r["id"], "documentId": r["document_id"], "previousVersionId": r.get("current_version_id") or "", "submittedVersionId": r.get("submitted_version_id"), "dueAt": r.get("renewal_due_at") or "", "status": {"CLOSED": "VERIFIED", "COMPLETED": "VERIFIED"}.get(upper(r["status"]), upper(r["status"])), "assignedTo": r.get("assigned_to") or ""} for r in t("document_renewal_cases") if r["document_id"] in doc_ids]


def _visits(result, tables, app_ids):
    t = lambda name: tables.get(name, [])
    visits = [v for v in t("evc_visits") if v["application_id"] in app_ids]
    visit_ids = {v["id"] for v in visits}
    experts = index(t("expert_profiles"))
    expert_by_user = {e["user_id"]: e["id"] for e in experts.values()}
    members = grouped(t("evc_committee_members"), "evc_visit_id")
    events = grouped(t("evc_visit_events"), "evc_visit_id")
    slots = grouped(t("slot_recommendations"), "evc_visit_id")
    result["experts"] = [{"id": e["id"], "userId": e["user_id"], "expertise": e.get("expertise") if isinstance(e.get("expertise"), list) else [str(e.get("expertise") or "")], "eligibility": "ELIGIBLE" if e.get("eligibility_status") in ("eligible", "active") else "INELIGIBLE", "availabilityMethod": "CALENDAR" if e.get("availability_method") == "calendar" else "MANUAL"} for e in experts.values()]
    result["availability"] = [{"id": a["id"], "participantType": "EXPERT", "participantId": expert_by_user.get(a["expert_user_id"], a["expert_user_id"]), "startAt": a["start_at"], "endAt": a["end_at"], "state": "AVAILABLE" if a["availability_status"] == "available" else "BUSY", "source": "CALENDAR" if a.get("source") == "calendar" else "MANUAL", "confirmedAt": a.get("last_confirmed_at") or a.get("created_at") or ""} for a in t("expert_availability")]
    visible_institutions = {i["id"] for i in result["institutions"]}
    result["availability"].extend({"id": a["id"], "participantType": "INSTITUTION", "participantId": a["institution_id"], "startAt": a["start_at"], "endAt": a["end_at"], "state": "AVAILABLE" if a["availability_status"] == "available" else "BUSY", "source": "MANUAL", "confirmedAt": a.get("last_confirmed_at") or a.get("created_at") or ""} for a in t("institution_availability") if a["institution_id"] in visible_institutions)
    result["visits"] = [{"id": v["id"], "applicationId": v["application_id"], "campusId": v.get("campus_id") or "", "status": "PROPOSED" if upper(v["status"]) == "SCHEDULING" and any(s.get("feasibility_status") == "feasible" for s in slots[v["id"]]) else VISIT_STATUSES.get(upper(v["status"]), upper(v["status"])), "requiredBy": v.get("required_by") or "", "durationMinutes": v.get("duration_minutes") or 480, "requiredMemberCount": v.get("required_member_count") or 5, "coordinatorId": v.get("coordinator_user_id") or "", "committee": [{"expertId": expert_by_user.get(m["expert_user_id"], m["expert_user_id"]), "role": upper(m["committee_role"]), "selectedBy": m.get("selected_by") or "", "selectedAt": m["selected_at"]} for m in members[v["id"]] if m["selection_status"] == "selected"], "confirmedSlotId": next((s["id"] for s in slots[v["id"]] if s["start_at"] == v.get("confirmed_start_at") and s["end_at"] == v.get("confirmed_end_at")), None), "version": v.get("version") or 1, "events": [{"at": e["event_at"], "type": e["event_type"], "actorId": e.get("actor_user_id") or "", "reason": e.get("reason") or ""} for e in events[v["id"]]]} for v in visits]
    result["slots"] = [{"id": s["id"], "visitId": s["evc_visit_id"], "startAt": s["start_at"], "endAt": s["end_at"], "rank": s["rank"], "feasible": s["feasibility_status"] == "feasible", "explanation": [s.get("explanation") or ""], "participantIds": [expert_by_user.get(m["expert_user_id"], m["expert_user_id"]) for m in members[s["evc_visit_id"]] if m["selection_status"] == "selected"], "snapshotAt": s.get("availability_snapshot_at") or s.get("created_at") or "", "expiresAt": s.get("expires_at") or "", "blockers": [] if s["feasibility_status"] == "feasible" else [s.get("explanation") or "Availability unresolved"]} for s in t("slot_recommendations") if s["evc_visit_id"] in visit_ids]
    result["invitations"] = [{"id": i["id"], "visitId": i["evc_visit_id"], "recipientId": i["recipient_user_id"], "response": upper(i["response_status"]), "delivery": upper(i["delivery_status"]), "calendarStatus": upper(i.get("calendar_status"), "PENDING")} for i in t("evc_invitations") if i["evc_visit_id"] in visit_ids]
    result["observations"] = [{"id": o["id"], "visitId": o["evc_visit_id"], "criterion": o.get("criterion_code") or "", "text": o["observation_text"], "authorId": o.get("created_by") or "", "sourceType": "COMMITTEE_NOTE" if o.get("source_type") == "committee_note" else "STRUCTURED_FORM", "status": "DRAFT" if o.get("review_status") == "draft" else "SUBMITTED"} for o in t("evc_observations") if o["evc_visit_id"] in visit_ids]
    versions = grouped(t("meeting_record_versions"), "evc_report_id")
    sources = grouped(t("meeting_record_sources"), "meeting_record_version_id")
    result["meetingRecords"] = []
    for report in t("evc_reports"):
        if report["evc_visit_id"] not in visit_ids:
            continue
        mapped = []
        current = next((v for v in versions[report["id"]] if v["id"] == report.get("current_version_id")), {})
        current_type = current.get("record_type", "evc_report")
        for v in versions[report["id"]]:
            if v.get("record_type", "evc_report") != current_type:
                continue
            manifest = v.get("source_manifest") or {}
            sections = manifest.get("sections", []) if isinstance(manifest, dict) else []
            sections = [{"title": section.get("title") or section.get("criterion") or "Observation",
                         "text": section.get("text") or "",
                         "sourceIds": section.get("sourceIds") or ([section["source_id"]] if section.get("source_id") else []),
                         "warning": section.get("warning")} for section in sections]
            if not sections and v.get("content_reference"):
                sections = [{"title": "Record", "text": str(v["content_reference"]), "sourceIds": [s["source_id"] for s in sources[v["id"]]], "warning": "Content reference; inspect the approved source document."}]
            mapped.append({"number": v["version_number"], "status": {"PENDING_APPROVAL":"IN_REVIEW", "REJECTED":"CHANGES_REQUESTED"}.get(upper(v["approval_status"]),upper(v["approval_status"])), "sections": sections, "approvedBy": v.get("approved_by"), "approvedAt": v.get("approved_at"), "correctionReason": v.get("correction_reason")})
        visible_numbers = {v["version_number"] for v in versions[report["id"]] if v.get("record_type", "evc_report") == current_type}
        result["meetingRecords"].append({"id": report["id"], "visitId": report["evc_visit_id"], "type": upper(current_type), "templateVersion": str(report.get("template_version") or "1"), "currentVersion": current.get("version_number") or max((v["number"] for v in mapped), default=1), "versions": sorted([v for v in mapped if v["number"] in visible_numbers], key=lambda v: v["number"])})
    roles = index(t("roles"))
    result["actionItems"] = [{"id": a["id"], "visitId": a["evc_visit_id"], "observationId": a.get("source_observation_id") or "", "description": a["description"], "responsibleRole": role(roles.get(a.get("responsible_role_id"), {}).get("role_code")) or "REGIONAL", "dueAt": a.get("due_at") or "", "status": "COMPLETED" if a["status"] == "completed" else "OPEN"} for a in t("action_items") if a["evc_visit_id"] in visit_ids]


def _compliance(result, tables, app_ids):
    t = lambda name: tables.get(name, [])
    result["decisions"] = [{"id": d["id"], "applicationId": d["application_id"], "type": {"APPROVAL": "APPROVE", "APPROVED": "APPROVE", "REJECTION": "REJECT", "REJECTED": "REJECT", "CLOSURE": "CLOSE", "CLOSED": "CLOSE"}.get(upper(d["decision_type"]), upper(d["decision_type"])), "status": "APPROVED" if d["decision_status"] in ("approved", "rejected", "withdrawn", "final", "issued") else "DRAFT", "authorityId": d.get("created_by") or d.get("decision_authority") or "", "reason": d.get("reason") or "", "at": d.get("decision_at")} for d in t("approval_decisions") if d["application_id"] in app_ids]
    conditions = [c for c in t("compliance_conditions") if c["application_id"] in app_ids]
    condition_ids = {c["id"] for c in conditions}
    closure_reasons = {}
    for event in sorted(t("audit_events"), key=lambda row: (row.get("event_at", ""), row["id"])):
        if event.get("action") == "COMPLIANCE_CONDITION_CLOSED" and event.get("entity_id") in condition_ids:
            closure_reasons[event["entity_id"]] = event.get("reason") or (event.get("metadata") or {}).get("reason")
    submission_conditions = {row["id"]: row["compliance_condition_id"] for row in t("evidence_submissions")}
    reviewers = {}
    for verification in sorted(t("compliance_verifications"), key=lambda row: (row.get("verified_at", ""), row["id"])):
        condition_id = submission_conditions.get(verification["evidence_submission_id"])
        if condition_id in condition_ids:
            reviewers[condition_id] = verification.get("reviewer_user_id")
    result["conditions"] = [{"id": c["id"], "applicationId": c["application_id"], "institutionId": c["institution_id"], "version": c.get("version", 1), "sourceDecisionId": c.get("source_approval_id") or "", "code": clean_text(c["condition_code"]), "description": clean_text(c["description"]), "evidenceRequired": c.get("evidence_requirements") or [], "dueAt": c.get("due_at") or "", "status": {"UNDER_VERIFICATION":"UNDER_REVIEW", "REJECTED":"VERIFIED_NON_COMPLIANT", "OVERDUE": "OPEN", "COMPLIANT": "VERIFIED_COMPLIANT", "NON_COMPLIANT": "VERIFIED_NON_COMPLIANT", "FULFILLED": "VERIFIED_COMPLIANT"}.get(upper(c["status"]), upper(c["status"])), "reviewerId": reviewers.get(c["id"]) or c.get("reviewer_user_id") or "", "closureReason": closure_reasons.get(c["id"]) if c["status"] == "closed" else None} for c in conditions]
    files = grouped(t("evidence_submission_files"), "evidence_submission_id")
    evidences = [e for e in t("evidence_submissions") if e["compliance_condition_id"] in condition_ids]
    evidence_ids = {e["id"] for e in evidences}
    result["evidence"] = [{"id": e["id"], "conditionId": e["compliance_condition_id"], "submissionNumber": e["submission_number"], "submittedAt": e["submitted_at"], "submittedBy": e.get("submitted_by") or "", "documentVersionIds": [f["document_version_id"] for f in files[e["id"]]], "responseToVerificationId": e.get("response_to_verification_id")} for e in evidences]
    result["verifications"] = [{"id": v["id"], "evidenceId": v["evidence_submission_id"], "reviewerId": v["reviewer_user_id"], "result": {"ACCEPTED":"COMPLIANT","REJECTED":"NON_COMPLIANT","NEEDS_CLARIFICATION":"CLARIFICATION_REQUIRED"}.get(upper(v["result"]),upper(v["result"])), "comments": v.get("comments") or "", "at": v.get("verified_at") or v.get("created_at") or ""} for v in t("compliance_verifications") if v["evidence_submission_id"] in evidence_ids]


def _shared(result, tables, subject, app_ids, institution_ids):
    t = lambda name: tables.get(name, [])
    visits = {v["id"] for v in result["visits"]}
    conditions = {c["id"] for c in result["conditions"]}
    docs = {d["id"] for d in result["documents"]}
    visible_entities = app_ids | institution_ids | visits | conditions | docs
    attempts = grouped(t("notification_attempts"), "notification_id")
    result["notifications"] = [{"id": n["id"], "recipientId": n["recipient_user_id"], "event": n["event_code"], "channel": upper((n.get("payload") or {}).get("channel"), "IN_APP"), "status": upper(n["status"]), "entityType": {"EVC_VISIT": "EVC", "COMPLIANCE_CONDITION": "CONDITION"}.get(upper(n.get("related_entity_type")), upper(n.get("related_entity_type"), "APPLICATION")), "entityId": n.get("related_entity_id") or "", "createdAt": n["created_at"], "read": bool((n.get("payload") or {}).get("read", False)), "attempts": [{"number": a["attempt_number"], "at": a["attempted_at"], "result": upper(a["result"]), "failureReason": a.get("failure_reason")} for a in attempts[n["id"]]]} for n in t("notifications") if n["recipient_user_id"] == subject or n.get("related_entity_id") in visible_entities]
    result["escalations"] = [{"id": e["id"], "entityType": upper(e.get("related_entity_type")), "entityId": e.get("related_entity_id") or "", "ruleId": e["rule_id"], "dueAt": e.get("due_at") or e["triggered_at"], "triggeredAt": e["triggered_at"], "ownerId": e.get("recipient_user_id") or "", "level": e.get("level") or 1, "status": "RESOLVED" if e["resolution_status"] == "resolved" else "OPEN", "reason": e.get("reason") or "Configured overdue threshold exceeded", "resolution": e.get("resolution")} for e in t("escalation_events") if e.get("related_entity_id") in visible_entities]
    definitions = index(t("report_definitions"))
    result["reportDefinitions"] = []
    for d in definitions.values():
        columns = d.get("columns_config") or []
        filters = d.get("filters_config") or []
        policy = d.get("access_policy") or {}
        result["reportDefinitions"].append({"id": report_code(d["report_code"]), "name": clean_text(d["name"]), "columns": columns if isinstance(columns, list) else columns.get("columns", []), "filters": filters if isinstance(filters, list) else filters.get("filters", []), "roles": [r for r in (role(r) for r in policy.get("roles", sorted(ROLES))) if r in ROLES]})
    result["reportRuns"] = []
    for r in t("report_runs"):
        if r.get("requested_by") != subject:
            continue
        filters = r.get("filters") or {}
        meta = r.get("result_metadata") or {}
        result["reportRuns"].append({"id": r["id"], "reportCode": report_code(definitions.get(r["report_definition_id"], {}).get("report_code")), "requestedBy": r["requested_by"], "generatedAt": r.get("completed_at"), "period": {"from": filters.get("date_from", ""), "to": filters.get("date_to", "")}, "filters": {k: str(v) for k, v in filters.items() if isinstance(v, (str, int, float, bool))}, "status": upper(r["status"]), "snapshotAt": r.get("started_at") or r["created_at"], "rowCount": meta.get("row_count", 0), "snapshotRows": meta.get("snapshot_rows"), "format": "CSV", "failureReason": meta.get("failure_reason")})
    anchors = grouped(t("audit_anchors"), "audit_event_id")
    result["auditEvents"] = [{"id": a["id"], "actorId": a.get("actor_id") or "", "action": a["action"], "entityType": upper(a["entity_type"]), "entityId": a.get("entity_id") or "", "at": a["event_at"], "reason": a.get("reason") or "", "correlationId": a.get("correlation_id") or "", "version": (a.get("metadata") or {}).get("version", 1), "previousHash": a.get("previous_hash"), "eventHash": a.get("event_hash") or "", "anchor": upper(anchors[a["id"]][-1].get("anchor_status")) if anchors[a["id"]] else "DISABLED"} for a in t("audit_events") if a.get("actor_id") == subject or a.get("entity_id") in visible_entities]
    configs = []
    for d in t("document_types"):
        configs.append({"id": d["id"], "category": "DOCUMENT_TYPE", "name": d["name"], "version": d.get("version", 1), "status": "PUBLISHED", "values": {"code": d["document_type_code"], "supportsExpiry": d["supports_expiry"]}})
    for r in t("aph_rule_sets"):
        configs.append({"id": r["id"], "category": "APH", "name": r["title"], "version": r.get("version", 1), "status": "PUBLISHED" if r["status"] == "published" else "DRAFT", "values": {"sourceReference": r.get("source_reference") or ""}})
    for c in t("committees"):
        configs.append({"id": c["id"], "category": "COMMITTEE", "name": c["name"], "version": c.get("version", 1), "status": "PUBLISHED" if c["status"] == "active" else "DRAFT", "values": c.get("configuration") or {}})
    for n in t("notification_rules"):
        recipient = n.get("recipient_rule") or {}
        configs.append({"id": n["id"], "category": "NOTIFICATION", "name": n["event_code"], "version": n.get("version", 1), "status": "PUBLISHED" if n["enabled"] else "DRAFT", "values": {"event": n["event_code"], "channel": upper(n["channel"]), "recipientRole": str(recipient.get("role") or ""), "templateVersion": str(n["template_version"])}})
    for e in t("escalation_rules"):
        configs.append({"id": e["id"], "category": "ESCALATION", "name": e["event_code"], "version": e.get("version", 1), "status": "PUBLISHED" if e["enabled"] else "DRAFT", "values": {"thresholdMinutes": e["threshold_minutes"], "action": e["action_type"]}})
    for s in t("system_settings"):
        values = s.get("setting_value")
        configs.append({"id": s["id"], "category": "SETTINGS", "name": s["setting_key"], "version": s.get("version", 1), "status": "PUBLISHED" if s.get("approved_by") else "DRAFT", "values": values if isinstance(values, dict) else {"value": str(values)}})
    for revision in t("configuration_revisions"):
        configs.append({"id": revision["id"], "category": revision["category"], "name": revision["name"],
                        "version": revision["version"], "status": upper(revision["status"]),
                        "values": revision.get("values") or {}})
    result["configurations"] = configs
    result["integrations"] = [{"id": i["id"], "name": i["system_name"], "type": i["integration_type"], "status": {"ACTIVE": "STALE", "CONFIGURED": "STALE"}.get(upper(i["status"]), upper(i["status"])), "lastSyncAt": (i.get("configuration") or {}).get("last_sync_at"), "fieldOwnership": (i.get("configuration") or {}).get("field_ownership", ""), "error": (i.get("configuration") or {}).get("error")} for i in t("integration_endpoints")]
    result["jobs"] = [{"id": j["id"], "type": j["job_type"], "entityId": j.get("related_entity_id"), "integrationId": None, "status": {"RUNNING":"PROCESSING","SUCCEEDED":"COMPLETED","RETRYING":"RETRY_PENDING"}.get(upper(j["status"]),upper(j["status"])), "attempts": j.get("attempt_count", 0), "lastError": j.get("last_error"), "nextAttemptAt": j.get("next_attempt_at")} for j in t("background_jobs") if not j.get("related_entity_id") or j.get("related_entity_id") in visible_entities]
    result["tasks"] = [{"id": a["id"], "title": "Review assigned application", "ownerId": a.get("assigned_user_id") or "", "applicationId": a["application_id"], "dueAt": a.get("due_at") or "", "href": f"/portal/applications/{a['application_id']}", "status": "COMPLETED" if a["status"] == "completed" else "PENDING"} for a in t("assignments") if a["application_id"] in app_ids]
