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

    @abstractmethod
    async def generate_digest(self, messages: list[str], language: str) -> str:
        """Generate a final digest from scored message summaries."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier for logging."""
