"""Add Google refresh token field to users table.

Revision ID: add_google_token
Revises: add_garmin_creds
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa

revision = "add_google_token"
down_revision = "add_garmin_creds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_refresh_token", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "google_refresh_token")
