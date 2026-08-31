"""Add stripe_session_id to payments table.

Revision ID: 20260809_0002
Revises: 20260809_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260809_0002"
down_revision = "20260809_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("stripe_session_id", sa.String(128), nullable=True))
    op.create_index("ix_payments_stripe_session_id", "payments", ["stripe_session_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_stripe_session_id", table_name="payments")
    op.drop_column("payments", "stripe_session_id")
