"""Rolled-back Phase 1 access matrix using the actual API read SQL and RLS.

Temporarily changes only the approved DEMO test account and synthetic records
inside one uncommitted transaction. SET ROLE applies the real API reader's
permissions in that transaction; every test change is rolled back on exit.
No Auth token, password, UUID or personal data is printed.
"""

from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dotenv import dotenv_values
from fastapi import HTTPException
import psycopg
from psycopg.rows import dict_row

from backend.app.accounts import me, me_permissions
from backend.app.records import application, applications, institution, institutions


ROOT = Path(__file__).resolve().parents[1]


class RollBackAll(Exception):
    pass


@contextmanager
def _as_reader(connection, subject):
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE aicte_api_reader")
        cursor.execute("SELECT set_config('aicte.subject_id', %s, true)", (str(subject),))
    try:
        source = lambda _url, _subject: nullcontext(connection)
        with patch("backend.app.accounts._read_connection", side_effect=source), \
             patch("backend.app.records._read_connection", side_effect=source):
            request = SimpleNamespace(
                app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(database_url="unused")))
            )
            yield request
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")


def _all_pages(endpoint, request, subject):
    data = []
    cursor = None
    for _ in range(20):
        result = endpoint(request, str(subject), limit=100, cursor=cursor, status=None)
        data.extend(result["data"])
        cursor = result["page"]["next_cursor"]
        if cursor is None:
            return data
    raise AssertionError("Too many DEMO pages")


def _hidden(endpoint, request, subject, target):
    try:
        endpoint(request, str(subject), target)
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Out-of-scope detail was visible")


def _role(cursor, code, permissions):
    cursor.execute(
        "INSERT INTO public.roles (role_code, role_name, description) "
        "VALUES (%s, %s, 'Rolled-back approved DEMO policy test') RETURNING id",
        (code, code.replace("_", " ")),
    )
    role_id = cursor.fetchone()["id"]
    for permission in permissions:
        cursor.execute(
            "SELECT id FROM public.permissions WHERE permission_code = %s",
            (permission,),
        )
        permission_id = cursor.fetchone()["id"]
        cursor.execute(
            "INSERT INTO public.role_permissions (role_id, permission_id) VALUES (%s, %s)",
            (role_id, permission_id),
        )
    return role_id


def _assignment(cursor, user_id, role_id, scope_type, scope_id):
    now = datetime.now(timezone.utc)
    cursor.execute(
        "INSERT INTO public.user_role_assignments "
        "(user_id, role_id, scope_type, scope_id, valid_from, valid_until, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'active') RETURNING id",
        (user_id, role_id, scope_type, scope_id,
         now - timedelta(days=1), now + timedelta(days=1)),
    )
    return cursor.fetchone()["id"]


