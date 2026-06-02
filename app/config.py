from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")

    database_url: str = Field(
        default="postgresql+asyncpg://digest:digest@localhost:5432/digest_bot",
        alias="DATABASE_URL",
    )

    ai_provider: Literal["local", "openai"] = Field(default="local", alias="AI_PROVIDER")

    local_ai_base_url: str = Field(
        default="http://178.170.249.108:40000",
        alias="LOCAL_AI_BASE_URL",
    )
    local_ai_model: str = Field(default="openai/gpt-oss-20b", alias="LOCAL_AI_MODEL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")

    telegram_api_id: int = Field(alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(alias="TELEGRAM_API_HASH")
    telegram_session_string: str = Field(default="", alias="TELEGRAM_SESSION_STRING")
    session_encryption_key: str = Field(default="", alias="SESSION_ENCRYPTION_KEY")
    telegram_proxy_url: str | None = Field(default=None, alias="TELEGRAM_PROXY_URL")
    telethon_connect_timeout: float = Field(default=45.0, alias="TELETHON_CONNECT_TIMEOUT")

    bot_proxy_url: str | None = Field(default=None, alias="BOT_PROXY_URL")
    bot_api_timeout: float = Field(default=60.0, alias="BOT_API_TIMEOUT")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_messages_per_source: int = Field(default=30, alias="MAX_MESSAGES_PER_SOURCE")
    min_importance_score: int = Field(default=5, alias="MIN_IMPORTANCE_SCORE")
    default_timezone: str = Field(default="Europe/Moscow", alias="DEFAULT_TIMEZONE")
    catalog_channels: str = Field(default="", alias="CATALOG_CHANNELS")


def effective_telethon_proxy_url(settings: Settings) -> str | None:
    """Telethon uses TELEGRAM_PROXY_URL, or BOT_PROXY_URL if the former is unset."""
    return settings.telegram_proxy_url or settings.bot_proxy_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
