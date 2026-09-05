import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Policy, PolicyChunk, PolicyVersion
from app.services.llm.registry import embed_texts

MAX_CHUNK_CHARS = 900
ARTICLE_PATTERN = re.compile(r"^(第[一二三四五六七八九十百千万0-9]+条|[一二三四五六七八九十]+、)")


def clean_policy_text(value: str | None) -> str:
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def chunk_policy_text(content: str) -> list[tuple[int, int, str, str | None]]:
    """Return exact, non-invented source spans; chunks never rewrite source text."""
    if not content:
        return []
    chunks: list[tuple[int, int, str, str | None]] = []
    start = 0
    while start < len(content):
        hard_end = min(start + MAX_CHUNK_CHARS, len(content))
        end = hard_end
        if hard_end < len(content):
            boundary = max(
                content.rfind("\n", start, hard_end), content.rfind("。", start, hard_end)
            )
            if boundary > start + MAX_CHUNK_CHARS // 2:
                end = boundary + 1
        text = content[start:end]
        heading = next((line for line in text.splitlines() if ARTICLE_PATTERN.match(line)), None)
        article = (
            ARTICLE_PATTERN.match(heading).group(1)
            if heading and ARTICLE_PATTERN.match(heading)
            else None
        )
        chunks.append((start, end, text, article))
        start = end
    return chunks


async def version_and_chunk_policy(db: Session, policy: Policy) -> PolicyVersion:
    content = clean_policy_text(policy.content or policy.original_text)
    policy.content = content or None
    latest = db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy.id)
        .order_by(PolicyVersion.version.desc())
    )
    version_number = (latest.version if latest else 0) + 1
    version = PolicyVersion(
        policy_id=policy.id,
        tenant_id=policy.tenant_id,
        version=version_number,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        title=policy.title,
        issuer=policy.issuing_authority,
        region=policy.jurisdiction,
        industry=policy.industry,
        policy_type=policy.policy_type,
        publish_date=policy.published_at,
        effective_date=policy.effective_at,
        expiry_date=policy.deadline,
        source_url=policy.source_url,
        source_name=policy.source,
        content=content,
        status=policy.status,
    )
    db.add(version)
    db.flush()

    spans = chunk_policy_text(content)
    vectors: list[list[float]] = []
    if spans:
        embedded = await embed_texts([content, *[text for _, _, text, _ in spans]])
        policy.embedding = embedded[0]
        vectors = embedded[1:]
    else:
        policy.embedding = None
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
                    "source": policy.source,
                    "title": policy.title,
                    "issuer": policy.issuing_authority,
                    "region": policy.jurisdiction,
                    "industry": policy.industry,
                    "policy_type": policy.policy_type,
                    "publish_date": policy.published_at.isoformat()
                    if policy.published_at
                    else None,
                    "effective_date": policy.effective_at.isoformat()
                    if policy.effective_at
                    else None,
                    "expiry_date": policy.deadline.isoformat() if policy.deadline else None,
                    "document_id": str(policy.id),
                    "article": article,
                    "url": policy.source_url,
                },
                embedding=vectors[index] if vectors else None,
            )
        )
    return version


def latest_policy_version(db: Session, policy_id) -> PolicyVersion | None:
    return db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyVersion.version.desc())
    )
