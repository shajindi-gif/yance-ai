"""Durable full-refund intents and provider idempotency references."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20261113_0041"
down_revision = "20261113_0040"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "refunds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("payment_id", UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_refund_no", sa.String(64), nullable=False, unique=True),
        sa.Column("provider_refund_id", sa.String(128)),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("requested_by", UUID(as_uuid=True)),
        sa.Column("error_code", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_refunds_full_order"),
    )
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"])
    op.create_index("ix_refunds_tenant_id", "refunds", ["tenant_id"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM refunds")):
        raise RuntimeError("Refund evidence exists; use application rollback and retain this table")
    op.drop_table("refunds")
