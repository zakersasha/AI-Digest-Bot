from openai import AsyncOpenAI

from app.ai.base import AIProvider, MessageScore
from app.ai.local_provider import _parse_score_response
from app.ai.prompts import FINAL_DIGEST_PROMPT, MESSAGE_SCORING_PROMPT
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        client_kwargs: dict = {"api_key": api_key, "timeout": timeout}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    async def complete(self, prompt: str) -> str:
        logger.info("ai_request", provider=self.name, model=self._model)
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        logger.info("ai_response", provider=self.name, chars=len(content))
        return content.strip()

    async def score_message(self, message: str) -> MessageScore:
        prompt = MESSAGE_SCORING_PROMPT.format(message=message)
        raw = await self.complete(prompt)
        return _parse_score_response(raw)

    async def generate_digest(self, messages: list[str]) -> str:
        if not messages:
            return ""
        joined = "\n\n".join(f"- {msg}" for msg in messages)
        prompt = FINAL_DIGEST_PROMPT.format(messages=joined)
        return await self.complete(prompt)
