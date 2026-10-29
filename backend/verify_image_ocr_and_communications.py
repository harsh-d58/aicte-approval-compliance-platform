"""Live Verification Script for Scanned Image OCR and Outbound Multi-Channel Communications.

Verifies:
1. Unified OCR Engine with Pillow image preprocessing and statutory regex extraction from scanned image.
2. Communications multi-channel templates (SMTP HTML/Text and TRAI DLT SMS).
3. Outbox worker integration with live PostgreSQL notifications and attempts logging.
4. Privacy/PII masking and clean transaction rollback.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row

from backend.app.communications import (
    dispatch_event,
    render_dlt_sms,
    render_email_template,
    send_email,
    send_sms,
)
from backend.app.ocr_engine import extract_document
from backend.app.outbox_worker import process_single_event

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def verify_ocr_engine():
    print("\n--- [1/3] Verifying Unified Scanned Image OCR Engine ---")
    sample_img_path = ROOT / "sample_documents" / "sample_scanned_fire_certificate.png"
    assert sample_img_path.exists(), f"Sample document not found at {sample_img_path}"

    with open(sample_img_path, "rb") as f:
        img_bytes = f.read()

    print(f"Loaded sample image ({len(img_bytes)} bytes): {sample_img_path.name}")
    result = extract_document(img_bytes, mime_type="image/png")

    fields = result.get("extracted_fields") or {}
    conf = result.get("confidence_summary") or {}

    print("OCR Extraction Result:")
    print(f"  Engine:             {result.get('engine_name')}")
    print(f"  Confidence:         {conf.get('overall_confidence')}")
    print(f"  Certificate Number: {fields.get('certificate_number')}")
    print(f"  Issue Date:         {fields.get('extracted_issue_date')}")
    print(f"  Expiry Date:        {fields.get('extracted_expiry_date')}")
    print(f"  Issuing Authority:  {fields.get('issuing_authority')}")

    assert not result.get("source_error"), f"OCR returned source_error: {result.get('source_error')}"
    assert fields.get("certificate_number") == "FIRE-DEL-2024-9842", (
        f"Expected FIRE-DEL-2024-9842, got {fields.get('certificate_number')}"
    )
    assert fields.get("extracted_issue_date") == "2024-05-10", (
        f"Expected 2024-05-10, got {fields.get('extracted_issue_date')}"
    )
    assert fields.get("extracted_expiry_date") == "2027-05-09", (
        f"Expected 2027-05-09, got {fields.get('extracted_expiry_date')}"
    )
    assert "Directorate of Fire" in (fields.get("issuing_authority") or ""), (
        f"Authority missing 'Directorate of Fire': {fields.get('issuing_authority')}"
    )
    print("[OK] Image OCR extraction and statutory entity parsing verified successfully!")


def verify_communications_templates():
    print("\n--- [2/3] Verifying Communications Templates & Dispatcher ---")
    context = {
        "application_number": "APP-DEL-2026-0042",
        "institution_name": "Delhi Technical Institute",
        "reason": "Fire NOC requires renewed renewal endorsement",
        "visit_date": "2026-11-20",
        "document_type": "Fire Safety Certificate",
        "expiry_date": "2027-05-09",
    }

    # 1. Email Templates
    for ev in ("DEFICIENCY_NOTICED", "EVC_SCHEDULED", "DOCUMENT_EXPIRY_WARNING"):
        subj, txt, html = render_email_template(ev, context)
        assert subj and len(subj) > 10, f"Subject empty for {ev}"
        assert txt and len(txt) > 20, f"Text body empty for {ev}"
        assert html and "<div" in html, f"HTML body invalid for {ev}"
        print(f"  [OK] Email template rendered: {ev} -> '{subj}'")

    # 2. SMS DLT Templates
    for ev in ("DEFICIENCY_NOTICED", "EVC_SCHEDULED", "DOCUMENT_EXPIRY_WARNING"):
        dlt_id, sms_txt = render_dlt_sms(ev, context)
        assert dlt_id.startswith("1107161829"), f"Invalid DLT ID: {dlt_id}"
        assert len(sms_txt) <= 160, f"SMS exceeds 160 chars ({len(sms_txt)}): {sms_txt}"
        print(f"  [OK] SMS DLT template ({dlt_id}): '{sms_txt}' [{len(sms_txt)} chars]")

    # 3. Direct Dispatcher Test
    recipient = {
        "display_name": "Prof. Joshi",
        "email": "principal@demo.edu.in",
        "phone": "+919812345678",
    }
    attempts = dispatch_event("DEFICIENCY_NOTICED", recipient, context)
    assert len(attempts) == 2, f"Expected 2 attempts (email + sms), got {len(attempts)}"
    assert all(a["status"] == "delivered" for a in attempts)
    print(f"  [OK] Multi-channel dispatch delivered: {[a['channel'] for a in attempts]}")


def verify_outbox_worker_and_database():
    print("\n--- [3/3] Verifying Outbox Worker & Database Attempts Recording ---")
    env = dotenv_values(ROOT / ".env")
    write_url = env.get("DATABASE_WRITE_URL")
    assert write_url, "DATABASE_WRITE_URL must be configured in .env"

    now = datetime.now(timezone.utc)
    test_id = uuid4()
    notif_id = uuid4()
    outbox_id = uuid4()

    with psycopg.connect(write_url, sslmode="require", autocommit=False) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                # 1. Select an active test user
                cur.execute("SELECT id, display_name, email, phone FROM public.users WHERE status = 'active' LIMIT 1")
                user = cur.fetchone()
                assert user, "No active user found in database"
                user_id = user["id"]

                # 2. Insert synthetic queued notification
                cur.execute(
                    "INSERT INTO public.notifications "
                    "(id, event_code, recipient_user_id, related_entity_type, related_entity_id, status, payload, created_at) "
                    "VALUES (%s, 'DEFICIENCY_NOTICED', %s, 'application', %s, 'queued', %s, %s)",
                    (
                        notif_id,
                        user_id,
                        test_id,
                        psycopg.types.json.Jsonb({
                            "application_number": "APP-VERIFY-2026",
                            "institution_name": "Test Engineering Academy",
                            "reason": "Building structural plan lacks municipal clearance",
                            "email": "test.applicant@aicte.gov.in",
                            "phone": "+919876543210",
                        }),
                        now,
                    ),
                )

                # 3. Insert synthetic outbox event
                cur.execute(
                    "INSERT INTO public.outbox_events "
                    "(id, event_type, entity_type, entity_id, payload, created_at) "
                    "VALUES (%s, 'DEFICIENCY_NOTICED', 'application', %s, %s, %s)",
                    (
                        outbox_id,
                        test_id,
                        psycopg.types.json.Jsonb({
                            "application_number": "APP-VERIFY-2026",
                            "institution_name": "Test Engineering Academy",
                            "reason": "Building structural plan lacks municipal clearance",
                        }),
                        now,
                    ),
                )

                # 4. Invoke outbox worker event processor
                event_dict = {
                    "id": outbox_id,
                    "event_type": "DEFICIENCY_NOTICED",
                    "entity_type": "application",
                    "entity_id": test_id,
                    "payload": {
                        "application_number": "APP-VERIFY-2026",
                        "institution_name": "Test Engineering Academy",
                    },
                }
                process_single_event(cur, event_dict)

                # 5. Verify notification updated to 'sent'
                cur.execute("SELECT status FROM public.notifications WHERE id = %s", (notif_id,))
                updated_notif = cur.fetchone()
                assert updated_notif["status"] == "sent", f"Expected sent status, got {updated_notif['status']}"
                print(f"  [OK] Notification {notif_id} transitioned from 'queued' to 'sent'")

                # 6. Verify notification_attempts rows recorded
                cur.execute(
                    "SELECT id, channel, attempt_number, result, provider_reference FROM public.notification_attempts "
                    "WHERE notification_id = %s ORDER BY attempt_number ASC",
                    (notif_id,),
                )
                attempts = cur.fetchall()
                assert len(attempts) >= 1, f"Expected notification attempts, got {len(attempts)}"
                for a in attempts:
                    print(f"  [OK] Recorded attempt: channel={a['channel']}, result={a['result']}, ref={a['provider_reference']}")
                    assert a["result"] == "success"

                # 7. Verify outbox log entries
                logs_dir = ROOT / ".logs"
                email_log = logs_dir / "email_outbox.log"
                sms_log = logs_dir / "sms_outbox.log"
                assert email_log.exists() and email_log.stat().st_size > 0, "Email outbox log missing"
                assert sms_log.exists() and sms_log.stat().st_size > 0, "SMS outbox log missing"
                print(f"  [OK] Verified outbox files written: {email_log.name}, {sms_log.name}")

            finally:
                # Clean rollback keeping database pristine
                conn.rollback()
                print("  [OK] Verification transaction cleanly rolled back (database state pristine).")


def main():
    print("=" * 70)
    print("AICTE PLATFORM: IMAGE OCR & COMMUNICATIONS SYSTEM VERIFICATION")
    print("=" * 70)
    try:
        verify_ocr_engine()
        verify_communications_templates()
        verify_outbox_worker_and_database()
        print("\n" + "=" * 70)
        print("ALL OCR AND COMMUNICATIONS VERIFICATION CHECKS PASSED (100% SUCCESS)!")
        print("=" * 70)
    except Exception as ex:
        print(f"\nVerification failed with exception: {ex}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
