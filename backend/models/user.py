"""User model."""

import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100))
    terra_user_id: Mapped[str | None] = mapped_column(String(255))
    wearable_type: Mapped[str | None] = mapped_column(String(50))
    garmin_email: Mapped[str | None] = mapped_column(String(255))
    garmin_password: Mapped[str | None] = mapped_column(String(255))  # TODO: encrypt in production
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Paris")
    language: Mapped[str] = mapped_column(String(5), default="fr")
    coaching_type: Mapped[str] = mapped_column(String(50), default="wellness")
    api_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
