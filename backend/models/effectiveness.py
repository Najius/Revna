"""Advice effectiveness tracking model."""

import uuid

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdviceEffectiveness(Base):
    __tablename__ = "advice_effectiveness"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    notif_type: Mapped[str | None] = mapped_column(String(50))
    readiness_before: Mapped[int | None] = mapped_column(Integer)
    sleep_before: Mapped[int | None] = mapped_column(Integer)
    readiness_after: Mapped[int | None] = mapped_column(Integer)
    sleep_after: Mapped[int | None] = mapped_column(Integer)
    delta_readiness: Mapped[int | None] = mapped_column(Integer)
    recorded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
