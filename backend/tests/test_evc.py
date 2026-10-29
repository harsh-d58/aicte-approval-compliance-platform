"""Unit tests for EVC visits, committee selection, expert availability, and scheduling."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.evc import (
    CommitteeMemberSelectionItem,
    CompleteVisitRequest,
    ConfirmScheduleRequest,
    CreateEvcVisitRequest,
    GenerateSlotRecommendationsRequest,
    SelectCommitteeMembersRequest,
    SubmitExpertAvailabilityRequest,
    complete_evc_visit,
    confirm_evc_schedule,
    create_evc_visit,
    generate_slot_recommendations,
    get_evc_visit_detail,
    get_expert_availability,
    list_evc_visit_events,
    list_evc_visits,
    list_slot_recommendations,
    select_committee_members,
    submit_expert_availability,
    screen_expert_coi,
    get_evc_coi_screening,
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
        return self.fetchall_val


class MockConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor


class EvcRouteTests(TestCase):
    def setUp(self):
        self.visit_id = UUID(int=1)
        self.application_id = UUID(int=2)
        self.campus_id = UUID(int=3)
        self.expert_1 = UUID(int=10)
        self.expert_2 = UUID(int=11)
        self.caller_id = UUID(int=99)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=999))),
        )
        self.caller_row = {
            "id": self.caller_id,
            "display_name": "Regional Officer",
            "email": "ro@example.com",
            "status": "active",
        }

    def test_list_evc_visits(self):
        visits = [
            {"id": self.visit_id, "application_id": self.application_id, "status": "required", "application_number": "APP-2026-0001"},
        ]
        cursor = MockCursor(fetchall_val=visits)

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_evc_visits(self.request, str(self.caller_id), limit=10)

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["status"], "required")

    def test_create_evc_visit_success(self):
        payload = CreateEvcVisitRequest(required_days=30, reason="Initiate EVC inspection")
        app_row = {"id": self.application_id, "status": "under_review", "campus_id": self.campus_id, "institution_id": UUID(int=4)}
        visit_row = {
            "id": self.visit_id,
            "application_id": self.application_id,
            "campus_id": self.campus_id,
            "status": "required",
            "required_by": "2026-11-29T00:00:00Z",
            "coordinator_user_id": None,
            "created_at": "2026-10-29T00:00:00Z",
        }
        cursor = MockCursor(fetchone_val=[app_row, visit_row])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.evc.append_event", return_value=None), \
             patch("backend.app.evc.enqueue", return_value=None):
            res = create_evc_visit(self.application_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["id"], self.visit_id)
        self.assertEqual(res["status"], "required")

    def test_create_evc_visit_closed_app_raises_409(self):
        payload = CreateEvcVisitRequest(required_days=30)
        app_row = {"id": self.application_id, "status": "approved", "campus_id": None, "institution_id": UUID(int=4)}
        cursor = MockCursor(fetchone_val=[app_row])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                create_evc_visit(self.application_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_select_committee_members_success(self):
        payload = SelectCommitteeMembersRequest(
            members=[
                CommitteeMemberSelectionItem(expert_user_id=self.expert_1, committee_role="convener"),
                CommitteeMemberSelectionItem(expert_user_id=self.expert_2, committee_role="member"),
            ],
            reason="Appoint statutory EVC committee",
        )
        visit_row = {"id": self.visit_id, "status": "required"}
        u1 = {"id": self.expert_1}
        u2 = {"id": self.expert_2}
        m1 = {"id": UUID(int=20), "evc_visit_id": self.visit_id, "expert_user_id": self.expert_1, "committee_role": "convener", "selection_status": "selected"}
        m2 = {"id": UUID(int=21), "evc_visit_id": self.visit_id, "expert_user_id": self.expert_2, "committee_role": "member", "selection_status": "selected"}
        cursor = MockCursor(fetchone_val=[visit_row, u1, m1, u2, m2])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.evc.append_event", return_value=None), \
             patch("backend.app.evc.enqueue", return_value=None):
            res = select_committee_members(self.visit_id, payload, self.request, str(self.caller_id))

        self.assertEqual(len(res["members"]), 2)
        self.assertEqual(res["members"][0]["committee_role"], "convener")

    def test_select_committee_members_duplicate_experts_raises_400(self):
        payload = SelectCommitteeMembersRequest(
            members=[
                CommitteeMemberSelectionItem(expert_user_id=self.expert_1, committee_role="convener"),
                CommitteeMemberSelectionItem(expert_user_id=self.expert_1, committee_role="member"),
            ],
            reason="Duplicate expert test",
        )
        with patch("backend.app.evc._user", return_value=self.caller_row):
            with self.assertRaises(HTTPException) as ctx:
                select_committee_members(self.visit_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_submit_and_get_expert_availability(self):
        payload = SubmitExpertAvailabilityRequest(
            start_at="2026-11-10T09:00:00Z",
            end_at="2026-11-10T17:00:00Z",
            availability_status="available",
            source="manual_entry",
        )
        user_row = {"id": self.expert_1}
        avail_row = {
            "id": UUID(int=30),
            "expert_user_id": self.expert_1,
            "start_at": "2026-11-10T09:00:00Z",
            "end_at": "2026-11-10T17:00:00Z",
            "availability_status": "available",
            "source": "manual_entry",
            "last_confirmed_at": "2026-10-29T00:00:00Z",
        }
        cursor_w = MockCursor(fetchone_val=[user_row, avail_row])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor_w))):
            res = submit_expert_availability(self.expert_1, payload, self.request, str(self.caller_id))

        self.assertEqual(res["availability_status"], "available")

        # Read back
        cursor_r = MockCursor(fetchall_val=[avail_row])
        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc._read_connection", return_value=nullcontext(MockConnection(cursor_r))):
            list_res = get_expert_availability(self.expert_1, self.request, str(self.caller_id))

        self.assertEqual(len(list_res["data"]), 1)

    def test_generate_slot_recommendations(self):
        payload = GenerateSlotRecommendationsRequest(search_horizon_days=30, visit_duration_hours=8)
        visit_row = {"id": self.visit_id, "status": "committee_selection", "required_by": None}
        members = [{"expert_user_id": self.expert_1}, {"expert_user_id": self.expert_2}]
        c1 = {"id": UUID(int=40), "evc_visit_id": self.visit_id, "rank": 1, "feasibility_status": "feasible"}
        c2 = {"id": UUID(int=41), "evc_visit_id": self.visit_id, "rank": 2, "feasibility_status": "feasible"}
        c3 = {"id": UUID(int=42), "evc_visit_id": self.visit_id, "rank": 3, "feasibility_status": "feasible"}
        cursor = MockCursor(fetchone_val=[c1, c2, c3], fetchall_val=members)
        context = (visit_row,members,{"durationMinutes":480,"availabilityFreshnessHours":72},[(datetime.now(timezone.utc)+timedelta(days=2),datetime.now(timezone.utc)+timedelta(days=4))],[])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.evc._scheduling_context", return_value=context):
            res = generate_slot_recommendations(self.visit_id, payload, self.request, str(self.caller_id))

        self.assertEqual(len(res["recommendations"]), 3)

    def test_confirm_evc_schedule_success(self):
        payload = ConfirmScheduleRequest(
            confirmed_start_at="2026-11-15T10:00:00Z",
            confirmed_end_at="2026-11-15T18:00:00Z",
            reason="Confirmed feasible slot",
        )
        visit_row = {"id": self.visit_id, "status": "scheduling", "confirmed_start_at": None, "confirmed_end_at": None}
        conflict_check = None  # No conflicting booking
        updated_visit = {
            "id": self.visit_id,
            "application_id": self.application_id,
            "status": "scheduled",
            "confirmed_start_at": "2026-11-15T10:00:00Z",
            "confirmed_end_at": "2026-11-15T18:00:00Z",
        }
        members = [{"expert_user_id": self.expert_1}, {"expert_user_id": self.expert_2}]
        cursor = MockCursor(fetchone_val=[updated_visit], fetchall_val=members)
        context=(visit_row,members,{"durationMinutes":480},[(datetime(2026,11,15,10,tzinfo=timezone.utc),datetime(2026,11,15,18,tzinfo=timezone.utc))],[])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.evc.append_event", return_value=None), \
             patch("backend.app.evc.enqueue", return_value=None), \
             patch("backend.app.evc._scheduling_context", return_value=context):
            res = confirm_evc_schedule(self.visit_id, payload, self.request, str(self.caller_id))

        self.assertEqual(res["status"], "scheduled")

    def test_confirm_evc_schedule_double_booking_conflict_raises_409(self):
        payload = ConfirmScheduleRequest(
            confirmed_start_at="2026-11-15T10:00:00Z",
            confirmed_end_at="2026-11-15T18:00:00Z",
        )
        visit_row = {"id": self.visit_id, "status": "scheduling"}
        conflict_check = {"id": UUID(int=999)}  # Concurrent booking exists!
        cursor = MockCursor(fetchone_val=[visit_row, conflict_check])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as ctx:
                confirm_evc_schedule(self.visit_id, payload, self.request, str(self.caller_id))
            self.assertEqual(ctx.exception.status_code, 409)

    def test_complete_evc_visit_success(self):
        visit_row = {"id": self.visit_id, "status": "scheduled", "confirmed_end_at": datetime.now(timezone.utc) - timedelta(hours=1)}
        updated_visit = {"id": self.visit_id, "status": "completed", "completed_at": "2026-11-15T18:30:00Z"}
        cursor = MockCursor(fetchone_val=[visit_row, updated_visit])

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.evc.append_event", return_value=None), \
             patch("backend.app.evc.enqueue", return_value=None):
            res = complete_evc_visit(self.visit_id, CompleteVisitRequest(), self.request, str(self.caller_id))

        self.assertEqual(res["status"], "completed")

    def test_future_or_unconfirmed_visit_cannot_be_completed(self):
        for state, end in [("required", None), ("scheduled", datetime.now(timezone.utc) + timedelta(days=1))]:
            cursor = MockCursor(fetchone_val={"id": self.visit_id, "status": state, "confirmed_end_at": end})
            with self.subTest(state=state), patch("backend.app.evc._user", return_value=self.caller_row), patch("backend.app.evc.write_transaction", return_value=nullcontext(MockConnection(cursor))):
                with self.assertRaises(HTTPException) as caught:
                    complete_evc_visit(self.visit_id, CompleteVisitRequest(), self.request, str(self.caller_id))
                self.assertEqual(caught.exception.status_code, 409)

    def test_list_evc_visit_events(self):
        events = [
            {"id": UUID(int=50), "evc_visit_id": self.visit_id, "event_type": "VISIT_REQUIRED", "reason": "Init", "details": {}},
        ]
        cursor = MockCursor(fetchall_val=events)

        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = list_evc_visit_events(self.visit_id, self.request, str(self.caller_id))

        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["event_type"], "VISIT_REQUIRED")

    def test_screen_expert_coi_clear(self):
        user_row = {
            "id": self.expert_1,
            "display_name": "Dr. Clear Expert",
            "email": "clear@example.com",
            "user_status": "active",
            "profile_id": UUID(int=101),
            "eligibility_status": "eligible",
            "expertise": ["Computer Science"],
        }
        # Cursors for: user_row, region check (None), inst check (None), past visits count (0)
        cursor = MockCursor(fetchone_val=[user_row, None, None, {"cnt": 0}])
        result = screen_expert_coi(cursor, self.expert_1, UUID(int=1), UUID(int=2))
        self.assertEqual(result["coi_status"], "CLEAR")
        self.assertTrue(result["is_eligible"])
        self.assertEqual(len(result["conflict_reasons"]), 0)

    def test_screen_expert_coi_regional_conflict(self):
        user_row = {
            "id": self.expert_1,
            "display_name": "Dr. Conflicted Expert",
            "email": "conflict@example.com",
            "user_status": "active",
            "profile_id": UUID(int=102),
            "eligibility_status": "eligible",
            "expertise": ["Mechanical"],
        }
        # region check returns a match!
        cursor = MockCursor(fetchone_val=[user_row, {"?column?": 1}, None, {"cnt": 0}])
        result = screen_expert_coi(cursor, self.expert_1, UUID(int=1), UUID(int=2))
        self.assertEqual(result["coi_status"], "CONFLICT_DETECTED")
        self.assertFalse(result["is_eligible"])
        self.assertTrue(any("Regional Jurisdiction Conflict" in r for r in result["conflict_reasons"]))

    def test_get_evc_coi_screening_endpoint(self):
        visit_info = {
            "id": self.visit_id,
            "institution_id": UUID(int=1),
            "official_name": "Test Engineering College",
            "institution_code": "TEC-001",
            "region_id": UUID(int=2),
            "region_name": "North Region",
        }
        candidates = [{"id": self.expert_1}]
        user_row = {
            "id": self.expert_1,
            "display_name": "Dr. Clear",
            "email": "clear@test.com",
            "user_status": "active",
            "profile_id": UUID(int=105),
            "eligibility_status": "eligible",
            "expertise": ["Civil"],
        }
        cursor = MockCursor(fetchone_val=[visit_info, user_row, None, None, {"cnt": 0}], fetchall_val=candidates)
        with patch("backend.app.evc._user", return_value=self.caller_row), \
             patch("backend.app.evc._read_connection", return_value=nullcontext(MockConnection(cursor))):
            res = get_evc_coi_screening(self.visit_id, self.request, str(self.caller_id))

        self.assertEqual(res["institution"]["name"], "Test Engineering College")
        self.assertEqual(res["summary"]["total_screened"], 1)
        self.assertEqual(res["candidates"][0]["coi_status"], "CLEAR")
