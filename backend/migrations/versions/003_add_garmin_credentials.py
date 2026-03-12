"""Add Garmin credentials fields to users table.

Revision ID: add_garmin_creds
Revises: fix_chat_id_bigint
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa

revision = "add_garmin_creds"
down_revision = "fix_chat_id_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("garmin_email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("garmin_password", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "garmin_password")
    op.drop_column("users", "garmin_email")
