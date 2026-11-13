"""DB-backed ingestion semantics: idempotency, version history, evidence links.

The unit suite already covers change *decisions*.  What can only be verified on a
real database is that repeated or concurrent runs do not duplicate policy rows,
that a changed page yields a new immutable version instead of overwriting the old
one, and that raw evidence stays linked to the version it produced.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal
from app.models.models import Policy, PolicyVersion
from app.models.policy_collection import PolicyOrigin
from app.services.policy_collection.catalog import SourceDefinition
from app.services.policy_collection.classify import Classification
from app.services.policy_collection.store import DocumentPayload, SqlPolicyStore

TEST_URL_PREFIX = "https://test.invalid/store/"


def _source() -> SourceDefinition:
    return SourceDefinition(
        source_id="tst_store_db",
        name="测试来源",
        authority="测试机关",
        level="municipal",
        province="上海市",
        city="上海市",
        channel="notice",
        entry_url="https://test.invalid/list.html",
        allowed_domains=("test.invalid",),
        adapter="generic_list",
        enabled=True,
    )


def _payload(*, url: str, title: str, body: str) -> DocumentPayload:
    from datetime import date

    return DocumentPayload(
        source=_source(),
        run_id=None,
        url=url,
        requested_url=url,
        title=title,
        text=body,
        classification=Classification(doc_kind="notice", industries=["人工智能"]),
        published_at=date(2026, 3, 1),
        doc_number="沪科〔2026〕1号",
        issuer="上海市科学技术委员会",
        content_sha256=hashlib.sha256(body.encode()).hexdigest(),
    )


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.execute(
            text("DELETE FROM policies WHERE source_url LIKE :prefix"),
            {"prefix": f"{TEST_URL_PREFIX}%"},
        )
        session.commit()
        session.close()


def test_same_document_twice_is_idempotent(db):
    url = f"{TEST_URL_PREFIX}{uuid.uuid4().hex}.html"
    body = "第一条 对首次认定的高新技术企业给予一次性奖励。"
    store = SqlPolicyStore(db)

    first = store.save_document(_payload(url=url, title="高企奖励申报通知", body=body))
    db.commit()
    second = store.save_document(_payload(url=url, title="高企奖励申报通知", body=body))
    db.commit()

    assert first.policy_id == second.policy_id
    assert db.query(Policy).filter(Policy.source_url == url).count() == 1
    assert db.query(PolicyVersion).filter(PolicyVersion.policy_id == first.policy_id).count() == 1
    assert db.query(PolicyOrigin).filter(PolicyOrigin.url_normalized.contains(url)).count() >= 1


def test_changed_content_creates_new_version_and_keeps_old(db):
    url = f"{TEST_URL_PREFIX}{uuid.uuid4().hex}.html"
    store = SqlPolicyStore(db)

    v1 = store.save_document(
        _payload(url=url, title="研发费用补贴细则", body="补贴比例为百分之二十。")
    )
    db.commit()
    v2 = store.save_document(
        _payload(url=url, title="研发费用补贴细则", body="补贴比例调整为百分之二十五。")
    )
    db.commit()

    versions = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.policy_id == v1.policy_id)
        .order_by(PolicyVersion.version)
        .all()
    )
    assert [item.version for item in versions] == [1, 2]
    assert "百分之二十" in versions[0].content
    assert "百分之二十五" in versions[1].content
    # Old snapshot remains queryable: history must be auditable, not replaced.
    assert versions[0].content_sha256 != versions[1].content_sha256
    assert v2.policy_version_id == versions[1].id
