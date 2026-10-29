"""Provision ten explicitly synthetic local demo identities, never real logins.

The auth.users rows only satisfy the existing public.users foreign key. They
have no password or Supabase session and use reserved example.invalid addresses.
Actual Supabase sign-in remains untouched. Run with --apply to commit dated
prototype assignments. Credentials and signing keys never leave .secrets/.
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
from uuid import NAMESPACE_URL, UUID, uuid5

from dotenv import dotenv_values
import psycopg

from backend.app.audit import append_event
from backend.app.prototype import PERSONAS, SECRET_FILE, persona_subject

ROOT = Path(__file__).resolve().parents[1]
PERMISSIONS = {
    "INSTITUTION": ("institution.read", "institution.write", "application.read", "application.write", "document.read", "document.write", "compliance.read", "evidence.write", "evc.read", "availability.write", "report.read"),
    "SCRUTINY": ("institution.read", "application.read", "application.review", "document.read", "document.review", "deficiency.write", "report.read"),
    "REGIONAL": ("institution.read", "application.read", "application.review", "application.decide", "document.read", "document.review", "deficiency.write", "evc.read", "evc.write", "compliance.read", "compliance.write", "report.read"),
    "EVC_COORDINATOR": ("institution.read", "application.read", "document.read", "evc.read", "evc.write", "report.read"),
    "EVC_EXPERT": ("institution.read", "application.read", "document.read", "evc.read", "observation.write", "record.write", "availability.write", "report.read"),
    "COMPLIANCE": ("institution.read", "application.read", "document.read", "document.review", "compliance.read", "compliance.write", "report.read"),
    "CENTRAL": ("institution.read", "application.read", "application.review", "application.decide", "document.read", "evc.read", "compliance.read", "report.read", "audit.read", "workflow.write"),
    "POLICY": ("institution.read", "application.read", "workflow.write", "configuration.write", "report.read"),
    "AUDITOR": ("institution.read", "application.read", "document.read", "evc.read", "compliance.read", "report.read", "audit.read"),
    "SYSTEM": ("institution.read", "application.read", "user.write", "configuration.write", "job.write", "notification.write", "audit.read", "report.read"),
}


def provision(apply: bool = False):
    env = dotenv_values(ROOT / ".env")
    if not env.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required")
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=30)
    with psycopg.connect(env["DATABASE_URL"], sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=15000 -c lock_timeout=5000") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, region_id FROM public.institutions WHERE institution_code='DEMO-INST-0001'")
            institution = cur.fetchone()
            if not institution:
                raise RuntimeError("Seeded DEMO institution is missing")
            cur.execute("SELECT id FROM public.applications WHERE institution_id=%s ORDER BY application_number LIMIT 1", (institution[0],))
            application = cur.fetchone()
            if not application:
                raise RuntimeError("Seeded DEMO application is missing")
            for persona, role, name, scope_type in PERSONAS:
                subject = UUID(persona_subject(persona))
                email = f"{persona}@prototype.example.invalid"
                cur.execute("SELECT email FROM auth.users WHERE id=%s", (subject,))
                existing = cur.fetchone()
                if existing and existing[0] != email:
                    raise RuntimeError("Reserved demo identity collides with another account")
                cur.execute(
                    "INSERT INTO auth.users (id,email,email_confirmed_at,is_anonymous,created_at,updated_at,raw_app_meta_data,raw_user_meta_data) "
                    "VALUES (%s,%s,NULL,false,%s,%s,'{\"provider\":\"prototype-only\"}'::jsonb,'{\"demo_only\":true}'::jsonb) ON CONFLICT (id) DO NOTHING",
                    (subject, email, now, now))
                cur.execute(
                    "INSERT INTO public.users (id,identity_subject,display_name,email,status) VALUES (%s,%s,%s,%s,'active') "
                    "ON CONFLICT (id) DO UPDATE SET identity_subject=EXCLUDED.identity_subject, display_name=EXCLUDED.display_name, email=EXCLUDED.email",
                    (subject, str(subject), name, email))
                cur.execute(
                    "INSERT INTO public.roles (role_code,role_name,description) VALUES (%s,%s,%s) "
                    "ON CONFLICT (role_code) DO UPDATE SET role_name=EXCLUDED.role_name RETURNING id",
                    (f"DEMO_{role}", f"Prototype {role}", "Synthetic local prototype only; no official statutory grant"))
                role_id = cur.fetchone()[0]
                for code in PERMISSIONS[role]:
                    cur.execute("INSERT INTO public.permissions (permission_code,description) VALUES (%s,%s) ON CONFLICT (permission_code) DO NOTHING", (code, f"Prototype action {code}"))
                    cur.execute("INSERT INTO public.role_permissions (role_id,permission_id) SELECT %s,id FROM public.permissions WHERE permission_code=%s ON CONFLICT DO NOTHING", (role_id, code))
                scope_id = {"institution": institution[0], "region": institution[1], "application": application[0], "global": None}[scope_type]
                assignment_id = uuid5(NAMESPACE_URL, f"aicte-prototype-assignment-v1/{persona}")
                cur.execute(
                    "INSERT INTO public.user_role_assignments (id,user_id,role_id,scope_type,scope_id,valid_from,valid_until,status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,'active') ON CONFLICT (id) DO NOTHING RETURNING id",
                    (assignment_id,subject,role_id,scope_type,scope_id,now,until))
                if cur.fetchone():
                    append_event(cur, actor_id=None, action="PROTOTYPE_PERSONA_PROVISIONED", entity_type="user_role_assignment", entity_id=assignment_id,
                                 correlation_id=None, reason="Project owner requested full first-prototype demo workflows on 29 October 2026",
                                 metadata={"demo_only": True,"persona": persona,"role":role,"scope_type":scope_type,"valid_until":until.isoformat()})
                if role == "EVC_EXPERT":
                    cur.execute("INSERT INTO public.expert_profiles (user_id,expertise,eligibility_status,availability_method) SELECT %s,ARRAY['Engineering','Institutional review'],'eligible','manual' WHERE NOT EXISTS (SELECT 1 FROM public.expert_profiles WHERE user_id=%s)", (subject,subject))
            if not apply:
                conn.rollback()
                print("Prototype persona provisioning dry run passed; no rows changed")
                return
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_urlsafe(64), encoding="utf-8")
    print("Ten synthetic prototype personas provisioned with dated assignments; Supabase sign-in unchanged")


def verify():
    """Exercise live session issuance and JWT verification for every card."""
    from types import SimpleNamespace
    from backend.app.prototype import PersonaSessionRequest, create_session, verify_prototype_token
    from backend.app.settings import Settings
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=Settings.load())))
    for persona, role, _name, _scope in PERSONAS:
        session = create_session(PersonaSessionRequest(persona_id=persona), request)
        subject = verify_prototype_token(request, session["access_token"])
        if subject != persona_subject(persona):
            raise RuntimeError("Prototype token round trip failed")
        print(f"PASS {role}: active database assignment, signed session and verified subject")
    print("VERDICT: PASS")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if args.verify:
        verify()
    else:
        provision(args.apply)
