from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MessageScore:
    score: int
    summary: str


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Send a prompt and return raw text response."""

    @abstractmethod
    async def score_message(self, message: str, language: str) -> MessageScore:
        """Score message importance and return a 1-2 sentence summary."""

    async def score_messages_batch(
        self,
        messages: list[str],
        language: str,
    ) -> list[MessageScore]:
        """Score multiple messages; default implementation calls score_message per item."""
        results: list[MessageScore] = []
        for message in messages:
            results.append(await self.score_message(message, language))
        return results

    @abstractmethod
    async def generate_digest(
        self,
        messages: list[str],
        language: str,
        *,
        max_chars: int | None = None,
    ) -> str:
        """Generate a final digest from scored message summaries."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier for logging."""
