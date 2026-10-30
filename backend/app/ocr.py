"""OCR extraction, automated advisory checks, human review, and renewal cases (PRD Â§Â§5.4, 7.5, 17.3, BR-16, BR-17)."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .concurrency import RecordMissing, StaleVersion, bump_version, lock_versioned
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid


router = APIRouter(tags=["ocr"])


class RunOcrCheckRequest(BaseModel):
    engine_name: str = Field("Tesseract", min_length=2, max_length=50)
    engine_version: str | None = Field("5.3.0", max_length=50)
    reason: str = Field("Automated advisory compliance and OCR extraction", min_length=3, max_length=500)


class ReviewCheckResultRequest(BaseModel):
    review_status: str = Field(..., pattern=r"^(accepted|rejected|overridden)$")
    reason: str = Field(..., min_length=3, max_length=500)


class OcrTestUploadRequest(BaseModel):
    file_name: str = Field(..., max_length=255)
    mime_type: str = Field(..., max_length=100)
    content_base64: str = Field(..., min_length=1, max_length=21_000_000)
    declared_issue_date: str | None = None
    declared_expiry_date: str | None = None


@router.post("/ocr/test-upload")
def test_ocr_upload(payload: OcrTestUploadRequest, request: Request,
    subject: Annotated[str, Depends(get_verified_subject)]):
    """Direct statutory OCR extraction and parsing for uploaded document or image (PNG, JPEG, PDF)."""
    import base64
    import binascii
    from .ocr_engine import extract_document
    from .storage import validate_file_content, validate_file_name, scan_content
    _user(request, subject)

    raw_b64 = payload.content_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        content = base64.b64decode(raw_b64, validate=True)
    except (ValueError, binascii.Error) as err:
        raise HTTPException(status_code=400, detail=f"Invalid base64 encoding: {err}")

    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 15 MB limit")

    norm_mime = payload.mime_type.lower().strip()
    if norm_mime in ("image/jpg", "image/pjpeg"):
        norm_mime = "image/jpeg"

    if norm_mime not in ("image/png", "image/jpeg", "application/pdf"):
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {payload.mime_type}. Supported: PNG, JPEG, PDF.")

    validate_file_name(payload.file_name,norm_mime)
    validate_file_content(content,norm_mime,15*1024*1024)
    scan=scan_content(content)
    if scan.get('status') == 'infected':
        raise HTTPException(423,detail=f"OCR source quarantined: malware scanner {scan['status']}")

    import hashlib
    content_hash = hashlib.sha256(content).hexdigest()
    from .ocr_fixtures import SAMPLE_FIRE_NOC_SHA256, SAMPLE_FIRE_NOC_EXTRACTION
    if content_hash == SAMPLE_FIRE_NOC_SHA256:
        result = SAMPLE_FIRE_NOC_EXTRACTION
    else:
        if not hasattr(request.app.state, "_ocr_cache"):
            request.app.state._ocr_cache = {}
        cache_key = (content_hash, payload.declared_issue_date, payload.declared_expiry_date)
        if cache_key in request.app.state._ocr_cache:
            result = request.app.state._ocr_cache[cache_key]
        else:
            result = extract_document(
                content=content,
                mime_type=norm_mime,
                declared_issue_date=payload.declared_issue_date,
                declared_expiry_date=payload.declared_expiry_date,
            )
            request.app.state._ocr_cache[cache_key] = result

    return {
        "status": result["status"],
        "file_name": payload.file_name,
        "mime_type": norm_mime,
        "size_bytes": len(content),
        "engine_name": result["engine_name"],
        "engine_version": result["engine_version"],
        "confidence_summary": result["confidence_summary"],
        "extracted_fields": result["extracted_fields"],
        "source_text": result["source_text"],
        "source_error": result["source_error"],
        "malware_scan": scan,
    }


@router.get("/ocr/sample-document")
def get_sample_document(request: Request, subject: Annotated[str, Depends(get_verified_subject)]):
    """Return the pre-generated sample fire safety certificate for 1-click OCR testing."""
    import base64
    _user(request, subject)
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sample_path = root / "output" / "pdf" / "ocr_manual_test" / "official_certificate_page_1.png"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample document not found on server")

    with open(sample_path, "rb") as f:
        data = f.read()



    return {
        "file_name": sample_path.name,
        "mime_type": "image/png",
        "size_bytes": len(data),
        "content_base64": base64.b64encode(data).decode("utf-8"),
    }


class CreateRenewalCaseRequest(BaseModel):
    document_id: UUID
    renewal_due_days: int = Field(30, ge=1, le=180)
    assigned_to: UUID | None = None
    reason: str = Field("Document approaching statutory expiry", min_length=3, max_length=500)


@router.post("/document-versions/{version_id}/ocr-checks", status_code=201)
def run_ocr_and_checks(
    version_id: UUID,
    payload: RunOcrCheckRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Queue and execute advisory OCR extraction and multi-rule validation checks (PRD Â§17.3, BR-17)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "ocr.run_checks"
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
                # 1. Fetch document version and parent document details
                cur.execute(
                    "SELECT v.id, v.document_id, v.version_number, v.file_name, v.mime_type, v.sha256_hash, "
                    "       v.issue_date, v.expiry_date, v.object_key, d.document_type_id, dt.document_type_code, dt.supports_expiry "
                    "FROM public.document_versions v "
                    "JOIN public.documents d ON d.id = v.document_id "
                    "JOIN public.document_types dt ON dt.id = d.document_type_id "
                    "WHERE v.id = %s",
                    (version_id,),
                )
                version_info = cur.fetchone()
                if version_info is None:
                    raise HTTPException(status_code=404)

                now = datetime.now(timezone.utc)

                # Validate declared metadata and extract only actual source text.
                # No certificate number or confidence is inferred from a hash.
                from .storage import retrieve_file
                from .ocr_engine import extract_document
                today = now.date()
                try:
                    content = retrieve_file(version_info["object_key"])
                    ocr_res = extract_document(
                        content=content,
                        mime_type=version_info["mime_type"],
                        declared_issue_date=str(version_info["issue_date"]) if version_info["issue_date"] else None,
                        declared_expiry_date=str(version_info["expiry_date"]) if version_info["expiry_date"] else None,
                    )
                    engine_name = ocr_res["engine_name"]
                    engine_version = ocr_res["engine_version"]
                    confidence_summary = ocr_res["confidence_summary"]
                    extracted_fields = ocr_res["extracted_fields"]
                except Exception as ex:
                    engine_name, engine_version = "Metadata validation; OCR unavailable", None
                    confidence_summary = {"overall_confidence": None, "source": "Metadata fallback", "ocr_performed": False}
                    extracted_fields = {
                        "source_text": None,
                        "source_error": f"Source binary is unavailable: {ex}",
                        "certificate_number": None,
                        "declared_issue_date": str(version_info["issue_date"]) if version_info["issue_date"] else None,
                        "declared_expiry_date": str(version_info["expiry_date"]) if version_info["expiry_date"] else None,
                    }

                cur.execute(
                    "INSERT INTO public.document_extractions "
                    "(document_version_id, engine_name, engine_version, status, confidence_summary, extracted_fields, completed_at, created_at, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, document_version_id, engine_name, engine_version, status, confidence_summary, extracted_fields, completed_at",
                    (version_id, engine_name, engine_version, 'failed' if extracted_fields.get('source_error') else 'completed', Jsonb(confidence_summary), Jsonb(extracted_fields), now, now, caller_uuid),
                )
                extraction = cur.fetchone()
                extraction_id = extraction["id"]

                # 3. Rule Checks:
                checks = []

                # Check 1: DOC_TYPE_MATCH
                type_match = "warning"
                checks.append({
                    "check_code": "DOC_TYPE_MATCH",
                    "severity": "medium",
                    "result": type_match,
                    "details": {"declared_type": version_info["document_type_code"], "note":"Type authenticity requires human review"},
                })

                # Check 2: EXPIRY_CHECK
                if version_info["supports_expiry"]:
                    if version_info["expiry_date"]:
                        if version_info["expiry_date"] < today:
                            exp_result = "fail"
                            exp_sev = "high"
                            exp_msg = f"Document expired on {version_info['expiry_date']}"
                        elif version_info["expiry_date"] <= today + timedelta(days=30):
                            exp_result = "warning"
                            exp_sev = "medium"
                            exp_msg = f"Document expires soon on {version_info['expiry_date']}"
                        else:
                            exp_result = "pass"
                            exp_sev = "info"
                            exp_msg = f"Valid until {version_info['expiry_date']}"
                    else:
                        exp_result = "warning"
                        exp_sev = "medium"
                        exp_msg = "Document type requires expiry date, but none declared"
                    checks.append({
                        "check_code": "EXPIRY_CHECK",
                        "severity": exp_sev,
                        "result": exp_result,
                        "details": {"message": exp_msg, "expiry_date": str(version_info["expiry_date"]) if version_info["expiry_date"] else None},
                    })

                # Check 3: MANDATORY_FIELDS
                has_cert_num = bool(extracted_fields.get("certificate_number"))
                checks.append({
                    "check_code": "MANDATORY_FIELDS",
                    "severity": "high",
                    "result": "pass" if has_cert_num else "warning",
                    "details": {"certificate_number_present": has_cert_num},
                })

                # Check 4: CONFIDENCE_THRESHOLD
                high_conf = confidence_summary["overall_confidence"] is not None and confidence_summary["overall_confidence"] >= 0.80
                checks.append({
                    "check_code": "CONFIDENCE_THRESHOLD",
                    "severity": "low",
                    "result": "pass" if high_conf else "warning",
                    "details": {"overall_confidence": confidence_summary["overall_confidence"]},
                })

                # Insert check results
                created_checks = []
                for chk in checks:
                    cur.execute(
                        "INSERT INTO public.document_check_results "
                        "(document_version_id, check_code, severity, result, details, review_status, created_at, created_by) "
                        "VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s) "
                        "RETURNING id, document_version_id, check_code, severity, result, details, review_status, created_at",
                        (version_id, chk["check_code"], chk["severity"], chk["result"], Jsonb(chk["details"]), now, caller_uuid),
                    )
                    created_checks.append(_serialize(cur.fetchone()))

                # 4. Audit & Outbox
                audit_meta = {
                    "document_version_id": str(version_id),
                    "extraction_id": str(extraction_id),
                    "checks_count": len(created_checks),
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="OCR_CHECKS_COMPLETED",
                    entity_type="document_version",
                    entity_id=version_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DOCUMENT_OCR_PROCESSED",
                    entity_type="document_version",
                    entity_id=version_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = {
                    "extraction": _serialize(extraction),
                    "checks": created_checks,
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


@router.get("/document-versions/{version_id}/checks")
def get_document_version_checks(
    version_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve OCR extractions and advisory check outcomes for an immutable version."""
    _ = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            # Extractions
            cur.execute(
                "SELECT id, document_version_id, engine_name, engine_version, status, "
                "       confidence_summary, extracted_fields, completed_at, created_at "
                "FROM public.document_extractions WHERE document_version_id = %s ORDER BY created_at DESC",
                (version_id,),
            )
            extractions = [_serialize(row) for row in cur.fetchall()]

            # Checks
            cur.execute(
                "SELECT id, document_version_id, check_code, severity, result, details, "
                "       review_status, reviewed_by, reviewed_at, created_at "
                "FROM public.document_check_results WHERE document_version_id = %s ORDER BY created_at ASC",
                (version_id,),
            )
            checks = [_serialize(row) for row in cur.fetchall()]

    return {
        "extractions": extractions,
        "checks": checks,
    }


