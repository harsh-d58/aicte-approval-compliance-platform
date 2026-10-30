from unittest import TestCase
from backend.app.authorization import allowed_roles


class DecisionAuthorizationTests(TestCase):
    def test_compliance_officer_can_close_verified_condition_but_not_application(self):
        self.assertIn('COMPLIANCE',allowed_roles('/compliance-conditions/condition/close'))
        self.assertNotIn('COMPLIANCE',allowed_roles('/applications/case/decisions'))
        self.assertIn('REGIONAL',allowed_roles('/applications/case/decisions'))

    def test_institution_can_submit_but_cannot_verify_condition_evidence(self):
        self.assertEqual(allowed_roles('/compliance-conditions/condition/evidence-submissions'),{'INSTITUTION'})
        self.assertNotIn('INSTITUTION',allowed_roles('/evidence-submissions/submission/verifications'))
