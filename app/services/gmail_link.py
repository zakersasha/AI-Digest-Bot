from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.repositories.user_repository import UserRepository
from app.services.gmail_service import GmailService
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def link_gmail_account(
    session: AsyncSession,
    settings: Settings,
    telegram_id: int,
    code: str,
) -> str:
    """Exchange OAuth code and save Gmail tokens. Returns linked email."""
    gmail = GmailService(settings)
    tokens, email = await gmail.complete_oauth(code)
    repo = UserRepository(session)
    await repo.get_or_create(telegram_id, None)
    saved = await repo.save_gmail_tokens(telegram_id, tokens, email)
    if not saved:
        raise ValueError("gmail_user_not_found")
    await session.commit()
    logger.info("gmail_linked", telegram_id=telegram_id, email=email)
    return email