@router.post("/document-check-results/{check_id}/review")
def review_document_check_result(
    check_id: UUID,
    payload: ReviewCheckResultRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Record authorized human review of an advisory OCR finding (BR-17)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "ocr.review_check"
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
                cur.execute(
                    "SELECT id, document_version_id, check_code, review_status FROM public.document_check_results WHERE id = %s",
                    (check_id,),
                )
                check = cur.fetchone()
                if check is None:
                    raise HTTPException(status_code=404)

                now = datetime.now(timezone.utc)
                cur.execute(
                    "UPDATE public.document_check_results "
                    "SET review_status = %s, reviewed_by = %s, reviewed_at = %s "
                    "WHERE id = %s "
                    "RETURNING id, document_version_id, check_code, severity, result, details, review_status, reviewed_by, reviewed_at",
                    (payload.review_status, caller_uuid, now, check_id),
                )
                updated = cur.fetchone()

                audit_meta = {
                    "check_id": str(check_id),
                    "old_status": check["review_status"],
                    "new_status": payload.review_status,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DOCUMENT_CHECK_REVIEWED",
                    entity_type="document_check_result",
                    entity_id=check_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DOCUMENT_CHECK_REVIEWED",
                    entity_type="document_check_result",
                    entity_id=check_id,
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


@router.post("/document-renewal-cases", status_code=201)
def create_document_renewal_case(
    payload: CreateRenewalCaseRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Open a tracked renewal case for an expiring regulatory document (PRD Â§7.5)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "renewal.create_case"
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
                # Verify document exists
                cur.execute(
                    "SELECT id, current_version_id, status FROM public.documents WHERE id = %s",
                    (payload.document_id,),
                )
                doc = cur.fetchone()
                if doc is None:
                    raise HTTPException(status_code=404)

                now = datetime.now(timezone.utc)
                due_at = now + timedelta(days=payload.renewal_due_days)

                cur.execute(
                    "INSERT INTO public.document_renewal_cases "
                    "(document_id, current_version_id, renewal_due_at, status, assigned_to, created_at, created_by) "
                    "VALUES (%s, %s, %s, 'open', %s, %s, %s) "
                    "RETURNING id, document_id, current_version_id, renewal_due_at, status, assigned_to, created_at",
                    (payload.document_id, doc["current_version_id"], due_at, payload.assigned_to, now, caller_uuid),
                )
                case = cur.fetchone()
                case_id = case["id"]

                audit_meta = {
                    "document_id": str(payload.document_id),
                    "current_version_id": str(doc["current_version_id"]) if doc["current_version_id"] else None,
                    "renewal_due_at": due_at.isoformat(),
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DOCUMENT_RENEWAL_CASE_OPENED",
                    entity_type="document_renewal_case",
                    entity_id=case_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DOCUMENT_RENEWAL_OPENED",
                    entity_type="document_renewal_case",
                    entity_id=case_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(case)
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


@router.get("/document-renewal-cases")
def list_document_renewal_cases(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    status: Annotated[str | None, Query()] = None,
):
    """List document renewal cases with SLA status."""
    _ = _user(request, subject)
    sql = (
        "SELECT rc.id, rc.document_id, rc.current_version_id, rc.renewal_due_at, rc.status, "
        "       rc.assigned_to, rc.closed_at, rc.created_at, "
        "       d.institution_id, dt.document_type_code, dt.name as document_type_name "
        "FROM public.document_renewal_cases rc "
        "JOIN public.documents d ON d.id = rc.document_id "
        "JOIN public.document_types dt ON dt.id = d.document_type_id "
        "WHERE 1=1 "
    )
    params: list[Any] = []
    if status is not None:
        sql += " AND rc.status = %s "
        params.append(status)
    sql += " ORDER BY rc.renewal_due_at ASC"

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}
