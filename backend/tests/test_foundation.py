"""B01 API conventions and fail-closed dependency checks."""

import asyncio
import unittest
from unittest.mock import patch

import httpx

from backend.app.main import create_app
from backend.app.settings import Settings


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(database_url=None)

    def request(self, app, path, headers=None):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get(path, headers=headers)

        return asyncio.run(send())

    def test_health_and_correlation_id(self):
        response = self.request(create_app(self.settings), "/health", headers={"X-Correlation-ID": "e24f669b-577d-489e-8e26-024621663ff9"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})
        self.assertEqual(response.headers["X-Correlation-ID"], "e24f669b-577d-489e-8e26-024621663ff9")

    def test_missing_route_uses_prd_error_envelope(self):
        response = self.request(create_app(self.settings), "/api/v1/applications")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": {
            "code": "NOT_FOUND",
            "message": "Resource not found.",
            "details": {},
            "correlation_id": response.headers["X-Correlation-ID"],
        }})

    def test_not_ready_without_identity_and_database(self):
        response = self.request(create_app(self.settings), "/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "DEPENDENCY_UNAVAILABLE")
        self.assertNotIn("database_url", response.text.lower())

    def test_ready_only_after_configured_database_probe(self):
        app = create_app(Settings(
            database_url="postgresql://placeholder",
            identity_issuer_url="https://identity.example/realms/aicte",
            identity_audience="aicte-api",
        ))
        with patch("backend.app.main.database_is_available", return_value=False) as probe:
            self.assertEqual(self.request(app, "/ready").status_code, 503)
            probe.assert_called_once_with("postgresql://placeholder")
        with patch("backend.app.main.database_is_available", return_value=True):
            self.assertEqual(self.request(app, "/ready").json(), {"status": "ready"})


if __name__ == "__main__":
    unittest.main()
