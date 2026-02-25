"""Application configuration using pydantic-settings.

All settings can be overridden via environment variables prefixed with MMIP_.
Example: MMIP_DEBUG=true, MMIP_DATABASE_URL=postgresql://...
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the MMIP application.

    Settings are loaded from environment variables with the MMIP_ prefix.
    A .env file in the working directory is also supported.
    """

    model_config = SettingsConfigDict(
        env_prefix="MMIP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql://mmip:mmip@localhost:5432/mmip"

    # Redis / Celery broker
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-a1b2c3d4e5f6g7h8i9j0"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate limiting
    API_RATE_LIMIT: int = 1000

    # Application metadata
    APP_NAME: str = "MMIP - Manga Market Intelligence Platform"
    DEBUG: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
