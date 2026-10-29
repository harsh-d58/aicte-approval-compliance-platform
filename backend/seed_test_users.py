"""Seed PRD-compliant test users, roles, and assignments for SIH prototype workflows.

Runs using DATABASE_URL (admin connection) to populate test personas:
- Council Admin
- Regional Officer
- Scrutiny Officer
- EVC Convener
- EVC Expert Member
- Institution User
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "sih-prd-users-v1"


def uid(kind: str, key: str):
    return uuid5(NAMESPACE_URL, f"{NAMESPACE}/{kind}/{key}")


ROLES = [
    ("COUNCIL_ADMIN", "Council Administrator", "Full statutory administrative governance across council"),
    ("REGIONAL_OFFICER", "Regional Officer", "Regional jurisdiction oversight, committee selection and actions"),
    ("SCRUTINY_OFFICER", "Scrutiny Officer", "Deficiency scrutiny and document verification authority"),
    ("EVC_EXPERT", "EVC Expert", "Expert Visit Committee panelist and report convener"),
    ("INSTITUTION_USER", "Institution Representative", "Authorized institutional applicant"),
]

USERS = [
    {
        "id": uid("user", "admin"),
        "subject": "auth_admin_demo",
        "name": "Dr. Ramesh Sharma (Council Admin)",
        "email": "council_admin@aicte.gov.in",
        "role_code": "COUNCIL_ADMIN",
        "scope_type": "global",
    },
    {
        "id": uid("user", "regional_officer"),
        "subject": "auth_ro_demo",
        "name": "Smt. Archana Deshmukh (Regional Officer)",
        "email": "ro_western@aicte.gov.in",
        "role_code": "REGIONAL_OFFICER",
        "scope_type": "global",
    },
    {
        "id": uid("user", "scrutiny_officer"),
        "subject": "auth_scrutiny_demo",
        "name": "Shri Arvind Verma (Scrutiny Officer)",
        "email": "scrutiny_officer@aicte.gov.in",
        "role_code": "SCRUTINY_OFFICER",
        "scope_type": "global",
    },
    {
        "id": uid("user", "evc_convener"),
        "subject": "auth_convener_demo",
        "name": "Prof. K. Ramanathan (EVC Convener)",
        "email": "evc_convener@aicte.gov.in",
        "role_code": "EVC_EXPERT",
        "scope_type": "global",
    },
    {
        "id": uid("user", "evc_member"),
        "subject": "auth_expert_demo",
        "name": "Dr. Sunita Patil (EVC Expert Member)",
        "email": "evc_expert@aicte.gov.in",
        "role_code": "EVC_EXPERT",
        "scope_type": "global",
    },
    {
        "id": uid("user", "inst_principal"),
        "subject": "auth_principal_demo",
        "name": "Prof. Rajesh Joshi (Principal Demo Inst)",
        "email": "principal@demo.edu.in",
        "role_code": "INSTITUTION_USER",
        "scope_type": "global",
    },
]


def seed_test_users():
    env = dotenv_values(ROOT / ".env")
    db_url = env.get("DATABASE_URL")
    assert db_url, "DATABASE_URL is required"

    now = datetime.now(timezone.utc)
    print("==> Seeding PRD test personas, roles, and assignments...")

    with psycopg.connect(db_url, sslmode="require", autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Seed Roles
            role_ids = {}
            for code, name, desc in ROLES:
                cur.execute(
                    "INSERT INTO public.roles (role_code, role_name, description) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (role_code) DO UPDATE SET role_name = EXCLUDED.role_name "
                    "RETURNING id, role_code",
                    (code, name, desc),
                )
                r = cur.fetchone()
                role_ids[code] = r["id"]
                print(f"  Role synced: {code} -> {r['id']}")

            # 2. Seed Users & Role Assignments
            for u in USERS:
                cur.execute(
                    "INSERT INTO auth.users (id, email, email_confirmed_at, is_anonymous, created_at, updated_at) "
                    "VALUES (%s, %s, %s, false, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, updated_at = %s",
                    (u["id"], u["email"], now, now, now, now),
                )
                cur.execute(
                    "INSERT INTO public.users "
                    "(id, identity_subject, display_name, status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, 'active', %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = %s "
                    "RETURNING id",
                    (u["id"], u["subject"], u["name"], now, now, now),
                )
                user_id = cur.fetchone()["id"]

                role_id = role_ids[u["role_code"]]
                cur.execute(
                    "INSERT INTO public.user_role_assignments "
                    "(id, user_id, role_id, scope_type, scope_id, valid_from, status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, NULL, %s, 'active', %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (uid("assignment", str(u["id"])), user_id, role_id, u["scope_type"], now, now, now),
                )
                print(f"  User synced: {u['name']} ({u['role_code']}) -> {user_id}")

    print("==> PRD test personas successfully seeded!")


if __name__ == "__main__":
    seed_test_users()
