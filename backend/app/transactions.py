"""Fail-closed write transaction and stable idempotency fingerprints.

Business routes must still recheck role, scope and workflow guards inside this
transaction, then insert business state, audit and outbox rows before commit.
"""

from contextlib import contextmanager
from hashlib import sha256
import json
from typing import Any, Iterator

import psycopg


class UnsafeWriteConnection(RuntimeError):
    """The configured connection must not execute business mutations."""


@contextmanager
def write_transaction(database_url: str | None, subject: str | None = None) -> Iterator[psycopg.Connection]:
    """Open one explicit TLS transaction, rejecting known RLS-bypass roles.

    The transaction context commits on normal exit and rolls back on error.
    Table ownership, inherited privileges, grants and policies still require
    a database-owner review before a write route can use this helper.
    """
    if not database_url:
        raise UnsafeWriteConnection("A runtime database connection is required")
    with psycopg.connect(
        database_url,
        connect_timeout=15,
        sslmode="require",
        options="-c statement_timeout=30000",
        autocommit=True,
    ) as connection:
        if not connection.pgconn.ssl_in_use:
            raise UnsafeWriteConnection("TLS is required for business writes")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
            flags = cursor.fetchone()
        if flags is None or flags[0] or flags[1]:
            raise UnsafeWriteConnection("Superuser and BYPASSRLS roles cannot perform business writes")
        with connection.transaction():
            if subject:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('aicte.subject_id', %s, true)", (str(subject),))
            yield connection


def idempotency_key_hash(raw_key: str) -> str:
    """Hash a bounded client key so its raw value is never persisted."""
    if (
        not isinstance(raw_key, str)
        or not 1 <= len(raw_key) <= 200
        or any(ord(character) < 32 or ord(character) == 127 for character in raw_key)
    ):
        raise ValueError("Invalid idempotency key")
    return sha256(raw_key.encode("utf-8")).hexdigest()


def request_hash(operation: str, body: Any) -> str:
    """Hash a JSON request deterministically for same-key conflict checks."""
    if not operation or len(operation) > 128:
        raise ValueError("Invalid operation")
    canonical = json.dumps(
        {"operation": operation, "body": body},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
