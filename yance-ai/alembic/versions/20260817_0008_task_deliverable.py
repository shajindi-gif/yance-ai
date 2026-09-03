"""Add Task, Deliverable, RevisionRequest tables for Outcome-based Agent SaaS."""

import sqlalchemy as sa

from alembic import op

revision = "20260817_0008"
down_revision = "20260814_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "company_id",
            sa.UUID(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("input_data", sa.JSON, default=dict),
        sa.Column("requirements", sa.Text, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("priority", sa.String(20), server_default="normal"),
        sa.Column("agent_type", sa.String(80), nullable=True),
        sa.Column("workflow_version", sa.String(20), server_default="v1"),
        sa.Column("model_provider", sa.String(40), nullable=True),
        sa.Column("model_name", sa.String(120), nullable=True),
        sa.Column("estimated_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("final_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_status", sa.String(40), server_default="unpaid"),
        sa.Column("review_status", sa.String(40), nullable=True),
        sa.Column("delivery_status", sa.String(40), nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column(
            "order_id", sa.UUID(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("metadata", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_company_id", "tasks", ["company_id"])

    op.create_table(
        "deliverables",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "task_id", sa.UUID(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("deliverable_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content_json", sa.JSON, nullable=True),
        sa.Column("content_markdown", sa.Text, nullable=True),
        sa.Column("file_url", sa.String(700), nullable=True),
        sa.Column("pdf_url", sa.String(700), nullable=True),
        sa.Column("version", sa.Integer, server_default=sa.text("1")),
        sa.Column("status", sa.String(40), server_default="generated"),
        sa.Column("quality_score", sa.Integer, nullable=True),
        sa.Column("evidence_score", sa.Integer, nullable=True),
        sa.Column("metadata", sa.JSON, default=dict),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deliverables_task_id", "deliverables", ["task_id"])
    op.create_index("ix_deliverables_tenant_id", "deliverables", ["tenant_id"])

    op.create_table(
        "revision_requests",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "task_id", sa.UUID(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "deliverable_id",
            sa.UUID(),
            sa.ForeignKey("deliverables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("request", sa.Text, nullable=False),
        sa.Column("status", sa.String(40), server_default="pending"),
        sa.Column("response", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rev_req_task_id", "revision_requests", ["task_id"])
    op.create_index("ix_rev_req_tenant_id", "revision_requests", ["tenant_id"])

    op.add_column("agent_runs", sa.Column("task_id", sa.UUID(), nullable=True))
    op.create_index("ix_agent_runs_task_id", "agent_runs", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_task_id", table_name="agent_runs")
    op.drop_column("agent_runs", "task_id")
    op.drop_index("ix_rev_req_tenant_id", table_name="revision_requests")
    op.drop_index("ix_rev_req_task_id", table_name="revision_requests")
    op.drop_table("revision_requests")
    op.drop_index("ix_deliverables_tenant_id", table_name="deliverables")
    op.drop_index("ix_deliverables_task_id", table_name="deliverables")
    op.drop_table("deliverables")
    op.drop_index("ix_tasks_company_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_tenant_id", table_name="tasks")
    op.drop_table("tasks")
