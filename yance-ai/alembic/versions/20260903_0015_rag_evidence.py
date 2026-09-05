"""Add immutable policy sources, typed rules, decisions, and evidence.

Revision ID: 20260903_0015
Revises: 20260903_0014
"""

import json

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260903_0015"
down_revision = "20260903_0014"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "policy_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("issuer", sa.String(240)),
        sa.Column("region", sa.String(160)),
        sa.Column("industry", sa.String(160)),
        sa.Column("policy_type", sa.String(80)),
        sa.Column("publish_date", sa.DateTime(timezone=True)),
        sa.Column("effective_date", sa.DateTime(timezone=True)),
        sa.Column("expiry_date", sa.DateTime(timezone=True)),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("source_name", sa.String(160)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="published"),
        *_timestamps(),
        sa.UniqueConstraint("policy_id", "version", name="uq_policy_version"),
    )
    for column in ("policy_id", "tenant_id", "content_sha256", "status"):
        op.create_index(f"ix_policy_versions_{column}", "policy_versions", [column])

    op.execute(
        sa.text("""
        INSERT INTO policy_versions (
            id, policy_id, tenant_id, version, content_sha256, title, issuer, region,
            industry, policy_type, publish_date, effective_date, expiry_date, source_url,
            source_name, content, status, created_at, updated_at
        )
        SELECT gen_random_uuid(), id, tenant_id, 1,
            encode(digest(COALESCE(content, original_text, ''), 'sha256'), 'hex'),
            title, issuing_authority, jurisdiction, industry, policy_type, published_at,
            effective_at, deadline, source_url, source,
            COALESCE(content, original_text, ''), status, created_at, updated_at
        FROM policies
    """)
    )

    op.add_column(
        "opportunities",
        sa.Column("policy_version_id", UUID, nullable=True),
    )
    op.create_foreign_key(
        "fk_opportunities_policy_version_id",
        "opportunities",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_opportunities_policy_version_id",
        "opportunities",
        ["policy_version_id"],
    )
    op.execute(
        sa.text("""
        UPDATE opportunities AS opportunity
        SET policy_version_id = version.id
        FROM policy_versions AS version
        WHERE opportunity.policy_id = version.policy_id
          AND version.version = (
              SELECT MAX(latest.version)
              FROM policy_versions AS latest
              WHERE latest.policy_id = opportunity.policy_id
          )
    """)
    )

    op.create_table(
        "policy_chunks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "policy_version_id",
            UUID,
            sa.ForeignKey("policy_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("article", sa.String(160)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("embedding", Vector(1024), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("policy_version_id", "chunk_index", name="uq_policy_chunk_index"),
    )
    for column in ("policy_id", "policy_version_id", "tenant_id"):
        op.create_index(f"ix_policy_chunks_{column}", "policy_chunks", [column])
    op.execute(
        sa.text("""
        INSERT INTO policy_chunks (
            id, policy_id, policy_version_id, tenant_id, chunk_index, content,
            char_start, char_end, content_sha256, metadata_json, created_at, updated_at
        )
        SELECT gen_random_uuid(), pv.policy_id, pv.id, pv.tenant_id, 0, pv.content,
            0, char_length(pv.content), pv.content_sha256,
            json_build_object('backfilled', true, 'embedding_status', 'not_generated'),
            pv.created_at, pv.updated_at
        FROM policy_versions pv WHERE pv.content <> ''
    """)
    )

    for table, extra in (
        (
            "eligibility_rules",
            [
                sa.Column("name", sa.String(300), nullable=False),
                sa.Column("fact_key", sa.String(120), nullable=False),
                sa.Column("operator", sa.String(40), nullable=False),
                sa.Column("expected_json", sa.JSON(), nullable=False),
                sa.Column("is_hard_gate", sa.Boolean(), nullable=False, server_default=sa.true()),
                sa.Column("source_quote", sa.Text(), nullable=False),
                sa.Column("article", sa.String(160)),
                sa.Column("status", sa.String(40), nullable=False, server_default="active"),
            ],
        ),
        (
            "required_materials",
            [
                sa.Column("name", sa.String(300), nullable=False),
                sa.Column("description", sa.Text()),
                sa.Column("is_hard_gate", sa.Boolean(), nullable=False, server_default=sa.false()),
                sa.Column("source_quote", sa.Text(), nullable=False),
                sa.Column("article", sa.String(160)),
            ],
        ),
        (
            "policy_benefits",
            [
                sa.Column("benefit_type", sa.String(80), nullable=False),
                sa.Column("description", sa.Text(), nullable=False),
                sa.Column("amount_text", sa.String(160)),
                sa.Column("source_quote", sa.Text(), nullable=False),
                sa.Column("article", sa.String(160)),
            ],
        ),
    ):
        op.create_table(
            table,
            sa.Column("id", UUID, primary_key=True),
            sa.Column(
                "policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "policy_version_id",
                UUID,
                sa.ForeignKey("policy_versions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
            ),
            *extra,
            *_timestamps(),
        )
        for column in ("policy_id", "policy_version_id", "tenant_id"):
            op.create_index(f"ix_{table}_{column}", table, [column])

    op.create_table(
        "eligibility_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "opportunity_id",
            UUID,
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_version_id", UUID, sa.ForeignKey("policy_versions.id", ondelete="SET NULL")
        ),
        sa.Column(
            "profile_version_id",
            UUID,
            sa.ForeignKey("company_profile_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("criteria_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column(
            "missing_information_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "engine_version", sa.String(80), nullable=False, server_default="deterministic-v1"
        ),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="not_reviewed"),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("opportunity_id", name="uq_eligibility_opportunity"),
    )
    for column in (
        "tenant_id",
        "opportunity_id",
        "policy_version_id",
        "profile_version_id",
        "status",
    ):
        op.create_index(f"ix_eligibility_results_{column}", "eligibility_results", [column])

    op.create_table(
        "evidence",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
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
            "policy_version_id",
            UUID,
            sa.ForeignKey("policy_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "policy_chunk_id",
            UUID,
            sa.ForeignKey("policy_chunks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "eligibility_rule_id", UUID, sa.ForeignKey("eligibility_rules.id", ondelete="SET NULL")
        ),
        sa.Column("source_title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("issuer", sa.String(240)),
        sa.Column("article", sa.String(160)),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("quote_start", sa.Integer(), nullable=False),
        sa.Column("quote_end", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="1"),
        sa.Column("verifier", sa.String(80), nullable=False, server_default="exact_span_v1"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    for column in (
        "tenant_id",
        "opportunity_id",
        "eligibility_result_id",
        "policy_version_id",
        "policy_chunk_id",
    ):
        op.create_index(f"ix_evidence_{column}", "evidence", [column])

    op.execute("UPDATE agents SET status = 'active' WHERE key IN ('eligibility', 'evidence')")
    op.execute(
        "UPDATE workflows SET status = 'inactive' WHERE key = 'policy_scan' AND version = 'v1'"
    )
    op.execute(
        sa.text("""
            INSERT INTO workflows (
                id, key, name, version, status, definition_json, created_at, updated_at
            ) VALUES (
                CAST(:id AS uuid), 'policy_scan', 'Evidence-first policy opportunity scan',
                'v2', 'active', CAST(:definition AS json), now(), now()
            ) ON CONFLICT (key, version) DO NOTHING
        """).bindparams(
            id="22222222-2222-4222-8222-222222222002",
            definition=json.dumps(
                {
                    "steps": ["plan", "retrieve", "reason", "act", "verify", "finish"],
                    "input_schema": "PolicyScanWorkflowInput.v1",
                    "output_schema": "PolicyScanWorkflowOutput.v1",
                    "evidence_required": True,
                    "eligibility_engine": "deterministic-v1",
                }
            ),
        )
    )


def downgrade() -> None:
    op.execute("UPDATE agents SET status = 'inactive' WHERE key IN ('eligibility', 'evidence')")
    op.execute("""
        UPDATE workflow_runs
        SET workflow_id = '22222222-2222-4222-8222-222222222001'
        WHERE workflow_id = '22222222-2222-4222-8222-222222222002'
    """)
    op.execute("DELETE FROM workflows WHERE id = '22222222-2222-4222-8222-222222222002'")
    op.execute(
        "UPDATE workflows SET status = 'active' WHERE key = 'policy_scan' AND version = 'v1'"
    )
    for table in (
        "evidence",
        "eligibility_results",
        "policy_benefits",
        "required_materials",
        "eligibility_rules",
        "policy_chunks",
    ):
        op.drop_table(table)
    op.drop_index("ix_opportunities_policy_version_id", table_name="opportunities")
    op.drop_constraint(
        "fk_opportunities_policy_version_id",
        "opportunities",
        type_="foreignkey",
    )
    op.drop_column("opportunities", "policy_version_id")
    op.drop_table("policy_versions")
