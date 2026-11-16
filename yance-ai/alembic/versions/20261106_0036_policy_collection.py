"""Additive tables for the continuous policy collection system.

Scope
-----
* Seven **new** tables only. No existing column is altered, so an older
  application build keeps running against a migrated database and the rollback
  path is "stop the collector", not "restore the database".
* ``downgrade`` refuses to drop evidence unless ``POLICY_COLLECTION_ALLOW_DROP=1``
  is set explicitly: raw evidence and provenance are the audit trail for every
  policy we ever showed a customer.
"""
import os

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261106_0036"
down_revision = "20261031_0035"
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
        "policy_sources",
        sa.Column("source_id", sa.String(80), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paused_reason", sa.String(400)),
        sa.Column("verification_state", sa.String(24), nullable=False, server_default="registered"),
        sa.Column("last_check_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_kind", sa.String(40)),
        sa.Column("last_error", sa.String(1000)),
        sa.Column("last_items_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_items_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_items_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_items_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cursor", sa.JSON(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_policy_sources_enabled", "policy_sources", ["enabled"])
    op.create_index("ix_policy_sources_paused", "policy_sources", ["paused"])
    op.create_index("ix_policy_sources_verification_state", "policy_sources", ["verification_state"])

    op.create_table(
        "policy_collection_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("trigger", sa.String(24), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(24), nullable=False, server_default="running"),
        sa.Column("lock_token", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_unchanged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attachments_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attachments_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("models_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_kind", sa.String(40)),
        sa.Column("error_summary", sa.Text()),
        sa.Column("stats", sa.JSON(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_policy_collection_runs_source_id", "policy_collection_runs", ["source_id"])
    op.create_index("ix_policy_collection_runs_status", "policy_collection_runs", ["status"])
    op.create_index("ix_policy_collection_runs_started_at", "policy_collection_runs", ["started_at"])
    op.create_index(
        "ix_policy_collection_runs_source_started",
        "policy_collection_runs",
        ["source_id", "started_at"],
    )

    op.create_table(
        "policy_raw_evidence",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column(
            "run_id",
            UUID,
            sa.ForeignKey("policy_collection_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("policy_id", UUID, sa.ForeignKey("policies.id", ondelete="SET NULL")),
        sa.Column(
            "policy_version_id",
            UUID,
            sa.ForeignKey("policy_versions.id", ondelete="SET NULL"),
        ),
        sa.Column("purpose", sa.String(24), nullable=False, server_default="document"),
        sa.Column("url_normalized", sa.String(1000), nullable=False),
        sa.Column("final_url", sa.String(1000)),
        sa.Column("http_status", sa.Integer()),
        sa.Column("content_type", sa.String(160)),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_sha256", sa.String(64)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_meta", sa.JSON(), nullable=True),
        sa.Column("storage_path", sa.String(1000)),
        sa.Column("parser_name", sa.String(80)),
        sa.Column("parser_version", sa.String(40)),
        sa.Column("parse_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("evidence_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_kind", sa.String(40)),
        sa.Column("error", sa.String(1000)),
        *_timestamps(),
    )
    op.create_index("ix_policy_raw_evidence_source_id", "policy_raw_evidence", ["source_id"])
    op.create_index("ix_policy_raw_evidence_run_id", "policy_raw_evidence", ["run_id"])
    op.create_index("ix_policy_raw_evidence_policy_id", "policy_raw_evidence", ["policy_id"])
    op.create_index(
        "ix_policy_raw_evidence_policy_version_id", "policy_raw_evidence", ["policy_version_id"]
    )
    op.create_index(
        "ix_policy_raw_evidence_url_normalized", "policy_raw_evidence", ["url_normalized"]
    )
    op.create_index("ix_policy_raw_evidence_content_sha256", "policy_raw_evidence", ["content_sha256"])
    op.create_index("ix_policy_raw_evidence_fetched_at", "policy_raw_evidence", ["fetched_at"])
    op.create_index("ix_policy_raw_evidence_parse_status", "policy_raw_evidence", ["parse_status"])
    op.create_index(
        "ix_policy_raw_evidence_evidence_complete", "policy_raw_evidence", ["evidence_complete"]
    )
    op.create_index(
        "ix_policy_raw_evidence_url_hash",
        "policy_raw_evidence",
        ["url_normalized", "content_sha256"],
    )
    op.create_index(
        "ix_policy_raw_evidence_source_fetched",
        "policy_raw_evidence",
        ["source_id", "fetched_at"],
    )

    op.create_table(
        "policy_attachments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "evidence_id", UUID, sa.ForeignKey("policy_raw_evidence.id", ondelete="SET NULL")
        ),
        sa.Column("source_id", sa.String(80)),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("url_normalized", sa.String(1000), nullable=False),
        sa.Column("filename", sa.String(300)),
        sa.Column("content_type", sa.String(160)),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_sha256", sa.String(64)),
        sa.Column("storage_path", sa.String(1000)),
        sa.Column("parser_name", sa.String(80)),
        sa.Column("parse_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("extracted_text_chars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ocr_confidence", sa.Numeric(4, 3)),
        sa.Column("error", sa.String(1000)),
        *_timestamps(),
        sa.UniqueConstraint("policy_id", "url_normalized", name="uq_policy_attachment_url"),
    )
    op.create_index("ix_policy_attachments_policy_id", "policy_attachments", ["policy_id"])
    op.create_index("ix_policy_attachments_source_id", "policy_attachments", ["source_id"])
    op.create_index("ix_policy_attachments_content_sha256", "policy_attachments", ["content_sha256"])
    op.create_index("ix_policy_attachments_parse_status", "policy_attachments", ["parse_status"])

    op.create_table(
        "policy_document_keys",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("same_document_key", sa.String(320), nullable=False),
        sa.Column("doc_number", sa.String(160)),
        sa.Column("issuer", sa.String(240)),
        sa.Column("title_key", sa.String(200)),
        sa.Column("first_source_id", sa.String(80)),
        *_timestamps(),
        sa.UniqueConstraint("policy_id", "same_document_key", name="uq_policy_document_key"),
    )
    op.create_index("ix_policy_document_keys_policy_id", "policy_document_keys", ["policy_id"])
    op.create_index(
        "ix_policy_document_keys_same_document_key", "policy_document_keys", ["same_document_key"]
    )
    op.create_index("ix_policy_document_keys_doc_number", "policy_document_keys", ["doc_number"])
    op.create_index("ix_policy_document_keys_title_key", "policy_document_keys", ["title_key"])

    op.create_table(
        "policy_origins",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("url_normalized", sa.String(1000), nullable=False),
        sa.Column("host", sa.String(160)),
        sa.Column("level", sa.String(40)),
        sa.Column("province", sa.String(80)),
        sa.Column("city", sa.String(80)),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_repost", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.String(64)),
        *_timestamps(),
        sa.UniqueConstraint("policy_id", "url_normalized", name="uq_policy_origin_url"),
    )
    op.create_index("ix_policy_origins_policy_id", "policy_origins", ["policy_id"])
    op.create_index("ix_policy_origins_source_id", "policy_origins", ["source_id"])
    op.create_index("ix_policy_origins_url_normalized", "policy_origins", ["url_normalized"])
    op.create_index("ix_policy_origins_host", "policy_origins", ["host"])
    op.create_index("ix_policy_origins_is_primary", "policy_origins", ["is_primary"])

    op.create_table(
        "policy_application_windows",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "policy_version_id", UUID, sa.ForeignKey("policy_versions.id", ondelete="SET NULL")
        ),
        sa.Column("window_key", sa.String(200), nullable=False),
        sa.Column("label", sa.String(300)),
        sa.Column("start_date", sa.DateTime(timezone=True)),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("entry_url", sa.String(1000)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("status", sa.String(24), nullable=False, server_default="unknown"),
        *_timestamps(),
        sa.UniqueConstraint(
            "policy_id", "window_key", name="uq_policy_application_window_key"
        ),
    )
    op.create_index(
        "ix_policy_application_windows_policy_id", "policy_application_windows", ["policy_id"]
    )
    op.create_index(
        "ix_policy_application_windows_policy_version_id",
        "policy_application_windows",
        ["policy_version_id"],
    )
    op.create_index(
        "ix_policy_application_windows_end_date", "policy_application_windows", ["end_date"]
    )
    op.create_index(
        "ix_policy_application_windows_status", "policy_application_windows", ["status"]
    )


def downgrade():
    if os.environ.get("POLICY_COLLECTION_ALLOW_DROP") != "1":
        raise RuntimeError(
            "Rolling back would drop raw policy evidence and provenance. "
            "Stop the collector and roll the application back instead; set "
            "POLICY_COLLECTION_ALLOW_DROP=1 only if you have archived the evidence."
        )
    op.drop_table("policy_application_windows")
    op.drop_table("policy_origins")
    op.drop_table("policy_document_keys")
    op.drop_table("policy_attachments")
    op.drop_table("policy_raw_evidence")
    op.drop_table("policy_collection_runs")
    op.drop_table("policy_sources")
