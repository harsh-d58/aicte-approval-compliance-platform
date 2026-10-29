"""Contract and isolation checks for the live portal projection."""

from copy import deepcopy
from datetime import datetime, timezone
import unittest
from uuid import uuid4

from backend.app.portal_snapshot import map_snapshot, role, serial
from backend.seed_mock_data import ROWS, build_rows


COLLECTIONS = set("regions users institutions applications submissions workflows stageEvents deficiencies documents documentChecks renewals experts availability visits slots invitations observations meetingRecords actionItems decisions conditions evidence verifications notifications escalations reportDefinitions reportRuns auditEvents configurations integrations jobs tasks".split())


class PortalSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ROWS.clear()
        build_rows()
        # Seed Jsonb wrappers are insertion helpers; the database returns their
        # underlying JSON objects, which is what the projection receives.
        def plain(value):
            if hasattr(value, "obj"):
                return plain(value.obj)
            if isinstance(value, dict):
                return {k: plain(v) for k, v in value.items()}
            if isinstance(value, list):
                return [plain(v) for v in value]
            return serial(value)
        cls.baseline = plain(dict(ROWS))

    def fixture(self, scope="global", scope_id=None, status="active"):
        data = deepcopy(self.baseline)
        data["users"] = [{"id": "actor", "display_name": "Demo user", "email": "demo@example.invalid", "status": status}]
        data["roles"] = [{"id": "role", "role_code": "DEMO_CENTRAL"}]
        data["user_role_assignments"] = [{"id": "grant", "user_id": "actor", "role_id": "role", "scope_type": scope, "scope_id": scope_id, "status": "active", "valid_until": "2099-01-01T00:00:00+00:00"}]
        return data

    def test_all_seeded_records_reach_full_scope_dashboard(self):
        result = map_snapshot(self.fixture(), "actor")
        self.assertEqual(set(result), COLLECTIONS)
        self.assertEqual(len(result["institutions"]), 180)
        self.assertEqual(len(result["applications"]), 1080)
        self.assertEqual(len(result["documents"]), 2160)
        self.assertEqual(len(result["documentChecks"]), 1080)
        self.assertEqual(len(result["reportDefinitions"]), 8)
        self.assertEqual(result["users"][0]["assignments"][0]["role"], "CENTRAL")
        statuses = {a["status"] for a in result["applications"]}
        self.assertIn("IN_REVIEW", statuses)
        self.assertIn("RETURNED_FOR_DEFICIENCY", statuses)
        self.assertTrue(all(a["currentStage"] for a in result["applications"]))
        self.assertTrue(all(d["currentVersionId"] == "" for d in result["documents"]))

    def test_exact_institution_scope_filters_broad_child_rls(self):
        institution_id = self.baseline["institutions"][0]["id"]
        result = map_snapshot(self.fixture("institution", institution_id), "actor")
        self.assertEqual(len(result["institutions"]), 1)
        self.assertEqual(len(result["applications"]), 6)
        self.assertEqual(len(result["documents"]), 12)
        app_ids = {a["id"] for a in result["applications"]}
        self.assertTrue(all(v["applicationId"] in app_ids for v in result["visits"]))
        self.assertTrue(all(c["applicationId"] in app_ids for c in result["conditions"]))
        self.assertTrue(all(d["applicationId"] in app_ids for d in result["documents"]))

    def test_exact_application_scope_does_not_leak_sibling_documents(self):
        app_id = self.baseline["applications"][4]["id"]
        result = map_snapshot(self.fixture("application", app_id), "actor")
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(len(result["documents"]), 2)
        self.assertEqual(len(result["deficiencies"]), 1)

    def test_region_scope_matches_live_institution_regions(self):
        region_id = self.baseline["regions"][0]["id"]
        result = map_snapshot(self.fixture("region", region_id), "actor")
        self.assertEqual(len(result["institutions"]), 15)
        self.assertEqual(len(result["applications"]), 90)
        self.assertEqual(len(result["documents"]), 180)

    def test_disabled_expired_revoked_and_unknown_users_have_no_business_data(self):
        for variant in ("disabled", "expired", "revoked", "unknown"):
            data = self.fixture()
            if variant == "disabled":
                data["users"][0]["status"] = "disabled"
            elif variant == "expired":
                data["user_role_assignments"][0]["valid_until"] = "2000-01-01T00:00:00Z"
            elif variant == "revoked":
                data["user_role_assignments"][0]["status"] = "revoked"
            result = map_snapshot(data, "unknown" if variant == "unknown" else "actor")
            with self.subTest(variant=variant):
                for key in ("applications", "institutions", "documents", "visits", "conditions"):
                    self.assertEqual(result[key], [])

    def test_secret_storage_fields_do_not_cross_projection(self):
        data = self.fixture()
        data["roles"][0]["role_code"] = "DEMO_SYSTEM"
        data["integration_endpoints"] = [{"id": "i", "system_name": "Test", "integration_type": "email", "status": "disabled", "secret_reference": "DO-NOT-EXPOSE", "base_url": "secret"}]
        result = map_snapshot(data, "actor")
        self.assertNotIn("DO-NOT-EXPOSE", str(result))
        self.assertNotIn("object_key", str(result))
        self.assertNotIn("identity_subject", str(result))

    def test_demo_global_assignment_cannot_read_non_demo_institutions(self):
        data = self.fixture()
        original = deepcopy(data["institutions"][0])
        original.update(id="official", institution_code="OFFICIAL-001", created_by=None)
        data["institutions"].append(original)
        application = deepcopy(data["applications"][0])
        application.update(id="official-app", institution_id="official")
        data["applications"].append(application)
        result = map_snapshot(data, "actor")
        self.assertNotIn("official", {i["id"] for i in result["institutions"]})
        self.assertNotIn("official-app", {a["id"] for a in result["applications"]})

    def test_serialization_and_role_aliases(self):
        value = uuid4()
        self.assertEqual(serial(value), str(value))
        self.assertEqual(serial(datetime(2026, 1, 1, tzinfo=timezone.utc)), "2026-01-01T00:00:00+00:00")
        self.assertEqual(role("DEMO_EVC_EXPERT"), "EVC_EXPERT")
        self.assertEqual(role("DEMO_INSTITUTION_VIEWER"), "INSTITUTION")

    def test_latest_item_response_survives_projection_without_mutating_source(self):
        data = self.fixture()
        item = data['deficiency_items'][0]
        data['deficiency_item_responses'] = [
            {'id':'old','deficiency_item_id':item['id'],'narrative':'Original response','document_version_id':None,'submitted_at':'2026-01-01'},
            {'id':'new','deficiency_item_id':item['id'],'narrative':'Corrected response','document_version_id':'version-2','submitted_at':'2026-01-02'}]
        result = map_snapshot(data, 'actor')
        projected = next(i for notice in result['deficiencies'] for i in notice['items'] if i['id']==item['id'])
        self.assertEqual(projected['response'],'Corrected response')
        self.assertEqual(projected['responseVersionId'],'version-2')
        self.assertNotIn('response_text', item)


if __name__ == "__main__":
    unittest.main()
