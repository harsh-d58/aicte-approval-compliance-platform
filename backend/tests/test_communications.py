"""Unit tests for outbound communications: Email, SMS, DLT templates, and Dispatcher (PRD §§8.1, 8.2)."""

from pathlib import Path
import unittest
from unittest.mock import patch

from backend.app.communications import (
    dispatch_event,
    render_dlt_sms,
    render_email_template,
    send_email,
    send_sms,
)


class CommunicationsTests(unittest.TestCase):
    def test_render_email_template_deficiency(self):
        data = {
            "application_number": "APP-2026-TEST-001",
            "institution_name": "Test Engineering College",
            "reason": "Fire Safety Certificate missing seal",
        }
        subject, text_body, html_body = render_email_template("DEFICIENCY_NOTICED", data)
        self.assertIn("APP-2026-TEST-001", subject)
        self.assertIn("Deficiency Notice Issued", subject)
        self.assertIn("Fire Safety Certificate missing seal", text_body)
        self.assertIn("14 days", text_body)
        self.assertIn("<div", html_body.lower())
        self.assertIn("APP-2026-TEST-001", html_body)

    def test_render_email_template_evc(self):
        data = {
            "application_number": "APP-2026-EVC-002",
            "institution_name": "National Polytechnic",
            "visit_date": "2026-11-15",
        }
        subject, text_body, html_body = render_email_template("EVC_SCHEDULED", data)
        self.assertIn("EVC", subject)
        self.assertIn("2026-11-15", text_body)
        self.assertIn("National Polytechnic", html_body)

    def test_render_email_template_expiry(self):
        data = {
            "institution_name": "Apex Institute",
            "document_type": "Land Title Deed",
            "expiry_date": "2026-12-31",
        }
        subject, text_body, html_body = render_email_template("DOCUMENT_EXPIRY_WARNING", data)
        self.assertIn("Statutory Expiry", subject)
        self.assertIn("Land Title Deed", text_body)
        self.assertIn("2026-12-31", html_body)

    def test_render_dlt_sms_templates(self):
        # Deficiency template
        dlt_id, text = render_dlt_sms("DEFICIENCY_ISSUED", {
            "application_number": "APP-9999",
            "institution_name": "Apex Tech",
        })
        self.assertEqual(dlt_id, "11071618293049102")
        self.assertIn("APP-9999", text)
        self.assertLessEqual(len(text), 160)

        # EVC template
        dlt_id, text = render_dlt_sms("EVC_SCHEDULED", {
            "application_number": "APP-8888",
            "visit_date": "2026-12-01",
        })
        self.assertEqual(dlt_id, "11071618293049103")
        self.assertIn("2026-12-01", text)
        self.assertLessEqual(len(text), 160)

        # Expiry template
        dlt_id, text = render_dlt_sms("EXPIRY_NOTICE", {
            "document_type": "Building NOC",
            "institution_name": "Apex Tech",
        })
        self.assertEqual(dlt_id, "11071618293049104")
        self.assertIn("Building NOC", text)
        self.assertLessEqual(len(text), 160)

        # Default template
        dlt_id, text = render_dlt_sms("GENERAL_NOTICE", {"application_number": "APP-1111"})
        self.assertEqual(dlt_id, "11071618293049101")
        self.assertIn("APP-1111", text)

    @patch.dict("os.environ", {}, clear=True)
    def test_unapproved_channels_are_blocked(self):
        for result in (send_email("test@example.invalid", "Notice", "Body"),
                       send_sms("+910000000000", "Notice", "template")):
            self.assertEqual(result["status"], "blocked")
            self.assertIsNone(result["provider_reference"])

    @patch.dict("os.environ", {"COMMUNICATIONS_EXTERNAL_ENABLED":"true",
        "COMMUNICATIONS_APPROVED_EMAILS":"approved@example.invalid",
        "COMMUNICATIONS_APPROVED_PHONES":"+910000000000",
        "SMS_DLT_ENTITY_ID":"approved-entity", "SMS_SENDER_ID":"APPROVED"}, clear=True)
    def test_missing_credentials_never_fake_delivery(self):
        self.assertEqual(send_email("approved@example.invalid","Notice","Body")["error"], "SMTP_NOT_CONFIGURED")
        self.assertEqual(send_sms("+910000000000","Notice","template")["error"], "SMS_NOT_CONFIGURED")

    @patch("backend.app.communications.email_provider.smtplib.SMTP")
    @patch.dict("os.environ", {"COMMUNICATIONS_EXTERNAL_ENABLED":"true",
        "COMMUNICATIONS_APPROVED_EMAILS":"approved@example.invalid", "SMTP_HOST":"smtp.example.invalid",
        "SMTP_USER":"test", "SMTP_PASSWORD":"test"}, clear=True)
    def test_smtp_acceptance_is_not_delivery(self, smtp):
        smtp.return_value.__enter__.return_value.sendmail.return_value = {}
        result = send_email("approved@example.invalid","Notice","Body",idempotency_key="job-1")
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["provider_reference"], "<job-1@notification.local>")

    @patch.dict("os.environ", {}, clear=True)
    def test_dispatch_event_multi_channel(self):
        attempts = dispatch_event("DEFICIENCY_NOTICED",
            {"email":"principal@example.edu","phone":"+910000000000"}, {"application_number":"APP-1"})
        self.assertEqual({a["channel"] for a in attempts}, {"email","sms"})
        self.assertTrue(all(a["status"] == "blocked" for a in attempts))

    def test_dispatch_event_skips_invalid_recipient_email(self):
        # Email ending with .invalid is skipped
        recipient = {
            "display_name": "Demo Prototype User",
            "email": "user@prototype.example.invalid",
            "phone": "+919812345678",
        }
        payload = {"application_number": "APP-2026-INV"}
        # For general notice (not alert), no SMS, and invalid email skipped -> empty attempts
        attempts = dispatch_event("GENERAL_UPDATE", recipient, payload)
        self.assertEqual(len(attempts), 0)


if __name__ == "__main__":
    unittest.main()
