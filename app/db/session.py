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
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS yandex_tokens_encrypted TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS yandex_email VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS yandex_linked_at TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_tokens_encrypted TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_name VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_member_id VARCHAR(64)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_linked_at TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS slack_tokens_encrypted TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS slack_team_name VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS slack_linked_at TIMESTAMPTZ",
)

_PLATFORM_SETTINGS_DDL = """
CREATE TABLE IF NOT EXISTS platform_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(16) NOT NULL,
    digest_frequency VARCHAR(8),
    delivery_hour INTEGER,
    delivery_minute INTEGER DEFAULT 0,
    last_digest_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_platform UNIQUE (user_id, platform)
)
"""


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in _USER_MIGRATIONS:
            await conn.execute(text(sql))

    async with engine.begin() as conn:
        await conn.execute(text(_PLATFORM_SETTINGS_DDL))

    async with async_session_factory() as session:
        from app.db.migrate_platform_settings import migrate_legacy_schedules

        await migrate_legacy_schedules(session)
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
