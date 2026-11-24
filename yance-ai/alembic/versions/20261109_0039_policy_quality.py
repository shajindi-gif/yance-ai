"""Policy quality rubric storage — 信度 / 效度 / 有效性 assessment results.

Why a separate table instead of columns on ``policies``
------------------------------------------------------
One policy has many immutable versions, and a rubric verdict is about a *version*
(its text, its dates, its evidence).  Storing the verdict on the policy would
overwrite history the moment a new version arrives, which is exactly the audit
trail a customer dispute needs.  So the full verdict, the issue codes and the raw
signals live per ``(policy_version_id, rubric_version)``, and only the *current*
headline (score, grade, deliverable) is denormalised onto ``policies`` for cheap
filtering in search queries.

Re-running a new rubric revision keeps the old rows: ``rubric_version`` is part of
the uniqueness key, so v1 verdicts survive alongside v1.1.  Nothing is destroyed
by a re-assessment.

Additive only: a pre-rubric application build ignores the new table and the new
nullable columns, so rollback stays "stop using the new endpoints", not "restore
the database".
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261109_0039"
down_revision = "20261106_0038"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "policy_quality_assessments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policy_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rubric_version", sa.String(40), nullable=False),
        sa.Column("reliability", sa.Numeric(5, 2), nullable=False),
        sa.Column("validity", sa.Numeric(5, 2), nullable=False),
        sa.Column("utility", sa.Numeric(5, 2), nullable=False),
        sa.Column("total", sa.Numeric(5, 2), nullable=False),
        sa.Column("grade", sa.String(2), nullable=False),
        sa.Column("delivery_tier", sa.String(32), nullable=False),
        sa.Column("deliverable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("timeline_state", sa.String(24), nullable=False, server_default="unknown"),
        sa.Column("source_tier", sa.String(2), nullable=False, server_default="D"),
        sa.Column("verdict", sa.String(400)),
        sa.Column("issues", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("signals", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "policy_version_id", "rubric_version", name="uq_policy_quality_version_rubric"
        ),
    )
    op.create_index(
        "ix_policy_quality_grade", "policy_quality_assessments", ["rubric_version", "grade"]
    )
    op.create_index(
        "ix_policy_quality_deliverable",
        "policy_quality_assessments",
        ["rubric_version", "deliverable"],
    )
    op.create_index("ix_policy_quality_policy", "policy_quality_assessments", ["policy_id"])

    # Headline columns for retrieval filtering.  Nullable on purpose: a document
    # that has not been through the rubric yet must stay visible (NULL != false),
    # otherwise deploying the rubric would silently empty the search index until
    # the backfill finishes.
    op.add_column("policies", sa.Column("quality_score", sa.Numeric(5, 2)))
    op.add_column("policies", sa.Column("quality_grade", sa.String(2)))
    op.add_column("policies", sa.Column("quality_deliverable", sa.Boolean()))
    op.add_column("policies", sa.Column("quality_assessed_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_policies_quality_deliverable", "policies", ["quality_deliverable", "quality_grade"]
    )


def downgrade():
    op.drop_index("ix_policies_quality_deliverable", table_name="policies")
    op.drop_column("policies", "quality_assessed_at")
    op.drop_column("policies", "quality_deliverable")
    op.drop_column("policies", "quality_grade")
    op.drop_column("policies", "quality_score")
    op.drop_index("ix_policy_quality_policy", table_name="policy_quality_assessments")
    op.drop_index("ix_policy_quality_deliverable", table_name="policy_quality_assessments")
    op.drop_index("ix_policy_quality_grade", table_name="policy_quality_assessments")
    op.drop_table("policy_quality_assessments")
