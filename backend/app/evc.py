"""EVC visits, expert selection, availability, scheduling, and lifecycle tracking (PRD §§5.5, 7.3, 9.2, BR-06–11)."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .records import _cursor_id, _next_cursor
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid


router = APIRouter(tags=["evc"])


class CreateEvcVisitRequest(BaseModel):
    campus_id: UUID | None = None
    coordinator_user_id: UUID | None = None
    required_days: int = Field(30, ge=1, le=180)
    reason: str = Field("EVC visit initiated per regulatory workflow", min_length=3, max_length=500)


class CommitteeMemberSelectionItem(BaseModel):
    expert_user_id: UUID
    committee_role: str = Field(..., pattern=r"^(convener|member|subject_expert)$")


class SelectCommitteeMembersRequest(BaseModel):
    members: list[CommitteeMemberSelectionItem] = Field(..., min_length=1, max_length=10)
    reason: str = Field("Authorised committee expert selection", min_length=3, max_length=500)
    allow_coi_override: bool = False
    coi_override_reason: str | None = None


class SubmitExpertAvailabilityRequest(BaseModel):
    start_at: str
    end_at: str
    availability_status: str = Field("available", pattern=r"^(available|unavailable)$")
    source: str = Field("manual_entry", min_length=2, max_length=50)


class GenerateSlotRecommendationsRequest(BaseModel):
    search_horizon_days: int = Field(30, ge=1, le=90)
    visit_duration_hours: float = Field(8, ge=0.25, le=24)


class ConfirmScheduleRequest(BaseModel):
    slot_recommendation_id: UUID | None = None
    confirmed_start_at: str
    confirmed_end_at: str
    reason: str = Field("Confirm EVC visit schedule", min_length=3, max_length=500)


class RescheduleVisitRequest(BaseModel):
    new_start_at: str
    new_end_at: str
    reason: str = Field(..., min_length=3, max_length=500)


class CompleteVisitRequest(BaseModel):
    reason: str = Field("EVC visit completed on site", min_length=3, max_length=500)


def _aware(value) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("A timezone is required")
        return parsed.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Use a valid timestamp with a timezone") from None


def _merge(windows):
    merged = []
    for start, end in sorted(windows):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _subtract(windows, blocked):
    result = list(windows)
    for busy_start, busy_end in _merge(blocked):
        pieces = []
        for start, end in result:
            if busy_end <= start or busy_start >= end:
                pieces.append((start, end))
            else:
                if start < busy_start:
                    pieces.append((start, busy_start))
                if busy_end < end:
                    pieces.append((busy_end, end))
        result = pieces
    return result


def common_availability(participants, *, now, earliest, latest, freshness_hours):
    """Intersect fresh positive availability for every required participant.

    Negative windows always block; stale or missing positive windows never imply
    availability. Confirmed bookings are supplied as unavailable windows.
    """
    common = [(earliest, latest)] if earliest < latest else []
    missing = []
    cutoff = now - timedelta(hours=freshness_hours)
    for participant, rows in participants.items():
        available, busy = [], []
        for row in rows:
            start, end = _aware(row["start_at"]), _aware(row["end_at"])
            if row["availability_status"] != "available":
                busy.append((start, end))
            elif row.get("last_confirmed_at") and cutoff <= _aware(row["last_confirmed_at"]) <= now + timedelta(seconds=30):
                available.append((start, end))
        windows = _subtract(_merge(available), busy)
        if not windows:
            missing.append(str(participant))
        common = _merge((max(a, c), min(b, d)) for a, b in common for c, d in windows
                        if max(a, c) < min(b, d))
    return common, missing


def _scheduling_lock(cur):
    # The same transaction lock is used for committee/availability writes. It
    # serializes the check+confirm pair across visits with shared participants.
    cur.execute("SELECT pg_advisory_xact_lock(hashtext('aicte.evc.scheduling'))")


def _scheduling_context(cur, visit_id, now, horizon_days=90):
    cur.execute(
        "SELECT v.*, a.institution_id FROM public.evc_visits v "
        "JOIN public.applications a ON a.id=v.application_id WHERE v.id=%s FOR UPDATE OF v", (visit_id,))
    visit = cur.fetchone()
    if visit is None:
        raise HTTPException(status_code=404)
    if visit["status"] in ("completed", "cancelled"):
        raise HTTPException(status_code=409)
    cur.execute("SELECT configuration FROM public.committees WHERE status='active' ORDER BY version DESC, updated_at DESC LIMIT 1")
    policy_row = cur.fetchone()
    # Explicit illustrative prototype defaults when no configured rule exists.
    policy = {"memberCount": 5, "durationMinutes": 480, "availabilityFreshnessHours": 72, "preparationLeadHours": 24,
              **((policy_row or {}).get("configuration") or {})}
    if int(policy["memberCount"]) not in (4, 5) or not 0 < float(policy["durationMinutes"]) <= 1440 or float(policy["availabilityFreshnessHours"]) <= 0 or float(policy["preparationLeadHours"]) < 0:
        raise HTTPException(status_code=409, detail="Committee scheduling configuration is invalid")
    cur.execute(
        "SELECT m.expert_user_id,m.committee_role,p.eligibility_status,u.status AS user_status "
        "FROM public.evc_committee_members m JOIN public.users u ON u.id=m.expert_user_id "
        "LEFT JOIN public.expert_profiles p ON p.user_id=m.expert_user_id "
        "WHERE m.evc_visit_id=%s AND m.selection_status='selected'", (visit_id,))
    members = cur.fetchall()
    expert_ids = [m["expert_user_id"] for m in members]
    if len(set(expert_ids)) != int(policy["memberCount"]) or len(expert_ids) != len(set(expert_ids)) or sum(m["committee_role"] == "convener" for m in members) != 1:
        raise HTTPException(status_code=409, detail="Select the complete required committee with one convener")
    if any(m.get("eligibility_status") != "eligible" or m.get("user_status") != "active" for m in members):
        raise HTTPException(status_code=409, detail="Every selected expert must have an active eligible profile")
    earliest = now + timedelta(hours=float(policy["preparationLeadHours"]))
    latest = min(now + timedelta(days=horizon_days), _aware(visit["required_by"])) if visit.get("required_by") else now + timedelta(days=horizon_days)
    cur.execute(
        "SELECT expert_user_id,start_at,end_at,availability_status,last_confirmed_at FROM public.expert_availability "
        "WHERE expert_user_id=ANY(%s) AND superseded_at IS NULL AND end_at>%s AND start_at<%s", (expert_ids, earliest, latest))
    participants = {str(expert): [] for expert in expert_ids}
    for row in cur.fetchall():
        participants[str(row["expert_user_id"])].append(row)
    institution_key = f"institution:{visit['institution_id']}"
    cur.execute(
        "SELECT start_at,end_at,availability_status,last_confirmed_at FROM public.institution_availability "
        "WHERE institution_id=%s AND superseded_at IS NULL AND end_at>%s AND start_at<%s", (visit["institution_id"], earliest, latest))
    participants[institution_key] = cur.fetchall()
    cur.execute(
        "SELECT v.confirmed_start_at AS start_at,v.confirmed_end_at AS end_at,a.institution_id,m.expert_user_id "
        "FROM public.evc_visits v JOIN public.applications a ON a.id=v.application_id "
        "LEFT JOIN public.evc_committee_members m ON m.evc_visit_id=v.id AND m.selection_status='selected' "
        "WHERE v.id<>%s AND v.status='scheduled' AND v.confirmed_end_at>%s AND v.confirmed_start_at<%s "
        "AND (a.institution_id=%s OR m.expert_user_id=ANY(%s))",
        (visit_id, earliest, latest, visit["institution_id"], expert_ids))
    for booking in cur.fetchall():
        blocked = {**booking, "availability_status": "unavailable"}
        if booking["institution_id"] == visit["institution_id"]:
            participants[institution_key].append(blocked)
        if str(booking.get("expert_user_id")) in participants:
            participants[str(booking["expert_user_id"])].append(blocked)
    windows, missing = common_availability(participants, now=now, earliest=earliest, latest=latest,
                                           freshness_hours=float(policy["availabilityFreshnessHours"]))
    return visit, members, policy, windows, missing


@router.get("/evc-visits")
def list_evc_visits(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    status: Annotated[str | None, Query()] = None,
    application_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
):
    """Search and list EVC visits in scope with cursor pagination."""
    _ = _user(request, subject)
    after = _cursor_id(cursor)
    sql = (
        "SELECT v.id, v.application_id, v.campus_id, v.status, v.required_by, "
        "       v.confirmed_start_at, v.confirmed_end_at, v.completed_at, v.coordinator_user_id, "
        "       v.created_at, v.updated_at, a.application_number "
        "FROM public.evc_visits v "
        "JOIN public.applications a ON a.id = v.application_id "
        "WHERE 1=1 "
    )
    params: list[Any] = []
    if status is not None:
        sql += " AND v.status = %s "
        params.append(status)
    if application_id is not None:
        sql += " AND v.application_id = %s "
        params.append(application_id)
    if after is not None:
        sql += " AND v.id > %s "
        params.append(after)
    sql += " ORDER BY v.created_at DESC, v.id ASC LIMIT %s"
    params.append(limit + 1)

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = [_serialize(row) for row in cur.fetchall()]

    has_more = len(rows) > limit
    data = rows[:limit]
    return {
        "data": data,
        "page": {
            "limit": limit,
            "next_cursor": _next_cursor(data[-1]["id"]) if has_more else None,
        },
    }


@router.post("/applications/{application_id}/evc-visits", status_code=201)
def create_evc_visit(
    application_id: UUID,
    payload: CreateEvcVisitRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Create an EVC visit work item when application workflow demands inspection (PRD BR-06)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "evc.create_visit"
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
                # 1. Verify application exists and not closed
                cur.execute(
                    "SELECT id, status, campus_id, institution_id FROM public.applications WHERE id = %s",
                    (application_id,),
                )
                app = cur.fetchone()
                if app is None:
                    raise HTTPException(status_code=404)
                if app["status"] in ("approved", "rejected", "closed", "withdrawn"):
                    raise HTTPException(status_code=409)

                now = datetime.now(timezone.utc)
                required_by = now + timedelta(days=payload.required_days)
                campus_id = payload.campus_id or app["campus_id"]

                # 2. Insert EVC visit
                cur.execute(
                    "INSERT INTO public.evc_visits "
                    "(application_id, campus_id, status, required_by, coordinator_user_id, created_at, created_by, updated_at, updated_by) "
                    "VALUES (%s, %s, 'required', %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, application_id, campus_id, status, required_by, coordinator_user_id, created_at",
                    (application_id, campus_id, required_by, payload.coordinator_user_id, now, caller_uuid, now, caller_uuid),
                )
                visit = cur.fetchone()
                visit_id = visit["id"]

                # 3. Log visit event
                cur.execute(
                    "INSERT INTO public.evc_visit_events "
                    "(evc_visit_id, event_type, event_at, actor_user_id, reason, details, created_at) "
                    "VALUES (%s, 'VISIT_REQUIRED', %s, %s, %s, %s, %s)",
                    (visit_id, now, caller_uuid, payload.reason, Jsonb({"required_days": payload.required_days}), now),
                )

                # 4. Audit & Outbox
                audit_meta = {
                    "application_id": str(application_id),
                    "required_by": required_by.isoformat(),
                    "coordinator_user_id": str(payload.coordinator_user_id) if payload.coordinator_user_id else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="EVC_VISIT_CREATED",
                    entity_type="evc_visit",
                    entity_id=visit_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="EVC_VISIT_CREATED",
                    entity_type="evc_visit",
                    entity_id=visit_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(visit)
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


@router.get("/evc-visits/{visit_id}")
def get_evc_visit_detail(
    visit_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve full EVC visit details including selected committee members."""
    _ = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT v.id, v.application_id, v.campus_id, v.status, v.required_by, "
                "       v.confirmed_start_at, v.confirmed_end_at, v.completed_at, v.coordinator_user_id, "
                "       v.created_at, v.updated_at, a.application_number "
                "FROM public.evc_visits v "
                "JOIN public.applications a ON a.id = v.application_id "
                "WHERE v.id = %s",
                (visit_id,),
            )
            visit = cur.fetchone()
            if visit is None:
                raise HTTPException(status_code=404)

            # Committee members
            cur.execute(
                "SELECT m.id, m.expert_user_id, m.committee_role, m.selection_status, m.selected_at, "
                "       u.display_name, u.email "
                "FROM public.evc_committee_members m "
                "JOIN public.users u ON u.id = m.expert_user_id "
                "WHERE m.evc_visit_id = %s AND m.selection_status = 'selected'",
                (visit_id,),
            )
            members = [_serialize(row) for row in cur.fetchall()]

            visit_data = _serialize(visit)
            visit_data["committee_members"] = members
            return visit_data


