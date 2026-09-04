"""Add durable Agent Harness execution and trace records.

Revision ID: 20260903_0014
Revises: 20260903_0013
"""

import json
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260903_0014"
down_revision = "20260903_0013"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)

AGENTS = [
    ("11111111-1111-4111-8111-111111111001", "orchestrator", "Orchestrator Agent", "active"),
    (
        "11111111-1111-4111-8111-111111111002",
        "company_profile",
        "Company Profile Agent",
        "inactive",
    ),
    ("11111111-1111-4111-8111-111111111003", "policy_search", "Policy Search Agent", "active"),
    ("11111111-1111-4111-8111-111111111004", "eligibility", "Eligibility Agent", "inactive"),
    ("11111111-1111-4111-8111-111111111005", "evidence", "Evidence Agent", "inactive"),
    (
        "11111111-1111-4111-8111-111111111006",
        "document_analysis",
        "Document Analysis Agent",
        "inactive",
    ),
    ("11111111-1111-4111-8111-111111111007", "application", "Application Agent", "inactive"),
    ("11111111-1111-4111-8111-111111111008", "report", "Report Agent", "active"),
    ("11111111-1111-4111-8111-111111111009", "qa", "QA Agent", "active"),
]
WORKFLOW_ID = "22222222-2222-4222-8222-222222222001"


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="inactive"),
        sa.Column(
            "input_schema_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "output_schema_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("key", "version", name="uq_agent_key_version"),
    )
    op.create_index("ix_agents_key", "agents", ["key"])

    op.create_table(
        "workflows",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column(
            "definition_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("key", "version", name="uq_workflow_key_version"),
    )
    op.create_index("ix_workflows_key", "workflows", ["key"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "workflow_id", UUID, sa.ForeignKey("workflows.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="SET NULL")),
        sa.Column("task_id", UUID),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("current_step", sa.String(40), nullable=True),
        sa.Column("input_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in ("tenant_id", "workflow_id", "company_id", "task_id", "status"):
        op.create_index(f"ix_workflow_runs_{column}", "workflow_runs", [column])

    op.add_column("policy_scans", sa.Column("workflow_run_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_policy_scan_workflow_run",
        "policy_scans",
        "workflow_runs",
        ["workflow_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_policy_scans_workflow_run_id", "policy_scans", ["workflow_run_id"])

    op.alter_column(
        "agent_runs", "started_at", existing_type=sa.DateTime(timezone=True), nullable=True
    )
    op.add_column("agent_runs", sa.Column("agent_id", UUID, nullable=True))
    op.add_column("agent_runs", sa.Column("workflow_run_id", UUID, nullable=True))
    op.add_column("agent_runs", sa.Column("prompt_version", sa.String(80), nullable=True))
    op.add_column(
        "agent_runs",
        sa.Column("input_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "agent_runs",
        sa.Column("output_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "agent_runs", sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "agent_runs", sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0")
    )
    op.add_column(
        "agent_runs",
        sa.Column("error_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "agent_runs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "agent_runs", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2")
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column("agent_runs", sa.Column("lease_owner", sa.String(160), nullable=True))
    op.add_column(
        "agent_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "agent_runs", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_foreign_key(
        "fk_agent_run_agent", "agent_runs", "agents", ["agent_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_agent_run_workflow_run",
        "agent_runs",
        "workflow_runs",
        ["workflow_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_agent_runs_agent_id", "agent_runs", ["agent_id"])
    op.create_index("ix_agent_runs_workflow_run_id", "agent_runs", ["workflow_run_id"])
    op.create_index(
        "ix_agent_runs_claimable",
        "agent_runs",
        ["status", "next_attempt_at", "lease_expires_at"],
    )

    op.create_table(
        "agent_steps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_run_id", UUID, sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("agent_id", UUID, sa.ForeignKey("agents.id", ondelete="RESTRICT")),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("input_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "verification_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.UniqueConstraint("agent_run_id", "sequence", name="uq_agent_step_sequence"),
    )
    op.create_index("ix_agent_steps_tenant_id", "agent_steps", ["tenant_id"])
    op.create_index("ix_agent_steps_agent_run_id", "agent_steps", ["agent_run_id"])

    op.create_table(
        "tool_calls",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_run_id", UUID, sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_step_id",
            UUID,
            sa.ForeignKey("agent_steps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.String(160), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="running"),
        sa.Column(
            "arguments_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
    )
    op.create_index("ix_tool_calls_tenant_id", "tool_calls", ["tenant_id"])
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_index("ix_tool_calls_agent_step_id", "tool_calls", ["agent_step_id"])

    op.create_table(
        "agent_run_errors",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_run_id", UUID, sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("agent_step_id", UUID, sa.ForeignKey("agent_steps.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("safe_message", sa.String(500), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_agent_run_errors_tenant_id", "agent_run_errors", ["tenant_id"])
    op.create_index("ix_agent_run_errors_agent_run_id", "agent_run_errors", ["agent_run_id"])

    op.create_table(
        "agent_retries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_run_id", UUID, sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("retry_number", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(120), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "scheduled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("agent_run_id", "retry_number", name="uq_agent_retry_number"),
    )
    op.create_index("ix_agent_retries_tenant_id", "agent_retries", ["tenant_id"])
    op.create_index("ix_agent_retries_agent_run_id", "agent_retries", ["agent_run_id"])

    op.create_table(
        "artifacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_run_id", UUID, sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="SET NULL")),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("artifact_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(40), nullable=False, server_default="generated"),
        sa.Column("mime_type", sa.String(160), nullable=True),
        sa.Column("object_key", sa.String(700), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "agent_run_id", "artifact_type", "version", name="uq_artifact_run_type_version"
        ),
    )
    for column in ("tenant_id", "agent_run_id", "task_id", "application_id"):
        op.create_index(f"ix_artifacts_{column}", "artifacts", [column])

    bind = op.get_bind()
    input_schema = {
        "type": "object",
        "required": ["tenant_id", "user_id", "workflow_id", "input"],
        "properties": {
            "tenant_id": {"type": "string", "format": "uuid"},
            "user_id": {"type": "string", "format": "uuid"},
            "workflow_id": {"type": "string", "format": "uuid"},
            "input": {"type": "object"},
        },
    }
    output_schema = {
        "type": "object",
        "required": ["status", "output"],
        "properties": {"status": {"type": "string"}, "output": {"type": "object"}},
    }
    descriptions = {
        "orchestrator": "Plans, routes, verifies and finishes a versioned workflow.",
        "company_profile": "Builds structured company intelligence from approved sources.",
        "policy_search": "Retrieves and ranks policy opportunities for a pinned company profile.",
        "eligibility": "Evaluates structured policy rules against verified company facts.",
        "evidence": "Builds clause-level evidence and citation records.",
        "document_analysis": "Parses and extracts structured facts from company documents.",
        "application": "Creates and updates application materials inside a workspace.",
        "report": "Produces versioned human-readable deliverables.",
        "qa": "Verifies provenance, schema compliance and workflow invariants.",
    }
    for agent_id, key, name, status in AGENTS:
        bind.execute(
            sa.text(
                """
                INSERT INTO agents (
                    id, key, name, description, version, status,
                    input_schema_json, output_schema_json, created_at, updated_at
                ) VALUES (
                    :id, :key, :name, :description, 'v1', :status,
                    CAST(:input_schema AS json), CAST(:output_schema AS json), now(), now()
                ) ON CONFLICT (key, version) DO NOTHING
                """
            ),
            {
                "id": uuid.UUID(agent_id),
                "key": key,
                "name": name,
                "description": descriptions[key],
                "status": status,
                "input_schema": json.dumps(input_schema),
                "output_schema": json.dumps(output_schema),
            },
        )
    bind.execute(
        sa.text(
            """
            INSERT INTO workflows (
                id, key, name, version, status, definition_json, created_at, updated_at
            ) VALUES (
                :id, 'policy_scan', 'Policy opportunity scan', 'v1', 'active',
                CAST(:definition AS json), now(), now()
            ) ON CONFLICT (key, version) DO NOTHING
            """
        ),
        {
            "id": uuid.UUID(WORKFLOW_ID),
            "definition": json.dumps(
                {
                    "steps": ["plan", "retrieve", "reason", "act", "verify", "finish"],
                    "input_schema": "PolicyScanWorkflowInput.v1",
                    "output_schema": "PolicyScanWorkflowOutput.v1",
                }
            ),
        },
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("agent_retries")
    op.drop_table("agent_run_errors")
    op.drop_table("tool_calls")
    op.drop_table("agent_steps")
    op.drop_index("ix_agent_runs_claimable", table_name="agent_runs")
    op.drop_index("ix_agent_runs_workflow_run_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_id", table_name="agent_runs")
    op.drop_constraint("fk_agent_run_workflow_run", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_run_agent", "agent_runs", type_="foreignkey")
    for column in (
        "updated_at",
        "created_at",
        "last_heartbeat_at",
        "lease_expires_at",
        "lease_owner",
        "next_attempt_at",
        "queued_at",
        "max_retries",
        "retry_count",
        "error_json",
        "cost_usd",
        "total_tokens",
        "output_json",
        "input_json",
        "prompt_version",
        "workflow_run_id",
        "agent_id",
    ):
        op.drop_column("agent_runs", column)
    op.alter_column(
        "agent_runs", "started_at", existing_type=sa.DateTime(timezone=True), nullable=False
    )
    op.drop_index("ix_policy_scans_workflow_run_id", table_name="policy_scans")
    op.drop_constraint("fk_policy_scan_workflow_run", "policy_scans", type_="foreignkey")
    op.drop_column("policy_scans", "workflow_run_id")
    op.drop_table("workflow_runs")
    op.drop_table("workflows")
    op.drop_table("agents")
