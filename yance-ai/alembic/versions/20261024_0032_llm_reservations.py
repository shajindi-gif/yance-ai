"""Durable per-tenant model output/call reservations, no monetary prices."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261024_0032"
down_revision = "20261023_0031"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "llm_invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("reserved_output_tokens", sa.Integer(), nullable=False),
        sa.Column("charged_output_tokens", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_llm_invocations_tenant_id", "llm_invocations", ["tenant_id"])
    op.create_index(
        "ix_llm_invocations_tenant_created", "llm_invocations", ["tenant_id", "created_at"]
    )


def downgrade():
    op.drop_table("llm_invocations")
