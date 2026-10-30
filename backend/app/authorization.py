"""Server role/scope boundary shared by the normalized API routes.

The earlier writer policies are permissive; a database login alone is not an
authorization decision. This guard runs before any route reads or mutates data.
"""
from datetime import datetime, timezone
from uuid import UUID
import re

from fastapi import HTTPException, Request
from psycopg.rows import dict_row
from starlette.concurrency import run_in_threadpool

from .auth import get_verified_subject
from .transactions import write_transaction

ALIASES = {"INSTITUTION_USER": "INSTITUTION", "SCRUTINY_OFFICER": "SCRUTINY",
           "REGIONAL_OFFICER": "REGIONAL", "COUNCIL_ADMIN": "CENTRAL"}


def role_name(code):
    code = code.removeprefix("DEMO_")
    return ALIASES.get(code, code)


def validate_role_grant(cur, actor, target, role_code, scope_type, scope_id,
                        valid_from, valid_until, exclude_id=None):
    """One grant boundary for normalized and portal APIs, including reactivation.

    These are conservative evaluation segregation rules; deployment still needs
    the signed institutional access policy. Serialize on the target user to
    prevent two otherwise valid concurrent grants creating a conflicting pair.
    """
    if valid_until and (valid_from is None or valid_until <= valid_from):
        raise HTTPException(422, detail="Role validity must be a nonempty interval")
    cur.execute("SELECT id,status FROM public.users WHERE id=%s FOR UPDATE", (target,))
    recipient = cur.fetchone()
    if not recipient or recipient["status"] != "active":
        raise HTTPException(409, detail="Role recipient must be active")
    cur.execute("SELECT r.role_code,a.scope_type FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id JOIN public.users u ON u.id=a.user_id WHERE a.user_id=%s AND u.status='active' AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (actor,))
    authority = cur.fetchall()
    if not any(role_name(a["role_code"]) == "SYSTEM" and a["scope_type"] == "global" for a in authority):
        raise HTTPException(403, detail="Global system administration is required for role grants")
    if all(a["role_code"].startswith("DEMO_") for a in authority) and not role_code.startswith("DEMO_"):
        raise HTTPException(403, detail="Evaluation administrators cannot grant production roles")
    role = role_name(role_code)
    permitted = {
        "INSTITUTION": {"institution", "campus"}, "SCRUTINY": {"region", "application"},
        "REGIONAL": {"region"}, "CENTRAL": {"global"}, "SYSTEM": {"global"},
        "POLICY": {"global"}, "AUDITOR": {"global", "region"},
        "EVC_COORDINATOR": {"region", "application"}, "EVC_EXPERT": {"application"},
        "COMPLIANCE": {"region", "institution", "application"},
    }
    if scope_type not in permitted.get(role, set()) or (scope_type == "global") != (scope_id is None):
        raise HTTPException(422, detail="Scope is incompatible with this role")
    if scope_type != "global":
        table = {"institution":"institutions", "campus":"institution_campuses", "region":"regions", "application":"applications"}[scope_type]
        cur.execute(f"SELECT id FROM public.{table} WHERE id=%s", (scope_id,))
        if not cur.fetchone(): raise HTTPException(422, detail="Role scope does not exist")
    cur.execute("SELECT r.role_code,a.scope_type,a.scope_id FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id WHERE a.user_id=%s AND a.status='active' AND (%s::uuid IS NULL OR a.id<>%s) AND (a.valid_until IS NULL OR a.valid_until>%s) AND (%s::timestamptz IS NULL OR a.valid_from IS NULL OR a.valid_from<%s)",
                (target, exclude_id, exclude_id, valid_from, valid_until, valid_until))
    for assignment in cur.fetchall():
        existing = role_name(assignment["role_code"])
        if existing == role and assignment["scope_type"] == scope_type and assignment["scope_id"] == scope_id:
            raise HTTPException(409, detail="Overlapping role assignment already exists")
        pair = {existing, role}
        if existing != role and ("AUDITOR" in pair or ("INSTITUTION" in pair) or ("SYSTEM" in pair and pair.intersection({"REGIONAL", "CENTRAL", "POLICY", "SCRUTINY", "COMPLIANCE", "EVC_EXPERT"}))):
            raise HTTPException(409, detail="Roles violate evaluation separation of duties")


def allowed_roles(path):
    if path.startswith("/users"): return {"SYSTEM"}
    if path.startswith("/institutions"): return {"INSTITUTION", "REGIONAL", "CENTRAL"}
    if path.startswith(("/workflows", "/configurations", "/aph-rules")): return {"POLICY", "CENTRAL"}
    if "deficien" in path:
        return {"INSTITUTION"} if any(x in path for x in ("response", "resubmit")) else {"SCRUTINY", "REGIONAL"}
    if path.startswith("/applications") and any(x in path for x in ("decisions", "close", "statutory")): return {"REGIONAL", "CENTRAL"}
    if path.startswith("/applications") and "evc-visits" in path: return {"REGIONAL", "EVC_COORDINATOR"}
    if path.startswith("/applications"):
        return {"REGIONAL", "CENTRAL"} if "assignments" in path else {"SCRUTINY", "REGIONAL", "CENTRAL"} if "transition" in path else {"INSTITUTION"}
    if path.startswith("/documents") or path.startswith("/document-"):
        return {"INSTITUTION", "SCRUTINY", "COMPLIANCE", "REGIONAL"} if "ocr-checks" in path else {"SCRUTINY", "COMPLIANCE", "REGIONAL"} if any(x in path for x in ("review", "check")) else {"INSTITUTION", "SCRUTINY", "COMPLIANCE"}
    if "availability" in path: return {"INSTITUTION", "EVC_EXPERT", "EVC_COORDINATOR"}
    if path.startswith("/evc") or path.startswith("/experts"):
        return {"EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL"} if any(x in path for x in ("observations", "reports", "invitations")) else {"EVC_COORDINATOR", "REGIONAL"}
    if path.startswith("/meeting-records"): return {"EVC_EXPERT", "EVC_COORDINATOR", "REGIONAL"}
    if path.startswith("/compliance") or path.startswith("/conditions") or path.startswith("/evidence"):
        return {"INSTITUTION"} if "evidence" in path and "verif" not in path else {"COMPLIANCE", "REGIONAL"}
    if path.startswith("/notifications") or path.startswith("/escalations"): return {"SYSTEM", "REGIONAL", "CENTRAL"}
    if path.startswith("/report"): return {"INSTITUTION", "SCRUTINY", "REGIONAL", "EVC_COORDINATOR", "EVC_EXPERT", "COMPLIANCE", "CENTRAL", "AUDITOR", "SYSTEM"}
    return set()


# Resource IDs are resolved through their true parent before checking scope.
RESOURCES = {
    "institutions": "SELECT id AS institution_id, region_id, NULL::uuid AS application_id, institution_code, created_by FROM institutions WHERE id=%s",
    "applications": "SELECT i.id AS institution_id,i.region_id,a.id AS application_id,i.institution_code,i.created_by FROM applications a JOIN institutions i ON i.id=a.institution_id WHERE a.id=%s",
    "documents": "SELECT i.id AS institution_id,i.region_id,d.application_id,i.institution_code,i.created_by FROM documents d JOIN institutions i ON i.id=d.institution_id WHERE d.id=%s",
    "document-versions": "SELECT i.id AS institution_id,i.region_id,d.application_id,i.institution_code,i.created_by FROM document_versions v JOIN documents d ON d.id=v.document_id JOIN institutions i ON i.id=d.institution_id WHERE v.id=%s",
    "evc-visits": "SELECT i.id AS institution_id,i.region_id,a.id AS application_id,i.institution_code,i.created_by FROM evc_visits v JOIN applications a ON a.id=v.application_id JOIN institutions i ON i.id=a.institution_id WHERE v.id=%s",
    "compliance-conditions": "SELECT i.id AS institution_id,i.region_id,c.application_id,i.institution_code,i.created_by FROM compliance_conditions c JOIN institutions i ON i.id=c.institution_id WHERE c.id=%s",
    "deficiency-notices": "SELECT i.id AS institution_id,i.region_id,a.id AS application_id,i.institution_code,i.created_by FROM deficiency_notices n JOIN applications a ON a.id=n.application_id JOIN institutions i ON i.id=a.institution_id WHERE n.id=%s",
}


RESOURCES.update({
 "deficiency-items": "SELECT i.id AS institution_id,i.region_id,a.id AS application_id,i.institution_code,i.created_by FROM deficiency_items d JOIN deficiency_notices n ON n.id=d.deficiency_notice_id JOIN applications a ON a.id=n.application_id JOIN institutions i ON i.id=a.institution_id WHERE d.id=%s",
 "document-check-results": "SELECT i.id AS institution_id,i.region_id,d.application_id,i.institution_code,i.created_by FROM document_check_results c JOIN document_versions v ON v.id=c.document_version_id JOIN documents d ON d.id=v.document_id JOIN institutions i ON i.id=d.institution_id WHERE c.id=%s",
 "evidence-submissions": "SELECT i.id AS institution_id,i.region_id,c.application_id,i.institution_code,i.created_by FROM evidence_submissions e JOIN compliance_conditions c ON c.id=e.compliance_condition_id JOIN institutions i ON i.id=c.institution_id WHERE e.id=%s",
 "meeting-records": "SELECT i.id AS institution_id,i.region_id,a.id AS application_id,i.institution_code,i.created_by FROM evc_reports r JOIN evc_visits v ON v.id=r.evc_visit_id JOIN applications a ON a.id=v.application_id JOIN institutions i ON i.id=a.institution_id WHERE r.id=%s",
})

def within(row, assignment):
    scope, ident = assignment["scope_type"], assignment["scope_id"]
    return scope == "global" or (scope == "institution" and ident == row["institution_id"]) or (scope == "region" and ident == row["region_id"]) or (scope == "application" and ident == row["application_id"])


def check_request(request, subject, body):
    path = request.url.path.removeprefix(request.app.state.settings.api_prefix)
    with write_transaction(request.app.state.settings.database_write_url, subject) as connection:
        with connection.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT a.*,r.role_code FROM user_role_assignments a JOIN roles r ON r.id=a.role_id JOIN users u ON u.id=a.user_id WHERE u.id=%s AND u.identity_subject=%s AND u.status='active' AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (UUID(subject), subject))
            assignments = cur.fetchall()
            if not assignments: raise HTTPException(403)
            mutate = request.method not in {"GET", "HEAD", "OPTIONS"}
            if mutate:
                roles = allowed_roles(path)
                assignments = [a for a in assignments if role_name(a["role_code"]) in roles and not a["role_code"].endswith("_VIEWER")]
                if not assignments: raise HTTPException(403)
            if mutate and path.startswith("/users") and all(a["role_code"].startswith("DEMO_") for a in assignments):
                if isinstance(body,dict) and body.get("role_code") and not str(body["role_code"]).startswith("DEMO_"):
                    raise HTTPException(403)
            refs = []
            parts = path.strip("/").split("/")
            for ix, part in enumerate(parts[:-1]):
                if part in RESOURCES:
                    try: refs.append((part, UUID(parts[ix+1])))
                    except ValueError: pass
            if isinstance(body, dict):
                for key, table in {"institution_id":"institutions", "application_id":"applications", "document_id":"documents", "document_version_id":"document-versions", "evc_visit_id":"evc-visits", "condition_id":"compliance-conditions"}.items():
                    if body.get(key):
                        try: refs.append((table, UUID(str(body[key]))))
                        except ValueError: raise HTTPException(400) from None
                for key in ("document_version_ids", "version_ids"):
                    for value in body.get(key, []) or []:
                        try: refs.append(("document-versions", UUID(str(value))))
                        except ValueError: raise HTTPException(400) from None
            for table, ident in refs:
                cur.execute(RESOURCES[table], (ident,)); row = cur.fetchone()
                if row is None or not any(within(row,a) for a in assignments): raise HTTPException(404)
                if row.get("application_id") and all(role_name(a["role_code"]) == "SCRUTINY" for a in assignments):
                    cur.execute("SELECT assigned_user_id FROM assignments WHERE application_id=%s AND status IN ('active', 'assigned', 'pending')", (row["application_id"],))
                    assigned = cur.fetchall()
                    if assigned and not any(str(r["assigned_user_id"]) == str(subject) for r in assigned):
                        raise HTTPException(404)
                if all(a["role_code"].startswith("DEMO_") for a in assignments) and not (str(row["institution_code"]).startswith("DEMO-") or str(row["institution_code"]).startswith("INST-")):
                    cur.execute("SELECT 1 FROM user_role_assignments a JOIN roles r ON r.id=a.role_id WHERE a.user_id=%s AND r.role_code LIKE 'DEMO_%%'",(row["created_by"],))
                    if not cur.fetchone(): raise HTTPException(404)


async def authorize_request(request: Request):
    path = request.url.path
    prefix = request.app.state.settings.api_prefix
    if not path.startswith(prefix + "/"): return
    relative = path.removeprefix(prefix)
    # These handlers have their own complete, scoped identity/command boundary.
    if relative in {"/me", "/me/permissions", "/portal/snapshot", "/portal/commands", "/portal/documents", "/prototype/session", "/ocr/test-upload", "/ocr/sample-document", "/notification-provider-receipts", "/audit/verify-chain"}: return
    # Original foundation reads already use permission- and scope-filtered SQL.
    if request.method == "GET" and re.fullmatch(r"/(institutions|applications)(/[0-9a-fA-F-]{36})?", relative): return
    subject = await run_in_threadpool(get_verified_subject, request)
    body = None
    if request.method not in {"GET", "HEAD", "OPTIONS"} and "application/json" in request.headers.get("content-type", ""):
        try: body = await request.json()
        except ValueError: raise HTTPException(400) from None
    await run_in_threadpool(check_request, request, subject, body)
