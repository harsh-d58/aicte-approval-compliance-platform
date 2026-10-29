"""B01 API conventions and fail-closed dependency checks."""

import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException

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
        response = self.request(create_app(self.settings), "/api/v1/never-defined")
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
            supabase_url="https://project.example.supabase.co",
        ))
        with patch("backend.app.main.database_is_available", return_value=False) as probe:
            self.assertEqual(self.request(app, "/ready").status_code, 503)
            probe.assert_called_once_with("postgresql://placeholder")
        with patch("backend.app.main.database_is_available", return_value=True):
            self.assertEqual(self.request(app, "/ready").json(), {"status": "ready"})

    def test_settings_never_fall_back_to_bypass_migration_url(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("backend.app.settings.ENV_FILE", Path(__file__)), \
             patch("backend.app.settings.dotenv_values", return_value={
                 "DATABASE_URL": "postgresql://migration-owner",
             }):
            self.assertIsNone(Settings.load().database_url)
        with patch.dict(os.environ, {}, clear=True), \
             patch("backend.app.settings.ENV_FILE", Path(__file__)), \
             patch("backend.app.settings.dotenv_values", return_value={
                 "DATABASE_URL": "postgresql://migration-owner",
                 "DATABASE_RUNTIME_URL": "postgresql://scoped-reader",
             }):
            self.assertEqual(Settings.load().database_url, "postgresql://scoped-reader")

    def test_browser_origin_is_explicitly_allowed_for_live_reads(self):
        app = create_app(Settings(app_env="production", frontend_origin="https://portal.example.org"))
        response = self.request(app, "/api/v1/me", headers={"Origin": "https://portal.example.org"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), "https://portal.example.org")
        denied = self.request(app, "/api/v1/me", headers={"Origin": "https://other.example.org"})
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_stale_and_conflicting_actions_use_prd_error_envelope(self):
        app = create_app(self.settings)

        @app.get("/test-stale")
        def stale():
            raise HTTPException(status_code=412)

        @app.get("/test-conflict")
        def conflict():
            raise HTTPException(status_code=409)

        self.assertEqual(self.request(app, "/test-stale").json()["error"]["code"],
                         "PRECONDITION_FAILED")
        self.assertEqual(self.request(app, "/test-conflict").json()["error"]["code"],
                         "CONFLICT")


if __name__ == "__main__":
    unittest.main()
