from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.catalog_channel import CatalogChannel

DEFAULT_CATALOG = [
    ("@ai_news", "AI News", 10),
    ("@python", "Python", 20),
    ("@openai", "OpenAI", 30),
    ("@durov", "Durov", 40),
]


def parse_catalog_env(raw: str) -> list[tuple[str, str, int]]:
    """Format: @channel:Title,@channel2:Title2"""
    if not raw.strip():
        return DEFAULT_CATALOG
    items: list[tuple[str, str, int]] = []
    for idx, part in enumerate(raw.split(",")):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            handle, title = part.split(":", 1)
        else:
            handle, title = part, part.lstrip("@")
        handle = handle if handle.startswith("@") else f"@{handle}"
        items.append((handle.lower(), title.strip(), (idx + 1) * 10))
    return items or DEFAULT_CATALOG


async def seed_catalog(session: AsyncSession, settings: Settings) -> None:
    catalog = parse_catalog_env(settings.catalog_channels)
    for telegram_source, title, sort_order in catalog:
        result = await session.execute(
            select(CatalogChannel).where(CatalogChannel.telegram_source == telegram_source)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.title = title
            existing.sort_order = sort_order
            existing.is_active = True
        else:
            session.add(
                CatalogChannel(
                    telegram_source=telegram_source,
                    title=title,
                    sort_order=sort_order,
                    is_active=True,
                )
            )
    await session.flush()
