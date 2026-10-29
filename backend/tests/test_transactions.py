"""The write boundary fails closed and retry fingerprints are stable."""

from contextlib import contextmanager
import unittest
from unittest.mock import patch

from backend.app.transactions import (
    UnsafeWriteConnection,
    idempotency_key_hash,
    request_hash,
    write_transaction,
)


class FakeConnection:
    def __init__(self, flags, tls=True):
        self.flags = flags
        self.pgconn = type("PgConn", (), {"ssl_in_use": tls})()
        self.transaction_entered = False
        self.transaction_exited_with = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self

    def execute(self, _query):
        pass

    def fetchone(self):
        return self.flags

    @contextmanager
    def transaction(self):
        self.transaction_entered = True
        try:
            yield
        except Exception as error:
            self.transaction_exited_with = type(error)
            raise
        else:
            self.transaction_exited_with = None


class TransactionTests(unittest.TestCase):
    def test_rejects_bypass_role_before_write_transaction(self):
        connection = FakeConnection((False, True))
        with patch("backend.app.transactions.psycopg.connect", return_value=connection):
            with self.assertRaises(UnsafeWriteConnection):
                with write_transaction("postgresql://unused"):
                    self.fail("Unsafe connection was yielded")
        self.assertFalse(connection.transaction_entered)

    def test_rejects_connection_without_tls_before_write_transaction(self):
        connection = FakeConnection((False, False), tls=False)
        with patch("backend.app.transactions.psycopg.connect", return_value=connection):
            with self.assertRaises(UnsafeWriteConnection):
                with write_transaction("postgresql://unused"):
                    self.fail("Unencrypted connection was yielded")
        self.assertFalse(connection.transaction_entered)

    def test_write_transaction_propagates_error_for_rollback(self):
        connection = FakeConnection((False, False))
        with patch("backend.app.transactions.psycopg.connect", return_value=connection):
            with self.assertRaisesRegex(ValueError, "guard failed"):
                with write_transaction("postgresql://unused"):
                    raise ValueError("guard failed")
        self.assertTrue(connection.transaction_entered)
        self.assertIs(connection.transaction_exited_with, ValueError)

    def test_idempotency_hashes_are_stable_and_do_not_store_raw_key(self):
        self.assertEqual(
            request_hash("application.submit", {"b": 2, "a": 1}),
            request_hash("application.submit", {"a": 1, "b": 2}),
        )
        self.assertNotEqual(
            request_hash("application.submit", {"a": 1}),
            request_hash("application.submit", {"a": 2}),
        )
        self.assertNotEqual(
            request_hash("application.submit", {"a": 1}),
            request_hash("evc.confirm", {"a": 1}),
        )
        digest = idempotency_key_hash("client-generated-key")
        self.assertEqual(len(digest), 64)
        self.assertNotIn("client-generated-key", digest)
        with self.assertRaises(ValueError):
            idempotency_key_hash("bad\nkey")


if __name__ == "__main__":
    unittest.main()
