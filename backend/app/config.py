import os
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine correct .env file location based on project structure
_app_dir = Path(__file__).resolve().parent
_backend_dir = _app_dir.parent
_root_dir = _backend_dir.parent

_env_file = ".env"
if not os.path.exists(_env_file):
    _root_env = _root_dir / ".env"
    if _root_env.exists():
        _env_file = str(_root_env)
    else:
        _backend_env = _backend_dir / ".env"
        if _backend_env.exists():
            _env_file = str(_backend_env)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "GeoAnalytica"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_BASE_URL: str = "http://localhost"  # Used in emails / external links
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/geoanalytica"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY: str = "change-this-before-deploying-to-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str = ""  # Fernet key for API key encryption

    # ── Master / Admin Bypass ─────────────────────────────────
    MASTER_USER_EMAIL: str = "admin@geoanalytica.io"
    MASTER_USER_PASSWORD: str = "admin123"
    MASTER_PASSWORD: str = "master123"

    # ── CORS ──────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost", "http://localhost:80"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [o.strip() for o in v.split(",")]
        return v

    # ── AI ────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ── Free Tier Limits ─────────────────────────────────────────────────────
    MAX_FREE_QUERIES_PER_DAY:      int = 20
    MAX_FREE_EXPORT_ROWS:          int = 5_000
    MAX_FREE_FIELDS_PER_QUERY:     int = 5
    MAX_FREE_CONCURRENT_QUERIES:   int = 2

    # ── Pro Tier Limits ─────────────────────────────────────────────────────
    MAX_PRO_QUERIES_PER_DAY:       int = 500
    MAX_PRO_EXPORT_ROWS:           int = 500_000
    MAX_PRO_FIELDS_PER_QUERY:      int = 20
    MAX_PRO_CONCURRENT_QUERIES:    int = 10

    # ── Scraping ──────────────────────────────────────────────
    SCRAPE_TIMEOUT_SECONDS: int = 30
    HTTP_REQUEST_TIMEOUT_SECONDS: int = 15
    MAX_PARALLEL_SCRAPE_WORKERS: int = 10

    # ── Cache TTLs ────────────────────────────────────────────
    CACHE_TTL_ANNUAL_DAYS: int = 7
    CACHE_TTL_MONTHLY_HOURS: int = 24
    CACHE_TTL_NEWS_HOURS: int = 2
    CACHE_TTL_WEATHER_HOURS: int = 1

    # ── Email ─────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "GeoAnalytica"
    SMTP_FROM_EMAIL: str = "noreply@geoanalytica.io"
    SMTP_TLS: bool = True

    # ── Optional External Keys ────────────────────────────────
    BRAVE_API_KEY: str = ""
    SERP_API_KEY: str = ""

    # ── Postgres (for Docker Compose env vars) ────────────────
    POSTGRES_DB: str = "geoanalytica"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cache_ttl_annual_seconds(self) -> int:
        return self.CACHE_TTL_ANNUAL_DAYS * 86400

    @property
    def cache_ttl_monthly_seconds(self) -> int:
        return self.CACHE_TTL_MONTHLY_HOURS * 3600

    @property
    def cache_ttl_news_seconds(self) -> int:
        return self.CACHE_TTL_NEWS_HOURS * 3600

    @property
    def cache_ttl_weather_seconds(self) -> int:
        return self.CACHE_TTL_WEATHER_HOURS * 3600


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
