"""Funding OS: structured funding facts, notifications, milestones.

Revision ID: 20260927_0022
Revises: 20260906_0021
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260927_0022"
down_revision = "20260906_0021"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _tenant_column() -> sa.Column:
    return sa.Column(
        "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    # Policies gain structured funding facts. All nullable: values only exist when
    # parsed deterministically from the official document or curated by admins.
    op.add_column("policies", sa.Column("funding_type", sa.String(40)))
    op.add_column("policies", sa.Column("funding_amount_min", sa.Numeric(14, 2)))
    op.add_column("policies", sa.Column("funding_amount_max", sa.Numeric(14, 2)))
    op.add_column("policies", sa.Column("funding_ratio", sa.Numeric(5, 2)))
    op.add_column(
        "policies", sa.Column("funding_currency", sa.String(8), server_default="CNY")
    )
    op.add_column("policies", sa.Column("applicant_type", sa.String(120)))
    op.add_column("policies", sa.Column("company_stage", sa.String(160)))
    op.add_column("policies", sa.Column("technology", sa.String(240)))
    op.create_index("ix_policies_funding_type", "policies", ["funding_type"])

    op.create_table(
        "notifications",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("entity_type", sa.String(40)),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("dedup_key", sa.String(200), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("tenant_id", "dedup_key", name="uq_notification_tenant_key"),
    )
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_kind", "notifications", ["kind"])
    op.create_index(
        "ix_notification_tenant_created", "notifications", ["tenant_id", "created_at"]
    )

    op.create_table(
        "milestones",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "application_id",
            UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(40), nullable=False, server_default="preparation"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("owner_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(40), nullable=False, server_default="todo"),
        sa.Column("completion_note", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_milestones_tenant_id", "milestones", ["tenant_id"])
    op.create_index("ix_milestones_status", "milestones", ["status"])
    op.create_index("ix_milestone_application", "milestones", ["application_id"])
    op.create_index("ix_milestone_tenant_due", "milestones", ["tenant_id", "due_at"])


def downgrade() -> None:
    op.drop_table("milestones")
    op.drop_table("notifications")
    op.drop_index("ix_policies_funding_type", table_name="policies")
    for column in (
        "technology",
        "company_stage",
        "applicant_type",
        "funding_currency",
        "funding_ratio",
        "funding_amount_max",
        "funding_amount_min",
        "funding_type",
    ):
        op.drop_column("policies", column)
