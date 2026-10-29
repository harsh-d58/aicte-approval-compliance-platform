"""Row-version guards for the first versioned PRD records.

Call both functions inside one write transaction. A lock is held until that
transaction ends; the caller still has to enforce role, scope and workflow
guards before changing any business fields.
"""

from uuid import UUID

from psycopg import sql


VERSIONED_TABLES = frozenset({"applications", "institutions", "documents"})


class RecordMissing(LookupError):
    """No record exists with this ID; do not reveal hidden records to callers."""


class StaleVersion(ValueError):
    """The client's expected version does not match the locked row."""


def _table_name(table: str) -> sql.Identifier:
    if table not in VERSIONED_TABLES:
        raise ValueError("Unsupported versioned table")
    return sql.Identifier(table)


def _expected_version(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("Expected version must be a positive integer")
    return value


def lock_versioned(cursor, *, table: str, record_id: UUID, expected_version: int) -> int:
    """Lock a row and reject a stale version before business validation."""
    name = _table_name(table)
    expected = _expected_version(expected_version)
    cursor.execute(
        sql.SQL("SELECT version FROM public.{} WHERE id = %s FOR UPDATE").format(name),
        (record_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise RecordMissing("Record not found")
    version = row["version"] if isinstance(row, dict) else row[0]
    if version != expected:
        raise StaleVersion("Record version is stale")
    return expected


def bump_version(cursor, *, table: str, record_id: UUID, expected_version: int) -> int:
    """Advance one locked version; zero updated rows means a competing edit."""
    name = _table_name(table)
    expected = _expected_version(expected_version)
    cursor.execute(
        sql.SQL(
            "UPDATE public.{} SET version = version + 1 "
            "WHERE id = %s AND version = %s RETURNING version"
        ).format(name),
        (record_id, expected),
    )
    row = cursor.fetchone()
    if row is None:
        raise StaleVersion("Record version changed during update")
    return row["version"] if isinstance(row, dict) else row[0]
