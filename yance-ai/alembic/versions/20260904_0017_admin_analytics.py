"""Add platform admin, analytics provenance, account stage and feedback.

Revision ID: 20260904_0017
Revises: 20260904_0016
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260904_0017"
down_revision = "20260904_0016"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("account_stage", sa.String(40), nullable=False, server_default="unclassified"),
    )
    op.create_index("ix_tenants_account_stage", "tenants", ["account_stage"])
    op.add_column(
        "users",
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_is_platform_admin", "users", ["is_platform_admin"])
    op.add_column(
        "analytics_events",
        sa.Column("source", sa.String(40), nullable=False, server_default="server"),
    )
    op.add_column("analytics_events", sa.Column("event_key", sa.String(240)))
    op.add_column("analytics_events", sa.Column("request_id", sa.String(120)))
    op.create_index("ix_analytics_events_source", "analytics_events", ["source"])
    op.create_unique_constraint(
        "uq_analytics_event_tenant_key", "analytics_events", ["tenant_id", "event_key"]
    )
    op.create_table(
        "feedback",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("category", sa.String(80), nullable=False, server_default="product"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("route", sa.String(500)),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in ("tenant_id", "user_id", "status"):
        op.create_index(f"ix_feedback_{column}", "feedback", [column])


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_constraint("uq_analytics_event_tenant_key", "analytics_events", type_="unique")
    op.drop_index("ix_analytics_events_source", table_name="analytics_events")
    op.drop_column("analytics_events", "request_id")
    op.drop_column("analytics_events", "event_key")
    op.drop_column("analytics_events", "source")
    op.drop_index("ix_users_is_platform_admin", table_name="users")
    op.drop_column("users", "is_platform_admin")
    op.drop_index("ix_tenants_account_stage", table_name="tenants")
    op.drop_column("tenants", "account_stage")
