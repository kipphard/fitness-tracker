"""Application configuration via pydantic-settings.

All secrets and connection strings come from the environment / a local .env file —
never hard-coded and never committed (see the deploy notes in the README).
"""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Fitness Tracker"
    debug: bool = False

    # SQLAlchemy URL, e.g. postgresql+psycopg://app:app@db:5432/fitness
    database_url: str = "postgresql+psycopg://app:app@db:5432/fitness"

    # Fernet key (encryption at rest, and the JWT signing fallback below). Required —
    # no default, so the app fails fast at startup if it is missing.
    fernet_key: str

    # Auth. JWT signing secret falls back to the Fernet key if unset, so no extra
    # server secret is required. Tokens are HS256 bearer tokens.
    jwt_secret: str | None = None
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    @property
    def effective_jwt_secret(self) -> str:
        return self.jwt_secret or self.fernet_key

    @field_validator("fernet_key")
    @classmethod
    def _validate_fernet_key(cls, value: str) -> str:
        try:
            Fernet(value.encode() if isinstance(value, str) else value)
        except Exception as exc:  # noqa: BLE001 - surface a clear config error
            raise ValueError(
                "FERNET_KEY is not a valid Fernet key. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            ) from exc
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
