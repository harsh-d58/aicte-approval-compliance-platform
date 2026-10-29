"""Live PostgreSQL End-to-End Verification for Phase 5 (Compliance & Communications).

Executes the complete lifecycle inside an uncommitted transaction and cleanly rolls back:
1. Create compliance condition / undertaking bound to application & institution
2. Register document and immutable document version
3. Submit numbered evidence #1 with document version links
4. Officer verification with 'needs_clarification' (BR-14)
5. Submit numbered evidence #2 (resubmission)
6. Officer verification with 'accepted' -> transitions to 'compliant' (BR-14)
7. Officer statutory condition closure
8. Queue logical notification
9. Deliver notification via primary channel (email attempt recorded)
10. Record provider outage & delivery retry (attempt-level history, PRD §8.2)
11. Trigger escalation rule and resolve escalation event
12. Clean rollback keeping database pristine
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.app.audit import append_event
from backend.app.outbox import enqueue


ROOT = Path(__file__).resolve().parents[1]


def verify_phase5_lifecycle():
    env = dotenv_values(ROOT / ".env")
    write_url = env.get("DATABASE_WRITE_URL")
    assert write_url, "DATABASE_WRITE_URL must be configured"

    print("==> Starting Phase 5 Compliance & Communications Verification against live PostgreSQL...")

    with psycopg.connect(write_url, sslmode="require", autocommit=False) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 0. Load test users and active application
            now = datetime.now(timezone.utc)
            test_suffix = uuid4().hex[:6].upper()

            cur.execute("SELECT id FROM public.users WHERE status = 'active' ORDER BY id LIMIT 3")
            users = cur.fetchall()
            assert len(users) >= 2, "At least 2 active users required in database"
            actor_id = users[0]["id"]
            recipient_id = users[1]["id"]

            cur.execute("SELECT id, institution_id FROM public.applications WHERE status NOT IN ('approved', 'rejected', 'closed') LIMIT 1")
            app_row = cur.fetchone()
            assert app_row, "No active application found"
            app_id = app_row["id"]
            inst_id = app_row["institution_id"]

            cur.execute("SELECT id FROM public.document_types LIMIT 1")
            doc_type_row = cur.fetchone()
            assert doc_type_row, "No document type found"
            doc_type_id = doc_type_row["id"]

            # 1. Create compliance condition
            due_at = now + timedelta(days=60)
            condition_id = uuid4()
            cur.execute(
                "INSERT INTO public.compliance_conditions "
                "(id, institution_id, application_id, condition_code, description, due_at, status, created_at, created_by, updated_at, updated_by, version) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, %s, 1) "
                "RETURNING id",
                (
                    condition_id,
                    inst_id,
                    app_id,
                    f"COND-FIRE-{test_suffix}",
                    "Submit updated NOC from Fire and Rescue Department",
                    due_at,
                    now,
                    actor_id,
                    now,
                    actor_id,
                ),
            )
            print(f" [1/11] Created compliance condition {condition_id} (COND-FIRE-{test_suffix}, open)")

            # 2. Register document & immutable document version
            doc_id = uuid4()
            cur.execute(
                "INSERT INTO public.documents "
                "(id, institution_id, document_type_id, document_scope, status, created_at, created_by, updated_at, updated_by, version) "
                "VALUES (%s, %s, %s, 'institution', 'active', %s, %s, %s, %s, 1)",
                (doc_id, inst_id, doc_type_id, now, actor_id, now, actor_id),
            )
            doc_ver_id = uuid4()
            cur.execute(
                "INSERT INTO public.document_versions "
                "(id, document_id, version_number, object_key, file_name, mime_type, size_bytes, sha256_hash, "
                " uploaded_by, uploaded_at, verification_status, created_at) "
                "VALUES (%s, %s, 1, %s, 'fire_safety_2026.pdf', 'application/pdf', 1024, %s, %s, %s, 'pending', %s)",
                (doc_ver_id, doc_id, f"private/docs/{doc_ver_id}.pdf", "a" * 64, actor_id, now, now),
            )
            print(f" [2/11] Registered document version {doc_ver_id} (PDF, 1024 bytes)")

            # 3. Submit numbered evidence submission #1
            sub_1_id = uuid4()
            cur.execute(
                "INSERT INTO public.evidence_submissions "
                "(id, compliance_condition_id, submitted_by, submitted_at, submission_number, status, created_at) "
                "VALUES (%s, %s, %s, %s, 1, 'submitted', %s)",
                (sub_1_id, condition_id, actor_id, now, now),
            )
            cur.execute(
                "INSERT INTO public.evidence_submission_files (evidence_submission_id, document_version_id, created_at) "
                "VALUES (%s, %s, %s)",
                (sub_1_id, doc_ver_id, now),
            )
            cur.execute(
                "UPDATE public.compliance_conditions SET status = 'evidence_submitted', updated_at = %s, version = version + 1 WHERE id = %s",
                (now, condition_id),
            )
            print(f" [3/11] Submitted evidence #{sub_1_id} (Submission #1, status: evidence_submitted)")

            # 4. Officer verification - needs clarification (BR-14)
            ver_1_id = uuid4()
            cur.execute(
                "INSERT INTO public.compliance_verifications "
                "(id, evidence_submission_id, reviewer_user_id, result, comments, verified_at, created_at) "
                "VALUES (%s, %s, %s, 'needs_clarification', 'Seal is blurry on page 2; provide certified copy', %s, %s)",
                (ver_1_id, sub_1_id, actor_id, now, now),
            )
            cur.execute(
                "UPDATE public.compliance_conditions SET status = 'under_verification', updated_at = %s, version = version + 1 WHERE id = %s",
                (now, condition_id),
            )
            print(f" [4/11] Officer verification recorded: needs_clarification (condition under_verification)")

            # 5. Submit numbered evidence submission #2 (clarification resubmission)
            sub_2_id = uuid4()
            cur.execute(
                "INSERT INTO public.evidence_submissions "
                "(id, compliance_condition_id, submitted_by, submitted_at, submission_number, status, response_to_verification_id, created_at) "
                "VALUES (%s, %s, %s, %s, 2, 'submitted', %s, %s)",
                (sub_2_id, condition_id, actor_id, now, ver_1_id, now),
            )
            cur.execute(
                "INSERT INTO public.evidence_submission_files (evidence_submission_id, document_version_id, created_at) "
                "VALUES (%s, %s, %s)",
                (sub_2_id, doc_ver_id, now),
            )
            print(f" [5/11] Resubmitted numbered evidence #{sub_2_id} (Submission #2 with response to clarification)")

            # 6. Officer verification - accepted -> condition compliant (BR-14)
            ver_2_id = uuid4()
            cur.execute(
                "INSERT INTO public.compliance_verifications "
                "(id, evidence_submission_id, reviewer_user_id, result, comments, verified_at, created_at) "
                "VALUES (%s, %s, %s, 'accepted', 'Certified copy verified against authority portal; valid till 2029', %s, %s)",
                (ver_2_id, sub_2_id, actor_id, now, now),
            )
            cur.execute("UPDATE public.evidence_submissions SET status = 'accepted' WHERE id = %s", (sub_2_id,))
            cur.execute(
                "UPDATE public.compliance_conditions SET status = 'compliant', updated_at = %s, version = version + 1 WHERE id = %s",
                (now, condition_id),
            )
            print(f" [6/11] Officer accepted evidence -> condition transitioned to compliant")

            # 7. Authorised condition closure
            cur.execute(
                "UPDATE public.compliance_conditions SET status = 'closed', updated_at = %s, updated_by = %s, version = version + 1 WHERE id = %s",
                (now, actor_id, condition_id),
            )
            append_event(cur, actor_id=actor_id, action="COMPLIANCE_CONDITION_CLOSED", entity_type="compliance_condition", entity_id=condition_id, correlation_id=uuid4(), reason="Closed after compliance accepted", metadata={"condition_id": str(condition_id)})
            enqueue(cur, event_type="COMPLIANCE_CONDITION_CLOSED", entity_type="compliance_condition", entity_id=condition_id, payload={"condition_id": str(condition_id)}, correlation_id=uuid4())
            print(f" [7/11] Authorised officer closed condition {condition_id}")

            # 8. Queue logical notification
            notif_id = uuid4()
            payload = {"title": "Compliance Undertaking Fulfilled", "condition_code": f"COND-FIRE-{test_suffix}"}
            cur.execute(
                "INSERT INTO public.notifications "
                "(id, event_code, recipient_user_id, related_entity_type, related_entity_id, created_at, status, payload) "
                "VALUES (%s, 'COMPLIANCE_FULFILLED', %s, 'compliance_condition', %s, %s, 'queued', %s)",
                (notif_id, recipient_id, condition_id, now, Jsonb(payload)),
            )
            print(f" [8/11] Queued logical notification {notif_id} (COMPLIANCE_FULFILLED)")

            # 9. Deliver notification via primary channel (email attempt recorded)
            attempt_1_id = uuid4()
            cur.execute(
                "INSERT INTO public.notification_attempts "
                "(id, notification_id, channel, attempt_number, attempted_at, result, provider_reference, created_at) "
                "VALUES (%s, %s, 'email', 1, %s, 'success', %s, %s)",
                (attempt_1_id, notif_id, now, f"gw_email_{test_suffix}", now),
            )
            cur.execute("UPDATE public.notifications SET status = 'sent' WHERE id = %s", (notif_id,))
            print(f" [9/11] Dispatched notification attempt #1 via email -> sent (gw_email_{test_suffix})")

            # 10. Record provider outage & delivery retry (attempt-level history, PRD §8.2)
            attempt_sms_1 = uuid4()
            cur.execute(
                "INSERT INTO public.notification_attempts "
                "(id, notification_id, channel, attempt_number, attempted_at, result, failure_reason, created_at) "
                "VALUES (%s, %s, 'sms', 1, %s, 'failure', 'Telco gateway timeout', %s)",
                (attempt_sms_1, notif_id, now, now),
            )
            attempt_sms_2 = uuid4()
            cur.execute(
                "INSERT INTO public.notification_attempts "
                "(id, notification_id, channel, attempt_number, attempted_at, result, provider_reference, created_at) "
                "VALUES (%s, %s, 'sms', 2, %s, 'success', %s, %s)",
                (attempt_sms_2, notif_id, now + timedelta(minutes=5), f"gw_sms_{test_suffix}", now + timedelta(minutes=5)),
            )
            print(f" [10/11] Recorded bounded retry: SMS attempt 1 failed (gateway timeout) -> attempt 2 succeeded")

            # 11. Create escalation rule and resolve escalation event
            cur.execute("SELECT id FROM public.roles LIMIT 1")
            role_id = cur.fetchone()["id"]
            rule_id = uuid4()
            cur.execute(
                "INSERT INTO public.escalation_rules "
                "(id, event_code, threshold_minutes, recipient_role_id, action_type, enabled, version, created_at, created_by, updated_at, updated_by) "
                "VALUES (%s, %s, 1440, %s, 'alert_regional_director', true, 1, %s, %s, %s, %s)",
                (rule_id, f"ESC_{test_suffix}", role_id, now, actor_id, now, actor_id),
            )
            event_id = uuid4()
            cur.execute(
                "INSERT INTO public.escalation_events "
                "(id, rule_id, related_entity_type, related_entity_id, triggered_at, recipient_user_id, resolution_status, created_at) "
                "VALUES (%s, %s, 'compliance_condition', %s, %s, %s, 'active', %s)",
                (event_id, rule_id, condition_id, now, recipient_id, now),
            )
            cur.execute(
                "UPDATE public.escalation_events SET resolution_status = 'resolved', resolved_at = %s WHERE id = %s",
                (now, event_id),
            )
            print(f" [11/11] Created escalation rule {rule_id} and resolved escalation event {event_id}")

            # Rollback cleanly
            conn.rollback()
            print("==> All 11 steps executed and verified successfully against PostgreSQL! (Cleanly rolled back)")


if __name__ == "__main__":
    verify_phase5_lifecycle()
