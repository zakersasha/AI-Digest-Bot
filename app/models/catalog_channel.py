from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CatalogChannel(Base):
    """Predefined channels users can subscribe to in their digest."""

    __tablename__ = "catalog_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_source: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
