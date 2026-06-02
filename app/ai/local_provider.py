import httpx

from app.ai.base import AIProvider
from app.ai.context_limits import truncate_text
from app.ai.prompts import SINGLE_DIGEST_PROMPT
from app.ai.response import completion_finish_reason, extract_chat_content
from app.config import get_settings
from app.i18n import language_name
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LocalAIProvider(AIProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "local"

    def _build_payload(self, prompt: str, max_tokens: int) -> dict:
        settings = get_settings()
        payload: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        if settings.ai_reasoning_effort:
            payload["reasoning_effort"] = settings.ai_reasoning_effort
        return payload

    async def _request(self, prompt: str, max_tokens: int) -> tuple[str, str | None]:
        url = f"{self._base_url}/v1/chat/completions"
        payload = self._build_payload(prompt, max_tokens)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        content = extract_chat_content(data)
        finish_reason = completion_finish_reason(data)
        return content, finish_reason

    async def complete(self, prompt: str) -> str:
        settings = get_settings()
        max_prompt_chars = settings.digest_prompt_max_chars()
        prompt = truncate_text(prompt, max_prompt_chars)

        base_tokens = settings.ai_max_output_tokens
        logger.info(
            "ai_request",
            provider=self.name,
            model=self._model,
            prompt_chars=len(prompt),
            max_tokens=base_tokens,
            reasoning_effort=settings.ai_reasoning_effort,
        )

        for attempt, token_mult in ((1, 1), (2, 2)):
            max_tokens = min(base_tokens * token_mult, 4096)
            content, finish_reason = await self._request(prompt, max_tokens)

            if content:
                logger.info("ai_response", provider=self.name, chars=len(content))
                return content

            logger.warning(
                "ai_empty_response",
                provider=self.name,
                model=self._model,
                finish_reason=finish_reason,
                max_tokens=max_tokens,
                attempt=attempt,
            )
            if finish_reason != "length" or attempt == 2:
                break

        logger.info("ai_response", provider=self.name, chars=0)
        return ""

    async def generate_digest(self, message_blocks: list[str], language: str) -> str:
        if not message_blocks:
            return ""
        joined = "\n\n".join(message_blocks)
        prompt = SINGLE_DIGEST_PROMPT.format(
            messages=joined,
            language_name=language_name(language),
        )
        return await self.complete(prompt)
