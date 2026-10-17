"""Shared DB-backed auth rate limiting.

Revision ID: 20261017_0024
Revises: 20261015_0023

ROLLBACK PLAN (required before production apply):
  downgrade() drops the auth_rate_limit table only. It contains no business
  data — pure ephemeral counters that rebuild themselves from traffic, so
  rolling back loses nothing and simply reverts to pre-migration behaviour.
  Verify before/after: select count(*) from auth_rate_limit (expected: 0 or
  counter rows only).
"""

import sqlalchemy as sa

from alembic import op

revision = "20261017_0024"
down_revision = "20261015_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_limit",
        sa.Column("key", sa.String(160), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("auth_rate_limit")
