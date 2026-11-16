"""Add checkout expiry without backfilling historical orders."""

import sqlalchemy as sa

from alembic import op

revision = "20261113_0040"
down_revision = "20261109_0039"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_orders_expires_at", "orders", ["expires_at"])


def downgrade():
    op.drop_index("ix_orders_expires_at", table_name="orders")
    op.drop_column("orders", "expires_at")
