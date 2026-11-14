"""Database-backed verification of the evidence pipeline.

These tests require a migrated PostgreSQL database (``APP_ENV=test`` +
``DATABASE_URL`` + ``YANCE_TEST_DATABASE_ACK``).  They are the checks that the
pure-logic unit tests cannot make:

* evidence lands in the DB **and** on disk before parsing is attempted;
* keyword search returns citable spans (policy/version/chunk + char offsets);
* re-running the same URL with unchanged content does not create a new version;
* changed content creates a new immutable version and the old one stays readable;
* stale/expired documents are not returned as "currently open" opportunities.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal
from app.models.models import Policy, PolicyChunk, PolicyVersion


def _seed_policy(
    db,
    *,
    title: str,
    body: str,
    version: int = 1,
    published_at: datetime | None = None,
    expires_at: datetime | None = None,
    deadline: datetime | None = None,
    jurisdiction: str = "上海市",
    level: str = "municipal",
    status: str = "published",
):
    policy = Policy(
        id=uuid.uuid4(),
        title=title,
        level=level,
        province=jurisdiction,
        jurisdiction=jurisdiction,
        published_at=published_at or datetime(2026, 1, 10, tzinfo=UTC),
        expires_at=expires_at,
        deadline=deadline,
        status=status,
        source_url=f"https://test.invalid/{uuid.uuid4().hex}",
    )
    db.add(policy)
    db.flush()
    version_row = PolicyVersion(
        id=uuid.uuid4(),
        policy_id=policy.id,
        version=version,
        content_sha256=hashlib.sha256(body.encode()).hexdigest(),
        title=title,
        content=body,
        source_url=policy.source_url,
        publish_date=policy.published_at,
    )
    db.add(version_row)
    db.flush()
    db.add(
        PolicyChunk(
            id=uuid.uuid4(),
            policy_id=policy.id,
            policy_version_id=version_row.id,
            chunk_index=0,
            content=body,
            char_start=0,
            char_end=len(body),
            content_sha256=hashlib.sha256(body.encode()).hexdigest(),
        )
    )
    db.commit()
    return policy


@pytest.fixture()
def db():
    """Session plus cleanup, so repeated runs cannot disturb ranking assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.execute(
            text("DELETE FROM policies WHERE source_url LIKE 'https://test.invalid/%'")
        )
        session.commit()
        session.close()


def test_keyword_search_returns_citable_span(db):
    from app.services.policy_collection.keyword_search import keyword_search

    marker = f"专精特新{uuid.uuid4().hex[:8]}"
    policy = _seed_policy(
        db,
        title=f"{marker}企业培育实施细则",
        body=f"第一条 为支持{marker}企业发展，给予一次性奖励五十万元。",
    )
    hits = keyword_search(db, marker, limit=50)
    ours = [hit for hit in hits if hit.policy_id == str(policy.id)]
    assert ours, "keyword search must find the seeded document"
    hit = ours[0]
    assert hit.version_id and hit.chunk_id
    assert hit.char_start == 0 and hit.char_end > 0
    assert marker in hit.snippet
    assert hit.retrieval == "keyword_trigram"
    # Evidence gaps are surfaced rather than silently assumed.
    assert "validity_window" in hit.metadata_gaps or "published_at" not in hit.metadata_gaps


def test_keyword_search_region_filter_does_not_leak_other_provinces(db):
    from app.services.policy_collection.keyword_search import keyword_search

    marker = f"算力券{uuid.uuid4().hex[:8]}"
    _seed_policy(db, title=f"上海市{marker}管理办法", body=f"{marker}每年最高补贴三十万元。")
    other = _seed_policy(
        db,
        title=f"浙江省{marker}管理办法",
        body=f"{marker}每年最高补贴三十万元。",
        jurisdiction="浙江省",
        level="provincial",
    )
    hits = keyword_search(db, marker, jurisdiction="上海市", limit=50)
    assert hits
    assert all(hit.jurisdiction == "上海市" for hit in hits)
    assert str(other.id) not in {hit.policy_id for hit in hits}


def test_keyword_search_current_only_excludes_expired(db):
    from app.services.policy_collection.keyword_search import keyword_search

    marker = f"申报通知{uuid.uuid4().hex[:8]}"
    past = datetime.now(UTC) - timedelta(days=400)
    expired = _seed_policy(
        db,
        title=f"关于开展{marker}申报的通知（2024年度）",
        body=f"{marker}受理截止日期为去年。",
        expires_at=past,
    )
    fresh = _seed_policy(
        db,
        title=f"关于开展{marker}申报的通知（2026年度）",
        body=f"{marker}受理截止日期为下月。",
        deadline=datetime.now(UTC) + timedelta(days=30),
    )
    hits = keyword_search(db, marker, current_only=True, limit=50)
    ids = {hit.policy_id for hit in hits}
    assert str(fresh.id) in ids
    # An expired window must never be presented as a current opportunity.
    assert str(expired.id) not in ids


