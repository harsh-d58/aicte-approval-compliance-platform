"""Background asynchronous worker and periodic compliance/expiry scanner (PRD §§7.4, 7.5, 8, 10, 15).

Processes transactional outbox events into communication deliveries and runs
background periodic scans for statutory compliance condition deadlines and document expiries.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import sys
import time
from uuid import UUID, uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .audit import append_event
from .communications import dispatch_event
from .outbox import claim_due, mark_processed, schedule_retry
from .communications.jobs import queue_jobs, claim_jobs, record_outcome

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("outbox_worker")

ROOT = Path(__file__).resolve().parents[2]


def get_connection(write: bool = True):
    env = dotenv_values(ROOT / ".env")
    key = "DATABASE_WRITE_URL" if write else "DATABASE_RUNTIME_URL"
    url = os.environ.get(key) or env.get(key)
    if not url:
        raise RuntimeError(f"{key} must be configured")
    return psycopg.connect(url, sslmode="require", autocommit=False)


def process_single_event(cur, event):
    """Materialize channel jobs atomically; network I/O belongs to delivery workers."""
    cur.execute("SELECT id FROM public.notifications WHERE (related_entity_id=%s OR id=%s) AND status='queued' FOR UPDATE", (event['entity_id'],event['entity_id']))
    for notification in cur.fetchall():
        queue_jobs(cur, notification['id'])


def run_outbox_cycle(limit=20):
    # Persist leases before work. A failed business transaction is rolled back
    # before a fresh transaction releases its claim with bounded retry.
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            events = claim_due(cur, limit=limit, lease_seconds=60)
        conn.commit()
    processed = 0
    for event in events:
        try:
            with get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    process_single_event(cur, event)
                    if not mark_processed(cur, event['id'], event['claim_token']):
                        raise RuntimeError('Lost outbox claim')
                conn.commit()
                processed += 1
        except Exception:
            with get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    schedule_retry(cur,event['id'],event['claim_token'],delay_seconds=min(3600,5*2**event['attempt_count']),error_code='HANDOFF_FAILED')
                conn.commit()
    return processed


def run_delivery_cycle(limit=5):
    """Commit each lease before provider I/O; unknown outcomes require reconciliation."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            jobs = claim_jobs(cur, min(5, max(1, limit)))
        conn.commit()
    processed = 0
    for job in jobs:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT n.event_code,n.payload,u.display_name,u.email,u.phone FROM public.notifications n LEFT JOIN public.users u ON u.id=n.recipient_user_id WHERE n.id=%s', (job['notification_id'],))
                notification = cur.fetchone()
        # No database connection or row lock is held during provider calls.
        if notification and job['channel'] in ('email','sms'):
            results = dispatch_event(notification['event_code'],notification,notification['payload'] or {},channel=job['channel'],idempotency_key=str(job['id']))
            result = results[0] if len(results)==1 else {'status':'blocked','error':'RECIPIENT_UNAVAILABLE'}
        else:
            result = {'status':'blocked','error':'CHANNEL_UNAVAILABLE'}
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                recorded = record_outcome(cur,job,result)
            conn.commit()
            processed += int(recorded)
    return processed

def scan_compliance_deadlines() -> int:
    """Scan compliance undertakings past their due date and transition them to overdue (PRD §7.4, BR-08)."""
    now = datetime.now(timezone.utc)
    with get_connection(write=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, application_id, institution_id, condition_code, due_at "
                "FROM public.compliance_conditions "
                "WHERE status IN ('in_progress', 'evidence_submitted') "
                "AND due_at IS NOT NULL AND due_at < %s",
                (now,),
            )
            overdue_conditions = cur.fetchall()
            count = 0
            for c in overdue_conditions:
                cid = c["id"]
                cur.execute(
                    "UPDATE public.compliance_conditions SET status = 'overdue' WHERE id = %s",
                    (cid,),
                )
                append_event(
                    cur,
                    actor_id=None,
                    action="COMPLIANCE_CONDITION_OVERDUE",
                    entity_type="compliance_condition",
                    entity_id=cid,
                    correlation_id=uuid4(),
                    reason="Automated background deadline scanner",
                    metadata={"condition_code": c["condition_code"], "due_at": c["due_at"].isoformat() if c["due_at"] else None},
                )
                count += 1
                logger.info(f"Condition {cid} ({c['condition_code']}) transitioned to OVERDUE")

            conn.commit()
            return count


def scan_document_expiries() -> int:
    """Scan documents expiring within 30 days and auto-open tracked renewal cases (PRD §7.5, BR-16)."""
    now = datetime.now(timezone.utc)
    threshold = (now + timedelta(days=30)).date()
    with get_connection(write=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT d.id AS doc_id, d.institution_id, d.current_version_id, v.expiry_date, dt.document_type_code "
                "FROM public.documents d "
                "JOIN public.document_types dt ON dt.id = d.document_type_id "
                "JOIN public.document_versions v ON v.id = d.current_version_id "
                "LEFT JOIN public.document_renewal_cases rc ON rc.document_id = d.id AND rc.status = 'open' "
                "WHERE dt.supports_expiry = true "
                "AND v.expiry_date IS NOT NULL "
                "AND v.expiry_date <= %s "
                "AND rc.id IS NULL "
                "LIMIT 50",
                (threshold,),
            )
            expiring_docs = cur.fetchall()
            count = 0
            for d in expiring_docs:
                case_id = uuid4()
                due_at = now + timedelta(days=30)
                cur.execute(
                    "INSERT INTO public.document_renewal_cases "
                    "(id, document_id, current_version_id, renewal_due_at, status, created_at) "
                    "VALUES (%s, %s, %s, %s, 'open', %s)",
                    (case_id, d["doc_id"], d["current_version_id"], due_at, now),
                )
                append_event(
                    cur,
                    actor_id=None,
                    action="DOCUMENT_RENEWAL_CASE_AUTO_OPENED",
                    entity_type="document_renewal_case",
                    entity_id=case_id,
                    correlation_id=uuid4(),
                    reason="Automated 30-day statutory expiry scanner",
                    metadata={"document_id": str(d["doc_id"]), "expiry_date": str(d["expiry_date"])},
                )
                count += 1
                logger.info(f"Opened renewal case {case_id} for doc {d['doc_id']} expiring on {d['expiry_date']}")

            conn.commit()
            return count


def run_all_checks() -> dict[str, int]:
    """Execute one full pass of outbox events, compliance deadlines, and expiry scanners."""
    events = run_outbox_cycle()
    deliveries = run_delivery_cycle()
    overdue = scan_compliance_deadlines()
    renewals = scan_document_expiries()
    return {"delivery_jobs_processed": deliveries, "events_processed": events, "overdue_conditions": overdue, "renewals_opened": renewals}


def main():
    logger.info("Starting AICTE Background Outbox Worker & Compliance/Expiry Scanner...")
    run_once = "--run-once" in sys.argv

    if run_once:
        summary = run_all_checks()
        logger.info(f"Single pass complete: {summary}")
        return

    while True:
        try:
            summary = run_all_checks()
            if any(summary.values()):
                logger.info(f"Worker cycle executed: {summary}")
        except Exception as e:
            logger.error(f"Error in worker cycle: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
