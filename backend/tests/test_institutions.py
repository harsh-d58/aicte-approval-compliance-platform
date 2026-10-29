"""Unit tests for institution profile, campus, and typed attributes management."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from backend.app.concurrency import RecordMissing, StaleVersion
from backend.app.institutions import (
    CreateCampusRequest,
    ProfileAttributeItem,
    UpdateInstitutionRequest,
    UpdateProfileAttributesRequest,
    create_campus,
    list_campuses,
    list_profile_attributes,
    update_institution,
    update_profile_attributes,
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


class InstitutionRouteTests(TestCase):
    def setUp(self):
        self.institution_id = UUID(int=1)
        self.caller_id = UUID(int=2)
        self.settings = Settings(
            database_url="postgresql://reader_unused",
            database_write_url="postgresql://writer_unused",
        )
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=self.settings)),
            state=SimpleNamespace(correlation_id=str(UUID(int=99))),
        )
        self.caller_row = {
            "id": self.caller_id,
            "display_name": "Admin Officer",
            "email": "admin@example.com",
            "status": "active",
        }

    def test_update_institution_success(self):
        payload = UpdateInstitutionRequest(
            official_name="Updated Institute of Tech",
            expected_version=1,
            reason="Official re-branding",
        )
        current_row = {
            "id": self.institution_id,
            "official_name": "Old Institute",
            "institution_type": "technical",
            "region_id": None,
        }
        updated_row = {
            "id": self.institution_id,
            "official_name": "Updated Institute of Tech",
            "institution_code": "INST-001",
            "institution_type": "technical",
            "status": "active",
            "region_id": None,
            "updated_at": "2026-10-29T00:00:00Z",
            "version": 2,
        }
        cursor = MockCursor(fetchone_val=[current_row, updated_row])

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.institutions.lock_versioned", return_value=None), \
             patch("backend.app.institutions.bump_version", return_value=2), \
             patch("backend.app.institutions.append_event", return_value=None), \
             patch("backend.app.institutions.enqueue", return_value=None):
            result = update_institution(
                institution_id=self.institution_id,
                payload=payload,
                request=self.request,
                subject=str(self.caller_id),
            )

        self.assertEqual(result["official_name"], "Updated Institute of Tech")
        self.assertEqual(result["version"], 2)

    def test_update_institution_stale_version_raises_412(self):
        payload = UpdateInstitutionRequest(
            official_name="Conflict Institute",
            expected_version=1,
            reason="Conflict update",
        )
        cursor = MockCursor()

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.institutions.lock_versioned", side_effect=StaleVersion("Version mismatch")):
            with self.assertRaises(HTTPException) as ctx:
                update_institution(
                    institution_id=self.institution_id,
                    payload=payload,
                    request=self.request,
                    subject=str(self.caller_id),
                )
            self.assertEqual(ctx.exception.status_code, 412)

    def test_update_institution_missing_record_raises_404(self):
        payload = UpdateInstitutionRequest(
            official_name="Missing Institute",
            expected_version=1,
            reason="Missing update",
        )
        cursor = MockCursor()

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.institutions.lock_versioned", side_effect=RecordMissing("Missing")):
            with self.assertRaises(HTTPException) as ctx:
                update_institution(
                    institution_id=self.institution_id,
                    payload=payload,
                    request=self.request,
                    subject=str(self.caller_id),
                )
            self.assertEqual(ctx.exception.status_code, 404)

    def test_list_campuses(self):
        campuses = [
            {"id": UUID(int=10), "institution_id": self.institution_id, "campus_name": "Main Campus", "address": {}, "is_primary": True},
        ]
        cursor = MockCursor(fetchall_val=campuses)

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions._read_connection", return_value=nullcontext(MockConnection(cursor))):
            result = list_campuses(self.institution_id, self.request, str(self.caller_id), limit=10)

        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["campus_name"], "Main Campus")

    def test_create_campus_success(self):
        payload = CreateCampusRequest(
            campus_name="North Campus",
            address={"city": "Pune", "state": "MH"},
            is_primary=True,
            reason="Added secondary facility",
        )
        inst_row = {"id": self.institution_id}
        campus_row = {
            "id": UUID(int=11),
            "institution_id": self.institution_id,
            "campus_name": "North Campus",
            "address": {"city": "Pune", "state": "MH"},
            "region_id": None,
            "is_primary": True,
            "created_at": "2026-10-29T00:00:00Z",
            "updated_at": "2026-10-29T00:00:00Z",
            "version": 1,
        }
        cursor = MockCursor(fetchone_val=[inst_row, campus_row])

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor))), \
             patch("backend.app.institutions.append_event", return_value=None), \
             patch("backend.app.institutions.enqueue", return_value=None):
            result = create_campus(self.institution_id, payload, self.request, str(self.caller_id))

        self.assertEqual(result["campus_name"], "North Campus")
        self.assertTrue(result["is_primary"])

    def test_list_and_update_profile_attributes(self):
        attrs = [
            {"id": UUID(int=20), "institution_id": self.institution_id, "attribute_key": "total_built_area_sqm", "value_number": 12500.0, "verified_status": "verified"},
        ]
        cursor_read = MockCursor(fetchall_val=attrs)

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions._read_connection", return_value=nullcontext(MockConnection(cursor_read))):
            result = list_profile_attributes(self.institution_id, self.request, str(self.caller_id))

        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["attribute_key"], "total_built_area_sqm")

        # Update attributes
        payload = UpdateProfileAttributesRequest(
            attributes=[
                ProfileAttributeItem(attribute_key="total_built_area_sqm", value_number=14200.0, verified_status="verified", source_document_version_id=UUID(int=31)),
            ],
            reason="Annual area survey completion",
        )
        saved_attr = {
            "id": UUID(int=20),
            "institution_id": self.institution_id,
            "attribute_key": "total_built_area_sqm",
            "value_text": None,
            "value_date": None,
            "value_number": 14200.0,
            "source_document_id": None,
            "verified_status": "verified",
            "version": 2,
        }
        inst_row = {"id": self.institution_id}
        cursor_write = MockCursor(fetchone_val=[inst_row, {"id": UUID(int=30)}, saved_attr], fetchall_val=[{"role_code": "DEMO_SCRUTINY"}])

        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor_write))), \
             patch("backend.app.institutions.append_event", return_value=None), \
             patch("backend.app.institutions.enqueue", return_value=None):
            update_res = update_profile_attributes(self.institution_id, payload, self.request, str(self.caller_id))

        self.assertEqual(len(update_res["data"]), 1)
        self.assertEqual(update_res["data"][0]["value_number"], 14200.0)

    def test_institution_cannot_self_verify_attribute(self):
        payload = UpdateProfileAttributesRequest(attributes=[ProfileAttributeItem(
            attribute_key="total_built_area_sqm", value_number=14200, verified_status="verified",
            source_document_version_id=UUID(int=31))], reason="Verify area survey evidence")
        cursor = MockCursor(fetchone_val={"id": self.institution_id},
                            fetchall_val=[{"role_code": "DEMO_INSTITUTION"}])
        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as raised:
                update_profile_attributes(self.institution_id, payload, self.request, str(self.caller_id))
        self.assertEqual(raised.exception.status_code, 403)

    def test_verified_attribute_requires_exact_evidence_version(self):
        payload = UpdateProfileAttributesRequest(attributes=[ProfileAttributeItem(
            attribute_key="total_built_area_sqm", value_number=14200, verified_status="verified")], reason="Verify area survey evidence")
        cursor = MockCursor(fetchone_val={"id": self.institution_id},
                            fetchall_val=[{"role_code": "DEMO_SCRUTINY"}])
        with patch("backend.app.institutions._user", return_value=self.caller_row), \
             patch("backend.app.institutions.write_transaction", return_value=nullcontext(MockConnection(cursor))):
            with self.assertRaises(HTTPException) as raised:
                update_profile_attributes(self.institution_id, payload, self.request, str(self.caller_id))
        self.assertEqual(raised.exception.status_code, 422)
