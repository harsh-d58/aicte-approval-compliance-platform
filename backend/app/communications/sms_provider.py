"""Outbound SMS provider supporting Indian regulatory DLT templates and truthful acceptance outcomes (PRD §§8.1, 16.3)."""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4
from urllib.error import HTTPError
from .policy import send_allowed, outcome

logger = logging.getLogger("sms_provider")
LOGS_DIR = Path(__file__).resolve().parents[3] / ".logs"


def _get_sms_config():
    return {
        "gateway_url": os.environ.get("SMS_GATEWAY_URL"),
        "api_key": os.environ.get("SMS_API_KEY"),
        "sender_id": os.environ.get("SMS_SENDER_ID", "AICTEG"),
        "entity_id": os.environ.get("SMS_DLT_ENTITY_ID", "110145229000001"),
    }


def render_dlt_sms(event_type: str, data: dict) -> tuple[str, str]:
    """Format short TRAI DLT-compliant SMS string and return (dlt_template_id, message_text)."""
    app_num = data.get("application_number") or data.get("app_num") or "AICTE-APP"
    inst = (data.get("institution_name") or "Institution")[:25]

    if "DEFICIENCY" in event_type:
        dlt_id = "11071618293049102"
        text = f"AICTE Alert: Deficiency issued on application {app_num} ({inst}). Respond within 14 days on portal."
    elif "EVC" in event_type:
        dlt_id = "11071618293049103"
        date_str = data.get("visit_date") or "scheduled date"
        text = f"AICTE Notice: EVC visit scheduled for application {app_num} on {date_str}. Ensure officials present."
    elif "EXPIRY" in event_type or "RENEWAL" in event_type:
        dlt_id = "11071618293049104"
        doc = (data.get("document_type") or "Document")[:20]
        text = f"AICTE Compliance: Document '{doc}' for {inst} expires soon. Renewal case opened on portal."
    else:
        dlt_id = "11071618293049101"
        text = f"AICTE Update: Status updated for application {app_num}. Check portal for details."

    return dlt_id, text


def send_sms(phone: str, message: str, dlt_template_id: str | None = None, idempotency_key: str | None = None) -> dict:
    """Submit SMS to the configured gateway; never infer delivery from acceptance."""
    config = _get_sms_config()
    now = datetime.now(timezone.utc)

    if not send_allowed('sms', phone):
        return outcome('sms', 'blocked', 'EXTERNAL_SEND_NOT_APPROVED')
    if not dlt_template_id or not os.getenv('SMS_DLT_ENTITY_ID') or not os.getenv('SMS_SENDER_ID'):
        return outcome('sms', 'blocked', 'APPROVED_SMS_TEMPLATE_REQUIRED')
    if config["gateway_url"] and config["api_key"] and config['gateway_url'].startswith('https://'):
        # Real SMS Gateway dispatch (e.g. CDAC / NIC / MSG91)
        try:
            payload = json.dumps({
                "sender": config["sender_id"],
                "mobile": phone,
                "message": message,
                "dlt_template_id": dlt_template_id,
                "dlt_entity_id": config["entity_id"],
            }).encode("utf-8")

            req = Request(
                config["gateway_url"],
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config['api_key']}",
                    "Idempotency-Key": idempotency_key or uuid4().hex,
                },
            )
            with urlopen(req, timeout=8) as res:
                body = json.loads(res.read(65537).decode("utf-8"))

            provider_ref = body.get('message_id')
            if not isinstance(provider_ref, str) or not 1 <= len(provider_ref) <= 200 or body.get('status') not in ('accepted', 'queued'):
                return outcome('sms', 'unknown', 'SMS_UNRECOGNIZED_RESPONSE')
            logger.info('SMS request accepted')
            return outcome('sms', 'accepted', reference=provider_ref)
        except HTTPError as ex:
            return outcome('sms', 'retry' if ex.code in (429, 502, 503, 504) else 'failed', 'SMS_HTTP_REJECTED')
        except Exception:
            logger.warning('SMS outcome unknown')
            return outcome('sms', 'unknown', 'SMS_OUTCOME_UNKNOWN')

    return outcome('sms', 'blocked', 'SMS_NOT_CONFIGURED')

