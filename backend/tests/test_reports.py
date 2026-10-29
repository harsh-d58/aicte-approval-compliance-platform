"""Unit tests for statutory reports generator supporting all eight PRD report categories."""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.reports import (
    CreateReportRunRequest,
    download_report_run,
    get_report_definition,
    list_report_runs,
    list_reports,
    run_statutory_report,
)
from backend.app.settings import Settings


class MockCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.fetchone_val = fetchone_val
        self.fetchall_val = fetchall_val or []
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchone(self):
        if isinstance(self.fetchone_val, list):
            return self.fetchone_val.pop(0) if self.fetchone_val else None
        return self.fetchone_val

    def fetchall(self):
        if isinstance(self.fetchall_val, list) and self.fetchall_val and isinstance(self.fetchall_val[0], list):
            return self.fetchall_val.pop(0)
        return self.fetchall_val


class MockConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor


class ReportRouteTests(TestCase):
    def setUp(self):
        self.scope_patch = patch('backend.app.reports._access_fingerprint', return_value='test-scope')
        self.scope_patch.start()
        self.addCleanup(self.scope_patch.stop)
        self.report_def_id = UUID(int=1)
        self.run_id = UUID(int=2)
        self.caller_id = UUID(int=3)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=99))),
        )
        self.subject = "test-subject"

    @patch("backend.app.reports._read_connection")
    @patch("backend.app.reports._user")
    def test_list_reports(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchall_val=[
                {
                    "id": self.report_def_id,
                    "report_code": "REGION_PERFORMANCE",
                    "name": "Region-wise performance",
                    "version": 1,
                    "columns_config": [],
                    "filters_config": [],
                    "enabled": True,
                    "created_at": datetime.now(timezone.utc),
                }
            ]
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        res = list_reports(self.request, self.subject)
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["report_code"], "REGION_PERFORMANCE")

    @patch("backend.app.reports._read_connection")
    @patch("backend.app.reports._user")
    def test_get_report_definition_not_found(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(fetchone_val=None)
        mock_conn.return_value = nullcontext(MockConnection(cur))

        with self.assertRaises(HTTPException) as ctx:
            get_report_definition("UNKNOWN_REPORT", self.request, self.subject)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("backend.app.reports.append_event", return_value=None)
    @patch("backend.app.reports._scoped_report_rows", return_value=[{"Region":"WEST", "Received":12, "Completed":8, "Stage pendency":"Review", "Processing time":"2 days", "Overdue":0, "EVC completion":"1/1", "Compliance":"1/1"}])
    @patch("backend.app.reports.enqueue", return_value=None)
    @patch("backend.app.reports.write_transaction")
    @patch("backend.app.reports._user")
    def test_run_statutory_report(self, mock_user, mock_tx, mock_enq, mock_rows, mock_audit):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        now = datetime.now(timezone.utc)
        cur = MockCursor(
            fetchone_val=[
                # Definition lookup
                {"id": self.report_def_id, "report_code": "REGION_PERFORMANCE", "name": "Region Performance"},
                # Insert report run
                {
                    "id": self.run_id,
                    "report_definition_id": self.report_def_id,
                    "requested_by": self.caller_id,
                    "filters": {},
                    "started_at": now,
                    "completed_at": now,
                    "status": "completed",
                    "result_metadata": {"row_count": 1, "format": "json"},
                    "created_at": now,
                },
            ],
            fetchall_val=[
                # Report query rows
                [
                    {
                        "region_code": "WEST",
                        "region_name": "Western",
                        "institutions_count": 10,
                        "total_applications": 12,
                        "approved": 8,
                        "rejected": 2,
                        "pending": 2,
                        "approval_rate_pct": 66.7,
                    }
                ]
            ],
        )
        mock_tx.return_value.__enter__.return_value = MockConnection(cur)

        req = CreateReportRunRequest(filters={}, format="json")
        res = run_statutory_report("REGION_PERFORMANCE", req, self.request, self.subject)
        self.assertEqual(res["report_code"], "REGION_PERFORMANCE")
        self.assertEqual(res["status"], "completed")
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["Region"], "WEST")

    @patch("backend.app.reports._read_connection")
    @patch("backend.app.reports._user")
    def test_download_report_run_csv(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val={"id": self.run_id, "filters": {}, "report_code": "REGION_PERFORMANCE", "name": "Region Performance", "result_metadata":{"access_fingerprint":"test-scope","snapshot_rows":[{"region_code":"WEST","region_name":"Western","institutions_count":10,"total_applications":12}]}},
            fetchall_val=[
                [
                    {
                        "region_code": "WEST",
                        "region_name": "Western",
                        "institutions_count": 10,
                        "total_applications": 12,
                    }
                ]
            ],
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        response = download_report_run(self.run_id, self.request, self.subject, format="csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "text/csv")
        self.assertIn("region_code,region_name,institutions_count,total_applications", response.body.decode())
        self.assertIn("WEST,Western,10,12", response.body.decode())

    @patch("backend.app.reports._read_connection")
    @patch("backend.app.reports._user")
    def test_download_report_run_json(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val={"id": self.run_id, "filters": {}, "report_code": "REGION_PERFORMANCE", "name": "Region Performance", "result_metadata":{"access_fingerprint":"test-scope","snapshot_rows":[{"region_code":"WEST","region_name":"Western","institutions_count":10,"total_applications":12}]}},
            fetchall_val=[
                [
                    {
                        "region_code": "WEST",
                        "region_name": "Western",
                    }
                ]
            ],
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        res = download_report_run(self.run_id, self.request, self.subject, format="json")
        self.assertEqual(res["report_code"], "REGION_PERFORMANCE")
        self.assertEqual(len(res["data"]), 1)
