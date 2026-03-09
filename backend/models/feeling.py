"""Feeling model — subjective check-in data."""

import uuid

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Feeling(Base):
    __tablename__ = "feelings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    mood: Mapped[str | None] = mapped_column(String(30))
    energy: Mapped[str | None] = mapped_column(String(30))
    pain: Mapped[str | None] = mapped_column(String(30))
    sentiment: Mapped[str | None] = mapped_column(String(30))
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
