from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.repositories.user_repository import UserRepository
from app.services.slack_service import SlackService
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def link_slack_account(
    session: AsyncSession,
    settings: Settings,
    telegram_id: int,
    code: str,
) -> str:
    """Exchange OAuth code and save Slack tokens. Returns linked team name."""
    slack = SlackService(settings)
    tokens, team_name = await slack.complete_oauth(code)
    repo = UserRepository(session)
    await repo.get_or_create(telegram_id, None)
    saved = await repo.save_slack_tokens(telegram_id, tokens, team_name)
    if not saved:
        raise ValueError("slack_user_not_found")
    await session.commit()
    logger.info("slack_linked", telegram_id=telegram_id, team=team_name)
    return team_name
