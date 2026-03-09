"""Coach history model — daily coaching entries."""

import uuid

from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class CoachHistory(Base):
    __tablename__ = "coach_history"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_coach_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    date: Mapped[Date] = mapped_column(Date)
    readiness_score: Mapped[int | None] = mapped_column(Integer)
    readiness_level: Mapped[str | None] = mapped_column(String(20))
    health_index: Mapped[int | None] = mapped_column(Integer)
    adaptation_summary: Mapped[str | None] = mapped_column(Text)
    health_bilan: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
