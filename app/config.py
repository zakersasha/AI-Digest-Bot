from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ai.context_limits import (
    capped_output_tokens,
    digest_input_char_budget,
    digest_prompt_max_chars as _digest_prompt_max_chars,
)
from app.ai.limits import DigestAiLimits


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
    openai_model: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL",
        description="Cheap model with large context (e.g. gpt-4o-mini, gpt-4.1-mini)",
    )
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

    # Local inference (gpt-oss / vLLM) — small context window
    ai_max_context_tokens: int = Field(default=4096, alias="AI_MAX_CONTEXT_TOKENS")
    ai_max_output_tokens: int = Field(default=2048, alias="AI_MAX_OUTPUT_TOKENS")
    ai_reasoning_effort: Literal["low", "medium", "high"] = Field(
        default="low",
        alias="AI_REASONING_EFFORT",
    )
    ai_score_message_max_chars: int = Field(default=300, alias="AI_SCORE_MESSAGE_MAX_CHARS")
    ai_max_messages_to_score: int = Field(default=20, alias="AI_MAX_MESSAGES_TO_SCORE")
    ai_min_message_chars: int = Field(default=40, alias="AI_MIN_MESSAGE_CHARS")

    # OpenAI API — larger digest (used when AI_PROVIDER=openai)
    ai_openai_max_context_tokens: int = Field(
        default=32000,
        alias="AI_OPENAI_MAX_CONTEXT_TOKENS",
    )
    ai_openai_max_output_tokens: int = Field(default=4096, alias="AI_OPENAI_MAX_OUTPUT_TOKENS")
    ai_openai_max_messages: int = Field(default=50, alias="AI_OPENAI_MAX_MESSAGES")
    ai_openai_message_max_chars: int = Field(default=500, alias="AI_OPENAI_MESSAGE_MAX_CHARS")

    default_timezone: str = Field(default="Europe/Moscow", alias="DEFAULT_TIMEZONE")
    catalog_channels: str = Field(default="", alias="CATALOG_CHANNELS")

    def digest_ai_limits(self) -> DigestAiLimits:
        if self.ai_provider == "openai":
            return DigestAiLimits(
                max_context_tokens=self.ai_openai_max_context_tokens,
                max_output_tokens=self.ai_openai_max_output_tokens,
                max_messages=self.ai_openai_max_messages,
                message_max_chars=self.ai_openai_message_max_chars,
                min_message_chars=self.ai_min_message_chars,
                reasoning_effort=None,
            )
        return DigestAiLimits(
            max_context_tokens=self.ai_max_context_tokens,
            max_output_tokens=self.ai_max_output_tokens,
            max_messages=self.ai_max_messages_to_score,
            message_max_chars=self.ai_score_message_max_chars,
            min_message_chars=self.ai_min_message_chars,
            reasoning_effort=self.ai_reasoning_effort,
        )

    def digest_template_chars(self) -> int:
        return 480

    def capped_output_tokens(self) -> int:
        limits = self.digest_ai_limits()
        return capped_output_tokens(limits.max_context_tokens, limits.max_output_tokens)

    def digest_input_char_budget(self) -> int:
        limits = self.digest_ai_limits()
        return digest_input_char_budget(
            limits.max_context_tokens,
            max_output_tokens=limits.max_output_tokens,
            template_chars=self.digest_template_chars(),
        )

    def digest_prompt_max_chars(self) -> int:
        limits = self.digest_ai_limits()
        return _digest_prompt_max_chars(
            limits.max_context_tokens,
            max_output_tokens=limits.max_output_tokens,
            template_chars=self.digest_template_chars(),
        )


def effective_telethon_proxy_url(settings: Settings) -> str | None:
    """Telethon uses TELEGRAM_PROXY_URL, or BOT_PROXY_URL if the former is unset."""
    return settings.telegram_proxy_url or settings.bot_proxy_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
