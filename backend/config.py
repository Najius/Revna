"""Revna — Centralized configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ─── App ────────────────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    log_level: str = "INFO"

    # ─── Database ───────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://revna:revna@localhost:5432/revna"
    redis_url: str = "redis://localhost:6379/0"

    # ─── Claude API ─────────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model_sonnet: str = "claude-sonnet-4-5-20250929"
    claude_model_haiku: str = "claude-haiku-4-5-20251001"
    claude_api_url: str = "https://api.anthropic.com/v1/messages"
    claude_max_tokens: int = 4500

    # ─── Telegram ───────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""

    # ─── Terra API (wearable data) ──────────────────────────────
    terra_api_key: str = ""
    terra_dev_id: str = ""
    terra_webhook_secret: str = ""

    # ─── Google Fit / Pixel Watch ─────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""  # e.g. https://your-domain/webhooks/google/callback

    # ─── Admin ────────────────────────────────────────────────
    admin_password: str = ""  # required — protects /admin/* endpoints

    # ─── Notification limits ────────────────────────────────────
    max_daily_notifications: int = 5
    max_burst_notifications: int = 2
    burst_window_minutes: int = 30

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def async_database_url(self) -> str:
        """Async URL for SQLAlchemy (converts Railway's postgres:// to postgresql+asyncpg://)."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic migrations."""
        url = self.database_url
        # Convert to standard postgresql:// format for psycopg2
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        elif "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        return url


settings = Settings()
