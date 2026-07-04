from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.repositories.user_repository import UserRepository
from app.services.yandex_mail_service import YandexMailService
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def link_yandex_account(
    session: AsyncSession,
    settings: Settings,
    telegram_id: int,
    code: str,
) -> str:
    yandex = YandexMailService(settings)
    tokens, email = await yandex.complete_oauth(code)
    repo = UserRepository(session)
    await repo.get_or_create(telegram_id, None)
    saved = await repo.save_yandex_tokens(telegram_id, tokens, email)
    if not saved:
        raise ValueError("yandex_user_not_found")
    await session.commit()
    logger.info("yandex_linked", telegram_id=telegram_id, email=email)
    return email
