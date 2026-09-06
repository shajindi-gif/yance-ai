"""Add durable document ingestion and reviewable company intelligence.

Revision ID: 20260906_0021
Revises: 20260905_0020
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260906_0021"
down_revision = "20260905_0020"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON_OBJECT = sa.text("'{}'::json")


def _tenant_column() -> sa.Column:
    return sa.Column(
        "tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "document_ingestion_runs",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "document_id",
            UUID,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column(
            "parser_version", sa.String(80), nullable=False, server_default="document-parser-v1"
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(120)),
        sa.Column("safe_message", sa.String(500)),
        sa.Column("metrics_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "attempt", name="uq_document_ingestion_attempt"),
    )
    for column in ("tenant_id", "document_id", "status", "lease_expires_at"):
        op.create_index(f"ix_document_ingestion_runs_{column}", "document_ingestion_runs", [column])

    op.create_table(
        "document_contents",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("parser", sa.String(80), nullable=False),
        sa.Column("parser_version", sa.String(80), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer()),
        sa.Column("language", sa.String(40)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", name="uq_document_content_document"),
    )
    op.create_index("ix_document_contents_tenant_id", "document_contents", ["tenant_id"])
    op.create_index("ix_document_contents_document_id", "document_contents", ["document_id"])
    op.create_index("ix_document_contents_text_sha256", "document_contents", ["text_sha256"])

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("character_start", sa.Integer(), nullable=False),
        sa.Column("character_end", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("locator_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("embedding", Vector(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "sequence", name="uq_document_chunk_sequence"),
    )
    for column in ("tenant_id", "document_id", "content_sha256"):
        op.create_index(f"ix_document_chunks_{column}", "document_chunks", [column])

    op.create_table(
        "document_fact_candidates",
        sa.Column("id", UUID, primary_key=True),
        _tenant_column(),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("field_key", sa.String(120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=False),
        sa.Column("source_locator_json", sa.JSON(), nullable=False, server_default=JSON_OBJECT),
        sa.Column("extraction_method", sa.String(80), nullable=False, server_default="deterministic"),
        sa.Column(
            "extraction_version",
            sa.String(80),
            nullable=False,
            server_default="company-intelligence-v1",
        ),
        sa.Column("candidate_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("reviewed_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "candidate_hash", name="uq_document_fact_candidate_hash"),
    )
    for column in ("tenant_id", "document_id", "company_id", "field_key", "status"):
        op.create_index(
            f"ix_document_fact_candidates_{column}", "document_fact_candidates", [column]
        )


def downgrade() -> None:
    op.drop_table("document_fact_candidates")
    op.drop_table("document_chunks")
    op.drop_table("document_contents")
    op.drop_table("document_ingestion_runs")
