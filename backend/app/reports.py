"""Statutory reports generator supporting all eight PRD report categories (PRD §§11.1–11.3, 17.4)."""

import csv
import io
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
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
from .report_catalog import contract_columns, snapshot_digest, validate_rows
from .report_exports import export_report


router = APIRouter(tags=["reports"])


def _access_fingerprint(cursor, caller_id):
    cursor.execute("SELECT r.role_code,a.scope_type,a.scope_id,a.valid_from,a.valid_until "
                   "FROM public.user_role_assignments a JOIN public.roles r ON r.id=a.role_id "
                   "WHERE a.user_id=%s AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) "
                   "AND (a.valid_until IS NULL OR a.valid_until>now()) ORDER BY r.role_code,a.scope_type,a.scope_id,a.id", (caller_id,))
    rows = [_serialize(dict(row)) for row in cursor.fetchall()]
    return hashlib.sha256(json.dumps(rows,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


class CreateReportRunRequest(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)
    format: str = Field("json", pattern=r"^(json|csv|xlsx|pdf)$")


def _scoped_report_rows(connection, subject, report_code, filters):
    from .portal_snapshot import snapshot
    from .report_projection import report_rows
    data = snapshot(connection, subject)
    code = report_code.removeprefix("DEMO-").lower().replace("_", "-")
    actor = next((u for u in data["users"] if u["id"] == subject), None)
    roles = {a["role"] for a in (actor or {}).get("assignments", [])}
    definition = next((d for d in data["reportDefinitions"] if d["id"] == code), None)
    if not definition or not roles.intersection(definition["roles"]):
        raise HTTPException(403)
    return report_rows(report_code, data, filters)


@router.get("/reports")
def list_reports(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """List all official statutory report definitions (PRD §11.1)."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, report_code, name, version, columns_config, filters_config, enabled, created_at "
                "FROM public.report_definitions "
                "ORDER BY report_code ASC, version DESC"
            )
            rows = cur.fetchall()

    return {"data": [_serialize(dict(r)) for r in rows]}


@router.get("/reports/{report_code}")
def get_report_definition(
    report_code: str,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve report definition metadata and schema configuration."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, report_code, name, version, columns_config, filters_config, access_policy, enabled, created_at "
                "FROM public.report_definitions "
                "WHERE report_code = %s OR report_code = %s",
                (report_code, f"DEMO-{report_code}"),
            )
            report = cur.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Report definition not found")

    return _serialize(dict(report))


@router.get("/reports/{report_code}/preview")
def preview_statutory_report(
    report_code: str,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    region_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
):
    """Live preview of statutory report rows with real column definitions and filters (PRD §11.1)."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    filters = {
        "region_id": str(region_id) if region_id else None,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "query": query,
    }

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, report_code, name, version, columns_config, filters_config, access_policy "
                "FROM public.report_definitions "
                "WHERE report_code = %s OR report_code = %s",
                (report_code, f"DEMO-{report_code}"),
            )
            report = cur.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Report definition not found")

        records = _scoped_report_rows(conn, subject, report_code, filters)

    cols = report["columns_config"] if isinstance(report["columns_config"], list) else (report["columns_config"] or {}).get("columns", [])
    return {
        "report_code": report["report_code"],
        "name": report["name"],
        "columns": cols,
        "row_count": len(records),
        "data": [_serialize(r) for r in records],
    }


@router.post("/reports/{report_code}/runs", status_code=201)
def run_statutory_report(
    report_code: str,
    payload: CreateReportRunRequest,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Generate and record a statutory report run (PRD §§11.2, 17.4)."""
    caller = _user(request, subject)
    write_url = request.app.state.settings.database_write_url
    if not write_url:
        raise HTTPException(status_code=503)

    caller_uuid = _to_uuid(caller["id"])
    correlation_id = getattr(request.state, "correlation_id", None)
    corr_uuid = _to_uuid(correlation_id)
    operation = "reports.run_report"
    body_dict = {"report_code": report_code, **payload.model_dump(mode="json")}
    now = datetime.now(timezone.utc)
    run_id = uuid4()

    try:
        with write_transaction(write_url, subject) as connection:
            with connection.cursor(row_factory=dict_row) as cur:
                if idempotency_key:
                    try:
                        prior = find_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict)
                        if prior:
                            return prior[1]
                    except (IdempotencyConflict, IdempotencyExpired) as e:
                        raise HTTPException(status_code=409)

                cur.execute(
                    "SELECT id, report_code, name FROM public.report_definitions WHERE report_code = %s OR report_code = %s",
                    (report_code, f"DEMO-{report_code}"),
                )
                definition = cur.fetchone()
                if not definition:
                    raise HTTPException(status_code=404, detail="Report definition not found")

                # Execute the statutory report query
                records = _scoped_report_rows(connection, subject, report_code, payload.filters)
                serialized_records = [_serialize(r) for r in records]
                columns = validate_rows(report_code, serialized_records)
                manifest = {"report_code": definition["report_code"], "generated_at": now.isoformat(),
                            "date_from": payload.filters.get("date_from", ""),
                            "date_to": payload.filters.get("date_to", ""),
                            "requested_by": str(caller_uuid), "filters": payload.filters}
                manifest["sha256"] = snapshot_digest(serialized_records, columns=columns,
                                                     period=payload.filters, code=report_code)
                access_fingerprint = _access_fingerprint(cur, caller_uuid)

                result_meta = {
                    "row_count": len(serialized_records),
                    "format": payload.format,
                    "generated_at": now.isoformat(),
                    "snapshot_rows": serialized_records,
                    "columns": columns,
                    "manifest": manifest,
                    "access_fingerprint": access_fingerprint,
                }

                cur.execute(
                    "INSERT INTO public.report_runs "
                    "(id, report_definition_id, requested_by, filters, started_at, completed_at, status, result_metadata, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s, %s) "
                    "RETURNING id, report_definition_id, requested_by, filters, started_at, completed_at, status, result_metadata, created_at",
                    (
                        run_id,
                        definition["id"],
                        caller_uuid,
                        Jsonb(payload.filters),
                        now,
                        now,
                        Jsonb(result_meta),
                        now,
                    ),
                )
                run_row = cur.fetchone()

                audit_meta = {
                    "report_code": report_code,
                    "run_id": str(run_id),
                    "row_count": len(serialized_records),
                    "format": payload.format,
                }
                append_event(
                    cur,
                    actor_id=caller_uuid,
                    action="REPORT_RUN_COMPLETED",
                    entity_type="report_run",
                    entity_id=run_id,
                    correlation_id=corr_uuid,
                    reason=f"Generated statutory report: {report_code}",
                    metadata=audit_meta,
                )
                enqueue(
                    cur,
                    event_type="REPORT_RUN_COMPLETED",
                    entity_type="report_run",
                    entity_id=run_id,
                    payload=audit_meta,
                    correlation_id=corr_uuid,
                )

                res = _serialize(dict(run_row))
                res["report_code"] = report_code
                res["data"] = serialized_records

                if idempotency_key:
                    store_result(cur, actor_id=caller_uuid, raw_key=idempotency_key, operation=operation, body=body_dict, http_status=201, response_json=res, expires_at=now + timedelta(days=1))
                return res
    except UnsafeWriteConnection:
        raise HTTPException(status_code=500)


@router.get("/report-runs")
def list_report_runs(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    report_definition_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """List historical report runs."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    query = (
        "SELECT r.id, r.report_definition_id, d.report_code, d.name AS report_name, "
        "r.requested_by, r.filters, r.started_at, r.completed_at, r.status, r.result_metadata, r.created_at "
        "FROM public.report_runs r "
        "JOIN public.report_definitions d ON d.id = r.report_definition_id "
        "WHERE r.requested_by = %s "
    )
    params: list[Any] = [caller["id"]]
    if report_definition_id:
        query += "AND r.report_definition_id = %s "
        params.append(report_definition_id)

    query += "ORDER BY r.created_at DESC LIMIT %s"
    params.append(limit)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    return {"data": [_serialize(dict(r)) for r in rows]}


@router.get("/report-runs/{run_id}/download")
def download_report_run(
    run_id: UUID,
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    format: Annotated[str, Query(pattern=r"^(csv|json|xlsx|pdf)$")] = "csv",
):
    """Download exported statutory report file in CSV or JSON format (PRD §11.2)."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT r.id, r.filters, r.result_metadata, r.requested_by, d.report_code, d.name "
                "FROM public.report_runs r "
                "JOIN public.report_definitions d ON d.id = r.report_definition_id "
                "WHERE r.id = %s AND r.requested_by = %s",
                (run_id, caller["id"]),
            )
            run = cur.fetchone()
            if not run:
                raise HTTPException(status_code=404, detail="Report run not found")

            records = (run.get("result_metadata") or {}).get("snapshot_rows")
            if records is None:
                raise HTTPException(409, detail="This old run has no frozen output; generate a new report.")
            fingerprint = (run.get("result_metadata") or {}).get("access_fingerprint")
            if not fingerprint:
                raise HTTPException(409, detail="This historical run has no saved access scope; generate a new report")
            if fingerprint != _access_fingerprint(cur, caller["id"]):
                raise HTTPException(403, detail="Your report access scope changed; generate a new report")

    meta = run.get("result_metadata") or {}
    columns = meta.get("columns") or (list(records[0]) if records else contract_columns(run["report_code"]))
    manifest = meta.get("manifest") or {"report_code": run["report_code"], "generated_at": meta.get("generated_at", "")}
    if manifest.get("sha256") and manifest["sha256"] != snapshot_digest(records, columns=columns, period=run.get("filters") or {}, code=run["report_code"]):
        raise HTTPException(409, detail="Report snapshot integrity check failed")
    if format == "json":
        return {"run_id": str(run_id), "report_code": run["report_code"], "manifest": manifest, "columns": columns, "data": records}
    content, media_type = export_report(records, columns, manifest, format)
    filename = f"{run_id.hex}.{format}"
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