def main() -> None:
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")
    with psycopg.connect(url, sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=15000 -c lock_timeout=5000",
                         autocommit=True, row_factory=dict_row) as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT u.id AS user_id, a.id AS assignment_id, a.scope_id AS institution_id, "
                        "a.valid_from AS original_from, a.valid_until AS original_until "
                        "FROM public.users u "
                        "JOIN public.user_role_assignments a ON a.user_id = u.id "
                        "JOIN public.roles r ON r.id = a.role_id "
                        "WHERE r.role_code = 'DEMO_INSTITUTION_VIEWER' "
                        "AND a.status = 'active' AND u.status = 'active' "
                        "AND a.scope_type = 'institution'"
                    )
                    matches = cursor.fetchall()
                    if len(matches) != 1:
                        raise RuntimeError("Expected one active approved DEMO viewer")
                    user_id = matches[0]["user_id"]
                    assignment_id = matches[0]["assignment_id"]
                    institution_id = matches[0]["institution_id"]
                    original_until = matches[0]["original_until"]
                    original_from = matches[0]["original_from"]
                    cursor.execute("SELECT id FROM public.regions WHERE code = 'DEMO-R01'")
                    region_id = cursor.fetchone()["id"]
                    cursor.execute("SELECT id FROM public.applications WHERE application_number = 'DEMO-APP-2026-000001'")
                    application_id = cursor.fetchone()["id"]
                    cursor.execute("SELECT id FROM public.institutions WHERE institution_code = 'DEMO-INST-0002'")
                    other_institution = cursor.fetchone()["id"]
                    cursor.execute("SELECT id FROM public.applications WHERE application_number = 'DEMO-APP-2026-000007'")
                    other_application = cursor.fetchone()["id"]
                    cursor.execute("SELECT id FROM public.institutions WHERE region_id = %s", (region_id,))
                    region_institutions = {row["id"] for row in cursor.fetchall()}
                    cursor.execute(
                        "SELECT id FROM public.applications WHERE institution_id IN "
                        "(SELECT id FROM public.institutions WHERE region_id = %s)",
                        (region_id,),
                    )
                    region_applications = {row["id"] for row in cursor.fetchall()}
                    if len(region_institutions) < 2 or len(region_applications) < 2:
                        raise RuntimeError("DEMO region fixture is too small for scope testing")

                    # This membership exists only within the outer rollback;
                    # no permanent administrator SET privilege is added.
                    cursor.execute(
                        "GRANT aicte_api_reader TO postgres WITH SET TRUE, INHERIT FALSE"
                    )

                with _as_reader(connection, user_id) as request:
                    assert len(me(request, str(user_id))["assignments"]) == 1
                    assert {p["permission_code"] for p in me_permissions(request, str(user_id))["data"]} == {
                        "institution.read", "application.read"
                    }
                    assert {row["id"] for row in _all_pages(institutions, request, user_id)} == {institution_id}
                    assert len(_all_pages(applications, request, user_id)) == 6
                    _hidden(institution, request, user_id, other_institution)
                    _hidden(application, request, user_id, other_application)

                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE public.user_role_assignments SET status = 'revoked' WHERE id = %s",
                        (assignment_id,),
                    )
                    cursor.execute("SELECT status FROM public.user_role_assignments WHERE id = %s",
                                   (assignment_id,))
                    assert cursor.fetchone()["status"] == "revoked"
                with _as_reader(connection, user_id) as request:
                    assignments_after = me(request, str(user_id))["assignments"]
                    assert assignments_after == [], [item["role_code"] for item in assignments_after]
                    assert _all_pages(institutions, request, user_id) == []
                    assert _all_pages(applications, request, user_id) == []
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE public.user_role_assignments SET status = 'active', "
                        "valid_until = %s WHERE id = %s",
                        (original_from + timedelta(microseconds=1), assignment_id),
                    )
                with _as_reader(connection, user_id) as request:
                    assert me(request, str(user_id))["assignments"] == []
                    assert _all_pages(institutions, request, user_id) == []
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE public.user_role_assignments SET valid_until = %s WHERE id = %s",
                        (original_until, assignment_id),
                    )
                    cursor.execute("UPDATE public.users SET status = 'disabled' WHERE id = %s", (user_id,))
                with _as_reader(connection, user_id) as request:
                    try:
                        me(request, str(user_id))
                    except HTTPException as error:
                        assert error.status_code == 403
                    else:
                        raise AssertionError("Disabled account was accepted")
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE public.users SET status = 'active' WHERE id = %s", (user_id,))
                    cursor.execute(
                        "UPDATE public.user_role_assignments SET status = 'revoked' WHERE id = %s",
                        (assignment_id,),
                    )
                    region_role = _role(cursor, "DEMO_REGION_VIEWER", ("institution.read", "application.read"))
                    region_assignment = _assignment(cursor, user_id, region_role, "region", region_id)
                with _as_reader(connection, user_id) as request:
                    assert {row["id"] for row in _all_pages(institutions, request, user_id)} == region_institutions
                    assert {row["id"] for row in _all_pages(applications, request, user_id)} == region_applications
                    _hidden(institution, request, user_id, other_institution)
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE public.user_role_assignments SET status = 'revoked' WHERE id = %s",
                        (region_assignment,),
                    )
                    app_role = _role(cursor, "DEMO_APPLICATION_VIEWER", ("application.read",))
                    _assignment(cursor, user_id, app_role, "application", application_id)
                with _as_reader(connection, user_id) as request:
                    assert _all_pages(institutions, request, user_id) == []
                    assert {row["id"] for row in _all_pages(applications, request, user_id)} == {application_id}
                    assert application(request, str(user_id), application_id)["id"] == application_id
                    _hidden(institution, request, user_id, institution_id)
                    _hidden(application, request, user_id, other_application)
                raise RollBackAll()
        except RollBackAll:
            pass
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT u.status AS user_status, a.status AS assignment_status, "
                "a.valid_until FROM public.users u "
                "JOIN public.user_role_assignments a ON a.user_id = u.id WHERE a.id = %s",
                (assignment_id,),
            )
            state = cursor.fetchone()
            assert state == {"user_status": "active", "assignment_status": "active",
                             "valid_until": original_until}
            cursor.execute(
                "SELECT count(*) FROM public.roles WHERE role_code IN "
                "('DEMO_REGION_VIEWER', 'DEMO_APPLICATION_VIEWER')"
            )
            assert cursor.fetchone()["count"] == 0
            cursor.execute(
                "SELECT m.set_option, m.inherit_option FROM pg_auth_members m "
                "JOIN pg_roles granted ON granted.oid = m.roleid "
                "JOIN pg_roles member ON member.oid = m.member "
                "WHERE granted.rolname = 'aicte_api_reader' AND member.rolname = 'postgres'"
            )
            membership = cursor.fetchone()
            assert membership == {"set_option": False, "inherit_option": False}
    print("DEMO institution, region and application scopes; revoke, expiry and disabled-user checks passed; all test changes rolled back")


if __name__ == "__main__":
    main()