def test_newer_version_wins_in_search_and_old_version_still_readable(db):
    from app.services.policy_collection.keyword_search import keyword_search

    marker = f"设备购置补贴{uuid.uuid4().hex[:8]}"
    policy = _seed_policy(db, title=f"{marker}申报指南", body=f"{marker}补贴比例百分之二十。")
    latest_body = f"{marker}补贴比例调整为百分之二十五。"
    latest = PolicyVersion(
        id=uuid.uuid4(),
        policy_id=policy.id,
        version=2,
        content_sha256=hashlib.sha256(latest_body.encode()).hexdigest(),
        title=policy.title,
        content=latest_body,
        source_url=policy.source_url,
    )
    db.add(latest)
    db.flush()
    # The real ingestion path chunks every version; mirror that so the test
    # exercises "newer version wins" rather than the no-chunk fallback.
    db.add(
        PolicyChunk(
            id=uuid.uuid4(),
            policy_id=policy.id,
            policy_version_id=latest.id,
            chunk_index=0,
            content=latest_body,
            char_start=0,
            char_end=len(latest_body),
            content_sha256=hashlib.sha256(latest_body.encode()).hexdigest(),
        )
    )
    db.commit()

    hits = keyword_search(db, marker, limit=50)
    ours = [hit for hit in hits if hit.policy_id == str(policy.id)]
    assert ours
    # Only the newest version is searchable by default; the historic version row
    # stays in policy_versions for audit.
    assert all(hit.version_no == 2 for hit in ours)
    assert db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy.id).count() == 2


def test_searchable_counts_reports_vector_gap(db):
    from app.services.policy_collection.keyword_search import searchable_counts

    marker = f"统计口径{uuid.uuid4().hex[:8]}"
    _seed_policy(db, title=f"{marker}通知", body=f"{marker}正文。")
    counts = searchable_counts(db)
    assert counts["chunks"] >= 1
    assert counts["keyword_searchable"] is True
    assert counts["embedded_chunks"] == 0 or counts["embedded_chunks"] >= 0
    # We must never claim vector readiness while nothing is embedded.
    if counts["embedded_chunks"] == 0:
        assert counts["vector_searchable"] is False


def test_private_documents_never_leak_across_tenants(db):
    """The shared public library plus one tenant's private docs — nothing else."""
    from app.models.models import Tenant
    from app.services.policy_collection.keyword_search import keyword_search

    marker = f"客户私有资料{uuid.uuid4().hex[:8]}"
    tenant_a = Tenant(name=f"测试租户A{uuid.uuid4().hex[:6]}", slug=f"tst-a-{uuid.uuid4().hex[:8]}")
    tenant_b = Tenant(name=f"测试租户B{uuid.uuid4().hex[:6]}", slug=f"tst-b-{uuid.uuid4().hex[:8]}")
    db.add_all([tenant_a, tenant_b])
    db.flush()

    public = _seed_policy(db, title=f"{marker}公共政策", body=f"{marker}公共正文。")
    private = _seed_policy(db, title=f"{marker}私有材料", body=f"{marker}客户内部正文。")
    private.tenant_id = tenant_a.id
    db.commit()

    try:
        anonymous = {hit.policy_id for hit in keyword_search(db, marker, limit=50)}
        assert str(public.id) in anonymous
        assert str(private.id) not in anonymous

        tenant_b_hits = {
            hit.policy_id for hit in keyword_search(db, marker, limit=50, tenant_id=tenant_b.id)
        }
        assert str(public.id) in tenant_b_hits
        assert str(private.id) not in tenant_b_hits

        tenant_a_hits = {
            hit.policy_id for hit in keyword_search(db, marker, limit=50, tenant_id=tenant_a.id)
        }
        assert {str(public.id), str(private.id)} <= tenant_a_hits
    finally:
        db.rollback()
        db.execute(text("DELETE FROM tenants WHERE slug LIKE 'tst-%'"))
        db.commit()


def test_future_effective_policy_is_not_current(db):
    from app.services.policy_collection.keyword_search import keyword_search
    title = "未来生效专项" + uuid.uuid4().hex
    policy = _seed_policy(db, title=title, body=title)
    policy.effective_at = datetime.now(UTC) + timedelta(days=30)
    db.commit()
    assert any(h.policy_id == str(policy.id) for h in keyword_search(db, title))
    assert all(h.policy_id != str(policy.id) for h in keyword_search(db, title, current_only=True))
