from openai import APIConnectionError, AsyncOpenAI

from app.ai.base import AIProvider
from app.ai.openai_urls import resolve_openai_base_url
from app.ai.context_limits import effective_output_tokens_for_prompt, truncate_text
from app.ai.prompts import GMAIL_DIGEST_PROMPT, TELEGRAM_DIGEST_PROMPT
from app.config import get_settings
from app.i18n import language_name
from app.utils.http_proxy import create_httpx_client, proxy_host
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        proxy_url: str | None = None,
        timeout: float = 180.0,
    ) -> None:
        self._model = model
        self._proxy_url = proxy_url
        self._http_client = create_httpx_client(proxy_url, timeout)

        resolved_base = resolve_openai_base_url(base_url)
        client_kwargs: dict = {
            "api_key": api_key,
            "base_url": resolved_base,
            "http_client": self._http_client,
            "max_retries": 2,
        }

        logger.info("openai_client_configured", base_url=resolved_base)
        if proxy_url:
            logger.info(
                "openai_proxy_enabled",
                proxy_host=proxy_host(proxy_url),
                scheme=urlparse_scheme(proxy_url),
            )
        else:
            logger.warning("openai_proxy_disabled")

        self._client = AsyncOpenAI(**client_kwargs)

    @property
    def name(self) -> str:
        return "openai"

    async def complete(self, prompt: str) -> str:
        settings = get_settings()
        limits = settings.digest_ai_limits()
        max_prompt_chars = settings.digest_prompt_max_chars()
        prompt = truncate_text(prompt, max_prompt_chars)

        max_tokens = effective_output_tokens_for_prompt(
            limits.max_context_tokens,
            limits.max_output_tokens,
            len(prompt),
        )
        kwargs: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }

        logger.info(
            "ai_request",
            provider=self.name,
            model=self._model,
            prompt_chars=len(prompt),
            max_tokens=max_tokens,
            context_tokens=limits.max_context_tokens,
            proxy_enabled=bool(self._proxy_url),
            proxy_host=proxy_host(self._proxy_url) if self._proxy_url else None,
        )

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except APIConnectionError as exc:
            logger.error(
                "openai_connection_failed",
                error=str(exc),
                cause=str(exc.__cause__) if exc.__cause__ else None,
                proxy_enabled=bool(self._proxy_url),
                proxy_host=proxy_host(self._proxy_url) if self._proxy_url else None,
            )
            raise

        content = response.choices[0].message.content or ""
        logger.info("ai_response", provider=self.name, chars=len(content))
        return content.strip()

    async def generate_digest(
        self,
        message_blocks: list[str],
        language: str,
        *,
        platform: str = "telegram",
    ) -> str:
        if not message_blocks:
            return ""
        joined = "\n\n".join(message_blocks)
        template = GMAIL_DIGEST_PROMPT if platform == "gmail" else TELEGRAM_DIGEST_PROMPT
        prompt = template.format(
            messages=joined,
            language_name=language_name(language),
        )
        return await self.complete(prompt)

    async def aclose(self) -> None:
        await self._http_client.aclose()


def urlparse_scheme(proxy_url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(proxy_url).scheme or "unknown"
    except Exception:
        return "unknown"
