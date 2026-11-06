"""Persistence layer for collected policy documents.

The runner only talks to :class:`PolicyStore`, so the same pipeline can be run
against PostgreSQL (``SqlPolicyStore``) or an in-memory recorder used by the
integration tests (``MemoryPolicyStore``) on machines without a database.

Idempotency rules implemented here
----------------------------------
1. A document is identified by its **normalised final URL** plus its **content
   hash**; reposits are linked through ``policy_document_keys`` and never merged
   away (``policy_origins`` holds every official URL).
2. Re-running the same item with the same content writes **no** new version and
   spends **no** embedding budget (``ChangeKind.UNCHANGED``).
3. A changed body for the same URL adds a new immutable ``PolicyVersion``; the
   previous version and its chunks are left untouched.
4. Regional scope comes from the registered source (``level/province/city``),
   never from string slicing of the title, so a provincial document cannot be
   downgraded to its capital city.
5. ``Policy.status`` records the collection state (``collected`` pending review),
   not a government approval.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import Policy, PolicyChunk, PolicyVersion
from app.models.policy_collection import (
    PolicyApplicationWindow,
    PolicyAttachment,
    PolicyDocumentKey,
    PolicyOrigin,
    PolicyRawEvidence,
)
from app.services.policies.ingestion import chunk_policy_text, clean_policy_text

from .catalog import SourceDefinition
from .classify import Classification
from .fingerprint import (
    ChangeKind,
    ExistingState,
    IncomingDocument,
    decide_change,
    same_document_key,
    same_round,
)
from .urlguard import normalize_url

logger = logging.getLogger(__name__)

PARSER_VERSION = "2026.11.06-1"
DEFAULT_STATUS = "collected"  # collected -> pending_review -> published (human/quality gate)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


@dataclass(frozen=True)
class AttachmentPayload:
    url: str
    filename: str | None = None
    content_type: str | None = None
    byte_size: int = 0
    content_sha256: str | None = None
    storage_path: str | None = None
    parser_name: str | None = None
    parse_status: str = "pending"
    extracted_text_chars: int = 0
    ocr_used: bool = False
    ocr_confidence: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class WindowPayload:
    label: str | None
    start_date: date | None
    end_date: date | None
    entry_url: str | None = None
    evidence_text: str | None = None


@dataclass(frozen=True)
class DocumentPayload:
    """Everything the pipeline extracted from one official page."""

    source: SourceDefinition
    run_id: uuid.UUID | None
    url: str
    requested_url: str
    title: str
    text: str
    classification: Classification
    published_at: date | None = None
    effective_at: date | None = None
    expires_at: date | None = None
    doc_number: str | None = None
    issuer: str | None = None
    http_meta: dict = field(default_factory=dict)
    http_status: int | None = None
    content_sha256: str | None = None
    storage_path: str | None = None
    evidence_complete: bool = True
    parse_status: str = "parsed"
    parser_name: str = "html"
    parser_version: str = PARSER_VERSION
    attachments: tuple[AttachmentPayload, ...] = ()
    windows: tuple[WindowPayload, ...] = ()


@dataclass
class StoreResult:
    policy_id: uuid.UUID
    policy_version_id: uuid.UUID | None
    change: ChangeKind
    version: int | None = None
    created: bool = False
    embedding_status: str = "skipped"
    attachments_saved: int = 0
    attachments_failed: int = 0


class PolicyStore(Protocol):
    def save_document(self, payload: DocumentPayload) -> StoreResult: ...


# --------------------------------------------------------------------------- #
# helpers shared by both stores
# --------------------------------------------------------------------------- #
def jurisdiction_for(source: SourceDefinition) -> str | None:
    """Region label derived from the registered source, never from title slicing."""
    level = source.level
    if level == "national":
        return "全国"
    if level == "provincial":
        # A provincial source applies province-wide: do not narrow it to the capital.
        return source.province or None
    if level == "municipal":
        if source.city and source.province:
            return f"{source.province}{source.city}"
        return source.city or source.province
    return source.city or source.province


def _policy_fields(payload: DocumentPayload) -> dict:
    classification = payload.classification
    industries = ",".join(classification.industries[:4]) or None
    forms = classification.support_forms
    primary_form = forms[0].form if forms else None
    amount = forms[0].amount_text if forms and forms[0].amount_text else None
    windows = payload.windows
    deadline = None
    if len(windows) == 1 and windows[0].end_date is not None:
        # Only a single unambiguous round may be projected onto the policy row;
        # multiple rounds stay in policy_application_windows.
        deadline = _as_datetime(windows[0].end_date)
    return {
        "title": payload.title[:500],
        "issuing_authority": (payload.issuer or payload.source.authority)[:240],
        "level": payload.source.level,
        "province": payload.source.province,
        "city": payload.source.city,
        "industry": industries[:160] if industries else None,
        "policy_type": classification.doc_kind[:80],
        "source_url": payload.url[:1000],
        "jurisdiction": (jurisdiction_for(payload.source) or "")[:160] or None,
        "published_at": _as_datetime(payload.published_at),
        "effective_at": _as_datetime(payload.effective_at),
        "expires_at": _as_datetime(payload.expires_at),
        "deadline": deadline,
        "content": payload.text,
        "original_text": payload.text,
        "source": payload.source.name[:160],
        "crawled_at": _utcnow(),
        "support_amount": (amount or "")[:120] or None,
        "support_type": (primary_form or "")[:120] or None,
        "status": DEFAULT_STATUS,
    }


def _write_version(db: Session, policy: Policy, *, embedding_enabled: bool) -> tuple[PolicyVersion, str]:
    """Persist an immutable version + chunks, with a no-embedding fallback path."""
    content = clean_policy_text(policy.content or policy.original_text)
    policy.content = content or None
    latest = db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy.id)
        .order_by(PolicyVersion.version.desc())
    )
    version_number = (latest.version if latest else 0) + 1
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    if latest is not None and latest.content_sha256 == content_hash:
        return latest, "unchanged"

    version = PolicyVersion(
        policy_id=policy.id,
        tenant_id=policy.tenant_id,
        version=version_number,
        content_sha256=content_hash,
        title=policy.title,
        issuer=policy.issuing_authority,
        region=policy.jurisdiction,
        industry=policy.industry,
        policy_type=policy.policy_type,
        publish_date=policy.published_at,
        effective_date=policy.effective_at,
        expiry_date=policy.expires_at,
        application_deadline=policy.deadline,
        source_url=policy.source_url,
        source_name=policy.source,
        content=content,
        status=policy.status,
    )
    db.add(version)
    db.flush()

    # Embeddings are intentionally *not* produced here.  They are an async,
    # budgeted stage (``embedding_backfill``) so that a missing provider never
    # blocks evidence storage and never silently burns quota on re-runs.
    policy.embedding = None
    spans = chunk_policy_text(content)
    embedding_status = "pending" if (spans and embedding_enabled) else "skipped"

    for index, (start, end, text, article) in enumerate(spans):
        db.add(
            PolicyChunk(
                policy_id=policy.id,
                policy_version_id=version.id,
                tenant_id=policy.tenant_id,
                chunk_index=index,
                article=article,
                content=text,
                char_start=start,
                char_end=end,
                content_sha256=hashlib.sha256(text.encode()).hexdigest(),
                metadata_json={
                    "embedding_status": embedding_status,
                    "source": policy.source,
                    "title": policy.title,
                    "issuer": policy.issuing_authority,
                    "region": policy.jurisdiction,
                    "industry": policy.industry,
                    "policy_type": policy.policy_type,
                    "publish_date": policy.published_at.isoformat() if policy.published_at else None,
                    "effective_date": policy.effective_at.isoformat()
                    if policy.effective_at
                    else None,
                    "document_id": str(policy.id),
                    "article": article,
                    "url": policy.source_url,
                    "evidence": "policy_collection",
                },
                embedding=None,
            )
        )
    return version, embedding_status


class SqlPolicyStore:
    """PostgreSQL-backed store; one instance per session/run."""

    def __init__(self, db: Session, *, embedding_enabled: bool = False) -> None:
        self.db = db
        self.embedding_enabled = embedding_enabled

    # -- lookups ---------------------------------------------------------- #
    def _existing(self, url_normalized: str, source_id: str) -> ExistingState | None:
        origin = self.db.scalar(
            select(PolicyOrigin)
            .where(PolicyOrigin.url_normalized == url_normalized)
            .order_by(PolicyOrigin.is_primary.desc())
        )
        if origin is not None:
            policy = self.db.get(Policy, origin.policy_id)
            return ExistingState(
                document_id=policy.id if policy else origin.policy_id,
                final_url=origin.url_normalized,
                content_sha256=origin.content_sha256
                or (self.db.scalar(
                    select(PolicyVersion.content_sha256)
                    .where(PolicyVersion.policy_id == origin.policy_id)
                    .order_by(PolicyVersion.version.desc())
                ) or ""),
                title=policy.title if policy else "",
                doc_number=None,
                issuer=policy.issuing_authority if policy else None,
            )
        return None

    def _repost_target(self, key: str) -> tuple[Policy | None, bool]:
        row = self.db.scalar(select(PolicyDocumentKey).where(PolicyDocumentKey.same_document_key == key))
        if row is None:
            return None, False
        policy = self.db.get(Policy, row.policy_id)
        if policy is None:
            return None, False
        other_host = policy.source_url or ""
        return policy, bool(other_host)

    # -- main entry point ------------------------------------------------- #
    def save_document(self, payload: DocumentPayload) -> StoreResult:
        source = payload.source
        url_normalized = normalize_url(payload.url)
        content_sha256 = payload.content_sha256 or hashlib.sha256(
            normalize_text_for_hash(payload.text).encode()
        ).hexdigest()
        key = same_document_key(payload.doc_number, payload.issuer or source.authority, payload.title)

        existing = self._existing(url_normalized, source.source_id)
        if existing is not None and not same_round(existing.title, payload.title):
            # The URL is reused by a different year/batch notice; treat the
            # incoming document as new instead of overwriting the prior round.
            existing = None
        repost_policy, _ = self._repost_target(key)
        existing_state = existing
        if existing is None and repost_policy is not None:
            existing_state = ExistingState(
                document_id=repost_policy.id,
                final_url=normalize_url(repost_policy.source_url or ""),
                content_sha256=self.db.scalar(
                    select(PolicyVersion.content_sha256)
                    .where(PolicyVersion.policy_id == repost_policy.id)
                    .order_by(PolicyVersion.version.desc())
                )
                or "",
                title=repost_policy.title,
                doc_number=payload.doc_number,
                issuer=repost_policy.issuing_authority,
                same_document_other_url=True,
                same_document_other_host=True,
            )
        incoming = IncomingDocument(
            final_url=url_normalized,
            content_sha256=content_sha256,
            title=payload.title,
            doc_number=payload.doc_number,
            issuer=payload.issuer or source.authority,
        )
        change = decide_change(existing_state, incoming)

        policy: Policy | None = None
        version: PolicyVersion | None = None
        embedding_status = "skipped"
        created = False

        if change in {ChangeKind.NEW, ChangeKind.NEW_VERSION}:
            if change is ChangeKind.NEW_VERSION and existing is not None:
                policy = self.db.get(Policy, existing.document_id)
            if policy is None and repost_policy is not None:
                policy = repost_policy
            if policy is None:
                policy = Policy(tenant_id=None, **_policy_fields(payload))
                self.db.add(policy)
                self.db.flush()
                created = True
            else:
                for key_name, value in _policy_fields(payload).items():
                    if key_name in {"content", "original_text"}:
                        continue
                    if value is not None:
                        setattr(policy, key_name, value)
            version, embedding_status = _write_version(
                self.db, policy, embedding_enabled=self.embedding_enabled
            )
        elif change in {ChangeKind.REPOST_NEW_SOURCE, ChangeKind.REPOST_UPDATED}:
            policy = repost_policy
            if change is ChangeKind.REPOST_UPDATED and policy is not None:
                version, embedding_status = _write_version(
                    self.db, policy, embedding_enabled=self.embedding_enabled
                )
        elif existing is not None:
            policy = self.db.get(Policy, existing.document_id)
            if policy is not None:
                version = self.db.scalar(
                    select(PolicyVersion)
                    .where(PolicyVersion.policy_id == policy.id)
                    .order_by(PolicyVersion.version.desc())
                )

        if policy is None:  # pragma: no cover - defensive
            raise RuntimeError("policy store could not resolve a target policy")

        # de-duplication key (idempotent)
        if self.db.scalar(
            select(PolicyDocumentKey).where(
                PolicyDocumentKey.policy_id == policy.id,
                PolicyDocumentKey.same_document_key == key,
            )
        ) is None:
            self.db.add(
                PolicyDocumentKey(
                    policy_id=policy.id,
                    same_document_key=key,
                    doc_number=payload.doc_number,
                    issuer=payload.issuer or source.authority,
                    title_key=payload.title,
                    first_source_id=source.source_id,
                )
            )

        # provenance (every official URL kept)
        origin = self.db.scalar(
            select(PolicyOrigin).where(
                PolicyOrigin.policy_id == policy.id,
                PolicyOrigin.url_normalized == url_normalized,
            )
        )
        if origin is None:
            is_primary = not self.db.scalar(
                select(PolicyOrigin.id).where(
                    PolicyOrigin.policy_id == policy.id, PolicyOrigin.is_primary.is_(True)
                )
            )
            self.db.add(
                PolicyOrigin(
                    policy_id=policy.id,
                    source_id=source.source_id,
                    url=payload.url[:1000],
                    url_normalized=url_normalized,
                    host=(payload.http_meta.get("host") or "")[:160] or None,
                    level=source.level,
                    province=source.province,
                    city=source.city,
                    is_primary=bool(is_primary),
                    is_repost=bool(is_primary) is False,
                    content_sha256=content_sha256,
                )
            )
        else:
            origin.last_seen_at = _utcnow()
            origin.content_sha256 = content_sha256

        # application windows are per-round, never flattened into one deadline
        for window in payload.windows:
            window_key = hashlib.sha256(
                f"{window.label or ''}|{window.start_date}|{window.end_date}|{window.entry_url or ''}".encode()
            ).hexdigest()[:40]
            if self.db.scalar(
                select(PolicyApplicationWindow).where(
                    PolicyApplicationWindow.policy_id == policy.id,
                    PolicyApplicationWindow.window_key == window_key,
                )
            ) is None:
                self.db.add(
                    PolicyApplicationWindow(
                        policy_id=policy.id,
                        policy_version_id=version.id if version else None,
                        window_key=window_key,
                        label=(window.label or "")[:300] or None,
                        start_date=_as_datetime(window.start_date),
                        end_date=_as_datetime(window.end_date),
                        entry_url=window.entry_url,
                        evidence_text=window.evidence_text,
                        status="open"
                        if window.end_date and window.end_date >= date.today()
                        else "unknown",
                    )
                )

        saved, failed = self._save_attachments(policy, payload)

        self._write_evidence(policy, version, payload, url_normalized, content_sha256, change)

        try:
            self.db.commit()
        except IntegrityError:  # concurrent insert of the same item
            self.db.rollback()
            raise

        return StoreResult(
            policy_id=policy.id,
            policy_version_id=version.id if version else None,
            change=change,
            version=version.version if version else None,
            created=created,
            embedding_status=embedding_status,
            attachments_saved=saved,
            attachments_failed=failed,
        )

    # -- attachments / evidence ------------------------------------------ #
    def _save_attachments(self, policy: Policy, payload: DocumentPayload) -> tuple[int, int]:
        saved = failed = 0
        for attachment in payload.attachments:
            url_normalized = normalize_url(attachment.url)
            existing = self.db.scalar(
                select(PolicyAttachment).where(
                    PolicyAttachment.policy_id == policy.id,
                    PolicyAttachment.url_normalized == url_normalized,
                )
            )
            if existing is not None:
                # Same file already stored: refresh parse state only.
                if attachment.parse_status not in {"pending", "failed"}:
                    existing.parse_status = attachment.parse_status
                    existing.storage_path = attachment.storage_path or existing.storage_path
                    existing.content_sha256 = attachment.content_sha256 or existing.content_sha256
                    existing.parser_name = attachment.parser_name or existing.parser_name
                else:
                    existing.error = attachment.error
                continue
            self.db.add(
                PolicyAttachment(
                    policy_id=policy.id,
                    source_id=payload.source.source_id,
                    url=attachment.url[:1000],
                    url_normalized=url_normalized,
                    filename=(attachment.filename or "")[:300] or None,
                    content_type=attachment.content_type,
                    byte_size=attachment.byte_size,
                    content_sha256=attachment.content_sha256,
                    storage_path=attachment.storage_path,
                    parser_name=attachment.parser_name,
                    parse_status=attachment.parse_status,
                    extracted_text_chars=attachment.extracted_text_chars,
                    ocr_used=attachment.ocr_used,
                    ocr_confidence=attachment.ocr_confidence,
                    error=attachment.error,
                )
            )
            # Archived bytes count as saved even when parsing failed; the
            # parse_status column carries that distinction separately.
            if attachment.storage_path or attachment.content_sha256:
                saved += 1
            else:
                failed += 1
        return saved, failed

    def _write_evidence(
        self,
        policy: Policy,
        version: PolicyVersion | None,
        payload: DocumentPayload,
        url_normalized: str,
        content_sha256: str,
        change: ChangeKind,
    ) -> None:
        self.db.add(
            PolicyRawEvidence(
                source_id=payload.source.source_id,
                run_id=payload.run_id,
                policy_id=policy.id,
                policy_version_id=version.id if version else None,
                purpose="document",
                url_normalized=url_normalized[:1000],
                final_url=payload.url[:1000],
                http_status=payload.http_status,
                content_type=payload.http_meta.get("content_type"),
                byte_size=int(payload.http_meta.get("byte_size") or len(payload.text.encode())),
                content_sha256=content_sha256,
                http_meta={k: v for k, v in payload.http_meta.items() if k != "body"},
                storage_path=payload.storage_path,
                parser_name=payload.parser_name,
                parser_version=payload.parser_version,
                parse_status=payload.parse_status,
                evidence_complete=bool(payload.storage_path) and payload.evidence_complete,
                error_kind=None if payload.evidence_complete else "raw_storage_missing",
                error=None
                if payload.evidence_complete
                else "raw page was not stored; evidence is incomplete",
            )
            # NOTE: ``change`` drives counters upstream; it is not duplicated here.
        )


def normalize_text_for_hash(text: str) -> str:
    from .fingerprint import normalize_text

    return normalize_text(text)


# --------------------------------------------------------------------------- #
# in-memory store used by tests / dry runs
# --------------------------------------------------------------------------- #
@dataclass
class MemoryRecord:
    policy_id: str
    url: str
    title: str
    content_sha256: str
    change: str
    version: int
    level: str
    jurisdiction: str | None
    windows: int
    attachments: int


class MemoryPolicyStore:
    """Deterministic stand-in for the SQL store; mirrors its idempotency rules."""

    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []
        self._by_url: dict[str, MemoryRecord] = {}
        self._by_key: dict[str, MemoryRecord] = {}
        self._versions: dict[str, list[str]] = {}

    def save_document(self, payload: DocumentPayload) -> StoreResult:
        url_normalized = normalize_url(payload.url)
        content_sha256 = payload.content_sha256 or hashlib.sha256(
            normalize_text_for_hash(payload.text).encode()
        ).hexdigest()
        key = same_document_key(payload.doc_number, payload.issuer or payload.source.authority, payload.title)

        existing = self._by_url.get(url_normalized)
        if existing is not None and not same_round(existing.title, payload.title):
            # Same page, different allocation round: a distinct document, so the
            # earlier round keeps its own record and evidence.
            self._by_url.pop(url_normalized, None)
            existing = None
        repost = self._by_key.get(key)
        existing_state = None
        if existing is not None:
            existing_state = ExistingState(
                document_id=existing.policy_id,
                final_url=existing.url,
                content_sha256=existing.content_sha256,
                title=existing.title,
                doc_number=None,
                issuer=None,
            )
        elif repost is not None:
            existing_state = ExistingState(
                document_id=repost.policy_id,
                final_url=repost.url,
                content_sha256=repost.content_sha256,
                title=repost.title,
                doc_number=payload.doc_number,
                issuer=None,
                same_document_other_url=True,
                same_document_other_host=True,
            )
        change = decide_change(
            existing_state,
            IncomingDocument(
                final_url=url_normalized,
                content_sha256=content_sha256,
                title=payload.title,
                doc_number=payload.doc_number,
                issuer=payload.issuer or payload.source.authority,
            ),
        )

        if change in {ChangeKind.UNCHANGED, ChangeKind.REPOST_NEW_SOURCE}:
            target = existing or repost
            assert target is not None
            return StoreResult(
                policy_id=uuid.UUID(target.policy_id),
                policy_version_id=None,
                change=change,
                version=target.version,
                created=False,
            )

        if change in {ChangeKind.NEW_VERSION, ChangeKind.REPOST_UPDATED}:
            target = existing or repost
            assert target is not None
            versions = self._versions[target.policy_id]
            if versions and versions[-1] == content_sha256:
                return StoreResult(
                    policy_id=uuid.UUID(target.policy_id),
                    policy_version_id=None,
                    change=ChangeKind.UNCHANGED,
                    version=target.version,
                )
            versions.append(content_sha256)
            target.content_sha256 = content_sha256
            target.version = len(versions)
            target.change = change.value
            return StoreResult(
                policy_id=uuid.UUID(target.policy_id),
                policy_version_id=uuid.uuid4(),
                change=change,
                version=target.version,
            )

        policy_id = str(uuid.uuid4())
        record = MemoryRecord(
            policy_id=policy_id,
            url=url_normalized,
            title=payload.title,
            content_sha256=content_sha256,
            change=change.value,
            version=1,
            level=payload.source.level,
            jurisdiction=jurisdiction_for(payload.source),
            windows=len(payload.windows),
            attachments=len(payload.attachments),
        )
        self.records.append(record)
        self._by_url[url_normalized] = record
        self._by_key.setdefault(key, record)
        self._versions[policy_id] = [content_sha256]
        return StoreResult(
            policy_id=uuid.UUID(policy_id),
            policy_version_id=uuid.uuid4(),
            change=change,
            version=1,
            created=True,
            # "saved" means the original bytes are archived, independent of
            # whether text extraction succeeded; parse state lives on the
            # attachment row so a corrupt PDF still counts as captured evidence.
            attachments_saved=len(
                [a for a in payload.attachments if a.storage_path or a.content_sha256]
            ),
            attachments_failed=len(
                [a for a in payload.attachments if not (a.storage_path or a.content_sha256)]
            ),
        )
