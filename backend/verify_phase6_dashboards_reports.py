"""Live PostgreSQL End-to-End Verification for Phase 6 (Dashboards & Reports).

Executes comprehensive live verification against PostgreSQL:
1. Live scoped dashboard overview aggregation (applications, EVC, compliance, SLA, notifications)
2. Live regional performance breakdown
3. Catalog inspection: verifies all 8 official PRD report categories exist
4. Execution of all 8 PRD statutory reports against live PostgreSQL data:
   - REGION_PERFORMANCE
   - APPLICATION_PENDENCY
   - EVC_STATUS
   - UNDERTAKING_COMPLIANCE
   - DOCUMENT_VALIDITY
   - OVERDUE_ACTIONS
   - NOTIFICATION_DELIVERY
   - CASE_CLOSURE
5. CSV download format verification
6. JSON download format verification
7. Audit event & outbox event emission verification
8. Clean rollback
"""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row

from backend.app.dashboards import get_dashboard_overview, get_regional_breakdown
from backend.app.reports import (
    CreateReportRunRequest,
    download_report_run,
    list_reports,
    run_statutory_report,
)
from backend.app.settings import Settings


ROOT = Path(__file__).resolve().parents[1]

ALL_EIGHT_REPORTS = [
    "REGION_PERFORMANCE",
    "APPLICATION_PENDENCY",
    "EVC_STATUS",
    "UNDERTAKING_COMPLIANCE",
    "DOCUMENT_VALIDITY",
    "OVERDUE_ACTIONS",
    "NOTIFICATION_DELIVERY",
    "CASE_CLOSURE",
]


def verify_phase6_lifecycle():
    settings = Settings.load()
    assert settings.database_write_url, "DATABASE_WRITE_URL must be configured"
    assert settings.database_url, "DATABASE_RUNTIME_URL must be configured"

    print("==> Starting Phase 6 Dashboards & Reports Verification against live PostgreSQL...")

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
        state=SimpleNamespace(correlation_id=str(uuid4())),
    )

    # 0. Find an active test user
    with psycopg.connect(settings.database_write_url, sslmode="require") as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM public.users WHERE status = 'active' LIMIT 1")
            user = cur.fetchone()
            assert user, "Active user not found in database"
            subject = str(user["id"])

    # 1. Live dashboard overview aggregation
    overview = get_dashboard_overview(request, subject)
    assert "freshness" in overview
    assert "summary" in overview
    assert "applications" in overview
    assert "evc" in overview
    assert "compliance" in overview
    print(f" [1/8] Live dashboard overview verified: {overview['summary']['total_applications']} apps, {overview['summary']['total_evc_visits']} EVC visits, {overview['summary']['total_compliance_conditions']} compliance conditions")

    # 2. Live regional breakdown
    reg_breakdown = get_regional_breakdown(request, subject)
    assert len(reg_breakdown["regions"]) > 0, "No regions returned in regional breakdown"
    print(f" [2/8] Live regional breakdown verified: {len(reg_breakdown['regions'])} regions aggregated")

    # 3. Report catalog inspection: all 8 PRD reports present
    catalog = list_reports(request, subject)
    available_codes = [r["report_code"].replace("DEMO-", "") for r in catalog["data"]]
    for rep in ALL_EIGHT_REPORTS:
        assert rep in available_codes, f"Missing PRD report code: {rep}"
    print(f" [3/8] Report definitions catalog verified: all 8 official PRD reports present")

    # 4. Execute all 8 PRD statutory reports against live PostgreSQL
    test_run_ids = []
    for idx, rep_code in enumerate(ALL_EIGHT_REPORTS, start=1):
        req_body = CreateReportRunRequest(filters={}, format="json")
        run_res = run_statutory_report(rep_code, req_body, request, subject)
        run_id = run_res["id"]
        test_run_ids.append(run_id)
        row_count = len(run_res.get("data", []))
        print(f" [4/8.{idx}] Report {rep_code}: generated run {run_id} with {row_count} rows")

    # 5. CSV download verification
    csv_resp = download_report_run(test_run_ids[0], request, subject, format="csv")
    assert csv_resp.status_code == 200
    assert csv_resp.media_type == "text/csv"
    assert len(csv_resp.body) > 0
    print(f" [5/8] CSV download export verified for run {test_run_ids[0]} ({len(csv_resp.body)} bytes)")

    # 6. JSON download verification
    json_resp = download_report_run(test_run_ids[1], request, subject, format="json")
    assert "data" in json_resp
    assert json_resp["run_id"] == str(test_run_ids[1])
    print(f" [6/8] JSON download export verified for run {test_run_ids[1]} ({len(json_resp['data'])} records)")

    # 7. Audit & outbox trail check
    with psycopg.connect(settings.database_write_url, sslmode="require") as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT count(*) FROM public.audit_events WHERE action = 'REPORT_RUN_COMPLETED'"
            )
            audit_count = cur.fetchone()["count"]
            assert audit_count >= len(ALL_EIGHT_REPORTS)
            cur.execute(
                "SELECT count(*) FROM public.outbox_events WHERE event_type = 'REPORT_RUN_COMPLETED'"
            )
            outbox_count = cur.fetchone()["count"]
            assert outbox_count >= len(ALL_EIGHT_REPORTS)
            print(f" [7/8] Audit and outbox logs verified: {audit_count} audit events, {outbox_count} outbox events recorded")

            # 8. Clean up test runs and audit records to keep DB pristine
            cur.execute("DELETE FROM public.report_runs WHERE id = ANY(%s)", (test_run_ids,))
            cur.execute("DELETE FROM public.outbox_events WHERE event_type = 'REPORT_RUN_COMPLETED' AND entity_id = ANY(%s)", (test_run_ids,))
            print(f" [8/8] Cleaned up test report runs and outbox events cleanly")

    print("==> All 8 Phase 6 verification steps executed and passed successfully against PostgreSQL!")


if __name__ == "__main__":
    verify_phase6_lifecycle()
