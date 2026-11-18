"""Additive tables for the park policy / evidence system.

Scope
-----
* Four **new** tables only: ``parks``, ``park_policy_scopes``,
  ``policy_conditions``, ``policy_eval_runs``.
* No existing column is altered, so an older application build keeps running
  against a migrated database. The rollback path is "stop writing park data",
  not "restore the database".
* ``downgrade`` refuses to drop evidence unless ``PARK_POLICY_ALLOW_DROP=1``:
  park scopes, conditions and quoted clauses are the audit trail behind every
  eligibility conclusion we showed a customer.
"""
import os

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261106_0037"
down_revision = "20261106_0036"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "parks",
        sa.Column("park_id", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("name_en", sa.String(240)),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("park_type", sa.String(40), nullable=False),
        sa.Column("designation_level", sa.String(24), nullable=False, server_default="national"),
        sa.Column("designation_basis", sa.String(500)),
        sa.Column("designation_year", sa.Integer()),
        sa.Column("province", sa.String(80), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("district", sa.String(80)),
        sa.Column("admin_division_code", sa.String(20)),
        sa.Column("operator", sa.String(240)),
        sa.Column("official_url", sa.String(1000)),
        sa.Column("status", sa.String(24), nullable=False, server_default="active"),
        # Boundary is never inferred: default keeps every park "needs_confirmation".
        sa.Column(
            "boundary_status", sa.String(24), nullable=False, server_default="needs_confirmation"
        ),
        sa.Column("boundary_note", sa.Text()),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("source_kind", sa.String(40)),
        sa.Column(
            "verification_status", sa.String(24), nullable=False, server_default="registered"
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("verification_note", sa.String(500)),
        sa.Column("catalog_version", sa.String(40)),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("extra", sa.JSON(), nullable=False, server_default="{}"),
        *_timestamps(),
        # Type must stay inside the known taxonomy: a high-tech zone is not an
        # industrial park, and an incubator is not a science city.
        sa.CheckConstraint(
            "park_type IN ('national_high_tech_zone','provincial_high_tech_zone',"
            "'economic_dev_zone','tech_park','science_city','incubator','other')",
            name="ck_parks_park_type",
        ),
        sa.CheckConstraint(
            "boundary_status IN ('confirmed','needs_confirmation','partial','unknown')",
            name="ck_parks_boundary_status",
        ),
        sa.CheckConstraint(
            "verification_status IN ('registered','reachable','metadata_verified','unreachable','withdrawn')",
            name="ck_parks_verification_status",
        ),
    )
    op.create_index("ix_parks_name", "parks", ["name"])
    op.create_index("ix_parks_park_type", "parks", ["park_type"])
    op.create_index("ix_parks_province", "parks", ["province"])
    op.create_index("ix_parks_city", "parks", ["city"])
    op.create_index("ix_parks_admin_division_code", "parks", ["admin_division_code"])
    op.create_index("ix_parks_status", "parks", ["status"])
    op.create_index("ix_parks_boundary_status", "parks", ["boundary_status"])
    op.create_index("ix_parks_verification_status", "parks", ["verification_status"])

    op.create_table(
        "park_policy_scopes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "policy_id",
            UUID,
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_version_id",
            UUID,
            sa.ForeignKey("policy_versions.id", ondelete="SET NULL"),
        ),
        sa.Column("scope_key", sa.String(200), nullable=False),
        sa.Column("scope_type", sa.String(24), nullable=False),
        sa.Column(
            "park_id", sa.String(80), sa.ForeignKey("parks.park_id", ondelete="SET NULL")
        ),
        sa.Column("province", sa.String(80)),
        sa.Column("city", sa.String(80)),
        sa.Column("district", sa.String(80)),
        sa.Column(
            "qualification_basis", sa.String(40), nullable=False, server_default="unspecified"
        ),
        sa.Column(
            "applies_to_all_enterprises", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("clause_ref", sa.String(120)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("review_status", sa.String(24), nullable=False, server_default="needs_review"),
        sa.Column("reviewed_by", sa.String(120)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("policy_id", "scope_key", name="uq_park_policy_scope_key"),
        sa.CheckConstraint(
            "scope_type IN ('national','province','city','district','park')",
            name="ck_park_policy_scopes_scope_type",
        ),
        sa.CheckConstraint(
            "qualification_basis IN ('registered_in_park','tax_in_park',"
            "'operating_in_park','statistical_in_park','unspecified')",
            name="ck_park_policy_scopes_qualification_basis",
        ),
        # A park-level scope without a park_id would silently match by city text.
        sa.CheckConstraint(
            "scope_type <> 'park' OR park_id IS NOT NULL",
            name="ck_park_policy_scopes_park_requires_id",
        ),
    )
    op.create_index("ix_park_policy_scopes_policy_id", "park_policy_scopes", ["policy_id"])
    op.create_index(
        "ix_park_policy_scopes_policy_version_id", "park_policy_scopes", ["policy_version_id"]
    )
    op.create_index("ix_park_policy_scopes_scope_type", "park_policy_scopes", ["scope_type"])
    op.create_index("ix_park_policy_scopes_park_id", "park_policy_scopes", ["park_id"])
    op.create_index("ix_park_policy_scopes_province", "park_policy_scopes", ["province"])
    op.create_index("ix_park_policy_scopes_city", "park_policy_scopes", ["city"])
    op.create_index(
        "ix_park_policy_scopes_requires_confirmation",
        "park_policy_scopes",
        ["requires_confirmation"],
    )
    op.create_index("ix_park_policy_scopes_review_status", "park_policy_scopes", ["review_status"])
    op.create_index(
        "ix_park_policy_scopes_park", "park_policy_scopes", ["park_id", "review_status"]
    )
    op.create_index("ix_park_policy_scopes_policy", "park_policy_scopes", ["policy_id"])

    op.create_table(
        "policy_conditions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "policy_id",
            UUID,
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_version_id",
            UUID,
            sa.ForeignKey("policy_versions.id", ondelete="SET NULL"),
        ),
        sa.Column("condition_key", sa.String(200), nullable=False),
        sa.Column("group_key", sa.String(80), nullable=False, server_default="主体资格"),
        sa.Column("group_logic", sa.String(16), nullable=False, server_default="all"),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("operator", sa.String(16), nullable=False, server_default="exists"),
        sa.Column("value_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("unit", sa.String(40)),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("category", sa.String(40), nullable=False, server_default="other"),
        sa.Column("clause_ref", sa.String(120)),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
        sa.Column("quote_char_start", sa.Integer()),
        sa.Column("quote_char_end", sa.Integer()),
        sa.Column("extraction_method", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("review_status", sa.String(24), nullable=False, server_default="needs_review"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra", sa.JSON(), nullable=False, server_default="{}"),
        *_timestamps(),
        sa.CheckConstraint(
            "group_logic IN ('all','any')", name="ck_policy_conditions_group_logic"
        ),
        sa.CheckConstraint(
            "operator IN ('gte','lte','eq','ne','in','not_in','between','exists','matches')",
            name="ck_policy_conditions_operator",
        ),
        # An unreviewed quote offset pair is meaningless for evidence display.
        sa.CheckConstraint(
            "quote_char_start IS NULL OR quote_char_end IS NULL OR quote_char_end >= quote_char_start",
            name="ck_policy_conditions_quote_span",
        ),
    )
    op.create_index("ix_policy_conditions_policy_id", "policy_conditions", ["policy_id"])
    op.create_index(
        "ix_policy_conditions_policy_version_id", "policy_conditions", ["policy_version_id"]
    )
    op.create_index("ix_policy_conditions_fact_key", "policy_conditions", ["fact_key"])
    op.create_index("ix_policy_conditions_category", "policy_conditions", ["category"])
    op.create_index("ix_policy_conditions_review_status", "policy_conditions", ["review_status"])
    op.create_index("ix_policy_conditions_group_key", "policy_conditions", ["group_key"])
    op.create_index(
        "ix_policy_conditions_policy_group", "policy_conditions", ["policy_id", "group_key"]
    )
    op.create_index(
        "ix_policy_conditions_version", "policy_conditions", ["policy_version_id"]
    )

    op.create_table(
        "policy_eval_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("dataset_version", sa.String(60), nullable=False),
        sa.Column("dataset_sha256", sa.String(64), nullable=False),
        sa.Column("arm", sa.String(8), nullable=False),
        sa.Column("runner", sa.String(60), nullable=False),
        sa.Column("model_id", sa.String(120)),
        sa.Column("model_version", sa.String(120)),
        sa.Column("online_search_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tools_enabled", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False, server_default="running"),
        sa.Column("model_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_estimate", sa.Numeric(12, 4)),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("case_results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text()),
        *_timestamps(),
        sa.CheckConstraint(
            "arm IN ('A','B','C')", name="ck_policy_eval_runs_arm"
        ),
    )
    op.create_index("ix_policy_eval_runs_dataset_version", "policy_eval_runs", ["dataset_version"])
    op.create_index("ix_policy_eval_runs_arm", "policy_eval_runs", ["arm"])
    op.create_index("ix_policy_eval_runs_status", "policy_eval_runs", ["status"])
    op.create_index(
        "ix_policy_eval_runs_dataset_arm", "policy_eval_runs", ["dataset_version", "arm"]
    )


def downgrade():
    if os.getenv("PARK_POLICY_ALLOW_DROP") != "1":
        raise RuntimeError(
            "Refusing to drop park policy evidence tables. "
            "Set PARK_POLICY_ALLOW_DROP=1 only after exporting parks, scopes, "
            "conditions and eval runs."
        )
    op.drop_table("policy_eval_runs")
    op.drop_table("policy_conditions")
    op.drop_table("park_policy_scopes")
    op.drop_table("parks")
