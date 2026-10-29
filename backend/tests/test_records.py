"""Cursor and permission-scoped read contracts."""

import asyncio
from contextlib import nullcontext
from uuid import UUID
import unittest
from unittest.mock import patch

from fastapi import HTTPException
import httpx

from backend.app.auth import get_verified_subject
from backend.app.main import create_app
from backend.app.records import _cursor_id, _next_cursor
from backend.app.settings import Settings


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class RecordTests(unittest.TestCase):
    def request(self, app, path):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get(path)

        return asyncio.run(send())

    def app(self):
        app = create_app(Settings(database_url="postgresql://unused"))
        app.dependency_overrides[get_verified_subject] = lambda: "verified-subject"
        return app

    def test_cursor_is_canonical_and_invalid_input_is_rejected(self):
        value = UUID("00000000-0000-0000-0000-000000000001")
        self.assertEqual(_cursor_id(_next_cursor(value)), value)
        with self.assertRaises(HTTPException) as raised:
            _cursor_id("not-a-cursor")
        self.assertEqual(raised.exception.status_code, 400)

    def test_institution_list_paginates_only_permission_scoped_query(self):
        first = UUID("00000000-0000-0000-0000-000000000001")
        second = UUID("00000000-0000-0000-0000-000000000002")
        cursor = FakeCursor([{"id": first, "official_name": "First"}, {"id": second, "official_name": "Second"}])
        with patch("backend.app.records._user", return_value={"id": UUID(int=9)}), patch(
            "backend.app.records._read_connection", return_value=nullcontext(FakeConnection(cursor))
        ):
            response = self.request(self.app(), "/api/v1/institutions?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["page"]["next_cursor"], _next_cursor(first))
        self.assertIn("p.permission_code = %s", cursor.sql)
        self.assertIn("a.status = 'active'", cursor.sql)
        self.assertIn("a.scope_type = 'institution'", cursor.sql)
        self.assertIn("a.scope_type = 'region'", cursor.sql)
        self.assertEqual(cursor.params[:2], [UUID(int=9), "institution.read"])

    def test_unseen_application_detail_returns_same_404_as_missing(self):
        cursor = FakeCursor([])
        with patch("backend.app.records._user", return_value={"id": UUID(int=9)}), patch(
            "backend.app.records._read_connection", return_value=nullcontext(FakeConnection(cursor))
        ):
            response = self.request(self.app(), "/api/v1/applications/00000000-0000-0000-0000-000000000001")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")
        self.assertIn("a.scope_type = 'application'", cursor.sql)
        self.assertEqual(cursor.params[-1], "application.read")


if __name__ == "__main__":
    unittest.main()
