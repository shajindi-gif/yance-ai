"""Keyword (lexical) retrieval — the part of search that needs no model.

Why this exists
---------------
Vector search is gated on a model budget that is not approved yet.  That gate must
not block the *other* half of retrieval: Chinese policy text is highly repetitive
("专精特新", "研发费用加计扣除", "申报截止"), which makes trigram matching a genuinely
useful baseline rather than a placeholder.

Properties:

* **No embeddings, no external calls.** Pure PostgreSQL (``pg_trgm``).
* **Evidence-preserving.** Every hit carries policy id, version id, chunk id and the
  character span inside the immutable version, so a citation can be re-checked.
* **Honest ranking.** ``rank`` is a lexical score (trigram similarity + term
  coverage + title weighting).  It is *not* a probability and must never be
  presented as "match confidence".
* **Filters are structural, not semantic.** Region/level/date filters come from
  parsed metadata; when a field is missing the hit is returned but flagged via
  ``metadata_gaps`` so an eligibility conclusion cannot silently rely on it.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Deliberately small: trigram similarity on long Chinese paragraphs is noisy, so
# ranking leans on term coverage in the title first.
_SQL = """
WITH terms AS (
    SELECT unnest(CAST(:terms AS text[])) AS term
),
scored AS (
    SELECT
        p.id                AS policy_id,
        v.title             AS policy_title,
        p.jurisdiction      AS jurisdiction,
        p.level             AS level,
        p.province          AS province,
        p.city              AS city,
        p.status            AS policy_status,
        p.published_at      AS published_at,
        p.effective_at      AS effective_at,
        p.deadline          AS deadline,
        p.expires_at        AS expires_at,
        p.source_url        AS source_url,
        p.issuing_authority AS issuing_authority,
        p.quality_grade     AS quality_grade,
        p.quality_score     AS quality_score,
        p.quality_deliverable AS quality_deliverable,
        v.id                AS version_id,
        v.version           AS version_no,
        (v.version < (SELECT max(v3.version) FROM policy_versions v3 WHERE v3.policy_id=p.id)) AS stale_version,
        c.id                AS chunk_id,
        c.chunk_index       AS chunk_index,
        c.article           AS article,
        c.char_start        AS char_start,
        c.char_end          AS char_end,
        c.content           AS chunk_content,
        (
            SELECT count(*) FROM terms t
            WHERE v.title ILIKE '%' || t.term || '%'
               OR c.content ILIKE '%' || t.term || '%'
        )::float                                                        AS term_coverage,
        (SELECT count(*) FROM terms t WHERE v.title ILIKE '%' || t.term || '%')::float
                                                                        AS title_hits,
        similarity(lower(v.title), lower(:query))                        AS title_similarity
    FROM policy_chunks c
    JOIN policy_versions v ON v.id = c.policy_version_id
    JOIN policies p ON p.id = c.policy_id
    -- ``collected`` is included on purpose: the collector stores documents before a
    -- human review pass, and a corpus nobody can search is not an asset.  The hit
    -- carries ``policy_status`` so callers can label unreviewed text and must not
    -- treat it as an eligibility conclusion.
    WHERE p.status = ANY(CAST(:statuses AS text[]))
      -- Tenant isolation is structural here, not a caller promise: the shared
      -- public library (tenant_id IS NULL) plus, only when a tenant is supplied,
      -- that tenant's private documents. A missing tenant id can never widen
      -- results to other customers.
      AND (p.tenant_id IS NULL
           OR (CAST(:tenant_id AS uuid) IS NOT NULL
               AND p.tenant_id = CAST(:tenant_id AS uuid)))
      -- Search the newest *searchable* version. A newer version can exist with no
      -- chunks (parse failed, empty body); falling back keeps an earlier, still
      -- accurate snapshot retrievable instead of silently dropping the document.
      AND v.version = (SELECT max(v2.version)
                       FROM policy_versions v2
                       JOIN policy_chunks c2 ON c2.policy_version_id = v2.id
                       WHERE v2.policy_id = p.id)
      AND (
            EXISTS (SELECT 1 FROM terms t WHERE c.content ILIKE '%' || t.term || '%')
         OR EXISTS (SELECT 1 FROM terms t WHERE v.title ILIKE '%' || t.term || '%')
      )
      -- Quality rubric gate: search must not surface documents the delivery policy
      -- withholds (repealed / expired / unsourced).  ``IS DISTINCT FROM false`` keeps
      -- never-assessed documents visible so deploying the rubric cannot empty the
      -- index before the backfill runs.
      AND (CAST(:include_low_quality AS boolean) = true
           OR p.quality_deliverable IS DISTINCT FROM false)
      AND (CAST(:level AS text) IS NULL OR p.level = CAST(:level AS text))
      AND (CAST(:jurisdiction AS text) IS NULL
           OR p.jurisdiction = CAST(:jurisdiction AS text)
           OR p.province = CAST(:jurisdiction AS text))
      AND (CAST(:published_from AS timestamptz) IS NULL
           OR p.published_at >= CAST(:published_from AS timestamptz))
      AND (CAST(:published_to AS timestamptz) IS NULL
           OR p.published_at <= CAST(:published_to AS timestamptz))
      AND (CAST(:current_only AS boolean) = false OR (
            (p.effective_at IS NULL OR p.effective_at <= now())
        AND (p.expires_at IS NULL OR p.expires_at >= now())
        AND (p.deadline IS NULL OR p.deadline >= now())
      ))
),
ranked AS (
    SELECT *,
           (term_coverage * 2.0 + title_hits * 3.0 + COALESCE(title_similarity, 0) * 1.5) AS rank,
           -- One row per document: without this the same policy filled every slot
           -- when several of its paragraphs matched, and a caller asking for 5
           -- results got 3 documents.
           row_number() OVER (
               PARTITION BY policy_id
               ORDER BY (term_coverage * 2.0 + title_hits * 3.0
                         + COALESCE(title_similarity, 0) * 1.5) DESC,
                        chunk_index
           ) AS policy_rank,
           count(*) OVER (PARTITION BY policy_id) AS matched_chunks
    FROM scored
)
SELECT * FROM ranked
WHERE policy_rank = 1
  -- Reranking noise floor.  A 4-character Chinese query is expanded into 2-char
  -- sliding windows for trigram recall; a single window matching ("专精" inside
  -- "专家精准") used to return documents that contain none of the query.  Requiring
  -- at least two matched terms keeps recall for 2-char queries while removing the
  -- single-window coincidence.
  AND term_coverage >= CAST(:min_coverage AS float)
