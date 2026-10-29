"""Rolled-back Phase 2 smoke test against one synthetic DEMO application.

Exercises a version update plus audit, outbox and completed idempotency rows in
one transaction. Both the forced-failure and successful inner paths are rolled
back before the script exits; no project data is retained or exposed.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row

from backend.app.audit import append_event, verify_event
from backend.app.concurrency import StaleVersion, bump_version, lock_versioned
from backend.app.idempotency import find_result, store_result
from backend.app.outbox import enqueue
from backend.app.transactions import idempotency_key_hash


ROOT = Path(__file__).resolve().parents[1]
OPERATION = "DEMO_ATOMIC_SMOKE"


class ForcedRollback(Exception):
    pass


def _write_all(cursor, *, user_id, application_id, version, raw_key, correlation_id):
    lock_versioned(cursor, table="applications", record_id=application_id,
                   expected_version=version)
    next_version = bump_version(cursor, table="applications", record_id=application_id,
                                expected_version=version)
    audit_id, _ = append_event(
        cursor, actor_id=user_id, action=OPERATION, entity_type="application",
        entity_id=application_id, correlation_id=correlation_id,
        reason="Rolled-back Phase 2 transaction smoke test",
        metadata={"old_version": version, "new_version": next_version, "demo_only": True},
    )
    outbox_id = enqueue(
        cursor, event_type=OPERATION, entity_type="application",
        entity_id=application_id, entity_version=next_version,
        payload={"demo_only": True}, correlation_id=correlation_id,
    )
    store_result(
        cursor, actor_id=user_id, operation=OPERATION, raw_key=raw_key,
        body={"application_id": str(application_id), "expected_version": version},
        http_status=200, response_json={"version": next_version},
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    return next_version, audit_id, outbox_id


def _absent(cursor, *, application_id, version, user_id, raw_key, audit_id, outbox_id):
    cursor.execute("SELECT version FROM public.applications WHERE id = %s", (application_id,))
    assert cursor.fetchone() == (version,), "Business version survived rollback"
    cursor.execute("SELECT count(*) FROM public.audit_events WHERE id = %s", (audit_id,))
    assert cursor.fetchone() == (0,), "Audit event survived rollback"
    cursor.execute("SELECT count(*) FROM public.outbox_events WHERE id = %s", (outbox_id,))
    assert cursor.fetchone() == (0,), "Outbox event survived rollback"
    cursor.execute(
        "SELECT count(*) FROM public.api_idempotency_records "
        "WHERE actor_id = %s AND operation = %s AND key_hash = %s",
        (user_id, OPERATION, idempotency_key_hash(raw_key)),
    )
    assert cursor.fetchone() == (0,), "Idempotency result survived rollback"


def main() -> None:
    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")
    with psycopg.connect(url, sslmode="require", connect_timeout=10,
                         options="-c statement_timeout=10000 -c lock_timeout=5000",
                         autocommit=True) as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS is required")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT u.id, a.scope_id FROM public.users u "
                "JOIN public.user_role_assignments a ON a.user_id = u.id "
                "JOIN public.roles r ON r.id = a.role_id "
                "WHERE r.role_code = 'DEMO_INSTITUTION_VIEWER' AND a.status = 'active' "
                "AND a.scope_type = 'institution'"
            )
            viewers = cursor.fetchall()
            if len(viewers) != 1:
                raise RuntimeError("Expected exactly one approved DEMO viewer")
            user_id, institution_id = viewers[0]
            cursor.execute(
                "SELECT id, version FROM public.applications "
                "WHERE institution_id = %s AND application_number LIKE 'DEMO-APP-2026-%%' "
                "ORDER BY application_number LIMIT 1",
                (institution_id,),
            )
            target = cursor.fetchone()
            if target is None:
                raise RuntimeError("DEMO application is missing")
            application_id, original_version = target

        first_key = str(uuid4())
        second_key = str(uuid4())
        failed_ids = None
        success_ids = None
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    try:
                        with connection.transaction():
                            failed_ids = _write_all(
                                cursor, user_id=user_id, application_id=application_id,
                                version=original_version, raw_key=first_key,
                                correlation_id=uuid4(),
                            )
                            raise ForcedRollback()
                    except ForcedRollback:
                        pass
                    assert failed_ids is not None
                    _absent(
                        cursor, application_id=application_id, version=original_version,
                        user_id=user_id, raw_key=first_key,
                        audit_id=failed_ids[1], outbox_id=failed_ids[2],
                    )
                    try:
                        lock_versioned(cursor, table="applications", record_id=application_id,
                                       expected_version=original_version + 1)
                    except StaleVersion:
                        pass
                    else:
                        raise AssertionError("Stale version was accepted")

                    success_ids = _write_all(
                        cursor, user_id=user_id, application_id=application_id,
                        version=original_version, raw_key=second_key,
                        correlation_id=uuid4(),
                    )
                    body = {"application_id": str(application_id),
                            "expected_version": original_version}
                    assert find_result(cursor, actor_id=user_id, operation=OPERATION,
                                       raw_key=second_key, body=body) == (200, {"version": success_ids[0]})
                    with connection.cursor(row_factory=dict_row) as audit_cursor:
                        audit_cursor.execute("SELECT * FROM public.audit_events WHERE id = %s",
                                             (success_ids[1],))
                        assert verify_event(audit_cursor.fetchone())
                    cursor.execute("SELECT count(*) FROM public.outbox_events WHERE id = %s",
                                   (success_ids[2],))
                    assert cursor.fetchone() == (1,)
                raise ForcedRollback()
        except ForcedRollback:
            pass
        assert success_ids is not None
        with connection.cursor() as cursor:
            _absent(
                cursor, application_id=application_id, version=original_version,
                user_id=user_id, raw_key=second_key,
                audit_id=success_ids[1], outbox_id=success_ids[2],
            )
    print("Version guard and atomic audit/outbox/idempotency rollback passed; no data retained")


if __name__ == "__main__":
    main()
