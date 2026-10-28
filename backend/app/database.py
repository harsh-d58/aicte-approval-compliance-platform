"""Bounded, read-only connectivity probe for the existing PostgreSQL database."""

import psycopg


def database_is_available(url: str | None) -> bool:
    if not url:
        return False
    try:
        with psycopg.connect(
            url,
            connect_timeout=8,
            sslmode="require",
            options="-c statement_timeout=3000",
        ) as connection:
            if not connection.pgconn.ssl_in_use:
                return False
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('transaction_read_only'), 1")
                return cursor.fetchone() == ("on", 1)
    except (psycopg.Error, OSError, ValueError):
        return False
