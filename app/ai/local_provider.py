import httpx

from app.ai.base import AIProvider, MessageScore
from app.ai.context_limits import chars_for_tokens, fit_items_to_budget, truncate_text
from app.ai.prompts import BATCH_SCORING_PROMPT, FINAL_DIGEST_PROMPT, MESSAGE_SCORING_PROMPT
from app.ai.response import extract_chat_content
from app.ai.scoring import (
    batch_response_usable,
    format_batch_messages,
    parse_batch_score_response,
    parse_score_response,
)
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

    async def complete(self, prompt: str) -> str:
        settings = get_settings()
        max_prompt_chars = chars_for_tokens(settings.ai_max_context_tokens - 700)
        prompt = truncate_text(prompt, max_prompt_chars)

        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": min(700, settings.ai_max_context_tokens // 2),
        }

        logger.info("ai_request", provider=self.name, model=self._model, prompt_chars=len(prompt))
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        content = extract_chat_content(data)
        if not content:
            logger.warning("ai_empty_response", provider=self.name, model=self._model)
        logger.info("ai_response", provider=self.name, chars=len(content))
        return content

    async def score_message(self, message: str, language: str) -> MessageScore:
        prompt = MESSAGE_SCORING_PROMPT.format(
            message=message,
            language_name=language_name(language),
        )
        raw = await self.complete(prompt)
        return parse_score_response(raw)

    async def score_messages_batch(
        self,
        messages: list[str],
        language: str,
    ) -> list[MessageScore]:
        if not messages:
            return []
        if len(messages) == 1:
            return [await self.score_message(messages[0], language)]

        joined = format_batch_messages(messages)
        prompt = BATCH_SCORING_PROMPT.format(
            messages=joined,
            language_name=language_name(language),
        )
        raw = await self.complete(prompt)
        if not batch_response_usable(raw, len(messages)):
            logger.warning(
                "batch_scoring_fallback",
                provider=self.name,
                batch_size=len(messages),
                response_chars=len(raw),
            )
            return [await self.score_message(text, language) for text in messages]
        return parse_batch_score_response(raw, len(messages))

    async def generate_digest(
        self,
        messages: list[str],
        language: str,
        *,
        max_chars: int | None = None,
    ) -> str:
        if not messages:
            return ""
        settings = get_settings()
        budget = max_chars or chars_for_tokens(settings.ai_digest_input_tokens)
        trimmed = fit_items_to_budget(messages, budget)
        joined = "\n\n".join(f"---\n{msg}" for msg in trimmed)
        prompt = FINAL_DIGEST_PROMPT.format(
            messages=joined,
            language_name=language_name(language),
        )
        return await self.complete(prompt)
