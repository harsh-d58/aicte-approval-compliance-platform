"""Institutional compliance, undertakings, evidence submission, and human verification (PRD §§5.5, 7.4, 9.2, 13.3, BR-14)."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
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


router = APIRouter(tags=["compliance"])


@contextmanager
def compliance_transaction(url, subject):
    """Keep the cursor open for the whole atomic compliance operation."""
    with write_transaction(url, subject) as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            yield cursor


class CreateConditionRequest(BaseModel):
    institution_id: UUID
    application_id: UUID | None = None
    source_approval_id: UUID | None = None
    condition_code: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=3, max_length=2000)
    due_at: datetime | None = None
    verification_role_id: UUID | None = None


class SubmitEvidenceRequest(BaseModel):
    document_version_ids: list[UUID] = Field(..., min_length=1)
    remarks: str | None = Field(None, max_length=1000)


class VerifyEvidenceRequest(BaseModel):
    result: str = Field(..., pattern=r"^(accepted|rejected|incomplete|needs_clarification)$")
    comments: str = Field(..., min_length=3, max_length=2000)


class CloseConditionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class ReopenConditionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


@router.post("/compliance-conditions", status_code=201)
def create_compliance_condition(
    payload: CreateConditionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Create an undertaking or compliance condition bound to an application or approval decision."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    if not payload.application_id and not payload.source_approval_id:
        raise HTTPException(status_code=400, detail="Either application_id or source_approval_id must be provided")

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "compliance.create_condition"
    body_dict = payload.model_dump(mode="json")

    now = datetime.now(timezone.utc)
    condition_id = uuid4()

    try:
        with compliance_transaction(write_url, caller["subject"]) as cur:
            if idempotency_key:
                try:
                    prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                    if prior:
                        return prior[1]
                except (IdempotencyConflict, IdempotencyExpired) as e:
                    raise HTTPException(status_code=409)

            cur.execute(
                "INSERT INTO public.compliance_conditions "
                "(id, institution_id, application_id, source_approval_id, condition_code, description, "
                "due_at, status, verification_role_id, created_at, created_by, updated_at, updated_by, version) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, %s, %s, 1) "
                "RETURNING id, institution_id, application_id, source_approval_id, condition_code, "
                "description, due_at, status, verification_role_id, created_at, version",
                (
                    condition_id,
                    payload.institution_id,
                    payload.application_id,
                    payload.source_approval_id,
                    payload.condition_code,
                    payload.description,
                    payload.due_at,
                    payload.verification_role_id,
                    now,
                    caller_uuid,
                    now,
                    caller_uuid,
                ),
            )
            created = cur.fetchone()

            audit_meta = {
                "condition_code": payload.condition_code,
                "institution_id": str(payload.institution_id),
                "application_id": str(payload.application_id) if payload.application_id else None,
            }
            append_event(
                cur,
                actor_id=caller_uuid,
                action="COMPLIANCE_CONDITION_CREATED",
                entity_type="compliance_condition",
                entity_id=condition_id,
                correlation_id=corr_uuid,
                reason="Created statutory compliance condition",
                metadata=audit_meta,
            )
            enqueue(
                cur,
                event_type="COMPLIANCE_CONDITION_CREATED",
                entity_type="compliance_condition",
                entity_id=condition_id,
                payload=audit_meta,
                correlation_id=corr_uuid,
            )

            res = _serialize(dict(created))
            if idempotency_key:
                store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=201, response_json=res, expires_at=now + timedelta(days=1))
            return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.get("/compliance-conditions")
def list_compliance_conditions(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    institution_id: Annotated[UUID | None, Query()] = None,
    application_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query()] = None,
):
    """List compliance conditions with cursor pagination and scope filtering."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    query = (
        "SELECT id, institution_id, application_id, source_approval_id, condition_code, "
        "description, due_at, status, verification_role_id, created_at, version "
        "FROM public.compliance_conditions WHERE 1=1 "
    )
    params: list[Any] = []

    if institution_id:
        query += "AND institution_id = %s "
        params.append(institution_id)
    if application_id:
        query += "AND application_id = %s "
        params.append(application_id)
    if status:
        query += "AND status = %s "
        params.append(status)

    if cursor:
        query += "AND id > %s "
        params.append(cursor)

    query += "ORDER BY id ASC LIMIT %s"
    params.append(limit + 1)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = str(items[-1]["id"]) if has_more and items else None

    return {
        "data": [_serialize(dict(r)) for r in items],
        "page": {
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.get("/compliance-conditions/{condition_id}")
def get_compliance_condition(
    condition_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve details of a compliance condition, numbered evidence submissions, and verifications."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, institution_id, application_id, source_approval_id, condition_code, "
                "description, due_at, status, verification_role_id, created_at, version "
                "FROM public.compliance_conditions WHERE id = %s",
                (condition_id,),
            )
            condition = cur.fetchone()
            if not condition:
                raise HTTPException(status_code=404, detail="Compliance condition not found")

            # Fetch submissions
            cur.execute(
                "SELECT s.id, s.compliance_condition_id, s.submitted_by, s.submitted_at, "
                "s.submission_number, s.status, s.response_to_verification_id, s.created_at "
                "FROM public.evidence_submissions s "
                "WHERE s.compliance_condition_id = %s "
                "ORDER BY s.submission_number ASC",
                (condition_id,),
            )
            submissions = cur.fetchall()

            enriched_submissions = []
            for sub in submissions:
                sub_dict = dict(sub)
                cur.execute(
                    "SELECT document_version_id FROM public.evidence_submission_files "
                    "WHERE evidence_submission_id = %s",
                    (sub["id"],),
                )
                sub_dict["files"] = [str(f["document_version_id"]) for f in cur.fetchall()]

                cur.execute(
                    "SELECT id, evidence_submission_id, reviewer_user_id, result, comments, verified_at, created_at "
                    "FROM public.compliance_verifications "
                    "WHERE evidence_submission_id = %s "
                    "ORDER BY verified_at DESC",
                    (sub["id"],),
                )
                sub_dict["verifications"] = [_serialize(dict(v)) for v in cur.fetchall()]
                enriched_submissions.append(_serialize(sub_dict))

            res = _serialize(dict(condition))
            res["submissions"] = enriched_submissions
            return res


@router.post("/compliance-conditions/{condition_id}/evidence-submissions", status_code=201)
def submit_condition_evidence(
    condition_id: UUID,
    payload: SubmitEvidenceRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Submit numbered evidence for a compliance condition linking immutable document versions."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "compliance.submit_evidence"
    body_dict = payload.model_dump(mode="json")
    now = datetime.now(timezone.utc)
    submission_id = uuid4()
    if len(set(payload.document_version_ids)) != len(payload.document_version_ids):
        raise HTTPException(422, detail="Each evidence document version may be linked only once")

    try:
        with compliance_transaction(write_url, caller["subject"]) as cur:
            if idempotency_key:
                try:
                    prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                    if prior:
                        return prior[1]
                except (IdempotencyConflict, IdempotencyExpired) as e:
                    raise HTTPException(status_code=409)

            cur.execute(
                "SELECT id, institution_id, application_id, status, version FROM public.compliance_conditions WHERE id = %s FOR UPDATE",
                (condition_id,),
            )
            condition = cur.fetchone()
            if not condition:
                raise HTTPException(status_code=404, detail="Compliance condition not found")

            if condition["status"] in ("compliant", "closed"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot submit evidence for condition in '{condition['status']}' state",
                )

            # Determine next submission number
            cur.execute(
                "SELECT COALESCE(MAX(submission_number), 0) + 1 AS next_sub_num "
                "FROM public.evidence_submissions WHERE compliance_condition_id = %s",
                (condition_id,),
            )
            next_sub_num = cur.fetchone()["next_sub_num"]

            # Validate document versions exist
            for doc_ver_id in payload.document_version_ids:
                cur.execute(
                    "SELECT v.id FROM public.document_versions v JOIN public.documents d ON d.id=v.document_id "
                    "WHERE v.id = %s AND d.institution_id=%s "
                    "AND (d.application_id IS NULL OR d.application_id=%s)",
                    (doc_ver_id, condition["institution_id"], condition["application_id"]),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail=f"Document version {doc_ver_id} not found")

            cur.execute(
                "INSERT INTO public.evidence_submissions "
                "(id, compliance_condition_id, submitted_by, submitted_at, submission_number, status, created_at) "
                "VALUES (%s, %s, %s, %s, %s, 'submitted', %s) "
                "RETURNING id, compliance_condition_id, submitted_by, submitted_at, submission_number, status, created_at",
                (submission_id, condition_id, caller_uuid, now, next_sub_num, now),
            )
            sub_row = cur.fetchone()

            for doc_ver_id in payload.document_version_ids:
                cur.execute(
                    "INSERT INTO public.evidence_submission_files "
                    "(evidence_submission_id, document_version_id, created_at) "
                    "VALUES (%s, %s, %s)",
                    (submission_id, doc_ver_id, now),
                )

            # Transition condition status to evidence_submitted
            cur.execute(
                "UPDATE public.compliance_conditions "
                "SET status = 'evidence_submitted', updated_at = %s, updated_by = %s, version = version + 1 "
                "WHERE id = %s",
                (now, caller_uuid, condition_id),
            )

            audit_meta = {
                "condition_id": str(condition_id),
                "submission_id": str(submission_id),
                "submission_number": next_sub_num,
                "document_version_ids": [str(x) for x in payload.document_version_ids],
                "remarks": payload.remarks,
            }
            append_event(
                cur,
                actor_id=caller_uuid,
                action="EVIDENCE_SUBMITTED",
                entity_type="evidence_submission",
                entity_id=submission_id,
                correlation_id=corr_uuid,
                reason="Institutional evidence submission",
                metadata=audit_meta,
            )
            enqueue(
                cur,
                event_type="EVIDENCE_SUBMITTED",
                entity_type="evidence_submission",
                entity_id=submission_id,
                payload=audit_meta,
                correlation_id=corr_uuid,
            )

            res = _serialize(dict(sub_row))
            res["files"] = [str(x) for x in payload.document_version_ids]
            if idempotency_key:
                store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=201, response_json=res, expires_at=now + timedelta(days=1))
            return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.post("/evidence-submissions/{submission_id}/verifications", status_code=201)
def verify_evidence_submission(
    submission_id: UUID,
    payload: VerifyEvidenceRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Statutory human officer verification of evidence submission (BR-14: Evidence alone does not equal compliance)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "compliance.verify_evidence"
    body_dict = payload.model_dump(mode="json")
    now = datetime.now(timezone.utc)
    verification_id = uuid4()

    try:
        with compliance_transaction(write_url, caller["subject"]) as cur:
            if idempotency_key:
                try:
                    prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                    if prior:
                        return prior[1]
                except (IdempotencyConflict, IdempotencyExpired) as e:
                    raise HTTPException(status_code=409)

            cur.execute(
                "SELECT id, compliance_condition_id, submitted_by, status FROM public.evidence_submissions WHERE id = %s FOR UPDATE",
                (submission_id,),
            )
            sub_row = cur.fetchone()
            if not sub_row:
                raise HTTPException(status_code=404, detail="Evidence submission not found")

            condition_id = sub_row["compliance_condition_id"]
            cur.execute(
                "SELECT id, status, version FROM public.compliance_conditions WHERE id = %s FOR UPDATE",
                (condition_id,),
            )
            condition = cur.fetchone()
            if not condition:
                raise HTTPException(status_code=404, detail="Condition not found")

            if condition["status"] in ("closed", "compliant") or sub_row["status"] != "submitted":
                raise HTTPException(409, detail="Only unverified evidence for an active condition can be verified")
            if sub_row["submitted_by"] == caller_uuid:
                raise HTTPException(403, detail="Evidence submitter cannot verify their own submission")
            cur.execute("SELECT id FROM public.evidence_submissions WHERE compliance_condition_id=%s ORDER BY submission_number DESC LIMIT 1", (condition_id,))
            latest = cur.fetchone()
            if not latest or latest["id"] != submission_id:
                raise HTTPException(409, detail="Only the latest evidence submission can be verified")

            # Insert verification record
            cur.execute(
                "INSERT INTO public.compliance_verifications "
                "(id, evidence_submission_id, reviewer_user_id, result, comments, verified_at, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id, evidence_submission_id, reviewer_user_id, result, comments, verified_at, created_at",
                (verification_id, submission_id, caller_uuid, payload.result, payload.comments, now, now),
            )
            ver_row = cur.fetchone()

            # Update submission and condition based on verification outcome
            if payload.result == "accepted":
                cur.execute(
                    "UPDATE public.evidence_submissions SET status = 'accepted' WHERE id = %s",
                    (submission_id,),
                )
                cur.execute(
                    "UPDATE public.compliance_conditions "
                    "SET status = 'compliant', updated_at = %s, updated_by = %s, version = version + 1 "
                    "WHERE id = %s",
                    (now, caller_uuid, condition_id),
                )
            else:
                # rejected, incomplete, or needs_clarification
                cur.execute(
                    "UPDATE public.evidence_submissions SET status = 'rejected' WHERE id = %s",
                    (submission_id,),
                )
                cur.execute(
                    "UPDATE public.compliance_conditions "
                    "SET status = 'under_verification', updated_at = %s, updated_by = %s, version = version + 1 "
                    "WHERE id = %s",
                    (now, caller_uuid, condition_id),
                )

            audit_meta = {
                "condition_id": str(condition_id),
                "submission_id": str(submission_id),
                "verification_id": str(verification_id),
                "result": payload.result,
                "comments": payload.comments,
            }
            append_event(
                cur,
                actor_id=caller_uuid,
                action="EVIDENCE_VERIFIED",
                entity_type="compliance_verification",
                entity_id=verification_id,
                correlation_id=corr_uuid,
                reason=f"Officer verified evidence: {payload.result}",
                metadata=audit_meta,
            )
            enqueue(
                cur,
                event_type="EVIDENCE_VERIFIED",
                entity_type="compliance_verification",
                entity_id=verification_id,
                payload=audit_meta,
                correlation_id=corr_uuid,
            )

            res = _serialize(dict(ver_row))
            if idempotency_key:
                store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=201, response_json=res, expires_at=now + timedelta(days=1))
            return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.post("/compliance-conditions/{condition_id}/close")
def close_compliance_condition(
    condition_id: UUID,
    payload: CloseConditionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Authorised officer closes a compliance condition with justification."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "compliance.close_condition"
    body_dict = payload.model_dump(mode="json")
    now = datetime.now(timezone.utc)

    try:
        with compliance_transaction(write_url, caller["subject"]) as cur:
            if idempotency_key:
                try:
                    prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                    if prior:
                        return prior[1]
                except (IdempotencyConflict, IdempotencyExpired) as e:
                    raise HTTPException(status_code=409)

            cur.execute(
                "SELECT id, status, version FROM public.compliance_conditions WHERE id = %s FOR UPDATE",
                (condition_id,),
            )
            condition = cur.fetchone()
            if not condition:
                raise HTTPException(status_code=404, detail="Compliance condition not found")

            if condition["status"] == "closed":
                raise HTTPException(status_code=400, detail="Condition is already closed")
            if condition["status"] != "compliant":
                raise HTTPException(status_code=409, detail="Only a condition with accepted evidence can be closed")

            cur.execute(
                "UPDATE public.compliance_conditions "
                "SET status = 'closed', updated_at = %s, updated_by = %s, version = version + 1 "
                "WHERE id = %s "
                "RETURNING id, status, version, updated_at",
                (now, caller_uuid, condition_id),
            )
            updated = cur.fetchone()

            audit_meta = {
                "condition_id": str(condition_id),
                "reason": payload.reason,
                "previous_status": condition["status"],
            }
            append_event(
                cur,
                actor_id=caller_uuid,
                action="COMPLIANCE_CONDITION_CLOSED",
                entity_type="compliance_condition",
                entity_id=condition_id,
                correlation_id=corr_uuid,
                reason=payload.reason,
                metadata=audit_meta,
            )
            enqueue(
                cur,
                event_type="COMPLIANCE_CONDITION_CLOSED",
                entity_type="compliance_condition",
                entity_id=condition_id,
                payload=audit_meta,
                correlation_id=corr_uuid,
            )

            res = _serialize(dict(updated))
            if idempotency_key:
                store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=200, response_json=res, expires_at=now + timedelta(days=1))
            return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.post("/compliance-conditions/{condition_id}/reopen")
def reopen_compliance_condition(
    condition_id: UUID,
    payload: ReopenConditionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Authorised officer reopens a compliance condition with justification."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "compliance.reopen_condition"
    body_dict = payload.model_dump(mode="json")
    now = datetime.now(timezone.utc)

    try:
        with compliance_transaction(write_url, caller["subject"]) as cur:
            if idempotency_key:
                try:
                    prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                    if prior:
                        return prior[1]
                except (IdempotencyConflict, IdempotencyExpired) as e:
                    raise HTTPException(status_code=409)

            cur.execute(
                "SELECT id, status, version FROM public.compliance_conditions WHERE id = %s FOR UPDATE",
                (condition_id,),
            )
            condition = cur.fetchone()
            if not condition:
                raise HTTPException(status_code=404, detail="Compliance condition not found")

            if condition["status"] != "closed":
                raise HTTPException(status_code=409, detail="Only a closed condition can be reopened")

            cur.execute(
                "UPDATE public.compliance_conditions "
                "SET status = 'reopened', updated_at = %s, updated_by = %s, version = version + 1 "
                "WHERE id = %s "
                "RETURNING id, status, version, updated_at",
                (now, caller_uuid, condition_id),
            )
            updated = cur.fetchone()

            audit_meta = {
                "condition_id": str(condition_id),
                "reason": payload.reason,
                "previous_status": condition["status"],
            }
            append_event(
                cur,
                actor_id=caller_uuid,
                action="COMPLIANCE_CONDITION_REOPENED",
                entity_type="compliance_condition",
                entity_id=condition_id,
                correlation_id=corr_uuid,
                reason=payload.reason,
                metadata=audit_meta,
            )
            enqueue(
                cur,
                event_type="COMPLIANCE_CONDITION_REOPENED",
                entity_type="compliance_condition",
                entity_id=condition_id,
                payload=audit_meta,
                correlation_id=corr_uuid,
            )

            res = _serialize(dict(updated))
            if idempotency_key:
                store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=200, response_json=res, expires_at=now + timedelta(days=1))
            return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)
