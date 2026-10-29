"""Provider receipt authentication and monotonic, replay-safe reconciliation."""
import hashlib
import hmac
import time


def authenticate_receipt(raw: bytes, timestamp: str, signature: str, secret: str, now=None):
    if len(secret) < 32:
        raise RuntimeError('Receipt authentication unavailable')
    if len(raw) > 16384:
        raise ValueError('Receipt too large')
    try:
        stamp = int(timestamp)
    except (ValueError, TypeError):
        raise ValueError('Invalid receipt timestamp') from None
    if abs((time.time() if now is None else now) - stamp) > 300:
        raise ValueError('Expired receipt signature')
    expected = hmac.new(secret.encode(), timestamp.encode()+b'.'+raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError('Invalid receipt signature')


def apply_receipt(cur, *, job_id, provider_event_id, provider_reference, outcome):
    from .jobs import refresh_notification
    if outcome not in ('delivered','failed'):
        raise ValueError('Invalid receipt outcome')
    cur.execute('SELECT * FROM public.notification_delivery_jobs WHERE id=%s FOR UPDATE', (job_id,))
    job = cur.fetchone()
    if not job or job['provider_reference'] != provider_reference:
        raise ValueError('Receipt has no matching provider acceptance')
    cur.execute('SELECT job_id,outcome FROM public.notification_delivery_receipts WHERE provider_event_id=%s', (provider_event_id,))
    previous = cur.fetchone()
    if previous:
        if str(previous['job_id']) != str(job_id) or previous['outcome'] != outcome:
            raise ValueError('Conflicting receipt replay')
        return False
    if job['status'] not in ('accepted','delivered','failed'):
        raise ValueError('Receipt requires accepted request')
    cur.execute('INSERT INTO public.notification_delivery_receipts(job_id,provider_event_id,outcome) VALUES(%s,%s,%s)', (job_id,provider_event_id,outcome))
    # A delayed failure receipt cannot undo a confirmed delivery.
    if job['status'] != 'delivered':
        cur.execute("UPDATE public.notification_delivery_jobs SET status=%s,delivered_at=CASE WHEN %s='delivered' THEN now() ELSE NULL END,last_error=CASE WHEN %s='failed' THEN 'PROVIDER_DELIVERY_FAILED' ELSE NULL END,updated_at=now() WHERE id=%s", (outcome,outcome,outcome,job_id))
        refresh_notification(cur,job['notification_id'])
    return True
