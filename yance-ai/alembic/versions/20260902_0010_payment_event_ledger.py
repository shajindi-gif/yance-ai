"""Add replay-safe payment provider event ledger.

Revision ID: 20260902_0010
Revises: 20260902_0009
"""

import sqlalchemy as sa

from alembic import op

revision = "20260902_0010"
down_revision = "20260902_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.UUID(),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="received"),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_payment_events_tenant_id", "payment_events", ["tenant_id"])
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])
    op.create_index(
        "uq_payment_events_provider_event",
        "payment_events",
        ["provider", "provider_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_payment_events_provider_event", table_name="payment_events")
    op.drop_index("ix_payment_events_payment_id", table_name="payment_events")
    op.drop_index("ix_payment_events_tenant_id", table_name="payment_events")
    op.drop_table("payment_events")
