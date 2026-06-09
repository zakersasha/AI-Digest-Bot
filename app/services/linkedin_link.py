from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.repositories.user_repository import UserRepository
from app.services.linkedin_service import LinkedInService


async def link_linkedin_account(
    session: AsyncSession,
    settings: Settings,
    telegram_id: int,
    code: str,
) -> str:
    service = LinkedInService(settings)
    tokens = await service.exchange_code(code)
    info = await service.resolve_member_info(tokens)
    name = info.get("name") or info.get("given_name") or "LinkedIn"
    member_id = str(info.get("sub") or "")

    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(telegram_id)
    if not user:
        raise ValueError("user_not_found")

    await repo.save_linkedin_tokens(telegram_id, tokens, name, member_id)
    await session.commit()
    return name
