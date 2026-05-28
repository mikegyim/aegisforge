"""Application configuration loaded from env vars or a .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AEGIS_", extra="ignore")

    # Identity
    app_name: str = "AegisForge"
    environment: Literal["local", "dev", "staging", "prod"] = "local"

    # Persistence
    database_url: str = "sqlite+aiosqlite:///./aegisforge.db"

    # LLM provider config
    llm_provider: Literal["mock", "anthropic", "openai", "bedrock"] = "mock"
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    bedrock_region: str = "us-east-1"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 30

    # Safety
    enable_autonomous_actions: bool = False
    require_human_approval: bool = True

    # GitHub / GitOps
    github_token: str | None = None
    github_repository: str | None = None  # "org/repo"
    github_base_branch: str = "main"
    github_dry_run: bool = True

    # API security
    api_key: str | None = None  # if set, /events requires X-API-Key
    rate_limit_per_minute: int = 60

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = False
    otlp_endpoint: str | None = None
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
