"""Add versioned evaluation datasets, runs and case evidence.

Revision ID: 20260905_0018
Revises: 20260904_0017
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260905_0018"
down_revision = "20260904_0017"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON_DEFAULT = sa.text("'{}'::json")
LIST_DEFAULT = sa.text("'[]'::json")


def _tenant_column() -> sa.Column:
    return sa.Column(
        "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "eval_datasets",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("eval_type", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column(
            "data_classification", sa.String(80), nullable=False, server_default="synthetic"
        ),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_eval_datasets_key", "eval_datasets", ["key"], unique=True)
    for column in ("eval_type", "status", "is_demo"):
        op.create_index(f"ix_eval_datasets_{column}", "eval_datasets", [column])

    op.create_table(
        "eval_dataset_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "dataset_id",
            UUID,
            sa.ForeignKey("eval_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("target_key", sa.String(160), nullable=False),
        sa.Column("target_version", sa.String(80), nullable=False),
        sa.Column("scorer_version", sa.String(80), nullable=False),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="unreviewed"),
        sa.Column("card_json", sa.JSON(), nullable=False, server_default=JSON_DEFAULT),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("dataset_id", "version", name="uq_eval_dataset_version"),
    )
    for column in ("dataset_id", "content_sha256", "review_status"):
        op.create_index(f"ix_eval_dataset_versions_{column}", "eval_dataset_versions", [column])

    op.create_table(
        "eval_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "dataset_version_id",
            UUID,
            sa.ForeignKey("eval_dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_id", sa.String(160), nullable=False),
        sa.Column("eval_type", sa.String(80), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("ground_truth_json", sa.JSON(), nullable=False),
        sa.Column("expected_evidence_json", sa.JSON(), nullable=False, server_default=LIST_DEFAULT),
        sa.Column("tags_json", sa.JSON(), nullable=False, server_default=LIST_DEFAULT),
        sa.Column("risk_tier", sa.String(40), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("dataset_version_id", "case_id", name="uq_eval_case_version_key"),
    )
    for column in ("dataset_version_id", "eval_type", "risk_tier", "content_sha256"):
        op.create_index(f"ix_eval_cases_{column}", "eval_cases", [column])

    op.create_table(
        "eval_runs",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column("batch_id", UUID, nullable=False),
        sa.Column(
            "dataset_version_id",
            UUID,
            sa.ForeignKey("eval_dataset_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("eval_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("target_key", sa.String(160), nullable=False),
        sa.Column("target_version", sa.String(80), nullable=False),
        sa.Column("scorer_version", sa.String(80), nullable=False),
        sa.Column("model", sa.String(160)),
        sa.Column("prompt_version", sa.String(120)),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requested_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("release_gate_passed", sa.Boolean()),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default=JSON_DEFAULT),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in (
        "tenant_id",
        "batch_id",
        "dataset_version_id",
        "eval_type",
        "status",
        "is_demo",
    ):
        op.create_index(f"ix_eval_runs_{column}", "eval_runs", [column])

    op.create_table(
        "evaluations",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "eval_run_id", UUID, sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "eval_case_id", UUID, sa.ForeignKey("eval_cases.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("agent_run_id", UUID, sa.ForeignKey("agent_runs.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("model_answer_json", sa.JSON(), nullable=False, server_default=JSON_DEFAULT),
        sa.Column("overall_score", sa.Numeric(6, 5)),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hallucination_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_types_json", sa.JSON(), nullable=False, server_default=LIST_DEFAULT),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("eval_run_id", "eval_case_id", name="uq_evaluation_run_case"),
    )
    for column in ("tenant_id", "eval_run_id", "eval_case_id", "agent_run_id", "status"):
        op.create_index(f"ix_evaluations_{column}", "evaluations", [column])

    op.create_table(
        "evaluation_dimension_scores",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "evaluation_id",
            UUID,
            sa.ForeignKey("evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimension", sa.String(80), nullable=False),
        sa.Column("score", sa.Numeric(6, 5)),
        sa.Column("is_applicable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scorer", sa.String(160), nullable=False),
        sa.Column("scorer_version", sa.String(80), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.UniqueConstraint("evaluation_id", "dimension", name="uq_evaluation_dimension"),
    )
    for column in ("tenant_id", "evaluation_id", "dimension"):
        op.create_index(f"ix_evaluation_dimension_scores_{column}", "evaluation_dimension_scores", [column])

    op.create_table(
        "evaluation_evidence",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "evaluation_id",
            UUID,
            sa.ForeignKey("evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expectation", sa.Text(), nullable=False),
        sa.Column("observed", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(500)),
        sa.Column("passed", sa.Boolean(), nullable=False),
    )
    for column in ("tenant_id", "evaluation_id"):
        op.create_index(f"ix_evaluation_evidence_{column}", "evaluation_evidence", [column])

    op.create_table(
        "evaluation_errors",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "eval_run_id", UUID, sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "evaluation_id", UUID, sa.ForeignKey("evaluations.id", ondelete="CASCADE")
        ),
        sa.Column("case_id", sa.String(160), nullable=False),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("error_type", sa.String(120), nullable=False),
        sa.Column("safe_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in (
        "tenant_id",
        "eval_run_id",
        "evaluation_id",
        "case_id",
        "code",
        "error_type",
    ):
        op.create_index(f"ix_evaluation_errors_{column}", "evaluation_errors", [column])


def downgrade() -> None:
    for table in (
        "evaluation_errors",
        "evaluation_evidence",
        "evaluation_dimension_scores",
        "evaluations",
        "eval_runs",
        "eval_cases",
        "eval_dataset_versions",
        "eval_datasets",
    ):
        op.drop_table(table)
