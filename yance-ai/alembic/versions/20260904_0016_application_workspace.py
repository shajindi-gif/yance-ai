"""Add Application document, artifact, review, and comment records.

Revision ID: 20260904_0016
Revises: 20260903_0015
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260904_0016"
down_revision = "20260903_0015"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "application_document_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", UUID, sa.ForeignKey("application_requirements.id", ondelete="SET NULL")),
        sa.Column("added_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False, server_default="linked"),
        *_timestamps(),
        sa.UniqueConstraint(
            "application_id", "document_id", "requirement_id",
            name="uq_application_document_requirement",
            postgresql_nulls_not_distinct=True,
        ),
    )
    for column in ("tenant_id", "application_id", "document_id", "requirement_id"):
        op.create_index(f"ix_application_document_links_{column}", "application_document_links", [column])

    op.create_table(
        "application_artifacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("artifact_type", sa.String(80), nullable=False, server_default="application_brief"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("generation_method", sa.String(120), nullable=False, server_default="deterministic-evidence-v1"),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("source_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("reviewed_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint(
            "application_id", "artifact_type", "version",
            name="uq_application_artifact_version",
        ),
    )
    for column in ("tenant_id", "application_id", "status", "checksum_sha256"):
        op.create_index(f"ix_application_artifacts_{column}", "application_artifacts", [column])

    op.create_table(
        "application_comments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("tenant_id", "application_id"):
        op.create_index(f"ix_application_comments_{column}", "application_comments", [column])


def downgrade() -> None:
    op.drop_table("application_comments")
    op.drop_table("application_artifacts")
    op.drop_table("application_document_links")
