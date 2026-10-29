"""Explicit external-send authorization; no credentials imply recipient consent."""
import os


def send_allowed(channel: str, recipient: str) -> bool:
    if os.getenv('COMMUNICATIONS_EXTERNAL_ENABLED', '').lower() != 'true':
        return False
    approved = {value.strip().casefold() for value in os.getenv(
        'COMMUNICATIONS_APPROVED_EMAILS' if channel == 'email' else 'COMMUNICATIONS_APPROVED_PHONES', ''
    ).split(',') if value.strip()}
    return recipient.casefold() in approved


def outcome(channel, status, error=None, reference=None):
    return {'channel': channel, 'status': status, 'error': error, 'provider_reference': reference}