def screen_expert_coi(cur, expert_user_id: UUID, institution_id: UUID | None, region_id: UUID | None) -> dict[str, Any]:
    """Evaluate Conflict of Interest (COI) per PRD §5.5, BR-07, BR-13."""
    cur.execute(
        "SELECT u.id, u.display_name, u.email, u.status AS user_status, "
        "       p.id AS profile_id, p.eligibility_status, p.expertise "
        "FROM public.users u "
        "LEFT JOIN public.expert_profiles p ON p.user_id = u.id "
        "WHERE u.id = %s",
        (expert_user_id,),
    )
    user_row = cur.fetchone()
    if not user_row:
        return {
            "expert_user_id": str(expert_user_id),
            "coi_status": "CONFLICT_DETECTED",
            "is_eligible": False,
            "conflict_reasons": ["Expert user not found in directory."],
        }

    conflicts = []
    if user_row.get("user_status") and user_row.get("user_status") != "active":
        conflicts.append(f"Ineligibility: User account status is '{user_row.get('user_status')}' (active required).")
    if user_row.get("eligibility_status") and user_row.get("eligibility_status") != "eligible":
        conflicts.append(f"Ineligibility: Expert profile eligibility is '{user_row.get('eligibility_status')}' (eligible required).")

    if region_id:
        cur.execute(
            "SELECT 1 FROM public.user_role_assignments a "
            "WHERE a.user_id = %s AND a.status = 'active' "
            "  AND ((a.scope_type = 'region' AND a.scope_id = %s) "
            "       OR (a.scope_type = 'institution' AND a.scope_id IN ( "
            "           SELECT id FROM public.institutions WHERE region_id = %s "
            "       )))",
            (expert_user_id, region_id, region_id),
        )
        if cur.fetchone():
            conflicts.append("Regional Jurisdiction Conflict: Expert has active roles or affiliations in the same regional jurisdiction.")

    if institution_id:
        cur.execute(
            "SELECT 1 FROM public.user_role_assignments a "
            "WHERE a.user_id = %s AND a.status = 'active' "
            "  AND a.scope_type = 'institution' AND a.scope_id = %s",
            (expert_user_id, institution_id),
        )
        if cur.fetchone():
            conflicts.append("Institutional Affiliation Conflict: Expert holds direct role assignment or affiliation with applicant institution.")

    past_count = 0
    if institution_id:
        cur.execute(
            "SELECT count(*) AS cnt FROM public.evc_visits v "
            "JOIN public.evc_committee_members m ON m.evc_visit_id = v.id "
            "JOIN public.applications a ON a.id = v.application_id "
            "WHERE a.institution_id = %s AND m.expert_user_id = %s "
            "  AND m.selection_status = 'selected' "
            "  AND v.status IN ('completed', 'scheduled', 'confirmed') "
            "  AND v.confirmed_start_at >= now() - INTERVAL '3 years'",
            (institution_id, expert_user_id),
        )
        past_row = cur.fetchone()
        past_count = (past_row["cnt"] if isinstance(past_row, dict) else past_row[0]) if past_row else 0
        if past_count > 0:
            conflicts.append(f"Inspection History Conflict: Expert conducted {past_count} EVC inspection(s) for this institution within past 36 months.")

    is_eligible = len(conflicts) == 0
    coi_status = "CLEAR" if is_eligible else "CONFLICT_DETECTED"

    return {
        "expert_user_id": str(expert_user_id),
        "expert_profile_id": str(user_row.get("profile_id")) if user_row.get("profile_id") else None,
        "display_name": user_row.get("display_name"),
        "email": user_row.get("email"),
        "expertise": user_row.get("expertise") or [],
        "user_status": user_row.get("user_status"),
        "eligibility_status": user_row.get("eligibility_status"),
        "coi_status": coi_status,
        "is_eligible": is_eligible,
        "conflict_reasons": conflicts,
        "past_visits_count": past_count,
    }


