"""Add isolated investor demo scenarios.

Revision ID: 20260905_0020
Revises: 20260905_0019
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260905_0020"
down_revision = "20260905_0019"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("tenants", sa.Column("demo_dataset_key", sa.String(120)))
    op.create_index("ix_tenants_is_demo", "tenants", ["is_demo"])
    op.create_index(
        "ix_tenants_demo_dataset_key", "tenants", ["demo_dataset_key"], unique=True
    )

    op.create_table(
        "demo_scenarios",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            UUID,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_version_id",
            UUID,
            sa.ForeignKey("company_profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            UUID,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scan_id",
            UUID,
            sa.ForeignKey("policy_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            UUID,
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "eligibility_result_id",
            UUID,
            sa.ForeignKey("eligibility_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            UUID,
            sa.ForeignKey("application_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_run_id",
            UUID,
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("industry", sa.String(160), nullable=False),
        sa.Column("persona", sa.String(240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("next_best_action", sa.Text(), nullable=False),
        sa.Column("dataset_version", sa.String(80), nullable=False),
        sa.Column(
            "data_classification",
            sa.String(40),
            nullable=False,
            server_default="synthetic",
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_demo_scenarios_key", "demo_scenarios", ["key"], unique=True)
    op.create_index(
        "ix_demo_scenarios_tenant_id", "demo_scenarios", ["tenant_id"], unique=True
    )
    op.create_index("ix_demo_scenarios_company_id", "demo_scenarios", ["company_id"])
    op.create_index("ix_demo_scenarios_dataset_version", "demo_scenarios", ["dataset_version"])
    op.create_index("ix_demo_scenarios_status", "demo_scenarios", ["status"])


def downgrade() -> None:
    op.drop_table("demo_scenarios")
    op.drop_index("ix_tenants_demo_dataset_key", table_name="tenants")
    op.drop_index("ix_tenants_is_demo", table_name="tenants")
    op.drop_column("tenants", "demo_dataset_key")
    op.drop_column("tenants", "is_demo")
