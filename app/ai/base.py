from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Send a prompt and return raw text response."""

    @abstractmethod
    async def generate_digest(self, message_blocks: list[str], language: str) -> str:
        """Generate a digest from pre-packed message blocks (one API call)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier for logging."""
