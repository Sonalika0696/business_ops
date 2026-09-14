"""Application settings, read from environment / .env (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Async DSN used by the running app (SQLAlchemy asyncpg driver).
    database_url: str = "postgresql+asyncpg://reconcile:reconcile@localhost:5432/reconcile_dev"

    # Sync DSN used only by Alembic migrations (psycopg driver).
    database_url_sync: str = "postgresql+psycopg://reconcile:reconcile@localhost:5432/reconcile_dev"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    storage_dir: str = "./storage/uploads"

    # Origins the browser-based SPA is served from (ARCHITECTURE.md §3: SPA
    # calls the API directly, cross-origin in dev since Vite runs on its own
    # port). Comma-separated; defaults cover the frontend's Vite dev server.
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def frontend_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached Settings instance — import this accessor, not Settings() directly."""
    return Settings()
