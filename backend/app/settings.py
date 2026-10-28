"""Local configuration. Secrets are never included in API responses or logs."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str | None = None
    identity_issuer_url: str | None = None
    identity_audience: str | None = None

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
            database_url=value("DATABASE_URL") or None,
            identity_issuer_url=value("IDENTITY_ISSUER_URL") or None,
            identity_audience=value("IDENTITY_AUDIENCE") or None,
        )
