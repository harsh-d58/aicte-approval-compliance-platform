"""Unit tests for live scoped dashboard overview and regional breakdown."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from backend.app.dashboards import get_dashboard_overview, get_regional_breakdown
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


class DashboardRouteTests(TestCase):
    def setUp(self):
        self.caller_id = UUID(int=1)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=99))),
        )
        self.subject = "test-subject"

    @patch("backend.app.dashboards._read_connection")
    @patch("backend.app.dashboards._user")
    def test_get_dashboard_overview(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchone_val=[
                {"on_track": 15, "sla_breached": 2},
                {"sent": 120, "failed": 3, "queued": 5},
            ],
            fetchall_val=[
                # 1. pendency rows
                [{"status": "submitted", "count": 10}, {"status": "under_review", "count": 7}],
                # 2. evc rows
                [{"status": "scheduled", "count": 4}, {"status": "completed", "count": 12}],
                # 3. comp rows
                [{"status": "open", "count": 6}, {"status": "compliant", "count": 18}],
                # 4. doc rows
                [{"verification_status": "verified", "count": 45}],
            ],
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        res = get_dashboard_overview(self.request, self.subject)
        self.assertIn("freshness", res)
        self.assertEqual(res["summary"]["total_applications"], 17)
        self.assertEqual(res["summary"]["total_evc_visits"], 16)
        self.assertEqual(res["summary"]["total_compliance_conditions"], 24)
        self.assertEqual(res["applications"]["sla"]["on_track"], 15)
        self.assertEqual(res["communications"]["sent"], 120)

    @patch("backend.app.dashboards._read_connection")
    @patch("backend.app.dashboards._user")
    def test_get_regional_breakdown(self, mock_user, mock_conn):
        mock_user.return_value = {"id": self.caller_id, "subject": self.subject}
        cur = MockCursor(
            fetchall_val=[
                {
                    "region_name": "Western Region",
                    "region_code": "WEST",
                    "institution_count": 50,
                    "application_count": 65,
                    "approved_count": 40,
                    "rejected_count": 5,
                    "pending_count": 20,
                }
            ]
        )
        mock_conn.return_value = nullcontext(MockConnection(cur))

        res = get_regional_breakdown(self.request, self.subject)
        self.assertIn("freshness", res)
        self.assertEqual(len(res["regions"]), 1)
        self.assertEqual(res["regions"][0]["region_code"], "WEST")
