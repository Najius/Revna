"""Conversation model — bidirectional Telegram messages."""

import uuid

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    role: Mapped[str] = mapped_column(String(10))  # 'coach' or 'user'
    text: Mapped[str] = mapped_column(Text)
    msg_type: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
