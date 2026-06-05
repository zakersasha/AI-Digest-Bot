from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.base import Base
from app.db.seed import seed_catalog
import app.models  # noqa: F401 — register models with metadata

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_USER_MIGRATIONS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(8)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN DEFAULT false",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_frequency VARCHAR(8)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS delivery_hour INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS delivery_minute INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'Europe/Moscow'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_digest_at TIMESTAMPTZ",
    "ALTER TABLE sources ADD COLUMN IF NOT EXISTS catalog_channel_id INTEGER",
    "ALTER TABLE sources ADD COLUMN IF NOT EXISTS telegram_peer_id BIGINT",
    "ALTER TABLE sources ALTER COLUMN catalog_channel_id DROP NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telethon_session_encrypted TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_phone VARCHAR(32)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telethon_linked_at TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS content_platform VARCHAR(16) DEFAULT 'telegram'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS gmail_tokens_encrypted TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS gmail_email VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS gmail_linked_at TIMESTAMPTZ",
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in _USER_MIGRATIONS:
            await conn.execute(text(sql))

    async with async_session_factory() as session:
        await seed_catalog(session, settings)
        await session.commit()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
