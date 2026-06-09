from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class LinkedInProfile(Base):
    __tablename__ = "linkedin_profiles"
    __table_args__ = (UniqueConstraint("user_id", "profile_slug", name="uq_user_li_profile"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_url: Mapped[str] = mapped_column(String(512))
    profile_slug: Mapped[str] = mapped_column(String(255))
    profile_type: Mapped[str] = mapped_column(String(16), default="person")
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_urn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="linkedin_profiles")
