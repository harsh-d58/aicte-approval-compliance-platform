"""Outbound email provider supporting standard SMTP, TLS, HTML branding, and truthful acceptance outcomes (PRD §§8.1, 16.3)."""

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
from pathlib import Path
import smtplib
from uuid import uuid4
from .policy import send_allowed, outcome

logger = logging.getLogger("email_provider")
LOGS_DIR = Path(__file__).resolve().parents[3] / ".logs"


def _get_smtp_config():
    return {
        "host": os.environ.get("SMTP_HOST"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
        "from_email": os.environ.get("SMTP_FROM_EMAIL", "no-reply-aicte@nic.in"),
        "use_tls": os.environ.get("SMTP_TLS", "true").lower() in ("true", "1", "yes"),
    }


def render_email_template(event_type: str, data: dict) -> tuple[str, str, str]:
    """Generate statutory AICTE email subject, plain-text body, and styled HTML body."""
    app_num = data.get("application_number") or data.get("app_num") or "AICTE-APP-2026"
    inst_name = data.get("institution_name") or "Authorized Technical Institution"
    reason = data.get("reason") or "Statutory update"

    if "DEFICIENCY" in event_type:
        subject = f"AICTE Alert: Deficiency Notice Issued — {app_num}"
        text_body = (
            f"Dear Representative,\n\n"
            f"A deficiency notice has been issued for application {app_num} ({inst_name}).\n"
            f"Reason: {reason}\n"
            f"Please log in to the AICTE Portal and submit the required evidence within 14 days.\n\n"
            f"Approval & Compliance Bureau, AICTE New Delhi"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #991b1b; padding: 20px; color: white; text-align: center;">
                <h2 style="margin: 0;">AICTE Statutory Compliance Bureau</h2>
                <p style="margin: 5px 0 0; opacity: 0.9;">Deficiency Notice Alert</p>
            </div>
            <div style="padding: 24px; color: #1e293b;">
                <p>Dear Representative,</p>
                <p>A formal deficiency notice has been issued for <strong>{app_num}</strong> (<em>{inst_name}</em>).</p>
                <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 16px 0;">
                    <strong>Details:</strong> {reason}
                </div>
                <p>Please log in to your portal workspace and submit the required clarifications or documentation within <strong>14 statutory days</strong>.</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="http://localhost:3000/portal/applications" style="background-color: #0f172a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Open Application Workspace &rarr;</a>
                </div>
            </div>
            <div style="background-color: #f8fafc; padding: 12px; text-align: center; color: #64748b; font-size: 12px;">
                This is an automated regulatory notification from the AICTE Approval Platform.
            </div>
        </div>
        """
    elif "EVC" in event_type:
        visit_date = data.get("visit_date") or "Scheduled Date"
        subject = f"AICTE Notification: Expert Visit Committee (EVC) Scheduled — {app_num}"
        text_body = (
            f"Dear Representative,\n\n"
            f"An Expert Visit Committee has been scheduled for application {app_num} ({inst_name}).\n"
            f"Visit Date: {visit_date}\n\n"
            f"Ensure campus availability and designated officials are present.\n"
            f"Regional Office, AICTE"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1e3a8a; padding: 20px; color: white; text-align: center;">
                <h2 style="margin: 0;">AICTE Expert Visit Committee</h2>
                <p style="margin: 5px 0 0; opacity: 0.9;">Visit Confirmation Notice</p>
            </div>
            <div style="padding: 24px; color: #1e293b;">
                <p>Dear Representative,</p>
                <p>An Expert Visit Committee (EVC) has been scheduled for <strong>{app_num}</strong> (<em>{inst_name}</em>).</p>
                <p><strong>Scheduled Visit:</strong> {visit_date}</p>
                <p>Ensure that all required infrastructure, laboratories, and records are available for physical scrutiny.</p>
            </div>
        </div>
        """
    elif "EXPIRY" in event_type or "RENEWAL" in event_type:
        doc_type = data.get("document_type") or "Regulatory Document"
        expiry_date = data.get("expiry_date") or "Soon"
        subject = f"AICTE Compliance Alert: Document Approaching Statutory Expiry ({doc_type})"
        text_body = (
            f"Dear Representative,\n\n"
            f"Document '{doc_type}' for {inst_name} expires on {expiry_date}.\n"
            f"An automated renewal case has been opened in the portal.\n"
            f"AICTE Compliance Monitoring Bureau"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #d97706; padding: 20px; color: white; text-align: center;">
                <h2 style="margin: 0;">AICTE Document Expiry Warning</h2>
            </div>
            <div style="padding: 24px; color: #1e293b;">
                <p>Your institutional document <strong>{doc_type}</strong> expires on <strong>{expiry_date}</strong>.</p>
                <p>Submit renewed documentation in the document registry before expiry to maintain valid approval status.</p>
            </div>
        </div>
        """
    else:
        subject = f"AICTE Statutory Notification: {event_type}"
        text_body = f"Notification for {inst_name}: {reason}\nAICTE Platform"
        html_body = f"<p>Notification for <strong>{inst_name}</strong>: {reason}</p>"

    return subject, text_body, html_body


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """SMTP submission is acceptance, never a delivery receipt. No log fallback."""
    config = _get_smtp_config()
    now = datetime.now(timezone.utc)

    if not send_allowed('email', to_email):
        return outcome('email', 'blocked', 'EXTERNAL_SEND_NOT_APPROVED')
    if config["host"] and config["user"] and config["password"]:
        # Real SMTP Delivery
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = config["from_email"]
            msg["To"] = to_email
            msg["Date"] = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
            provider_ref = f"<{idempotency_key or uuid4().hex}@notification.local>"
            msg['Message-ID'] = provider_ref

            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
                if config["use_tls"]:
                    server.starttls()
                server.login(config["user"], config["password"])
                refused = server.sendmail(config["from_email"], [to_email], msg.as_string())
                if refused:
                    return outcome('email', 'failed', 'SMTP_RECIPIENT_REJECTED')

            logger.info('SMTP request accepted')
            return outcome('email', 'accepted', reference=provider_ref)
        except smtplib.SMTPResponseException as ex:
            return outcome('email', 'retry' if 400 <= ex.smtp_code < 500 else 'failed', 'SMTP_REJECTED')
        except Exception:
            # A timeout after DATA can mean acceptance. Do not blindly resend.
            logger.warning('SMTP outcome unknown')
            return outcome('email', 'unknown', 'SMTP_OUTCOME_UNKNOWN')

    return outcome('email', 'blocked', 'SMTP_NOT_CONFIGURED')
