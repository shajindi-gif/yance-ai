"""Bind purchased entitlements to an explicit tenant resource.

Revision ID: 20260903_0011
Revises: 20260902_0010
"""

import sqlalchemy as sa

from alembic import op

revision = "20260903_0011"
down_revision = "20260902_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("resource_type", sa.String(40), nullable=True))
    op.add_column("orders", sa.Column("resource_id", sa.UUID(), nullable=True))
    op.create_index(
        "ix_orders_tenant_resource",
        "orders",
        ["tenant_id", "resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_tenant_resource", table_name="orders")
    op.drop_column("orders", "resource_id")
    op.drop_column("orders", "resource_type")
