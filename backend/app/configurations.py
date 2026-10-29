"""Typed, immutable-value configuration revisions with explicit publication.

This stores evaluation policy and its runtime catalogue projection. Publication
records the authenticated human; it does not certify an official APH policy.
"""
from datetime import date
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .outbox import enqueue
from .transactions import write_transaction

router = APIRouter(tags=["configuration"])

class StrictValues(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class AphValues(StrictValues):
    reference: str = Field(min_length=3, max_length=200)
    effectiveFrom: date
    sourceReference: str = Field(min_length=3, max_length=2000)

class DocumentTypeValues(StrictValues):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=100)
    supportsExpiry: bool
    maxSizeMb: int = Field(ge=1, le=100)
    allowedMimeTypes: list[Literal["application/pdf", "image/png", "image/jpeg"]] = Field(min_length=1)
    reminderDays: list[int] = Field(default_factory=list)

class RequirementValues(StrictValues):
    applicationType: str = Field(min_length=2, max_length=100)
    documentTypes: list[str] = Field(min_length=1, max_length=100)

class CommitteeValues(StrictValues):
    memberCount: Literal[4,5]
    durationMinutes: int = Field(ge=30, le=1440)
    availabilityFreshnessHours: int = Field(ge=1, le=8760)
    preparationLeadHours: int = Field(ge=0, le=8760)

class TemplateValues(StrictValues):
    code: str = Field(min_length=2, max_length=100)
    sections: list[str] = Field(min_length=1, max_length=100)

class RetentionValues(StrictValues):
    retentionDays: int = Field(ge=1, le=36500)

class NotificationValues(StrictValues):
    event: str = Field(min_length=2, max_length=100)
    channel: Literal["IN_APP", "EMAIL", "SMS", "WEBHOOK"]
    recipientRole: str = Field(min_length=2, max_length=100)
    enabled: bool

class EscalationValues(StrictValues):
    event: str = Field(min_length=2, max_length=100)
    thresholdMinutes: int = Field(ge=0, le=525600)
    recipientRole: str = Field(min_length=2, max_length=100)
    maxLevel: int = Field(ge=1, le=10)
    enabled: bool

class SettingValues(StrictValues):
    label: str = Field(min_length=2, max_length=200)
    enabled: bool

VALUE_MODELS = {"APH":AphValues,"DOCUMENT_TYPE":DocumentTypeValues,"DOCUMENT_REQUIREMENT":RequirementValues,
                "COMMITTEE":CommitteeValues,"TEMPLATE":TemplateValues,"RETENTION":RetentionValues,
                "NOTIFICATION":NotificationValues,"ESCALATION":EscalationValues,"SETTINGS":SettingValues}

def validate_values(category, values):
    if category not in VALUE_MODELS: raise HTTPException(422, detail="Unknown configuration category")
    try: parsed = VALUE_MODELS[category].model_validate(values).model_dump(mode="json")
    except ValidationError as exc: raise HTTPException(422, detail=str(exc)) from None
    if category == "DOCUMENT_TYPE" and any(type(day) is not int or day<0 or day>3650 for day in parsed["reminderDays"]):
        raise HTTPException(422, detail="Reminder days must be nonnegative integers")
    return parsed


def save_revision(cur, actor, source_id, values):
    source = None
    if source_id:
        cur.execute("SELECT * FROM public.configuration_revisions WHERE id=%s FOR UPDATE", (source_id,))
        source = cur.fetchone()
        # Existing normalized catalogues can be explicitly cloned into typed
        # revision families through the category supplied by the editor.
    category = source["category"] if source else values.get("category")
    body = validate_values(category, values.get("values"))
    name = str(values.get("name", "")).strip()
    if len(name)<2 or len(name)>200: raise HTTPException(422, detail="Configuration name is required")
    family = source["family_id"] if source else source_id or uuid4()
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (str(family),))
    cur.execute("SELECT COALESCE(MAX(version),0)+1 AS version FROM public.configuration_revisions WHERE family_id=%s", (family,))
    version = cur.fetchone()["version"]
    target = uuid4()
    cur.execute("INSERT INTO public.configuration_revisions(id,family_id,category,name,version,values,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s)", (target,family,category,name,version,Jsonb(body),actor))
    return target


