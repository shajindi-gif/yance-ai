"""Add subscription billing, usage metering and enterprise controls.

Revision ID: 20260905_0019
Revises: 20260905_0018
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260905_0019"
down_revision = "20260905_0018"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON_OBJECT = sa.text("'{}'::json")
JSON_LIST = sa.text("'[]'::json")


def _tenant_column() -> sa.Column:
    return sa.Column(
        "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("sales_motion", sa.String(40), nullable=False, server_default="self_serve"),
        sa.Column("limits_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("features_json", sa.JSON(), nullable=False, server_default=JSON_LIST),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)
    op.create_index("ix_plans_status", "plans", ["status"])

    op.create_table(
        "price_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("plan_id", UUID, sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("unit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_interval", sa.String(20), nullable=False, server_default="month"),
        sa.Column("provider", sa.String(40)),
        sa.Column("provider_price_id", sa.String(160)),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "version", name="uq_price_version_plan"),
        sa.UniqueConstraint("provider_price_id", name="uq_price_versions_provider_price_id"),
    )
    op.create_index("ix_price_versions_plan_id", "price_versions", ["plan_id"])
    op.create_index("ix_price_versions_status", "price_versions", ["status"])

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("plan_id", UUID, sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("price_version_id", UUID, sa.ForeignKey("price_versions.id", ondelete="RESTRICT")),
        sa.Column("provider", sa.String(40), nullable=False, server_default="internal"),
        sa.Column("provider_customer_id", sa.String(160)),
        sa.Column("provider_subscription_id", sa.String(160)),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("grace_ends_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("tenant_id", "plan_id", "price_version_id", "provider_customer_id", "status", "current_period_end"):
        op.create_index(f"ix_subscriptions_{column}", "subscriptions", [column])
    op.create_index(
        "ix_subscriptions_provider_subscription_id",
        "subscriptions",
        ["provider_subscription_id"],
        unique=True,
    )

    op.create_table(
        "subscription_items",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("subscription_id", UUID, sa.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meter_key", sa.String(80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("subscription_id", "meter_key", name="uq_subscription_item_meter"),
    )
    for column in ("tenant_id", "subscription_id", "meter_key"):
        op.create_index(f"ix_subscription_items_{column}", "subscription_items", [column])

    op.create_table(
        "usage_meters",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("aggregation", sa.String(40), nullable=False, server_default="sum"),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("reset_period", sa.String(20), nullable=False, server_default="subscription"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_usage_meters_key", "usage_meters", ["key"], unique=True)

    op.create_table(
        "usage_records",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("subscription_id", UUID, sa.ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("workflow_run_id", UUID, sa.ForeignKey("workflow_runs.id", ondelete="SET NULL")),
        sa.Column("meter_key", sa.String(80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("resource_type", sa.String(80)),
        sa.Column("resource_id", sa.String(160)),
        sa.Column("source", sa.String(80), nullable=False, server_default="server"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_usage_record_tenant_key"),
    )
    for column in ("tenant_id", "subscription_id", "user_id", "workflow_run_id", "meter_key"):
        op.create_index(f"ix_usage_records_{column}", "usage_records", [column])
    op.create_index("ix_usage_records_meter_period", "usage_records", ["tenant_id", "meter_key", "occurred_at"])

    op.create_table(
        "usage_budgets",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("scope_type", sa.String(40), nullable=False),
        sa.Column("scope_id", UUID),
        sa.Column("meter_key", sa.String(80), nullable=False),
        sa.Column("hard_limit", sa.Integer(), nullable=False),
        sa.Column("warning_threshold", sa.Integer()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "scope_type", "scope_id", "meter_key", name="uq_usage_budget_scope"),
    )
    for column in ("tenant_id", "scope_type", "scope_id", "meter_key"):
        op.create_index(f"ix_usage_budgets_{column}", "usage_budgets", [column])

    op.create_table(
        "api_keys",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("prefix", sa.String(24), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("scopes_json", sa.JSON(), nullable=False, server_default=JSON_LIST),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "prefix", name="uq_api_key_tenant_prefix"),
        sa.UniqueConstraint("secret_hash", name="uq_api_keys_secret_hash"),
    )
    for column in ("tenant_id", "prefix", "revoked_at"):
        op.create_index(f"ix_api_keys_{column}", "api_keys", [column])

    op.create_table(
        "retention_policies",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("document_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("agent_trace_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("analytics_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("audit_days", sa.Integer(), nullable=False, server_default="730"),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legal_hold_reason", sa.String(500)),
        sa.Column("configured_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_retention_policy_tenant"),
    )
    op.create_index("ix_retention_policies_tenant_id", "retention_policies", ["tenant_id"])

    op.create_table(
        "export_jobs",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("format", sa.String(20), nullable=False, server_default="json"),
        sa.Column("scope", sa.String(40), nullable=False, server_default="workspace"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("checksum_sha256", sa.String(64)),
        sa.Column("record_counts_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("tenant_id", "status"):
        op.create_index(f"ix_export_jobs_{column}", "export_jobs", [column])

    op.create_table(
        "deletion_requests",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False, server_default="scheduled"),
        sa.Column("reason", sa.String(500)),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("blocker_json", sa.JSON(), nullable=False, server_default=JSON_LIST),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("tenant_id", "status", "scheduled_for"):
        op.create_index(f"ix_deletion_requests_{column}", "deletion_requests", [column])

    op.create_table(
        "feature_flags",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("enabled_by_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_feature_flags_key", "feature_flags", ["key"], unique=True)

    op.create_table(
        "tenant_feature_flags",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("feature_flag_id", UUID, sa.ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "feature_flag_id", name="uq_tenant_flag"),
    )
    op.create_index("ix_tenant_feature_flags_tenant_id", "tenant_feature_flags", ["tenant_id"])
    op.create_index("ix_tenant_feature_flags_feature_flag_id", "tenant_feature_flags", ["feature_flag_id"])

    op.add_column("audit_logs", sa.Column("request_id", sa.String(120)))
    op.add_column("audit_logs", sa.Column("result", sa.String(40), nullable=False, server_default="success"))
    op.add_column("audit_logs", sa.Column("reason", sa.String(500)))
    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(64)))
    op.add_column("audit_logs", sa.Column("entry_hash", sa.String(64)))
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_entry_hash", "audit_logs", ["entry_hash"])

    op.get_bind().exec_driver_sql(
        """
        INSERT INTO plans (id, code, name, description, tier, status, sales_motion, limits_json, features_json, created_at, updated_at)
        VALUES
        (gen_random_uuid(), 'free', 'Free', '单企业政策机会工作区', 0, 'active', 'self_serve',
         '{"policy_scans":3,"companies":2,"reports":2,"documents":20,"generated_documents":3,"agent_runs":30,"users":1,"storage_bytes":104857600}'::json,
         '["企业画像","证据型机会扫描","基础申报工作区"]'::json, now(), now()),
        (gen_random_uuid(), 'pro', 'Pro', '小型团队持续政策扫描与申报执行', 1, 'active', 'contact',
         '{"policy_scans":100,"companies":5,"reports":50,"documents":500,"generated_documents":100,"agent_runs":500,"users":5,"storage_bytes":10737418240}'::json,
         '["持续扫描","多企业工作区","材料生成与版本"]'::json, now(), now()),
        (gen_random_uuid(), 'business', 'Business', '专业服务机构的多企业协作与治理', 2, 'active', 'contact',
         '{"policy_scans":1000,"companies":50,"reports":500,"documents":5000,"generated_documents":1000,"agent_runs":5000,"users":25,"storage_bytes":107374182400}'::json,
         '["团队预算","API Keys","数据导出","保留策略"]'::json, now(), now()),
        (gen_random_uuid(), 'enterprise', 'Enterprise', '合同定义的企业级容量、支持与集成', 3, 'active', 'enterprise',
         '{"policy_scans":null,"companies":null,"reports":null,"documents":null,"generated_documents":null,"agent_runs":null,"users":null,"storage_bytes":null}'::json,
         '["合同容量","高级治理","企业集成"]'::json, now(), now())
        """
    )
    op.execute(
        """
        INSERT INTO price_versions (id, plan_id, version, currency, unit_amount, billing_interval, provider, status, effective_at, created_at, updated_at)
        SELECT gen_random_uuid(), id, 1, 'CNY', 0, 'month', 'internal', 'active', now(), now(), now()
        FROM plans WHERE code = 'free'
        """
    )
    op.execute(
        """
        INSERT INTO usage_meters (id, key, name, unit, aggregation, source, reset_period, active, created_at, updated_at)
        VALUES
        (gen_random_uuid(), 'policy_scans', 'Policy scans', 'run', 'sum', 'usage_records', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'companies', 'Companies', 'company', 'current', 'companies', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'reports', 'Reports', 'report', 'sum', 'usage_records', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'documents', 'Documents', 'document', 'current', 'documents', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'generated_documents', 'Generated documents', 'artifact', 'sum', 'usage_records', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'agent_runs', 'Agent runs', 'run', 'sum', 'usage_records', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'users', 'Users', 'user', 'current', 'users', 'subscription', true, now(), now()),
        (gen_random_uuid(), 'storage_bytes', 'Storage', 'byte', 'current', 'documents', 'subscription', true, now(), now())
        """
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entry_hash", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    for column in ("entry_hash", "previous_hash", "reason", "result", "request_id"):
        op.drop_column("audit_logs", column)
    for table in (
        "tenant_feature_flags",
        "feature_flags",
        "deletion_requests",
        "export_jobs",
        "retention_policies",
        "api_keys",
        "usage_budgets",
        "usage_records",
        "usage_meters",
        "subscription_items",
        "subscriptions",
        "price_versions",
        "plans",
    ):
        op.drop_table(table)
