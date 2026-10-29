"""Durable channel handoff. All helpers run in their caller's transaction."""
from uuid import uuid4


MAX_ATTEMPTS = 8


def queue_jobs(cur, notification_id, channels=None):
    cur.execute('SELECT n.*,u.email,u.phone FROM public.notifications n LEFT JOIN public.users u ON u.id=n.recipient_user_id WHERE n.id=%s FOR UPDATE OF n', (notification_id,))
    notification = cur.fetchone()
    if not notification:
        return []
    if channels is None:
        channels = ['email']
        if any(word in notification['event_code'] for word in ('DEFICIENCY', 'EVC', 'EXPIRY', 'RENEWAL', 'OVERDUE', 'ALERT')):
            channels.append('sms')
    for channel in channels:
        if channel not in ('email', 'sms', 'in_app'):
            raise ValueError('Unsupported channel')
        cur.execute('INSERT INTO public.notification_delivery_jobs(notification_id,channel) VALUES(%s,%s) ON CONFLICT(notification_id,channel) DO NOTHING', (notification_id, channel))
    return channels


def refresh_notification(cur, notification_id):
    # A logical notification is delivered only when every required channel has a
    # receipt. Pending/blocked failures remain visible even if one was accepted.
    cur.execute("UPDATE public.notifications n SET status=(SELECT CASE WHEN bool_and(j.status='delivered') THEN 'delivered' WHEN bool_or(j.status IN ('dead_letter','failed','unknown')) THEN 'failed' WHEN bool_or(j.status='blocked') THEN 'blocked' WHEN bool_and(j.status IN ('accepted','delivered')) THEN 'accepted' ELSE 'queued' END FROM public.notification_delivery_jobs j WHERE j.notification_id=n.id) WHERE n.id=%s AND EXISTS(SELECT 1 FROM public.notification_delivery_jobs j WHERE j.notification_id=n.id)", (notification_id,))


def claim_jobs(cur, limit):
    # A process dying during I/O cannot prove the provider did not accept. Expired
    # sending leases become unknown for operator reconciliation, never redelivery.
    cur.execute("UPDATE public.notification_delivery_jobs SET status='unknown',last_error='WORKER_INTERRUPTED_UNKNOWN',claim_token=NULL,claimed_until=NULL,updated_at=now() WHERE status='sending' AND claimed_until<=now() RETURNING notification_id")
    for row in cur.fetchall():
        refresh_notification(cur, row['notification_id'])
    cur.execute("WITH due AS (SELECT id FROM public.notification_delivery_jobs WHERE status IN ('queued','retry') AND available_at<=now() AND attempt_count<8 ORDER BY available_at,id FOR UPDATE SKIP LOCKED LIMIT %s) UPDATE public.notification_delivery_jobs j SET status='sending',claim_token=gen_random_uuid(),claimed_until=now()+interval '60 seconds',attempt_count=attempt_count+1,updated_at=now() FROM due WHERE j.id=due.id RETURNING j.*", (limit,))
    return cur.fetchall()


def record_outcome(cur, job, result):
    state = result.get('status')
    if state not in ('accepted', 'blocked', 'retry', 'failed', 'unknown'):
        state = 'unknown'  # Provider adapters cannot self-attest delivery.
    if state == 'accepted' and not result.get('provider_reference'):
        state = 'unknown'
    if state == 'retry' and job['attempt_count'] >= MAX_ATTEMPTS:
        state = 'dead_letter'
    error = result.get('error')
    # Store bounded codes only, never provider bodies/contact details.
    error = error if isinstance(error, str) and error.replace('_', '').isalnum() and len(error) <= 128 else None
    cur.execute("UPDATE public.notification_delivery_jobs SET status=%s,provider_reference=%s,last_error=%s,claim_token=NULL,claimed_until=NULL,accepted_at=CASE WHEN %s='accepted' THEN now() ELSE accepted_at END,available_at=now()+(%s*interval '1 second'),updated_at=now() WHERE id=%s AND claim_token=%s AND status='sending' RETURNING id", (state, result.get('provider_reference'), error, state, min(3600, 5 * 2 ** job['attempt_count']), job['id'], job['claim_token']))
    if not cur.fetchone():
        return False
    cur.execute('SELECT id FROM public.notifications WHERE id=%s FOR UPDATE', (job['notification_id'],))
    cur.execute('SELECT COALESCE(MAX(attempt_number),0)+1 AS number FROM public.notification_attempts WHERE notification_id=%s AND channel=%s', (job['notification_id'], job['channel']))
    attempt_number = cur.fetchone()['number']
    cur.execute("INSERT INTO public.notification_attempts(id,notification_id,channel,attempt_number,attempted_at,result,provider_reference,failure_reason,delivery_job_id,provider_status) VALUES(%s,%s,%s,%s,now(),%s,%s,%s,%s,%s)", (uuid4(), job['notification_id'], job['channel'], attempt_number, 'success' if state == 'accepted' else 'failure', result.get('provider_reference'), error, job['id'], state))
    refresh_notification(cur, job['notification_id'])
    return True
