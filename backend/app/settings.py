"""Local configuration. Secrets are never included in API responses or logs."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str | None = None
    database_write_url: str | None = None
    supabase_url: str | None = None
    frontend_origin: str | None = None

    @classmethod
    def load(cls) -> "Settings":
        file_values = dotenv_values(ENV_FILE) if ENV_FILE.is_file() else {}

        def value(name: str, default: str = "") -> str:
            return (os.environ.get(name) or file_values.get(name) or default).strip()

        prefix = value("API_PREFIX", "/api/v1")
        if prefix != "/api/v1":
            raise ValueError("API_PREFIX must be /api/v1 for the PRD v1 contract")
        return cls(
            app_env=value("APP_ENV", "development"),
            api_prefix=prefix,
            # The API uses the scoped runtime credential for reads and writes.
            # DATABASE_URL remains for migrations and never enters request handling.
            database_url=value("DATABASE_RUNTIME_URL") or None,
            database_write_url=value("DATABASE_WRITE_URL") or None,
            supabase_url=value("SUPABASE_URL").rstrip("/") or None,
            frontend_origin=value("FRONTEND_ORIGIN").rstrip("/") or None,
        )
