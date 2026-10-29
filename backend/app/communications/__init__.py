"""Communications package supporting SMTP Email, DLT SMS, and outbox routing."""

from .dispatcher import dispatch_event
from .email_provider import render_email_template, send_email
from .sms_provider import render_dlt_sms, send_sms

__all__ = [
    "dispatch_event",
    "send_email",
    "render_email_template",
    "send_sms",
    "render_dlt_sms",
]
