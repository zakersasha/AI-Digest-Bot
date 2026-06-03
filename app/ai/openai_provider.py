import httpx
from openai import AsyncOpenAI

from app.ai.base import AIProvider
from app.ai.context_limits import effective_output_tokens_for_prompt, truncate_text
from app.ai.prompts import SINGLE_DIGEST_PROMPT
from app.config import get_settings
from app.i18n import language_name
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
        self._http_client: httpx.AsyncClient | None = None

        client_kwargs: dict = {"api_key": api_key, "timeout": timeout}
        if base_url:
            client_kwargs["base_url"] = base_url
        if proxy_url:
            self._http_client = httpx.AsyncClient(proxy=proxy_url, timeout=timeout)
            client_kwargs["http_client"] = self._http_client
            logger.info("openai_proxy_enabled", proxy_host=_proxy_host(proxy_url))

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
        )
        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.info("ai_response", provider=self.name, chars=len(content))
        return content.strip()

    async def generate_digest(self, message_blocks: list[str], language: str) -> str:
        if not message_blocks:
            return ""
        joined = "\n\n".join(message_blocks)
        prompt = SINGLE_DIGEST_PROMPT.format(
            messages=joined,
            language_name=language_name(language),
        )
        return await self.complete(prompt)

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()


def _proxy_host(proxy_url: str) -> str:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(proxy_url)
        return parsed.hostname or "unknown"
    except Exception:
        return "unknown"
