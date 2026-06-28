from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.digest import Digest
    from app.models.linkedin_profile import LinkedInProfile
    from app.models.platform_settings import PlatformSettings
    from app.models.slack_channel import SlackChannel
    from app.models.source import Source


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    content_platform: Mapped[str] = mapped_column(String(16), default="telegram", server_default="telegram")
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    digest_frequency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    delivery_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_minute: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", server_default="Europe/Moscow")
    last_digest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telethon_session_encrypted: Mapped[str | None] = mapped_column(nullable=True)
    telegram_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telethon_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gmail_tokens_encrypted: Mapped[str | None] = mapped_column(nullable=True)
    gmail_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gmail_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linkedin_tokens_encrypted: Mapped[str | None] = mapped_column(nullable=True)
    linkedin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_member_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linkedin_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    slack_tokens_encrypted: Mapped[str | None] = mapped_column(nullable=True)
    slack_team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sources: Mapped[list["Source"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    digests: Mapped[list["Digest"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    platform_settings: Mapped[list["PlatformSettings"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    linkedin_profiles: Mapped[list["LinkedInProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    slack_channels: Mapped[list["SlackChannel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
