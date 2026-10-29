"""Bootstrap one approved, read-only DEMO institution viewer.

Run from repository root with --apply after the project owner's test-policy
approval. This uses the database administration credential for a controlled
bootstrap; it is not an API write path or an official AICTE grant.
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values
import psycopg

from backend.app.audit import append_event


ROOT = Path(__file__).resolve().parents[1]
ROLE_CODE = "DEMO_INSTITUTION_VIEWER"
PERMISSIONS = ("institution.read", "application.read")
INSTITUTION_CODE = "DEMO-INST-0001"
POLICY_VERSION = "DEMO-READ-V1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the approved test-only grant")
    args = parser.parse_args()
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")
    with psycopg.connect(url, sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=10000 -c lock_timeout=5000") as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM auth.users WHERE email_confirmed_at IS NOT NULL "
                           "AND is_anonymous IS FALSE")
            users = cursor.fetchall()
            if len(users) != 1:
                raise RuntimeError("Expected exactly one confirmed, non-anonymous Auth user")
            user_id = users[0][0]
            cursor.execute("SELECT id FROM public.institutions WHERE institution_code = %s",
                           (INSTITUTION_CODE,))
            institution = cursor.fetchone()
            if institution is None:
                raise RuntimeError("DEMO target institution is missing")
            institution_id = institution[0]
            cursor.execute("SELECT identity_subject, status FROM public.users WHERE id = %s", (user_id,))
            existing_user = cursor.fetchone()
            if existing_user and existing_user != (str(user_id), "active"):
                raise RuntimeError("Existing application identity does not match the approved test account")
            cursor.execute("SELECT id FROM public.roles WHERE role_code = %s", (ROLE_CODE,))
            role = cursor.fetchone()
            if role:
                cursor.execute(
                    "SELECT p.permission_code FROM public.role_permissions rp "
                    "JOIN public.permissions p ON p.id = rp.permission_id WHERE rp.role_id = %s",
                    (role[0],),
                )
                actual = {row[0] for row in cursor.fetchall()}
                if actual != set(PERMISSIONS):
                    raise RuntimeError("Existing DEMO role has an unexpected permission set")
                cursor.execute(
                    "SELECT id, status, valid_until FROM public.user_role_assignments "
                    "WHERE user_id = %s AND role_id = %s AND scope_type = 'institution' "
                    "AND scope_id = %s",
                    (user_id, role[0], institution_id),
                )
                existing_assignments = cursor.fetchall()
                if len(existing_assignments) == 1 and existing_assignments[0][1] == "active" \
                        and existing_assignments[0][2] > datetime.now(timezone.utc):
                    print("Approved DEMO institution viewer already provisioned; no changes made")
                    connection.rollback()
                    return
                if existing_assignments:
                    raise RuntimeError("Existing DEMO assignment needs manual review")
            if not args.apply:
                print("Ready: one confirmed Auth user, DEMO institution and read-only policy. "
                      "Pass --apply to provision for 30 days")
                connection.rollback()
                return

            now = datetime.now(timezone.utc)
            until = now + timedelta(days=30)
            if not existing_user:
                cursor.execute(
                    "INSERT INTO public.users (id, identity_subject, display_name, status) "
                    "VALUES (%s, %s, %s, 'active')",
                    (user_id, str(user_id), "DEMO Test Viewer"),
                )
            if not role:
                cursor.execute(
                    "INSERT INTO public.roles (role_code, role_name, description) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (ROLE_CODE, "DEMO Institution Viewer", "Test-only read access to one DEMO institution"),
                )
                role_id = cursor.fetchone()[0]
            else:
                role_id = role[0]
            for code in PERMISSIONS:
                cursor.execute(
                    "INSERT INTO public.permissions (permission_code, description) "
                    "VALUES (%s, %s) ON CONFLICT (permission_code) DO NOTHING",
                    (code, f"DEMO prototype read permission: {code}"),
                )
                cursor.execute("SELECT id FROM public.permissions WHERE permission_code = %s", (code,))
                permission_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO public.role_permissions (role_id, permission_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING", (role_id, permission_id),
                )
            cursor.execute(
                "INSERT INTO public.user_role_assignments "
                "(user_id, role_id, scope_type, scope_id, valid_from, valid_until, status) "
                "VALUES (%s, %s, 'institution', %s, %s, %s, 'active') RETURNING id",
                (user_id, role_id, institution_id, now, until),
            )
            assignment_id = cursor.fetchone()[0]
            append_event(
                cursor, actor_id=None, action="DEMO_ROLE_ASSIGNED", entity_type="user_role_assignment",
                entity_id=assignment_id, correlation_id=None,
                reason="Project owner approved test-only read policy in chat on 29 October 2026",
                metadata={"policy_version": POLICY_VERSION, "role_code": ROLE_CODE,
                          "scope_type": "institution", "scope_id": str(institution_id),
                          "valid_until": until.isoformat(), "demo_only": True},
            )
    print("Provisioned one DEMO institution viewer for 30 days with audit evidence")


if __name__ == "__main__":
    main()
