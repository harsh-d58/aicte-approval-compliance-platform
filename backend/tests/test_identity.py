"""Bearer verification and fail-closed current-user access."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
import httpx
import jwt

from backend.app.auth import get_verified_subject
from backend.app.main import create_app
from backend.app.settings import Settings


ISSUER = "https://identity.example/realms/aicte"
AUDIENCE = "aicte-api"


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def request(self, app, path, headers=None):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get(path, headers=headers)

        return asyncio.run(send())

    def token(self, **overrides):
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "identity-subject-001",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test-key"})

    def request_context(self, token):
        return SimpleNamespace(
            headers={"Authorization": "Bearer " + token},
            app=SimpleNamespace(state=SimpleNamespace(settings=Settings(
                identity_issuer_url=ISSUER, identity_audience=AUDIENCE
            ))),
        )

    def test_missing_bearer_is_unauthenticated(self):
        response = self.request(create_app(Settings()), "/api/v1/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")

    def test_unconfigured_provider_fails_closed(self):
        response = self.request(
            create_app(Settings()), "/api/v1/me", {"Authorization": "Bearer anything"}
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "DEPENDENCY_UNAVAILABLE")

    def test_signed_token_requires_expected_issuer_audience_and_expiry(self):
        key = SimpleNamespace(key=self.private_key.public_key())
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: key)
        with patch("backend.app.auth._jwk_client", return_value=client):
            self.assertEqual(get_verified_subject(self.request_context(self.token())), "identity-subject-001")
            for claims in (
                {"aud": "another-api"},
                {"iss": "https://another.example"},
                {"exp": datetime.now(timezone.utc) - timedelta(minutes=2)},
            ):
                with self.assertRaises(HTTPException) as raised:
                    get_verified_subject(self.request_context(self.token(**claims)))
                self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