def publish_revision(cur, actor, target, effective_from=None):
    cur.execute("SELECT * FROM public.configuration_revisions WHERE id=%s FOR UPDATE", (target,))
    row = cur.fetchone()
    if not row: raise HTTPException(404, detail="Save this catalogue as a typed draft before publication")
    if row["status"] != "draft": raise HTTPException(409, detail="Only a draft can be published")
    v = validate_values(row["category"],row["values"])
    effective = date.fromisoformat(effective_from) if effective_from else date.today()
    category, operational = row["category"], None
    if category in ("NOTIFICATION","ESCALATION"):
        cur.execute("SELECT id FROM public.roles WHERE role_code IN (%s,%s) ORDER BY CASE WHEN role_code=%s THEN 0 ELSE 1 END LIMIT 1", (v["recipientRole"],"DEMO_"+v["recipientRole"],v["recipientRole"]))
        role = cur.fetchone()
        if not role: raise HTTPException(422, detail="Recipient role is unavailable")
        if category == "NOTIFICATION":
            cur.execute("INSERT INTO public.notification_rules(event_code,channel,recipient_rule,template_version,enabled,version,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id", (v["event"],v["channel"].lower(),Jsonb({"role_code":v["recipientRole"]}),str(row["version"]),v["enabled"],row["version"],actor))
        else:
            cur.execute("INSERT INTO public.escalation_rules(event_code,threshold_minutes,recipient_role_id,action_type,enabled,version,created_by) VALUES(%s,%s,%s,'notify',%s,%s,%s) RETURNING id", (v["event"],v["thresholdMinutes"],role["id"],v["enabled"],row["version"],actor))
        operational = cur.fetchone()["id"]
    elif category == "APH":
        cur.execute("INSERT INTO public.aph_rule_sets(rule_set_code,title,source_reference,effective_from,status,created_by) VALUES(%s,%s,%s,%s,'published',%s) RETURNING id", (v["reference"]+":"+str(target),row["name"],v["sourceReference"],v["effectiveFrom"],actor))
        rule_set=cur.fetchone()["id"]
        cur.execute("INSERT INTO public.aph_rule_versions(rule_set_id,version_number,approved_by,approved_at,content_reference,created_by) VALUES(%s,%s,%s,now(),%s,%s) RETURNING id", (rule_set,row["version"],actor,v["sourceReference"],actor))
        operational=cur.fetchone()["id"]
    elif category == "DOCUMENT_TYPE":
        cur.execute("INSERT INTO public.document_types(document_type_code,name,supports_expiry,metadata_schema,version,created_by) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id", (v["code"]+"_V"+str(row["version"])+"_"+str(target)[:8],row["name"],v["supportsExpiry"],Jsonb(v),row["version"],actor))
        operational=cur.fetchone()["id"]
    elif category == "COMMITTEE":
        cur.execute("SELECT id FROM public.committee_types ORDER BY code LIMIT 1")
        kind=cur.fetchone()
        if not kind: raise HTTPException(409, detail="A committee type must be configured first")
        cur.execute("INSERT INTO public.committees(committee_type_id,name,status,configuration,version,created_by) VALUES(%s,%s,'active',%s,%s,%s) RETURNING id", (kind["id"],row["name"],Jsonb(v),row["version"],actor))
        operational=cur.fetchone()["id"]
    else:
        cur.execute("INSERT INTO public.system_settings(setting_key,setting_value,version,approved_by,effective_at,created_by) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id", (category+":"+str(target),Jsonb(v),row["version"],actor,effective,actor))
        operational=cur.fetchone()["id"]
    # Keep immutable values and all historical operational IDs. Supersession
    # changes visibility for future configuration selection only.
    cur.execute("UPDATE public.configuration_revisions SET status='superseded' WHERE family_id=%s AND status='published'", (row["family_id"],))
    cur.execute("UPDATE public.configuration_revisions SET status='published',effective_from=%s,operational_id=%s,approved_by=%s,approved_at=now() WHERE id=%s", (effective,operational,actor,target))
    return target


class ConfigurationDraft(BaseModel):
    category: str
    name: str = Field(min_length=2,max_length=200)
    values: dict
    source_id: UUID | None = None
    reason: str = Field(min_length=3,max_length=500)

class PublishConfiguration(BaseModel):
    effective_from: date
    reason: str = Field(min_length=3,max_length=500)

@router.get("/configurations")
def list_configurations(request: Request, subject: Annotated[str,Depends(get_verified_subject)]):
    _user(request,subject)
    with _read_connection(request.app.state.settings.database_url,subject) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM public.configuration_revisions ORDER BY family_id,version DESC")
            return {"data":[_serialize(row) for row in cur.fetchall()]}

@router.post("/configurations",status_code=201)
def create_configuration(payload:ConfigurationDraft,request:Request,subject:Annotated[str,Depends(get_verified_subject)]):
    from .portal_commands import execute_command,PortalCommand
    return execute_command(request,subject,PortalCommand(kind="config.save",id=payload.source_id,values=payload.model_dump(mode="json")))

@router.post("/configurations/{configuration_id}/publish")
def publish_configuration(configuration_id:UUID,payload:PublishConfiguration,request:Request,subject:Annotated[str,Depends(get_verified_subject)]):
    from .portal_commands import execute_command,PortalCommand
    return execute_command(request,subject,PortalCommand(kind="config.publish",id=configuration_id,values={"effectiveFrom":payload.effective_from.isoformat(),"reason":payload.reason}))
