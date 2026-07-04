import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.ai.base import AIProvider
from app.ai.context_limits import effective_output_tokens_for_prompt, truncate_text
from app.ai.openai_slots import OpenAISlot
from app.ai.openai_urls import resolve_openai_base_url
from app.ai.prompts import (
    COMBINED_DIGEST_PROMPT,
    GMAIL_DIGEST_PROMPT,
    YANDEX_DIGEST_PROMPT,
    LINKEDIN_DIGEST_PROMPT,
    SLACK_DIGEST_PROMPT,
    TELEGRAM_DIGEST_PROMPT,
)
from app.config import get_settings
from app.i18n import language_name, t
from app.utils.http_proxy import create_httpx_client, proxy_host
from app.utils.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in _RETRYABLE_STATUS:
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True
    return False


def urlparse_scheme(proxy_url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(proxy_url).scheme or "unknown"
    except Exception:
        return "unknown"


class _SlotClient:
    def __init__(
        self,
        slot: OpenAISlot,
        *,
        base_url: str,
        timeout: float,
    ) -> None:
        self.slot = slot
        self._http_client = create_httpx_client(slot.proxy_url, timeout)
        self._client = AsyncOpenAI(
            api_key=slot.api_key,
            base_url=base_url,
            http_client=self._http_client,
            max_retries=0,
        )

    async def aclose(self) -> None:
        await self._http_client.aclose()


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        slots: list[OpenAISlot],
        model: str,
        base_url: str | None = None,
        timeout: float = 180.0,
    ) -> None:
        if not slots:
            raise ValueError("At least one OpenAI slot is required")

        self._model = model
        self._resolved_base = resolve_openai_base_url(base_url)
        self._timeout = timeout
        self._slots = slots
        self._next_start = 0
        self._clients: dict[int, _SlotClient] = {}

        for slot in slots:
            logger.info(
                "openai_slot_configured",
                slot=slot.index,
                base_url=self._resolved_base,
                proxy_enabled=bool(slot.proxy_url),
                proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                scheme=urlparse_scheme(slot.proxy_url) if slot.proxy_url else None,
            )

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self, slot: OpenAISlot) -> _SlotClient:
        cached = self._clients.get(slot.index)
        if cached:
            return cached
        client = _SlotClient(slot, base_url=self._resolved_base, timeout=self._timeout)
        self._clients[slot.index] = client
        return client

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

        last_exc: Exception | None = None
        n = len(self._slots)

        for offset in range(n):
            slot_idx = (self._next_start + offset) % n
            slot = self._slots[slot_idx]
            client = self._get_client(slot)

            logger.info(
                "ai_request",
                provider=self.name,
                model=self._model,
                slot=slot.index,
                prompt_chars=len(prompt),
                max_tokens=max_tokens,
                context_tokens=limits.max_context_tokens,
                proxy_enabled=bool(slot.proxy_url),
                proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
            )

            try:
                response = await client._client.chat.completions.create(**kwargs)
            except Exception as exc:
                if not _is_retryable(exc) or offset == n - 1:
                    logger.error(
                        "openai_request_failed",
                        slot=slot.index,
                        error=str(exc),
                        retryable=_is_retryable(exc),
                        proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                    )
                    raise
                last_exc = exc
                logger.warning(
                    "openai_slot_failed",
                    slot=slot.index,
                    error=str(exc),
                    next_slot=self._slots[(slot_idx + 1) % n].index,
                    proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                )
                continue

            self._next_start = (slot_idx + 1) % n
            content = response.choices[0].message.content or ""
            logger.info(
                "ai_response",
                provider=self.name,
                slot=slot.index,
                chars=len(content),
                next_slot=self._next_start,
            )
            return content.strip()

        if last_exc:
            raise last_exc
        return ""

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
        templates = {
            "gmail": GMAIL_DIGEST_PROMPT,
            "yandex": YANDEX_DIGEST_PROMPT,
            "linkedin": LINKEDIN_DIGEST_PROMPT,
            "slack": SLACK_DIGEST_PROMPT,
            "telegram": TELEGRAM_DIGEST_PROMPT,
            "combined": COMBINED_DIGEST_PROMPT,
        }
        template = templates.get(platform, TELEGRAM_DIGEST_PROMPT)
        prompt = template.format(
            messages=joined,
            language_name=language_name(language),
            link_label=t(language, "digest_link_label"),
        )
        return await self.complete(prompt)

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
