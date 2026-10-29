"""Identity read queries match the existing database's lowercase lifecycle values."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from backend.app.accounts import me, me_permissions
from backend.app.settings import Settings


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class AccountQueryTests(TestCase):
    def setUp(self):
        self.request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(settings=Settings(database_url="postgresql://unused")))
        )
        self.user = {"id": UUID(int=1), "display_name": "Test User", "email": None, "status": "active", "last_login_at": None}

    def test_me_uses_database_active_values(self):
        identity = Cursor([self.user])
        assignments = Cursor([{"id": UUID(int=2), "role_code": "test", "scope_type": "institution", "scope_id": UUID(int=3)}])
        with patch("backend.app.accounts._read_connection", side_effect=[
            nullcontext(Connection(identity)), nullcontext(Connection(assignments))
        ]):
            result = me(self.request, str(UUID(int=1)))
        self.assertEqual(result["user"]["id"], UUID(int=1))
        self.assertEqual(result["assignments"][0]["scope_type"], "institution")
        self.assertIn("status = 'active'", identity.sql)
        self.assertIn("(id::text = %s OR identity_subject = %s)", identity.sql)
        self.assertEqual(identity.params, (str(UUID(int=1)), str(UUID(int=1))))
        self.assertIn("a.status = 'active'", assignments.sql)
        self.assertIn("a.valid_until > CURRENT_TIMESTAMP", assignments.sql)

    def test_effective_permissions_use_active_assignments(self):
        identity = Cursor([self.user])
        permissions = Cursor([{"permission_code": "institution.read", "scope_type": "institution", "scope_id": UUID(int=3)}])
        with patch("backend.app.accounts._read_connection", side_effect=[
            nullcontext(Connection(identity)), nullcontext(Connection(permissions))
        ]):
            result = me_permissions(self.request, str(UUID(int=1)))
        self.assertEqual(result["data"][0]["permission_code"], "institution.read")
        self.assertIn("a.status = 'active'", permissions.sql)
        self.assertIn("a.valid_from <= CURRENT_TIMESTAMP", permissions.sql)
