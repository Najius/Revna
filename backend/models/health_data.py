"""Health snapshot model — daily wearable data."""

import uuid

from sqlalchemy import Date, DateTime, Float, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_health_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    date: Mapped[Date] = mapped_column(Date)
    sleep_score: Mapped[int | None] = mapped_column(Integer)
    body_battery: Mapped[int | None] = mapped_column(Integer)
    resting_heart_rate: Mapped[int | None] = mapped_column(Integer)
    hrv_status: Mapped[float | None] = mapped_column(Float)
    avg_stress: Mapped[int | None] = mapped_column(Integer)
    total_steps: Mapped[int | None] = mapped_column(Integer)
    active_minutes: Mapped[int | None] = mapped_column(Integer)
    total_sleep_minutes: Mapped[int | None] = mapped_column(Integer)
    deep_sleep_minutes: Mapped[int | None] = mapped_column(Integer)
    light_sleep_minutes: Mapped[int | None] = mapped_column(Integer)
    rem_sleep_minutes: Mapped[int | None] = mapped_column(Integer)
    spo2_avg: Mapped[float | None] = mapped_column(Float)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
