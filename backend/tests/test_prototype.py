from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException
import jwt

from backend.app.prototype import PERSONAS, enabled, persona_subject, verify_prototype_token


class PrototypeSessionTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            settings=SimpleNamespace(app_env="development"))))
        self.key = "test-only-prototype-secret-" * 4

    def token(self, **overrides):
        now=datetime.now(timezone.utc)
        claims={"iss":"aicte-prototype","aud":"prototype","sub":persona_subject("user-central"),
                "persona":"user-central","iat":now,"exp":now+timedelta(hours=1)}
        claims.update(overrides)
        return jwt.encode(claims,self.key,algorithm="HS256")

    def test_all_ten_card_ids_have_distinct_subjects(self):
        self.assertEqual(len(PERSONAS),10)
        self.assertEqual(len({persona_subject(p[0]) for p in PERSONAS}),10)

    def test_unknown_persona_is_rejected(self):
        with self.assertRaises(HTTPException): persona_subject("COUNCIL_ADMIN")

    @patch("backend.app.prototype.dotenv_values",return_value={"PROTOTYPE_DEMO_ENABLED":"true"})
    def test_production_cannot_enable_demo_tokens(self, _):
        self.request.app.state.settings.app_env="production"
        self.assertFalse(enabled(self.request))

    @patch("backend.app.prototype.enabled",return_value=False)
    def test_disabled_demo_rejects_local_token(self, _):
        with self.assertRaises(HTTPException) as err:
            verify_prototype_token(self.request,self.token())
        self.assertEqual(err.exception.status_code,401)

    @patch("backend.app.prototype.enabled",return_value=True)
    def test_signed_token_subject_is_verified(self, _):
        with patch("backend.app.prototype._secret",return_value=self.key):
            self.assertEqual(verify_prototype_token(self.request,self.token()),persona_subject("user-central"))

    @patch("backend.app.prototype.enabled",return_value=True)
    def test_mismatched_subject_cannot_change_persona(self, _):
        with patch("backend.app.prototype._secret",return_value=self.key):
            with self.assertRaises(HTTPException):
                verify_prototype_token(self.request,self.token(sub=persona_subject("user-system")))

    @patch("backend.app.prototype.enabled",return_value=True)
    def test_wrong_key_is_rejected(self, _):
        with patch("backend.app.prototype._secret",return_value="other-key"*12):
            with self.assertRaises(HTTPException): verify_prototype_token(self.request,self.token())

    @patch("backend.app.prototype.enabled",return_value=True)
    def test_expired_token_is_rejected(self, _):
        with patch("backend.app.prototype._secret",return_value=self.key):
            with self.assertRaises(HTTPException):
                verify_prototype_token(self.request,self.token(exp=datetime.now(timezone.utc)-timedelta(seconds=1)))

    def test_supabase_issuer_falls_through_unchanged(self):
        self.assertIsNone(verify_prototype_token(self.request,self.token(iss="https://example.supabase.co/auth/v1")))
        self.assertIsNone(verify_prototype_token(self.request,"invalid"))


if __name__=="__main__": unittest.main()
