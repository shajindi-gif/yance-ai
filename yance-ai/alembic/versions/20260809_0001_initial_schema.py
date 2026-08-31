"""Initial yance.ai schema with pgvector.

Revision ID: 20260809_0001
Revises:
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "20260809_0001"
down_revision = None
branch_labels = None
depends_on = None


def tenant_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE")


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("agent_name", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_tenant_id"), "agent_runs", ["tenant_id"])

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analytics_event_tenant_name_time",
        "analytics_events",
        ["tenant_id", "name", "occurred_at"],
    )
    op.create_index(op.f("ix_analytics_events_tenant_id"), "analytics_events", ["tenant_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_tenant_id"), "audit_logs", ["tenant_id"])

    op.create_table(
        "companies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("unified_credit_code", sa.String(length=64), nullable=True),
        sa.Column("province", sa.String(length=80), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=True),
        sa.Column("industry", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_tenant_id"), "companies", ["tenant_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("product_code", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_order_no"), "orders", ["order_no"], unique=True)
    op.create_index(op.f("ix_orders_tenant_id"), "orders", ["tenant_id"])

    op.create_table(
        "policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("jurisdiction", sa.String(length=160), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_policies_tenant_id"), "policies", ["tenant_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "admin", "member", "viewer", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"])
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"])
    op.create_index("uq_users_tenant_email", "users", ["tenant_id", "email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("object_key", sa.String(length=700), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(op.f("ix_documents_tenant_id"), "documents", ["tenant_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("tax_number", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_tenant_id"), "invoices", ["tenant_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="SET NULL"),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opportunities_company_id"), "opportunities", ["company_id"])
    op.create_index(op.f("ix_opportunities_tenant_id"), "opportunities", ["tenant_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_trade_no", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_trade_no"),
    )
    op.create_index(op.f("ix_payments_tenant_id"), "payments", ["tenant_id"])

    op.create_table(
        "policy_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("rule_type", sa.String(length=80), nullable=False),
        sa.Column("rule_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="CASCADE"),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_policy_rules_policy_id"), "policy_rules", ["policy_id"])
    op.create_index(op.f("ix_policy_rules_tenant_id"), "policy_rules", ["tenant_id"])

    op.create_table(
        "applications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("form_data", sa.JSON(), nullable=False),
        *timestamp_columns(),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applications_company_id"), "applications", ["company_id"])
    op.create_index(op.f("ix_applications_tenant_id"), "applications", ["tenant_id"])


def downgrade() -> None:
    for table in (
        "applications",
        "policy_rules",
        "payments",
        "opportunities",
        "invoices",
        "documents",
        "users",
        "policies",
        "orders",
        "companies",
        "audit_logs",
        "analytics_events",
        "agent_runs",
        "tenants",
    ):
        op.drop_table(table)
    op.execute("DROP TYPE IF EXISTS userrole")
