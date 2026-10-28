"""Supabase Auth JWT verification and fail-closed current-user access."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
import httpx
import jwt

from backend.app.auth import _issuer, _jwks_client, get_verified_subject
from backend.app.main import create_app
from backend.app.settings import Settings


PROJECT_URL = "https://project.example.supabase.co"
ISSUER = PROJECT_URL + "/auth/v1"
SUBJECT = "00000000-0000-0000-0000-000000000001"
SESSION = "00000000-0000-0000-0000-000000000002"


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = ec.generate_private_key(ec.SECP256R1())

    def request(self, app, path, headers=None):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get(path, headers=headers)

        return asyncio.run(send())

    def claims(self, **overrides):
        claims = {
            "iss": ISSUER,
            "aud": "authenticated",
            "sub": SUBJECT,
            "role": "authenticated",
            "session_id": SESSION,
            "is_anonymous": False,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        claims.update(overrides)
        return claims

    def token(self, **overrides):
        return jwt.encode(self.claims(**overrides), self.private_key, algorithm="ES256", headers={"kid": "test-key"})

    def request_context(self, token):
        return SimpleNamespace(
            headers={"Authorization": "Bearer " + token},
            app=SimpleNamespace(state=SimpleNamespace(settings=Settings(supabase_url=PROJECT_URL))),
        )

    def test_missing_bearer_is_unauthenticated(self):
        response = self.request(create_app(Settings()), "/api/v1/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")

    def test_unconfigured_project_fails_closed(self):
        response = self.request(
            create_app(Settings()), "/api/v1/me", {"Authorization": "Bearer anything"}
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "DEPENDENCY_UNAVAILABLE")

    def test_project_jwks_url_is_fixed_and_https(self):
        _jwks_client.cache_clear()
        self.assertEqual(_jwks_client(PROJECT_URL).uri, ISSUER + "/.well-known/jwks.json")
        for bad in ("http://localhost:54321", "https://project.example.supabase.co/other", "https://user:pass@project.example.supabase.co"):
            with self.assertRaises(ValueError):
                _issuer(bad)

    def test_signed_token_requires_project_claims_and_real_user_role(self):
        key = SimpleNamespace(key=self.private_key.public_key())
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: key)
        with patch("backend.app.auth._jwks_client", return_value=client):
            self.assertEqual(get_verified_subject(self.request_context(self.token())), SUBJECT)
            for claims in (
                {"aud": "anon"},
                {"iss": "https://another.example/auth/v1"},
                {"exp": datetime.now(timezone.utc) - timedelta(minutes=2)},
                {"role": "service_role"},
                {"is_anonymous": True},
                {"session_id": "not-a-uuid"},
            ):
                with self.assertRaises(HTTPException) as raised:
                    get_verified_subject(self.request_context(self.token(**claims)))
                self.assertEqual(raised.exception.status_code, 401)

    def test_legacy_symmetric_token_is_rejected(self):
        token = jwt.encode(self.claims(), "legacy-secret", algorithm="HS256", headers={"kid": "legacy"})
        with self.assertRaises(HTTPException) as raised:
            get_verified_subject(self.request_context(token))
        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
