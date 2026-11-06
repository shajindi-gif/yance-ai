"""Runtime state and raw evidence tables for the continuous policy collection system.

Design constraints
------------------
* **Additive only.**  Every table here is new, so an older application build keeps
  working against a migrated database (it simply ignores these tables).  No
  existing column is altered, which keeps the rollback path to "stop the
  collector" instead of "restore the database".
* **Evidence first.**  ``policy_raw_evidence`` records what the crawler actually
  received (hash, HTTP metadata, storage path).  A record with
  ``evidence_complete = False`` must never be presented as complete evidence.
* **Provenance is not merged.**  ``policy_origins`` links every official URL that
  carries the same document (reposts included) without overwriting the first
  source, and ``policy_document_keys`` holds the deterministic de-duplication key.

The tables deliberately do not touch tenant-owned data: the public policy base is
platform level, and tenant documents live in ``documents`` / ``document_chunks``.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.models import TimestampMixin, now_utc


class PolicySourceState(Base, TimestampMixin):
    """Mutable runtime state per registered source (the catalog YAML stays the source of truth)."""

    __tablename__ = "policy_sources"

    source_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    paused_reason: Mapped[str | None] = mapped_column(String(400))
    verification_state: Mapped[str] = mapped_column(String(24), default="registered", index=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_error_kind: Mapped[str | None] = mapped_column(String(40))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    last_items_seen: Mapped[int] = mapped_column(Integer, default=0)
    last_items_new: Mapped[int] = mapped_column(Integer, default=0)
    last_items_changed: Mapped[int] = mapped_column(Integer, default=0)
    last_items_failed: Mapped[int] = mapped_column(Integer, default=0)
    cursor: Mapped[dict] = mapped_column(JSON, default=dict)


class PolicyCollectionRun(Base, TimestampMixin):
    """One execution of one source; the audit trail for "0 new items" claims."""

    __tablename__ = "policy_collection_runs"
    __table_args__ = (
        Index("ix_policy_collection_runs_source_started", "source_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    trigger: Mapped[str] = mapped_column(String(24), default="manual")
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    lock_token: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    items_changed: Mapped[int] = mapped_column(Integer, default=0)
    items_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    attachments_saved: Mapped[int] = mapped_column(Integer, default=0)
    attachments_failed: Mapped[int] = mapped_column(Integer, default=0)
    models_used: Mapped[int] = mapped_column(Integer, default=0)
    error_kind: Mapped[str | None] = mapped_column(String(40))
    error_summary: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)


class PolicyRawEvidence(Base, TimestampMixin):
    """Immutable record of one fetched artefact (list page, article, attachment)."""

    __tablename__ = "policy_raw_evidence"
    __table_args__ = (
        Index("ix_policy_raw_evidence_url_hash", "url_normalized", "content_sha256"),
        Index("ix_policy_raw_evidence_source_fetched", "source_id", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_collection_runs.id", ondelete="SET NULL"), index=True
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="SET NULL"), index=True
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="SET NULL"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(24), default="document")
    url_normalized: Mapped[str] = mapped_column(String(1000), index=True)
    final_url: Mapped[str | None] = mapped_column(String(1000))
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(160))
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    http_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    parser_name: Mapped[str | None] = mapped_column(String(80))
    parser_version: Mapped[str | None] = mapped_column(String(40))
    parse_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    evidence_complete: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error_kind: Mapped[str | None] = mapped_column(String(40))
    error: Mapped[str | None] = mapped_column(String(1000))


class PolicyAttachment(Base, TimestampMixin):
    """Attachment of a policy document (form, table, scanned notice)."""

    __tablename__ = "policy_attachments"
    __table_args__ = (
        UniqueConstraint("policy_id", "url_normalized", name="uq_policy_attachment_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_raw_evidence.id", ondelete="SET NULL")
    )
    source_id: Mapped[str | None] = mapped_column(String(80), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    url_normalized: Mapped[str] = mapped_column(String(1000))
    filename: Mapped[str | None] = mapped_column(String(300))
    content_type: Mapped[str | None] = mapped_column(String(160))
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    parser_name: Mapped[str | None] = mapped_column(String(80))
    parse_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    extracted_text_chars: Mapped[int] = mapped_column(Integer, default=0)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    error: Mapped[str | None] = mapped_column(String(1000))


class PolicyDocumentKey(Base, TimestampMixin):
    """Deterministic de-duplication / repost-linking key for a policy document."""

    __tablename__ = "policy_document_keys"
    __table_args__ = (
        UniqueConstraint("policy_id", "same_document_key", name="uq_policy_document_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    same_document_key: Mapped[str] = mapped_column(String(320), index=True)
    doc_number: Mapped[str | None] = mapped_column(String(160), index=True)
    issuer: Mapped[str | None] = mapped_column(String(240))
    title_key: Mapped[str | None] = mapped_column(String(200), index=True)
    first_source_id: Mapped[str | None] = mapped_column(String(80))


class PolicyOrigin(Base, TimestampMixin):
    """Every official URL that carries the document; reposts are linked, never merged away."""

    __tablename__ = "policy_origins"
    __table_args__ = (
        UniqueConstraint("policy_id", "url_normalized", name="uq_policy_origin_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    url_normalized: Mapped[str] = mapped_column(String(1000), index=True)
    host: Mapped[str | None] = mapped_column(String(160), index=True)
    level: Mapped[str | None] = mapped_column(String(40))
    province: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_repost: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    content_sha256: Mapped[str | None] = mapped_column(String(64))


class PolicyApplicationWindow(Base, TimestampMixin):
    """A specific application round (batch) — never flattened into the policy deadline."""

    __tablename__ = "policy_application_windows"
    __table_args__ = (
        UniqueConstraint(
            "policy_id", "window_key", name="uq_policy_application_window_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="SET NULL"), index=True
    )
    window_key: Mapped[str] = mapped_column(String(200))
    label: Mapped[str | None] = mapped_column(String(300))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    entry_url: Mapped[str | None] = mapped_column(String(1000))
    evidence_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="unknown", index=True)
