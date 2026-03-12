"""Fix telegram_chat_id to BIGINT for large Telegram IDs.

Revision ID: fix_chat_id_bigint
Revises: 351e69243b95
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa

revision = "fix_chat_id_bigint"
down_revision = "351e69243b95"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "telegram_chat_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "telegram_chat_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
