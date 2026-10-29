"""Rolled-back live proof of portal supplemental mutations and authorization.

Uses the configured restricted writer. No fixture or business record survives.
Run: python -m backend.verify_portal_commands_live
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4
import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException
from .app.settings import Settings
from .app.portal_commands import PortalCommand, execute_command
from .app.portal_snapshot import snapshot


def main():
    settings = Settings.load()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)), state=SimpleNamespace(correlation_id=str(uuid4())))
    with psycopg.connect(settings.database_write_url, sslmode="require", autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT u.id,r.role_code FROM public.users u JOIN public.user_role_assignments a ON a.user_id=u.id JOIN public.roles r ON r.id=a.role_id WHERE u.status='active' AND a.status='active'")
            personas = {row["role_code"]: str(row["id"]) for row in cur.fetchall()}
        @contextmanager
        def reuse(*_):
            yield conn
        checks = []
        def run(role, builder, expected=None):
            subject = personas[role]
            with conn.transaction(force_rollback=True):
                with conn.cursor() as cur:
                    cur.execute("SELECT set_config('aicte.subject_id',%s,true)", (subject,))
                data = snapshot(conn, subject)
                command = builder(conn, data, subject)
                with patch("backend.app.portal_commands.write_transaction", reuse):
                    try:
                        result = execute_command(request, subject, PortalCommand(**command))
                        if expected:
                            raise AssertionError(f"Expected {expected}; command succeeded")
                        with conn.cursor() as cur:
                            cur.execute("SELECT count(*) AS n FROM public.audit_events WHERE correlation_id=%s", (request.state.correlation_id,))
                            assert cur.fetchone()["n"] > 0
                        checks.append(role + ": " + command["kind"] + " persisted in transaction")
                    except HTTPException as error:
                        if expected != error.status_code:
                            raise
                        checks.append(role + ": " + command["kind"] + " denied " + str(expected))
        def notification(conn, data, subject):
            target = uuid4()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO public.notifications (id,event_code,recipient_user_id,status,payload) VALUES (%s,'DEMO_VERIFY_READ',%s,'queued','{}')", (target, subject))
            return {"kind":"notification.read", "id":str(target), "values":{"read":True}}
        run("DEMO_INSTITUTION", notification)
        run("DEMO_INSTITUTION_VIEWER", lambda *_: {"kind":"notification.read", "id":str(uuid4()), "values":{"read":True}}, 403)
        run("DEMO_INSTITUTION", lambda c,d,s: {"kind":"availability.save", "values":{"participantType":"INSTITUTION", "participantId":d["institutions"][0]["id"], "startAt":(datetime.now(timezone.utc)+timedelta(days=3)).isoformat(), "endAt":(datetime.now(timezone.utc)+timedelta(days=3,hours=4)).isoformat(), "state":"AVAILABLE"}})
        run("DEMO_INSTITUTION", lambda c,d,s: {"kind":"availability.save", "values":{"participantType":"INSTITUTION", "participantId":str(uuid4()), "startAt":"2026-12-01T09:00:00Z", "endAt":"2026-12-01T12:00:00Z", "state":"AVAILABLE"}}, 404)
        run("DEMO_INSTITUTION", lambda *_: {"kind":"visit.cancel", "id":str(uuid4())}, 403)
        run("DEMO_REGIONAL", lambda *_: {"kind":"visit.cancel", "id":str(uuid4())}, 404)
        run("DEMO_REGIONAL", lambda c,d,s: {"kind":"application.assign", "id":d["applications"][0]["id"], "expectedVersion":d["applications"][0]["version"]+99, "values":{"ownerId":s,"dueAt":"2026-12-01T12:00:00Z"}}, 412)
        run("DEMO_REGIONAL", lambda c,d,s: {"kind":"application.assign", "id":d["applications"][0]["id"], "expectedVersion":d["applications"][0]["version"], "values":{"ownerId":s,"dueAt":"2026-12-01T12:00:00Z"}})
        run("DEMO_CENTRAL", lambda c,d,s: {"kind":"institution.save", "values":{"code":"DEMO-VERIFY-"+uuid4().hex[:8],"name":"DEMO rolled-back integration institution","type":"Private","regionId":d["regions"][0]["id"],"campusName":"DEMO proof campus","city":"Pune"}})
        workflow_values = {"name":"DEMO integration workflow", "aphVersion":"DEMO", "stages":[{"code":"INTAKE","name":"Intake","slaDays":3,"ownerRole":"INSTITUTION"},{"code":"SCRUTINY","name":"Scrutiny","slaDays":3,"ownerRole":"SCRUTINY"}], "transitions":[{"from":"INTAKE","to":"SCRUTINY","guards":[]}]}
        run("DEMO_POLICY", lambda *_: {"kind":"workflow.save", "values":workflow_values})
        run("DEMO_POLICY", lambda *_: {"kind":"config.save", "values":{"category":"SETTINGS","name":"DEMO proof setting","values":{"timezone":"Asia/Kolkata"}}})
        run("DEMO_POLICY", lambda *_: {"kind":"config.save", "values":{"category":"COMMITTEE","name":"DEMO proof committee","values":{"memberCount":5,"durationMinutes":180,"availabilityFreshnessHours":72,"preparationLeadHours":24}}})
        run("DEMO_SYSTEM", lambda *_: {"kind":"job.process", "id":str(uuid4())}, 422)
        print("\n".join(checks))
        print(f"{len(checks)} live checks; every transaction rolled back")
        print("VERDICT: PASS")


if __name__ == "__main__":
    main()
