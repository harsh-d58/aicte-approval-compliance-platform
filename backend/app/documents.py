"""Private files, document registry, immutable versioning, and download authorization (PRD §§5.4, 7.5, 13.2)."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID, uuid4
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from .accounts import _read_connection, _serialize, _user
from .audit import append_event
from .auth import get_verified_subject
from .concurrency import RecordMissing, StaleVersion, bump_version, lock_versioned
from .idempotency import IdempotencyConflict, IdempotencyExpired, find_result, store_result
from .outbox import enqueue
from .storage import generate_download_token, retrieve_file, verify_download_token, store_file, validate_file_content, validate_file_name, file_scan_evidence
from .transactions import UnsafeWriteConnection, write_transaction
from .users import _to_uuid


router = APIRouter(tags=["documents"])


class CreateUploadSessionRequest(BaseModel):
    institution_id: UUID
    document_type_id: UUID
    file_name: str = Field(..., min_length=3, max_length=255)
    mime_type: str = Field(..., pattern=r"^(application/pdf|image/png|image/jpeg)$")
    max_size_bytes: int = Field(10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)


class RegisterDocumentRequest(BaseModel):
    institution_id: UUID
    document_type_id: UUID
    document_scope: str = Field("institution", pattern=r"^(institution|campus|application|compliance|other)$")
    campus_id: UUID | None = None
    application_id: UUID | None = None
    reason: str = Field("Register new compliance document", min_length=3, max_length=500)


class AddDocumentVersionRequest(BaseModel):
    upload_session_id: UUID | None = None
    file_name: str = Field(..., min_length=3, max_length=255)
    mime_type: str = Field(..., pattern=r"^(application/pdf|image/png|image/jpeg)$")
    size_bytes: int = Field(..., ge=1)
    sha256_hash: str = Field(..., min_length=64, max_length=64)
    object_key: str = Field(..., min_length=3, max_length=500)
    issue_date: str | None = None
    expiry_date: str | None = None
    reason: str = Field("Upload new document version", min_length=3, max_length=500)
    expected_version: int = Field(..., ge=1)


@router.get("/document-types")
def list_document_types(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List published document types and schema requirements."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, document_type_code, name, description, supports_expiry, metadata_schema, version "
        "FROM public.document_types ORDER BY document_type_code ASC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql)
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.get("/institutions/{institution_id}/documents")
def list_institution_documents(institution_id: UUID, request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    limit: Annotated[int, Query(ge=1,le=100)] = 50, cursor: UUID | None = None):
    _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,institution_id,document_type_id,current_version_id,issuer,reference,status,version FROM documents WHERE institution_id=%s AND (%s::uuid IS NULL OR id>%s) ORDER BY id LIMIT %s",(institution_id,cursor,cursor,limit+1))
            rows=cur.fetchall()
    return {'data':[_serialize(r) for r in rows[:limit]],'page':{'next_cursor':str(rows[limit-1]['id']) if len(rows)>limit else None}}


@router.post("/documents/upload-sessions", status_code=201)
def create_upload_session(
    payload: CreateUploadSessionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Obtain a controlled upload session with size/type bounds (PRD §9.2)."""
    caller = _user(request, subject)
    validate_file_name(payload.file_name, payload.mime_type)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=30)
    upload_token = secrets.token_urlsafe(32)

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                # Verify institution exists
                cur.execute("SELECT id FROM public.institutions WHERE id = %s", (payload.institution_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404)

                # Verify document type exists
                cur.execute("SELECT id FROM public.document_types WHERE id = %s", (payload.document_type_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=400)

                cur.execute(
                    "INSERT INTO public.upload_sessions "
                    "(institution_id, document_type_id, file_name, mime_type, max_size_bytes, status, upload_token, expires_at, created_at, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, 'created', %s, %s, %s, %s) "
                    "RETURNING id, institution_id, document_type_id, file_name, mime_type, max_size_bytes, status, upload_token, expires_at",
                    (payload.institution_id, payload.document_type_id, payload.file_name, payload.mime_type, payload.max_size_bytes, upload_token, expires_at, now, caller_uuid),
                )
                session = cur.fetchone()

        return _serialize(session)
    except UnsafeWriteConnection:
        raise HTTPException(status_code=503)


@router.put("/documents/upload-sessions/{session_id}/content")
async def upload_session_content(session_id: UUID, request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    upload_token: Annotated[str, Header(alias="X-Upload-Token")]):
    """Bounded binary transfer; binds computed metadata to the actor's single-use session."""
    caller = _user(request, subject)
    with _read_connection(request.app.state.settings.database_url, subject) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM upload_sessions WHERE id=%s AND created_by=%s", (session_id, caller['id']))
            session = cur.fetchone()
    if not session: raise HTTPException(404)
    if not secrets.compare_digest(session['upload_token'], upload_token): raise HTTPException(403)
    if session['status'] != 'created' or session['expires_at'] <= datetime.now(timezone.utc): raise HTTPException(409, detail="Upload session expired or consumed")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > session['max_size_bytes']: raise HTTPException(413)
        content.extend(chunk)
    checksum, size = validate_file_content(bytes(content), session['mime_type'], session['max_size_bytes'])
    key = f"uploads/{session_id}/{uuid4()}"
    with write_transaction(request.app.state.settings.database_write_url, subject) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT status,expires_at FROM upload_sessions WHERE id=%s AND created_by=%s FOR UPDATE", (session_id,caller['id']))
            locked=cur.fetchone()
            if not locked or locked['status']!='created' or locked['expires_at']<=datetime.now(timezone.utc): raise HTTPException(409)
            store_file(key,bytes(content))
            cur.execute("UPDATE upload_sessions SET status='uploaded',object_key=%s,sha256_hash=%s,size_bytes=%s WHERE id=%s",(key,checksum,size,session_id))
    return {'upload_session_id':str(session_id),'object_key':key,'sha256_hash':checksum,'size_bytes':size,'scan':file_scan_evidence(key)}


@router.post("/documents", status_code=201)
def register_document(
    payload: RegisterDocumentRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Register document metadata linking an institution, campus, or application (PRD §5.4)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "document.register"
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
                # 1. Verify institution
                cur.execute("SELECT id FROM public.institutions WHERE id = %s", (payload.institution_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404)

                # 2. Verify document type
                cur.execute("SELECT id FROM public.document_types WHERE id = %s", (payload.document_type_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=400)

                # 3. Verify campus if provided
                if payload.campus_id is not None:
                    cur.execute(
                        "SELECT id FROM public.institution_campuses WHERE id = %s AND institution_id = %s",
                        (payload.campus_id, payload.institution_id),
                    )
                    if cur.fetchone() is None:
                        raise HTTPException(status_code=400)

                # 4. Verify application if provided
                if payload.application_id is not None:
                    cur.execute(
                        "SELECT id FROM public.applications WHERE id = %s AND institution_id = %s",
                        (payload.application_id, payload.institution_id),
                    )
                    if cur.fetchone() is None:
                        raise HTTPException(status_code=400)

                now = datetime.now(timezone.utc)
                cur.execute(
                    "INSERT INTO public.documents "
                    "(institution_id, campus_id, application_id, document_type_id, document_scope, status, created_at, created_by, updated_at, updated_by, version) "
                    "VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, 1) "
                    "RETURNING id, institution_id, campus_id, application_id, document_type_id, document_scope, status, created_at, version",
                    (payload.institution_id, payload.campus_id, payload.application_id, payload.document_type_id, payload.document_scope, now, caller_uuid, now, caller_uuid),
                )
                doc = cur.fetchone()
                doc_id = doc["id"]

                # Audit & Outbox
                audit_meta = {
                    "institution_id": str(payload.institution_id),
                    "document_type_id": str(payload.document_type_id),
                    "document_scope": payload.document_scope,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DOCUMENT_REGISTERED",
                    entity_type="document",
                    entity_id=doc_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DOCUMENT_REGISTERED",
                    entity_type="document",
                    entity_id=doc_id,
                    entity_version=1,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(doc)
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


@router.get("/documents/{document_id}")
def get_document_detail(
    document_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve document metadata with active version information."""
    _ = _user(request, subject)
    sql = (
        "SELECT d.id, d.institution_id, d.campus_id, d.application_id, d.document_type_id, "
        "       d.document_scope, d.status, d.current_version_id, d.created_at, d.updated_at, d.version, "
        "       dt.document_type_code, dt.name as document_type_name, dt.supports_expiry "
        "FROM public.documents d "
        "JOIN public.document_types dt ON dt.id = d.document_type_id "
        "WHERE d.id = %s"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (document_id,))
            doc = cur.fetchone()
            if doc is None:
                raise HTTPException(status_code=404)
    return _serialize(doc)


@router.get("/documents/{document_id}/versions")
def list_document_versions(
    document_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List immutable versions for a document."""
    _ = _user(request, subject)
    sql = (
        "SELECT id, document_id, version_number, object_key, file_name, mime_type, size_bytes, "
        "       sha256_hash, uploaded_by, uploaded_at, issue_date, expiry_date, verification_status, created_at "
        "FROM public.document_versions WHERE document_id = %s ORDER BY version_number DESC"
    )
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(sql, (document_id,))
            rows = [_serialize(row) for row in cur.fetchall()]
    return {"data": rows}


@router.post("/documents/{document_id}/versions", status_code=201)
def add_document_version(
    document_id: UUID,
    payload: AddDocumentVersionRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Append an immutable version to a document, preserving history and bumping document version."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "document.add_version"
    body_dict = payload.model_dump(mode="json")

    expected_version = payload.expected_version
    if if_match is not None:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError:
            raise HTTPException(status_code=400)

    # Validate dates if both given
    try:
        issue_d = date.fromisoformat(payload.issue_date) if payload.issue_date else None
        expiry_d = date.fromisoformat(payload.expiry_date) if payload.expiry_date else None
    except ValueError:
        raise HTTPException(422, detail="Dates must use YYYY-MM-DD") from None
    validate_file_name(payload.file_name, payload.mime_type)
    if not payload.upload_session_id:
        raise HTTPException(400, detail="A completed upload session is required")
    if issue_d and expiry_d and expiry_d < issue_d:
        raise HTTPException(status_code=400, detail="Expiry date cannot precede issue date")

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
                # 1. Lock and bump version on documents table
                cur.execute("SELECT d.institution_id,d.document_type_id,dt.supports_expiry FROM documents d JOIN document_types dt ON dt.id=d.document_type_id WHERE d.id=%s FOR UPDATE",(document_id,))
                parent=cur.fetchone()
                if not parent: raise HTTPException(404)
                cur.execute("SELECT * FROM upload_sessions WHERE id=%s AND created_by=%s FOR UPDATE",(payload.upload_session_id,caller_uuid))
                session=cur.fetchone()
                if not session or session['status']!='uploaded' or session['finalized_version_id'] or session['expires_at']<=datetime.now(timezone.utc):
                    raise HTTPException(409, detail="Upload session missing, expired or already finalized")
                if (session['institution_id']!=parent['institution_id'] or session['document_type_id']!=parent['document_type_id']
                    or session['file_name']!=payload.file_name or session['mime_type']!=payload.mime_type
                    or session['object_key']!=payload.object_key or session['sha256_hash']!=payload.sha256_hash or session['size_bytes']!=payload.size_bytes):
                    raise HTTPException(400, detail="Version metadata does not match the uploaded bytes or document scope")
                if expiry_d and not parent['supports_expiry']: raise HTTPException(400, detail="Non-expiring document category")
                try:
                    lock_versioned(cur, table="documents", record_id=document_id, expected_version=expected_version)
                    next_doc_version = bump_version(cur, table="documents", record_id=document_id, expected_version=expected_version)
                except StaleVersion:
                    raise HTTPException(status_code=412)
                except RecordMissing:
                    raise HTTPException(status_code=404)

                # 2. Get next version number
                cur.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver "
                    "FROM public.document_versions WHERE document_id = %s",
                    (document_id,),
                )
                ver_num = cur.fetchone()["next_ver"]

                now = datetime.now(timezone.utc)

                # 3. Insert immutable version
                cur.execute(
                    "INSERT INTO public.document_versions "
                    "(document_id, version_number, object_key, file_name, mime_type, size_bytes, "
                    " sha256_hash, uploaded_by, uploaded_at, issue_date, expiry_date, verification_status, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s) "
                    "RETURNING id, document_id, version_number, object_key, file_name, mime_type, size_bytes, "
                    "          sha256_hash, uploaded_at, issue_date, expiry_date, verification_status, created_at",
                    (document_id, ver_num, payload.object_key, payload.file_name, payload.mime_type, payload.size_bytes,
                     payload.sha256_hash, caller_uuid, now, issue_d, expiry_d, now),
                )
                doc_version = cur.fetchone()
                version_id = doc_version["id"]

                # 4. Update document's current_version_id
                cur.execute(
                    "UPDATE public.documents SET current_version_id = %s, updated_at = %s, updated_by = %s WHERE id = %s",
                    (version_id, now, caller_uuid, document_id),
                )

                # 5. Mark upload session as uploaded if provided
                if payload.upload_session_id:
                    cur.execute(
                        "UPDATE public.upload_sessions SET finalized_version_id = %s WHERE id = %s",
                        (version_id, payload.upload_session_id),
                    )
                    from psycopg.types.json import Jsonb
                    scan = file_scan_evidence(payload.object_key)
                    cur.execute('INSERT INTO document_file_scans(document_version_id,status,evidence) VALUES(%s,%s,%s)',(version_id,scan['status'],Jsonb(scan)))

                # 6. Audit & Outbox
                audit_meta = {
                    "document_id": str(document_id),
                    "version_number": ver_num,
                    "sha256_hash": payload.sha256_hash,
                    "file_name": payload.file_name,
                    "old_version": expected_version,
                    "new_version": next_doc_version,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="DOCUMENT_VERSION_ADDED",
                    entity_type="document_version",
                    entity_id=version_id,
                    correlation_id=corr_uuid,
                    reason=payload.reason,
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="DOCUMENT_VERSION_ADDED",
                    entity_type="document_version",
                    entity_id=version_id,
                    entity_version=ver_num,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                response_data = _serialize(doc_version)
                response_data["document_version"] = next_doc_version

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


@router.get("/document-versions/{version_id}/download-token")
def get_download_token(
    version_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Generate a short-lived download token enforcing independent document scope check (PRD §13.2)."""
    caller = _user(request, subject)
    caller_uuid = _to_uuid(caller["id"])

    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM public.document_versions WHERE id = %s", (version_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404)

    token, expires_at = generate_download_token(version_id, caller_uuid)
    return {
        "download_token": token,
        "expires_at": expires_at.isoformat(),
        "download_url": f"/api/v1/document-versions/{version_id}/download?token={token}",
    }


@router.get("/document-versions/{version_id}/download")
def download_document_version(
    version_id: UUID,
    token: Annotated[str, Query()],
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Serve binary file content with token authorization and content headers."""
    caller = _user(request, subject)
    caller_uuid = _to_uuid(caller["id"])

    # 1. Verify token
    if not verify_download_token(version_id, caller_uuid, token):
        raise HTTPException(status_code=403, detail="Invalid or expired download token")

    # 2. Get version metadata
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, object_key, file_name, mime_type FROM public.document_versions WHERE id = %s",
                (version_id,),
            )
            version = cur.fetchone()
            if version is None:
                raise HTTPException(status_code=404)

    # 3. Retrieve binary bytes
    file_bytes = retrieve_file(version["object_key"])
    return Response(
        content=file_bytes,
        media_type=version["mime_type"],
        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(version["file_name"], safe=""),
                 "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
                 "Content-Security-Policy": "sandbox"},
    )
