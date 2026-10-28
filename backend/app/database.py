"""Bounded, read-only connectivity probe for the existing PostgreSQL database."""

import psycopg


def database_is_available(url: str | None) -> bool:
    if not url:
        return False
    try:
        with psycopg.connect(
            url,
            connect_timeout=3,
            options="-c default_transaction_read_only=on -c statement_timeout=3000",
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except (psycopg.Error, OSError, ValueError):
        return False