@router.get("/evc-visits/{visit_id}/coi-screening")
def get_evc_coi_screening(
    visit_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Automated Conflict of Interest (COI) screening for all candidate experts (PRD §5.5, BR-07, BR-13)."""
    _ = _user(request, subject)
    read_url = request.app.state.settings.database_url
    with _read_connection(read_url, subject) as connection:
        with connection.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT v.id, a.institution_id, i.official_name, i.institution_code, i.region_id, r.name AS region_name "
                "FROM public.evc_visits v "
                "JOIN public.applications a ON a.id = v.application_id "
                "JOIN public.institutions i ON i.id = a.institution_id "
                "LEFT JOIN public.regions r ON r.id = i.region_id "
                "WHERE v.id = %s",
                (visit_id,),
            )
            visit_info = cur.fetchone()
            if not visit_info:
                raise HTTPException(status_code=404, detail="EVC visit not found")

            cur.execute(
                "SELECT u.id "
                "FROM public.users u "
                "JOIN public.expert_profiles p ON p.user_id = u.id "
                "ORDER BY u.display_name ASC"
            )
            candidates = cur.fetchall()

            screened = []
            for row in candidates:
                screened.append(screen_expert_coi(cur, row["id"], visit_info["institution_id"], visit_info["region_id"]))

            clear_count = sum(1 for c in screened if c["coi_status"] == "CLEAR")
            return {
                "visit_id": str(visit_id),
                "institution": {
                    "id": str(visit_info["institution_id"]),
                    "name": visit_info["official_name"],
                    "code": visit_info["institution_code"],
                    "region_id": str(visit_info["region_id"]) if visit_info["region_id"] else None,
                    "region_name": visit_info["region_name"],
                },
                "summary": {
                    "total_screened": len(screened),
                    "clear_count": clear_count,
                    "conflict_count": len(screened) - clear_count,
                    "rule_enforcement": "PRD §5.5 BR-07 (Regional independence, zero 36-month history, institutional detachment)",
                },
                "candidates": screened,
            }


@router.put("/evc-visits/{visit_id}/committee-members")
def select_committee_members(
    visit_id: UUID,
    payload: SelectCommitteeMembersRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Record authorized human officer selection of committee experts (PRD BR-07, BR-08)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "evc.select_members"
    body_dict = payload.model_dump(mode="json")

    # Verify distinct experts
    expert_ids = [m.expert_user_id for m in payload.members]
    if len(expert_ids) != len(set(expert_ids)):
        raise HTTPException(status_code=400, detail="Committee member selection must not contain duplicates")
    if sum(member.committee_role == "convener" for member in payload.members) != 1:
        raise HTTPException(422, detail="Select exactly one committee convener")

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
                _scheduling_lock(cur)
                # 1. Fetch visit
                cur.execute(
                    "SELECT v.id, v.status, a.institution_id, i.region_id "
                    "FROM public.evc_visits v "
                    "LEFT JOIN public.applications a ON a.id = v.application_id "
                    "LEFT JOIN public.institutions i ON i.id = a.institution_id "
                    "WHERE v.id = %s",
                    (visit_id,),
                )
                visit = cur.fetchone()
                if visit is None:
                    raise HTTPException(status_code=404)
                if visit["status"] in ("scheduled", "completed", "cancelled"):
                    raise HTTPException(status_code=409)

                now = datetime.now(timezone.utc)

                # 2. Mark any existing active members as replaced
                cur.execute("UPDATE public.user_role_assignments a SET status='revoked',updated_at=%s,updated_by=%s "
                            "FROM public.roles r WHERE a.role_id=r.id AND r.role_code IN ('EVC_EXPERT','DEMO_EVC_EXPERT') "
                            "AND a.scope_type='application' AND a.scope_id=(SELECT application_id FROM public.evc_visits WHERE id=%s) "
                            "AND a.user_id IN (SELECT expert_user_id FROM public.evc_committee_members WHERE evc_visit_id=%s AND selection_status='selected') "
                            "AND a.status='active' AND NOT(a.user_id=ANY(%s))", (now,caller_uuid,visit_id,visit_id,expert_ids))
                cur.execute(
                    "UPDATE public.evc_committee_members "
                    "SET selection_status = 'replaced', replacement_reason = %s "
                    "WHERE evc_visit_id = %s AND selection_status = 'selected'",
                    (payload.reason, visit_id),
                )

                # 2.5 Conflict of Interest (COI) Screening (PRD §5.5, BR-07, BR-13)
                coi_overridden = False
                inst_id = visit.get("institution_id")
                reg_id = visit.get("region_id")
                if inst_id:
                    for m in payload.members:
                        coi = screen_expert_coi(cur, m.expert_user_id, inst_id, reg_id)
                        if coi["coi_status"] != "CLEAR":
                            if not payload.allow_coi_override:
                                reasons_str = "; ".join(coi["conflict_reasons"])
                                raise HTTPException(
                                    status_code=409,
                                    detail=f"Conflict of interest detected for expert {coi.get('display_name') or m.expert_user_id}: {reasons_str}. Authorised officer override required.",
                                )
                            if not payload.coi_override_reason or len(payload.coi_override_reason.strip()) < 5:
                                raise HTTPException(
                                    status_code=422,
                                    detail="A substantive override reason (min 5 characters) is required to bypass a Conflict of Interest flag.",
                                )
                            coi_overridden = True

                # 3. Insert newly selected members
                saved_members = []
                for m in payload.members:
                    # Check expert user exists
                    cur.execute("SELECT u.id FROM public.users u JOIN public.expert_profiles p ON p.user_id=u.id WHERE u.id = %s AND u.status='active' AND p.eligibility_status='eligible'", (m.expert_user_id,))
                    if cur.fetchone() is None:
                        raise HTTPException(status_code=400, detail=f"User {m.expert_user_id} not found")

                    cur.execute(
                        "INSERT INTO public.evc_committee_members "
                        "(evc_visit_id, expert_user_id, committee_role, selection_status, selected_by, selected_at, created_at) "
                        "VALUES (%s, %s, %s, 'selected', %s, %s, %s) "
                        "RETURNING id, evc_visit_id, expert_user_id, committee_role, selection_status, selected_at",
                        (visit_id, m.expert_user_id, m.committee_role, caller_uuid, now, now),
                    )
                    saved_members.append(_serialize(cur.fetchone()))
                    # Committee selection grants only this application's existing
                    # expert role; replacement revokes that case scope atomically.
                    cur.execute("INSERT INTO public.user_role_assignments(user_id,role_id,scope_type,scope_id,valid_from,status,created_by) "
                                "SELECT %s,g.role_id,'application',v.application_id,%s,'active',%s FROM public.evc_visits v "
                                "JOIN LATERAL(SELECT a.role_id FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id "
                                "WHERE a.user_id=%s AND a.status='active' AND r.role_code IN ('EVC_EXPERT','DEMO_EVC_EXPERT') "
                                "AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now()) LIMIT 1) g ON true "
                                "WHERE v.id=%s AND NOT EXISTS(SELECT 1 FROM public.user_role_assignments a WHERE a.user_id=%s AND a.role_id=g.role_id "
                                "AND a.scope_type='application' AND a.scope_id=v.application_id AND a.status='active' AND (a.valid_until IS NULL OR a.valid_until>now()))",
                                (m.expert_user_id,now,caller_uuid,m.expert_user_id,visit_id,m.expert_user_id))

                # 4. Advance visit status to committee_selection or scheduling
                cur.execute(
                    "UPDATE public.evc_visits "
                    "SET status = 'committee_selection', updated_at = %s, updated_by = %s "
                    "WHERE id = %s",
                    (now, caller_uuid, visit_id),
                )

                # 5. Log visit event
                cur.execute(
                    "INSERT INTO public.evc_visit_events "
                    "(evc_visit_id, event_type, event_at, actor_user_id, reason, details, created_at) "
                    "VALUES (%s, 'COMMITTEE_SELECTED', %s, %s, %s, %s, %s)",
                    (visit_id, now, caller_uuid, payload.reason, Jsonb({"members_count": len(saved_members), "coi_override": coi_overridden, "coi_override_reason": payload.coi_override_reason if coi_overridden else None}), now),
                )

                # 6. Audit & Outbox
                audit_meta = {
                    "visit_id": str(visit_id),
                    "members_count": len(saved_members),
                    "coi_override": coi_overridden,
                    "coi_override_reason": payload.coi_override_reason if coi_overridden else None,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="EVC_COMMITTEE_SELECTED",
                    entity_type="evc_visit",
                    entity_id=visit_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="EVC_COMMITTEE_SELECTED",
                    entity_type="evc_visit",
                    entity_id=visit_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = {"visit_id": visit_id, "members": saved_members}
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


@router.post("/experts/{expert_id}/availability", status_code=201)
def submit_expert_availability(
    expert_id: UUID,
    payload: SubmitExpertAvailabilityRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Record expert availability window with source and freshness (PRD BR-09)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    start_dt = datetime.fromisoformat(payload.start_at)
    end_dt = datetime.fromisoformat(payload.end_at)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_at must be strictly greater than start_at")

    now = datetime.now(timezone.utc)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT id FROM public.users WHERE id = %s", (expert_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404)

                cur.execute(
                    "INSERT INTO public.expert_availability "
                    "(expert_user_id, start_at, end_at, availability_status, source, last_confirmed_at, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, expert_user_id, start_at, end_at, availability_status, source, last_confirmed_at",
                    (expert_id, start_dt, end_dt, payload.availability_status, payload.source, now, now),
                )
                avail = cur.fetchone()

        return _serialize(avail)
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.get("/experts/{expert_id}/availability")
def get_expert_availability(
    expert_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve availability windows for an expert."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, expert_user_id, start_at, end_at, availability_status, source, last_confirmed_at, created_at "
        "FROM public.expert_availability WHERE expert_user_id = %s ORDER BY start_at ASC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (expert_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.post("/evc-visits/{visit_id}/slot-recommendations", status_code=201)
def generate_slot_recommendations(visit_id: UUID, payload: GenerateSlotRecommendationsRequest, request: Request, subject: Annotated[str, Depends(get_verified_subject)]):
    caller = _user(request, subject)
    now = datetime.now(timezone.utc)
    try:
        with write_transaction(request.app.state.settings.database_write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                _scheduling_lock(cur)
                visit, members, policy, windows, missing = _scheduling_context(cur, visit_id, now, payload.search_horizon_days)
                if visit['status'] == 'scheduled':
                    raise HTTPException(409, detail='Postpone the confirmed visit before generating new proposals')
                duration = timedelta(minutes=float(policy['durationMinutes']))
                if abs(payload.visit_duration_hours * 60 - duration.total_seconds() / 60) > 0.001:
                    raise HTTPException(400, detail='Duration must match the configured committee rule')
                cur.execute('UPDATE public.slot_recommendations SET expires_at=%s WHERE evc_visit_id=%s AND expires_at>%s', (now, visit_id, now))
                candidates = []
                expires_at = now + timedelta(hours=min(24, float(policy['availabilityFreshnessHours'])))
                for window_start, window_end in windows:
                    slot_start = window_start
                    while slot_start + duration <= window_end and len(candidates) < 3:
                        slot_end = slot_start + duration
                        explanation = f'Fresh availability intersects for all {len(members)} selected experts and the institution; no overlapping booking; before deadline. Rechecked at confirmation.'
                        cur.execute("INSERT INTO public.slot_recommendations (evc_visit_id,start_at,end_at,rank,feasibility_status,explanation,availability_snapshot_at,expires_at,created_at,created_by) VALUES (%s,%s,%s,%s,'feasible',%s,%s,%s,%s,%s) RETURNING id,evc_visit_id,start_at,end_at,rank,feasibility_status,explanation,expires_at",(visit_id,slot_start,slot_end,len(candidates)+1,explanation,now,expires_at,now,_to_uuid(caller['id'])))
                        candidates.append(_serialize(cur.fetchone()))
                        slot_start = slot_end
                if candidates:
                    cur.execute("UPDATE public.evc_visits SET status='scheduling',updated_at=%s,updated_by=%s WHERE id=%s",(now,_to_uuid(caller['id']),visit_id))
        blockers = [f'Missing or stale availability: {p}' for p in missing]
        if not candidates and not blockers: blockers = ['No common window satisfies duration, preparation time, deadline and booking constraints.']
        return {'recommendations':candidates,'blockers':blockers}
    except UnsafeWriteConnection:
        raise HTTPException(503)


@router.get("/evc-visits/{visit_id}/slot-recommendations")
def list_slot_recommendations(
    visit_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List generated slot recommendations for a visit."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, evc_visit_id, start_at, end_at, rank, feasibility_status, explanation, expires_at, created_at "
        "FROM public.slot_recommendations WHERE evc_visit_id = %s ORDER BY rank ASC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (visit_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.post("/evc-visits/{visit_id}/confirm-schedule")
def confirm_evc_schedule(visit_id: UUID, payload: ConfirmScheduleRequest, request: Request, subject: Annotated[str, Depends(get_verified_subject)], idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None):
    caller = _user(request, subject)
    caller_uuid = _to_uuid(caller['id'])
    corr_uuid = _to_uuid(getattr(request.state, 'correlation_id', None))
    operation = 'evc.confirm_schedule'
    body_dict = payload.model_dump(mode='json')
    start_dt, end_dt = _aware(payload.confirmed_start_at), _aware(payload.confirmed_end_at)
    if end_dt <= start_dt: raise HTTPException(400)
    try:
        with write_transaction(request.app.state.settings.database_write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                now = datetime.now(timezone.utc)
                _scheduling_lock(cur)
                if idempotency_key:
                    try:
                        cached=find_result(cur,actor_id=caller_uuid,operation=operation,raw_key=idempotency_key,body=body_dict)
                        if cached is not None: return cached[1]
                    except (IdempotencyConflict,IdempotencyExpired): raise HTTPException(409)
                visit,members,policy,windows,missing = _scheduling_context(cur,visit_id,now)
                if visit['status'] == 'scheduled': raise HTTPException(409,detail='The visit already has a confirmed schedule')
                if end_dt-start_dt != timedelta(minutes=float(policy['durationMinutes'])): raise HTTPException(400,detail='Duration does not match the configured committee rule')
                if payload.slot_recommendation_id:
                    cur.execute('SELECT start_at,end_at,expires_at,feasibility_status FROM public.slot_recommendations WHERE id=%s AND evc_visit_id=%s FOR UPDATE',(payload.slot_recommendation_id,visit_id))
                    proposal=cur.fetchone()
                    if not proposal or proposal['feasibility_status'] != 'feasible' or _aware(proposal['expires_at']) <= now: raise HTTPException(412,detail='Proposal expired or unavailable; generate fresh recommendations')
                    if _aware(proposal['start_at']) != start_dt or _aware(proposal['end_at']) != end_dt: raise HTTPException(400,detail='Requested times differ from selected proposal')
                if missing or not any(a <= start_dt and end_dt <= b for a,b in windows): raise HTTPException(409,detail='Fresh availability, deadline or participant booking constraints no longer permit this slot')
                cur.execute("UPDATE public.evc_visits SET status='scheduled',confirmed_start_at=%s,confirmed_end_at=%s,updated_at=%s,updated_by=%s WHERE id=%s RETURNING id,application_id,status,confirmed_start_at,confirmed_end_at",(start_dt,end_dt,now,caller_uuid,visit_id))
                updated=cur.fetchone()
                for member in members:
                    cur.execute("INSERT INTO public.evc_invitations (evc_visit_id,recipient_user_id,sent_at,response_status,delivery_status,created_at,created_by) VALUES (%s,%s,NULL,'pending','pending',%s,%s)",(visit_id,member['expert_user_id'],now,caller_uuid))
                metadata={'visit_id':str(visit_id),'start_at':start_dt.isoformat(),'end_at':end_dt.isoformat(),'invitations_pending':len(members)}
                cur.execute("INSERT INTO public.evc_visit_events (evc_visit_id,event_type,event_at,actor_user_id,reason,details,created_at) VALUES (%s,'SCHEDULE_CONFIRMED',%s,%s,%s,%s,%s)",(visit_id,now,caller_uuid,payload.reason,Jsonb(metadata),now))
                append_event(cur,actor_id=caller_uuid,action='EVC_SCHEDULE_CONFIRMED',entity_type='evc_visit',entity_id=visit_id,correlation_id=corr_uuid,reason=payload.reason,metadata=metadata)
                enqueue(cur,event_type='EVC_SCHEDULE_CONFIRMED',entity_type='evc_visit',entity_id=visit_id,payload=metadata,correlation_id=corr_uuid)
                result=_serialize(updated)
                if idempotency_key: store_result(cur,actor_id=caller_uuid,operation=operation,raw_key=idempotency_key,body=body_dict,http_status=200,response_json=result,expires_at=now+timedelta(days=1))
        return result
    except UnsafeWriteConnection: raise HTTPException(503)


@router.post("/evc-visits/{visit_id}/complete")
def complete_evc_visit(
    visit_id: UUID,
    payload: CompleteVisitRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Record verified on-site visit completion with timestamps."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "evc.complete_visit"
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
                _scheduling_lock(cur)
                cur.execute("SELECT id, status, confirmed_end_at FROM public.evc_visits WHERE id = %s FOR UPDATE", (visit_id,))
                visit = cur.fetchone()
                if visit is None:
                    raise HTTPException(status_code=404)
                now = datetime.now(timezone.utc)
                if visit["status"] != "scheduled" or not visit.get("confirmed_end_at") or _aware(visit["confirmed_end_at"]) > now:
                    raise HTTPException(409, detail="Only a confirmed visit whose scheduled period has ended can be completed")
                cur.execute(
                    "UPDATE public.evc_visits "
                    "SET status = 'completed', completed_at = %s, updated_at = %s, updated_by = %s "
                    "WHERE id = %s "
                    "RETURNING id, status, completed_at",
                    (now, now, caller_uuid, visit_id),
                )
                updated = cur.fetchone()

                cur.execute(
                    "INSERT INTO public.evc_visit_events "
                    "(evc_visit_id, event_type, event_at, actor_user_id, reason, details, created_at) "
                    "VALUES (%s, 'VISIT_COMPLETED', %s, %s, %s, '{}', %s)",
                    (visit_id, now, caller_uuid, payload.reason, now),
                )

                audit_meta = {"visit_id": str(visit_id), "completed_at": now.isoformat()}
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="EVC_VISIT_COMPLETED",
                    entity_type="evc_visit",
                    entity_id=visit_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="EVC_VISIT_COMPLETED",
                    entity_type="evc_visit",
                    entity_id=visit_id,
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


@router.get("/evc-visits/{visit_id}/events")
def list_evc_visit_events(
    visit_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve full audit history and lifecycle events for an EVC visit."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, evc_visit_id, event_type, event_at, actor_user_id, reason, details, created_at "
        "FROM public.evc_visit_events WHERE evc_visit_id = %s ORDER BY event_at ASC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (visit_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}
