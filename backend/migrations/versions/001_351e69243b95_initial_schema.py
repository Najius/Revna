"""initial_schema

Revision ID: 351e69243b95
Revises:
Create Date: 2026-03-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "351e69243b95"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ─────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("telegram_chat_id", sa.BigInteger, unique=True),
        sa.Column("telegram_username", sa.String(100)),
        sa.Column("terra_user_id", sa.String(255)),
        sa.Column("wearable_type", sa.String(50)),
        sa.Column("timezone", sa.String(50), server_default="Europe/Paris"),
        sa.Column("language", sa.String(5), server_default="fr"),
        sa.Column("coaching_type", sa.String(50), server_default="wellness"),
        sa.Column("api_key", sa.String(255), unique=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── Health snapshots ──────────────────────────────────
    op.create_table(
        "health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("sleep_score", sa.Integer),
        sa.Column("body_battery", sa.Integer),
        sa.Column("resting_heart_rate", sa.Integer),
        sa.Column("hrv_status", sa.Float),
        sa.Column("avg_stress", sa.Integer),
        sa.Column("total_steps", sa.Integer),
        sa.Column("active_minutes", sa.Integer),
        sa.Column("total_sleep_minutes", sa.Integer),
        sa.Column("deep_sleep_minutes", sa.Integer),
        sa.Column("light_sleep_minutes", sa.Integer),
        sa.Column("rem_sleep_minutes", sa.Integer),
        sa.Column("spo2_avg", sa.Float),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_health_user_date"),
    )

    # ── Coach history ─────────────────────────────────────
    op.create_table(
        "coach_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("readiness_score", sa.Integer),
        sa.Column("readiness_level", sa.String(20)),
        sa.Column("health_index", sa.Integer),
        sa.Column("adaptation_summary", sa.Text),
        sa.Column("health_bilan", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_coach_user_date"),
    )

    # ── Notifications sent ────────────────────────────────
    op.create_table(
        "notifications_sent",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("notif_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("success", sa.Boolean, server_default=sa.text("true")),
    )

    # ── Conversations ─────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("msg_type", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Feelings ──────────────────────────────────────────
    op.create_table(
        "feelings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("raw_text", sa.Text),
        sa.Column("mood", sa.String(30)),
        sa.Column("energy", sa.String(30)),
        sa.Column("pain", sa.String(30)),
        sa.Column("sentiment", sa.String(30)),
        sa.Column("needs_attention", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Advice effectiveness ──────────────────────────────
    op.create_table(
        "advice_effectiveness",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("notif_type", sa.String(50)),
        sa.Column("readiness_before", sa.Integer),
        sa.Column("sleep_before", sa.Integer),
        sa.Column("readiness_after", sa.Integer),
        sa.Column("sleep_after", sa.Integer),
        sa.Column("delta_readiness", sa.Integer),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("advice_effectiveness")
    op.drop_table("feelings")
    op.drop_table("conversations")
    op.drop_table("notifications_sent")
    op.drop_table("coach_history")
    op.drop_table("health_snapshots")
    op.drop_table("users")
