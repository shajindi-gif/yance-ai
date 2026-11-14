"""De-duplication and version decision rules.

The previous importer skipped any row whose ``source_url`` already existed,
which silently dropped updates to the same official page. The rule implemented
here separates the three questions:

1. *Is this the same document?* — canonical URL, then document number +
   issuer + normalised title.
2. *Is the content new?* — SHA-256 over the normalised extracted text.
3. *Is this a different official site republishing the same text?* — same
   document number with a different host becomes a linked repost, never a merge
   that erases the original source.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from .urlguard import normalize_url


class ChangeKind(StrEnum):
    NEW = "new"
    NEW_VERSION = "new_version"
    UNCHANGED = "unchanged"
    REPOST_NEW_SOURCE = "repost_new_source"
    REPOST_UPDATED = "repost_updated"


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t\u3000]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def title_key(title: str) -> str:
    value = normalize_text(title)
    value = re.sub(r"[\s　]+", "", value)
    value = re.sub(r"[（(].*?[)）]", "", value)
    return value[-80:]


@dataclass(frozen=True)
class ExistingState:
    """What the database already knows about a given source URL."""

    document_id: object
    final_url: str
    content_sha256: str
    title: str
    doc_number: str | None
    issuer: str | None
    same_document_other_url: object | None = None
    same_document_other_host: bool = False


@dataclass(frozen=True)
class IncomingDocument:
    final_url: str
    content_sha256: str
    title: str
    doc_number: str | None
    issuer: str | None


def decide_change(existing: ExistingState | None, incoming: IncomingDocument) -> ChangeKind:
    if existing is None:
        if incoming.doc_number and incoming.issuer:
            return ChangeKind.NEW
        return ChangeKind.NEW
    if existing.content_sha256 == incoming.content_sha256:
        if existing.final_url != incoming.final_url and existing.same_document_other_host:
            return ChangeKind.REPOST_NEW_SOURCE
        return ChangeKind.UNCHANGED
    if existing.final_url == incoming.final_url:
        return ChangeKind.NEW_VERSION
    if existing.same_document_other_host:
        return ChangeKind.REPOST_UPDATED
    return ChangeKind.NEW


def same_document_key(doc_number: str | None, issuer: str | None, title: str) -> str:
    """Stable key used to link reposts without merging provenance."""
    normalized_issuer = re.sub(r"\s+", "", issuer or "")
    if doc_number:
        return f"docno:{re.sub(r'\\s+', '', doc_number)}|{normalized_issuer}"
    return f"title:{title_key(title)}|{normalized_issuer}"


_BATCH_PATTERNS = (
    re.compile(r"(20\d{2})\s*年?(?:度)?"),
    re.compile(r"第\s*([一二三四五六七八九十0-9]+)\s*批"),
    re.compile(r"([一二三四五六七八九十0-9]+)\s*批"),
)


def batch_signature(title: str) -> tuple[str, ...]:
    """Year + batch markers carried by a title.

    Two notices for different funding rounds may live under the same URL on some
    CMS setups (a "current round" page). The year/batch markers keep them apart
    so a 2026 second-round notice never merges into the 2025 first-round policy.
    """
    text = title or ""
    years = sorted({match.group(1) for match in _BATCH_PATTERNS[0].finditer(text)})
    batches: set[str] = set()
    for pattern in _BATCH_PATTERNS[1:]:
        batches.update(match.group(1) for match in pattern.finditer(text))
    return tuple([*(f"y{year}" for year in years), *(f"b{batch}" for batch in sorted(batches))])


def same_round(left: str, right: str) -> bool:
    """True when two titles do not contradict each other on year/batch markers."""
    left_sig = batch_signature(left)
    right_sig = batch_signature(right)
    if not left_sig or not right_sig:
        return True
    return left_sig == right_sig
