"""Multi-channel communications dispatcher coordinating email and SMS dispatches (PRD §§8.1, 8.2)."""

import logging
from typing import Any

from .email_provider import render_email_template, send_email
from .sms_provider import render_dlt_sms, send_sms

logger = logging.getLogger("dispatcher")


def dispatch_event(
    event_type: str,
    recipient: dict[str, Any],
    payload: dict[str, Any],
    *, channel: str | None = None, idempotency_key: str | None = None,
) -> list[dict[str, Any]]:
    """Dispatch statutory event to appropriate external channels (Email, SMS) based on recipient details.

    Returns list of delivery attempt records: [{"channel": "email", "status": "delivered", "provider_reference": "..."}]
    """
    attempts = []
    to_email = recipient.get("email")
    phone = recipient.get("phone")

    context = {
        **payload,
        "recipient_name": recipient.get("display_name") or recipient.get("name") or "Authorized User",
    }

    # 1. Outbound Email Dispatch
    if channel in (None, 'email') and to_email and "@" in to_email and not to_email.endswith(".invalid"):
        try:
            subject, text_body, html_body = render_email_template(event_type, context)
            email_res = send_email(to_email=to_email, subject=subject, text_body=text_body, html_body=html_body, idempotency_key=idempotency_key)
            attempts.append(email_res)
        except Exception:
            logger.warning('Email dispatch outcome unknown')
            attempts.append({"channel": "email", "status": "unknown", "error": 'PROVIDER_OUTCOME_UNKNOWN'})

    # 2. Outbound SMS Dispatch (for alert events: deficiency, EVC, expiry)
    is_alert = any(k in event_type for k in ("DEFICIENCY", "EVC", "EXPIRY", "RENEWAL", "OVERDUE", "ALERT"))
    if channel in (None, 'sms') and phone and (is_alert or channel == 'sms'):
        try:
            dlt_id, sms_text = render_dlt_sms(event_type, context)
            sms_res = send_sms(phone=phone, message=sms_text, dlt_template_id=dlt_id, idempotency_key=idempotency_key)
            attempts.append(sms_res)
        except Exception:
            logger.warning('SMS dispatch outcome unknown')
            attempts.append({"channel": "sms", "status": "unknown", "error": 'PROVIDER_OUTCOME_UNKNOWN'})

    return attempts

