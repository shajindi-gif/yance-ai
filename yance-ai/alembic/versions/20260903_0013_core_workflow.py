"""Add the persistent core product workflow spine.

Revision ID: 20260903_0013
Revises: 20260903_0012
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260903_0013"
down_revision = "20260903_0012"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
USER_ROLE = postgresql.ENUM("owner", "admin", "member", "viewer", name="userrole", create_type=False)


def upgrade() -> None:
    op.create_table(
        "memberships",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", USER_ROLE, nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
    )
    op.create_index("ix_memberships_tenant_id", "memberships", ["tenant_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.execute(
        sa.text(
            """
            INSERT INTO memberships (id, tenant_id, user_id, role, status, created_at, updated_at)
            SELECT gen_random_uuid(), tenant_id, id, role, 'active', created_at, updated_at
            FROM users
            ON CONFLICT (tenant_id, user_id) DO NOTHING
            """
        )
    )

    op.create_table(
        "company_profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("draft_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_version", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", name="uq_company_profile_company"),
    )
    op.create_index("ix_company_profiles_tenant_id", "company_profiles", ["tenant_id"])
    op.create_index("ix_company_profiles_company_id", "company_profiles", ["company_id"])
    op.execute(
        sa.text(
            """
            INSERT INTO company_profiles (
                id, tenant_id, company_id, status, draft_json, completeness_score,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(), tenant_id, id, 'draft',
                jsonb_strip_nulls(
                    jsonb_build_object(
                        'industry', industry,
                        'province', province,
                        'city', city
                    ) || COALESCE(metadata_json::jsonb, '{}'::jsonb)
                )::json,
                LEAST(100, ROUND(
                    100.0 * (
                        CASE WHEN NULLIF(industry, '') IS NOT NULL THEN 1 ELSE 0 END +
                        CASE WHEN NULLIF(province, '') IS NOT NULL THEN 1 ELSE 0 END +
                        CASE WHEN NULLIF(city, '') IS NOT NULL THEN 1 ELSE 0 END
                    ) / 16
                )),
                created_at, updated_at
            FROM companies
            ON CONFLICT (company_id) DO NOTHING
            """
        )
    )

    op.create_table(
        "company_profile_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("company_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("completeness_score", sa.Integer(), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("profile_id", "version", name="uq_company_profile_version"),
    )
    op.create_index(
        "ix_company_profile_versions_tenant_id", "company_profile_versions", ["tenant_id"]
    )
    op.create_index(
        "ix_company_profile_versions_profile_id", "company_profile_versions", ["profile_id"]
    )
    op.create_index(
        "ix_company_profile_versions_company_id", "company_profile_versions", ["company_id"]
    )

    op.create_table(
        "company_facts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "profile_version_id",
            UUID,
            sa.ForeignKey("company_profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("source_document_id", UUID, sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("extraction_method", sa.String(40), nullable=False, server_default="user_asserted"),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "profile_version_id", "fact_key", name="uq_company_fact_version_key"
        ),
    )
    op.create_index("ix_company_facts_tenant_id", "company_facts", ["tenant_id"])
    op.create_index(
        "ix_company_facts_profile_version_id", "company_facts", ["profile_version_id"]
    )

    op.create_table(
        "policy_scans",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "profile_version_id",
            UUID,
            sa.ForeignKey("company_profile_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("task_id", UUID, nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("total_opportunities", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_policy_scan_idempotency"),
    )
    op.create_index("ix_policy_scans_tenant_id", "policy_scans", ["tenant_id"])
    op.create_index("ix_policy_scans_company_id", "policy_scans", ["company_id"])
    op.create_index("ix_policy_scans_profile_version_id", "policy_scans", ["profile_version_id"])
    op.create_index("ix_policy_scans_task_id", "policy_scans", ["task_id"])
    op.create_index("ix_policy_scans_status", "policy_scans", ["status"])

    op.add_column(
        "documents", sa.Column("source_type", sa.String(40), nullable=False, server_default="file")
    )
    op.add_column(
        "documents",
        sa.Column("ingestion_status", sa.String(40), nullable=False, server_default="not_requested"),
    )
    op.add_column("documents", sa.Column("ingestion_error", sa.String(240), nullable=True))
    op.add_column("documents", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_documents_ingestion_status", "documents", ["ingestion_status"])

    op.add_column("opportunities", sa.Column("scan_id", UUID, nullable=True))
    op.add_column("opportunities", sa.Column("profile_version_id", UUID, nullable=True))
    op.add_column(
        "opportunities",
        sa.Column("policy_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "eligibility_status",
            sa.String(40),
            nullable=False,
            server_default="NEED_MORE_INFORMATION",
        ),
    )
    op.add_column(
        "opportunities", sa.Column("eligibility_confidence", sa.Numeric(4, 3), nullable=True)
    )
    op.create_foreign_key(
        "fk_opportunity_scan", "opportunities", "policy_scans", ["scan_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_opportunity_profile_version",
        "opportunities",
        "company_profile_versions",
        ["profile_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_opportunities_scan_id", "opportunities", ["scan_id"])
    op.create_index("ix_opportunities_eligibility_status", "opportunities", ["eligibility_status"])
    op.create_unique_constraint(
        "uq_opportunity_scan_policy", "opportunities", ["scan_id", "policy_id"]
    )

    op.add_column("applications", sa.Column("owner_user_id", UUID, nullable=True))
    op.add_column("applications", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "applications", sa.Column("progress", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "applications",
        sa.Column("review_status", sa.String(40), nullable=False, server_default="not_requested"),
    )
    op.create_foreign_key(
        "fk_application_owner", "applications", "users", ["owner_user_id"], ["id"], ondelete="SET NULL"
    )

    op.create_table(
        "application_requirements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(80), nullable=False, server_default="material"),
        sa.Column("status", sa.String(40), nullable=False, server_default="missing"),
        sa.Column("is_hard_gate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_application_requirements_tenant_id", "application_requirements", ["tenant_id"]
    )
    op.create_index(
        "ix_application_requirements_application_id",
        "application_requirements",
        ["application_id"],
    )

    op.create_table(
        "application_activities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("actor_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_application_activities_tenant_id", "application_activities", ["tenant_id"]
    )
    op.create_index(
        "ix_application_activities_application_id", "application_activities", ["application_id"]
    )

    op.add_column("tasks", sa.Column("application_id", UUID, nullable=True))
    op.add_column("tasks", sa.Column("scan_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_task_application", "tasks", "applications", ["application_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_task_scan", "tasks", "policy_scans", ["scan_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_tasks_application_id", "tasks", ["application_id"])
    op.create_index("ix_tasks_scan_id", "tasks", ["scan_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_scan_id", table_name="tasks")
    op.drop_index("ix_tasks_application_id", table_name="tasks")
    op.drop_constraint("fk_task_scan", "tasks", type_="foreignkey")
    op.drop_constraint("fk_task_application", "tasks", type_="foreignkey")
    op.drop_column("tasks", "scan_id")
    op.drop_column("tasks", "application_id")
    op.drop_table("application_activities")
    op.drop_table("application_requirements")
    op.drop_constraint("fk_application_owner", "applications", type_="foreignkey")
    op.drop_column("applications", "review_status")
    op.drop_column("applications", "progress")
    op.drop_column("applications", "due_at")
    op.drop_column("applications", "owner_user_id")
    op.drop_constraint("uq_opportunity_scan_policy", "opportunities", type_="unique")
    op.drop_index("ix_opportunities_eligibility_status", table_name="opportunities")
    op.drop_index("ix_opportunities_scan_id", table_name="opportunities")
    op.drop_constraint("fk_opportunity_profile_version", "opportunities", type_="foreignkey")
    op.drop_constraint("fk_opportunity_scan", "opportunities", type_="foreignkey")
    op.drop_column("opportunities", "eligibility_confidence")
    op.drop_column("opportunities", "eligibility_status")
    op.drop_column("opportunities", "policy_snapshot_json")
    op.drop_column("opportunities", "profile_version_id")
    op.drop_column("opportunities", "scan_id")
    op.drop_index("ix_documents_ingestion_status", table_name="documents")
    op.drop_column("documents", "ingested_at")
    op.drop_column("documents", "ingestion_error")
    op.drop_column("documents", "ingestion_status")
    op.drop_column("documents", "source_type")
    op.drop_table("policy_scans")
    op.drop_table("company_facts")
    op.drop_table("company_profile_versions")
    op.drop_table("company_profiles")
    op.drop_table("memberships")
