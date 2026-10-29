"""Bounded, read-only connectivity probe for the existing PostgreSQL database."""

import psycopg


def database_is_available(url: str | None) -> bool:
    if not url:
        return False
    try:
        with psycopg.connect(
            url,
            connect_timeout=15,
            sslmode="require",
            options="-c statement_timeout=30000",
        ) as connection:
            if not connection.pgconn.ssl_in_use:
                return False
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_setting('transaction_read_only'), current_user, "
                    "rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                )
                return cursor.fetchone() == ("on", "aicte_api_reader", False, False)
    except (psycopg.Error, OSError, ValueError):
        return False