ORDER BY rank DESC, published_at DESC NULLS LAST, policy_id
LIMIT :limit
"""


@dataclass
class KeywordHit:
    policy_id: str
    version_id: str
    chunk_id: str
    title: str
    snippet: str
    rank: float
    chunk_index: int | None = None
    article: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    level: str | None = None
    jurisdiction: str | None = None
    published_at: str | None = None
    effective_at: str | None = None
    deadline: str | None = None
    expires_at: str | None = None
    source_url: str | None = None
    issuing_authority: str | None = None
    version_no: int | None = None
    metadata_gaps: list[str] = field(default_factory=list)
    retrieval: str = "keyword_trigram"
    policy_status: str | None = None
    review_state: str = "unreviewed"
    matched_chunks: int = 1
    quality_grade: str | None = None
    quality_score: float | None = None
    quality_deliverable: bool | None = None
    quality_note: str | None = None

    def as_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version_id": self.version_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "snippet": self.snippet,
            "rank": round(self.rank, 4),
            "chunk_index": self.chunk_index,
            "article": self.article,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "level": self.level,
            "jurisdiction": self.jurisdiction,
            "published_at": self.published_at,
            "effective_at": self.effective_at,
            "deadline": self.deadline,
            "expires_at": self.expires_at,
            "source_url": self.source_url,
            "issuing_authority": self.issuing_authority,
            "version_no": self.version_no,
            "metadata_gaps": self.metadata_gaps,
            "retrieval": self.retrieval,
            "policy_status": self.policy_status,
            "review_state": self.review_state,
            "matched_chunks": self.matched_chunks,
            "quality_grade": self.quality_grade,
            "quality_score": self.quality_score,
            "quality_deliverable": self.quality_deliverable,
            "quality_note": self.quality_note,
        }


def _terms(query: str) -> list[str]:
    """Split a Chinese/latin query into trigram-friendly terms.

    Chinese has no spaces, so a naive whitespace split yields one huge term that
    only matches verbatim paragraphs.  We keep the full query *and* emit 2-char
    sliding windows for CJK runs, which is what ``pg_trgm`` indexes well.
    """
    cleaned = (query or "").strip()
    if not cleaned:
        return []
    terms: list[str] = []
    for token in cleaned.replace("\u3000", " ").split():
        if not token:
            continue
        if len(token) <= 12:
            terms.append(token)
        cjk = "".join(ch for ch in token if "\u4e00" <= ch <= "\u9fff")
        if len(token) > 4 and cjk:
            for index in range(len(cjk) - 1):
                candidate = cjk[index : index + 2]
                if candidate not in terms:
                    terms.append(candidate)
    # Deduplicate, keep order, drop tokens that would match everything.
    seen: set[str] = set()
    unique = []
    for term in terms:
        if len(term) < 2 and not term.isascii():
            continue
        if term in seen:
            continue
        seen.add(term)
        unique.append(term)
    return unique[:24]


def _snippet(content: str, terms: list[str], *, width: int = 220) -> str:
    lowered = content.lower()
    position = -1
    for term in terms:
        found = lowered.find(term.lower())
        if found >= 0 and (position < 0 or found < position):
            position = found
    if position < 0:
        return content[:width] + ("…" if len(content) > width else "")
    start = max(0, position - width // 3)
    end = min(len(content), start + width)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{content[start:end]}{suffix}"


def keyword_search(
    db: Session,
    query: str,
    *,
    limit: int = 10,
    level: str | None = None,
    jurisdiction: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    current_only: bool = False,
    tenant_id: uuid.UUID | str | None = None,
    statuses: Sequence[str] = ("published", "collected"),
    include_low_quality: bool = False,
) -> list[KeywordHit]:
    terms = _terms(query)
    if not terms:
        return []
    compact = "".join(ch for ch in query if not ch.isspace())
    min_coverage = 2.0 if len(compact) >= 3 and len(terms) > 2 else 1.0
    rows = db.execute(
        text(_SQL),
        {
            "query": query.strip(),
            "terms": terms,
            "limit": max(1, min(limit, 100)),
            "level": level,
            "jurisdiction": jurisdiction,
            "published_from": published_from,
            "published_to": published_to,
            "current_only": current_only,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "statuses": list(statuses),
            "min_coverage": min_coverage,
            "include_low_quality": include_low_quality,
        },
    ).mappings()
    hits: list[KeywordHit] = []
    for row in rows:
        gaps: list[str] = []
        if row["stale_version"]:
            gaps.append("newer_version_unavailable")
        if row["published_at"] is None:
            gaps.append("published_at")
        if row["jurisdiction"] is None and row["province"] is None:
            gaps.append("jurisdiction")
        if row["expires_at"] is None and row["deadline"] is None:
            gaps.append("validity_window")
        hits.append(
            KeywordHit(
                policy_id=str(row["policy_id"]),
                version_id=str(row["version_id"]),
                chunk_id=str(row["chunk_id"]),
                title=row["policy_title"],
                snippet=_snippet(row["chunk_content"] or "", terms),
                rank=float(row["rank"] or 0),
                chunk_index=row["chunk_index"],
                article=row["article"],
                char_start=row["char_start"],
                char_end=row["char_end"],
                level=row["level"],
                jurisdiction=row["jurisdiction"] or row["province"],
                published_at=row["published_at"].isoformat() if row["published_at"] else None,
                effective_at=row["effective_at"].isoformat() if row["effective_at"] else None,
                deadline=row["deadline"].isoformat() if row["deadline"] else None,
                expires_at=row["expires_at"].isoformat() if row["expires_at"] else None,
                source_url=row["source_url"],
                issuing_authority=row["issuing_authority"],
                version_no=row["version_no"],
                metadata_gaps=gaps,
                policy_status=row["policy_status"],
                review_state="published" if row["policy_status"] == "published" else "unreviewed",
                matched_chunks=int(row["matched_chunks"] or 1),
                quality_grade=row["quality_grade"],
                quality_score=float(row["quality_score"]) if row["quality_score"] is not None else None,
                quality_deliverable=row["quality_deliverable"],
                quality_note=(
                    None
                    if row["quality_grade"] == "A"
                    else "quality_grade_" + (row["quality_grade"] or "unassessed")
                ),
            )
        )
    return hits


def searchable_counts(db: Session, tenant_id: uuid.UUID | None = None) -> dict:
    """Count only public and explicitly scoped tenant evidence."""
    row = db.execute(text("""
        WITH visible AS (
          SELECT id, status FROM policies
          WHERE (tenant_id IS NULL OR tenant_id = CAST(:tenant_id AS uuid))
            AND status IN ('published', 'collected')
        )
        SELECT
          (SELECT count(*) FROM visible WHERE status='published') AS published_policies,
          (SELECT count(*) FROM visible) AS searchable_policies,
          (SELECT count(*) FROM policy_versions v JOIN visible p ON p.id=v.policy_id) AS versions,
          (SELECT count(*) FROM policy_chunks c JOIN visible p ON p.id=c.policy_id) AS chunks,
          (SELECT count(*) FROM policy_chunks c JOIN visible p ON p.id=c.policy_id
             WHERE c.embedding IS NOT NULL) AS embedded_chunks
    """), {"tenant_id": str(tenant_id) if tenant_id else None}).mappings().one()
    result = {key: int(value) for key, value in row.items()}
    return {**result, "keyword_searchable": result["chunks"] > 0,
            "vector_searchable": result["embedded_chunks"] > 0}


__all__ = ["KeywordHit", "keyword_search", "searchable_counts"]
