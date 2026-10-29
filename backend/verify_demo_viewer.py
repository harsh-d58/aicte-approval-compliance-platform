"""Read-only database and scoped-query checks for the approved DEMO viewer."""

from pathlib import Path
from types import SimpleNamespace

from dotenv import dotenv_values
from fastapi import HTTPException
import psycopg
from psycopg.rows import dict_row

from backend.app.accounts import me, me_permissions
from backend.app.audit import verify_event
from backend.app.records import applications, institution, institutions, application


ROOT = Path(__file__).resolve().parents[1]
values = dotenv_values(ROOT / ".env")
admin_url = values.get("DATABASE_URL")
runtime_url = values.get("DATABASE_RUNTIME_URL")
if not admin_url or not runtime_url:
    raise SystemExit("Both DATABASE_URL and DATABASE_RUNTIME_URL are required")
with psycopg.connect(admin_url, sslmode="require", connect_timeout=10, row_factory=dict_row) as connection:
    connection.read_only = True
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM auth.users WHERE email_confirmed_at IS NOT NULL AND is_anonymous IS FALSE")
        subjects = cursor.fetchall()
        assert len(subjects) == 1
        subject = str(subjects[0]["id"])
        cursor.execute("SELECT id FROM public.institutions WHERE institution_code = 'DEMO-INST-0002'")
        other_institution = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM public.applications WHERE application_number = 'DEMO-APP-2026-000007'")
        other_application = cursor.fetchone()["id"]
        cursor.execute("SELECT * FROM public.audit_events WHERE action = 'DEMO_ROLE_ASSIGNED'")
        events = cursor.fetchall()
        assert len(events) == 1 and verify_event(events[0])
    connection.rollback()

request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(database_url=runtime_url))))
profile = me(request, subject)
permissions = me_permissions(request, subject)
visible_institutions = institutions(request, subject, limit=100, cursor=None, status=None)["data"]
visible_applications = applications(request, subject, limit=100, cursor=None, status=None)["data"]
assert len(profile["assignments"]) == 1
assert profile["assignments"][0]["scope_type"] == "institution"
assert {row["permission_code"] for row in permissions["data"]} == {"institution.read", "application.read"}
assert len(visible_institutions) == 1
assert len(visible_applications) == 6
for detail, target in ((institution, other_institution), (application, other_application)):
    try:
        detail(request, subject, target)
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Out-of-scope detail was visible")
print("DEMO viewer: 1 institution, 6 applications, 2 read permissions; other records denied; audit hash valid")
