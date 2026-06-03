from app.ai.base import AIProvider
from app.ai.local_provider import LocalAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.config import Settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        limits = settings.digest_ai_limits()
        logger.info(
            "openai_digest_limits",
            model=settings.openai_model,
            context_tokens=limits.max_context_tokens,
            max_messages=limits.max_messages,
        )
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )

    return LocalAIProvider(
        base_url=settings.local_ai_base_url,
        model=settings.local_ai_model,
    )
