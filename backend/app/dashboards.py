"""Authoritative live scoped dashboard metrics and aggregations (PRD §§7.2, 11, 14, 17.4)."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from psycopg.rows import dict_row

from .accounts import _read_connection, _serialize, _user
from .auth import get_verified_subject


router = APIRouter(tags=["dashboards"])


@router.get("/dashboards/overview")
def get_dashboard_overview(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
    institution_id: Annotated[UUID | None, Query()] = None,
):
    """Retrieve authoritative live scoped dashboard overview across workflow, EVC, compliance, and SLA metrics."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    now = datetime.now(timezone.utc)

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Application pendency by stage/status
            app_filter = ""
            app_params: list[Any] = []
            if institution_id:
                app_filter = "WHERE institution_id = %s"
                app_params.append(institution_id)

            cur.execute(
                f"SELECT status, count(*) AS count FROM public.applications {app_filter} GROUP BY status",
                tuple(app_params),
            )
            pendency_rows = cur.fetchall()
            applications_by_status = {r["status"]: r["count"] for r in pendency_rows}
            total_applications = sum(applications_by_status.values())

            # 2. EVC status breakdown
            cur.execute(
                "SELECT status, count(*) AS count FROM public.evc_visits GROUP BY status"
            )
            evc_rows = cur.fetchall()
            evc_by_status = {r["status"]: r["count"] for r in evc_rows}
            total_evc_visits = sum(evc_by_status.values())

            # 3. Compliance conditions breakdown
            comp_filter = ""
            comp_params: list[Any] = []
            if institution_id:
                comp_filter = "WHERE institution_id = %s"
                comp_params.append(institution_id)

            cur.execute(
                f"SELECT status, count(*) AS count FROM public.compliance_conditions {comp_filter} GROUP BY status",
                tuple(comp_params),
            )
            comp_rows = cur.fetchall()
            compliance_by_status = {r["status"]: r["count"] for r in comp_rows}
            total_conditions = sum(compliance_by_status.values())

            # 4. Document validity summary
            doc_filter = ""
            doc_params: list[Any] = []
            if institution_id:
                doc_filter = "WHERE d.institution_id = %s"
                doc_params.append(institution_id)

            cur.execute(
                f"SELECT v.verification_status, count(*) AS count "
                f"FROM public.document_versions v "
                f"JOIN public.documents d ON d.id = v.document_id "
                f"{doc_filter} "
                f"GROUP BY v.verification_status",
                tuple(doc_params),
            )
            doc_rows = cur.fetchall()
            documents_by_status = {r["verification_status"]: r["count"] for r in doc_rows}

            # 5. Active SLA metrics
            cur.execute(
                f"SELECT "
                f"  count(*) FILTER (WHERE status IN ('submitted', 'under_review') AND created_at >= %s) AS on_track, "
                f"  count(*) FILTER (WHERE status IN ('submitted', 'under_review') AND created_at < %s) AS SLA_breached "
                f"FROM public.applications {app_filter}",
                (now - timedelta(days=21), now - timedelta(days=21), *app_params),
            )
            sla_stats = cur.fetchone() or {"on_track": 0, "sla_breached": 0}

            # 6. Notifications performance
            cur.execute(
                "SELECT "
                "  count(*) FILTER (WHERE status = 'sent') AS sent, "
                "  count(*) FILTER (WHERE status = 'failed') AS failed, "
                "  count(*) FILTER (WHERE status = 'queued') AS queued "
                "FROM public.notifications"
            )
            notif_stats = cur.fetchone() or {"sent": 0, "failed": 0, "queued": 0}

    return {
        "freshness": now.isoformat(),
        "summary": {
            "total_applications": total_applications,
            "total_evc_visits": total_evc_visits,
            "total_compliance_conditions": total_conditions,
        },
        "applications": {
            "by_status": applications_by_status,
            "sla": {
                "on_track": sla_stats.get("on_track", 0),
                "breached": sla_stats.get("sla_breached", 0),
            },
        },
        "evc": {
            "by_status": evc_by_status,
        },
        "compliance": {
            "by_status": compliance_by_status,
        },
        "documents": {
            "by_verification_status": documents_by_status,
        },
        "communications": {
            "sent": notif_stats.get("sent", 0),
            "failed": notif_stats.get("failed", 0),
            "queued": notif_stats.get("queued", 0),
        },
        "notifications": {
            "sent": notif_stats.get("sent", 0),
            "failed": notif_stats.get("failed", 0),
            "queued": notif_stats.get("queued", 0),
        },
    }


@router.get("/dashboards/regional-breakdown")
def get_regional_breakdown(
    request: Request,
    subject: Annotated[str, Depends(get_verified_subject)],
):
    """Retrieve regional performance metrics breakdown across all regions."""
    caller = _user(request, subject)
    read_url = request.app.state.settings.database_url
    if not read_url:
        raise HTTPException(status_code=503)

    query = (
        "SELECT "
        "  COALESCE(r.name, 'Unassigned') AS region_name, "
        "  COALESCE(r.code, 'N/A') AS region_code, "
        "  count(DISTINCT i.id) AS institution_count, "
        "  count(a.id) AS application_count, "
        "  count(a.id) FILTER (WHERE a.status = 'approved') AS approved_count, "
        "  count(a.id) FILTER (WHERE a.status = 'rejected') AS rejected_count, "
        "  count(a.id) FILTER (WHERE a.status NOT IN ('approved', 'rejected', 'closed', 'withdrawn')) AS pending_count "
        "FROM public.regions r "
        "LEFT JOIN public.institution_campuses c ON c.region_id = r.id "
        "LEFT JOIN public.institutions i ON i.id = c.institution_id "
        "LEFT JOIN public.applications a ON a.campus_id = c.id "
        "GROUP BY r.name, r.code "
        "ORDER BY r.code ASC"
    )

    with _read_connection(read_url, caller["subject"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return {
        "freshness": datetime.now(timezone.utc).isoformat(),
        "regions": [_serialize(dict(r)) for r in rows],
    }
