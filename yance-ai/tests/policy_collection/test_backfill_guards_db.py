"""Backfill-queue behaviour that must hold before any long run is trusted.

The backfill queue is the one component allowed to touch a large slice of the
archive, so its guards matter more than its throughput:

* a global pause or a source pause must stop work **without** moving the cursor,
* a finished or non-pageable archive must be marked once instead of being re-read,
* a storage alarm must abort the batch instead of downloading into a full disk,
* and none of that may require network access to prove.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal
from app.models.policy_collection import PolicySourceState
from app.services.policy_collection import backfill, runner
from app.services.policy_collection.backfill import BackfillConfig
from app.services.policy_collection.catalog import load_catalog

SOURCE_IDS = ("nat_cnipa_notice", "nat_mof_notice")


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session
        session.rollback()


@pytest.fixture()
def catalog():
    from app.core.config import settings

    return load_catalog(settings.policy_collection_catalog_dir)


def _clear_states(db) -> None:
    db.execute(text("DELETE FROM policy_sources WHERE source_id = ANY(:ids)"), {"ids": list(SOURCE_IDS)})
    db.commit()


def _config(*, max_sources: int = 2, **overrides) -> BackfillConfig:
    return BackfillConfig.from_settings(max_sources=max_sources, source_ids=SOURCE_IDS, **overrides)


def test_global_pause_stops_batch_without_touching_cursors(db, catalog, monkeypatch):
    _clear_states(db)
    monkeypatch.setattr(
        backfill, "pause_state", lambda *_a, **_k: type("P", (), {"paused": True, "scope": "global"})()
    )
    monkeypatch.setattr(backfill, "execute_source_run", _fail_if_called)

    report = backfill.run_batch(db, catalog, config=_config())

    assert report.stop_reason == "paused"
    assert report.sources == []
    assert db.get(PolicySourceState, SOURCE_IDS[0]) is None


def test_storage_alarm_aborts_before_downloading(db, catalog, monkeypatch):
    _clear_states(db)
    monkeypatch.setattr(
        backfill,
        "storage_guard",
        lambda *_a, **_k: type(
            "G",
            (),
            {
                "ok": False,
                "reason": "free disk below threshold",
                "as_dict": lambda self: {"ok": False, "free_mb": 12, "reason": "low"},
            },
        )(),
    )
    monkeypatch.setattr(backfill, "execute_source_run", _fail_if_called)

    report = backfill.run_batch(db, catalog, config=_config())

    assert report.stop_reason == "storage_full"
    assert report.sources == []
    assert report.storage and report.storage["free_mb"] == 12


def test_exhausted_and_unsupported_archives_are_skipped_not_reread(db, catalog, monkeypatch):
    _clear_states(db)
    exhausted = PolicySourceState(
        source_id=SOURCE_IDS[0], consecutive_failures=0, cursor={"backfill": {"page": 4, "exhausted": True}}
    )
    unsupported = PolicySourceState(
        source_id=SOURCE_IDS[1],
        consecutive_failures=0,
        cursor={"backfill": {"page": 1, "unsupported_reason": "single-page list adapter"}},
    )
    db.add_all([exhausted, unsupported])
    db.commit()
    monkeypatch.setattr(backfill, "execute_source_run", _fail_if_called)
    monkeypatch.setattr(
        backfill, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False, "scope": "none"})()
    )

    report = backfill.run_batch(db, catalog, config=_config())

    reasons = {row["source_id"]: row["reason"] for row in report.skipped}
    assert reasons == {
        SOURCE_IDS[0]: "archive_exhausted",
        SOURCE_IDS[1]: "pagination_unsupported",
    }
    assert report.sources == []
    _clear_states(db)


def test_plan_is_bounded_and_read_only(db, catalog):
    _clear_states(db)
    rows = backfill.plan(db, catalog, config=_config(max_sources=2))
    assert len(rows) >= 1
    assert all(row["next_page"] >= 1 for row in rows)
    assert db.get(PolicySourceState, SOURCE_IDS[0]) is None


def test_cursor_roundtrip_keeps_page_and_flags(db):
    source_id = f"tst_cursor_{uuid.uuid4().hex[:8]}"
    state = PolicySourceState(source_id=source_id, consecutive_failures=0, cursor={})
    db.add(state)
    db.flush()
    try:
        backfill.write_cursor(state, {"page": 7, "documents_stored": 42, "exhausted": False})
        db.commit()
        db.refresh(state)
        cursor = backfill.read_cursor(state)
        assert cursor["page"] == 7
        assert cursor["documents_stored"] == 42
    finally:
        db.execute(text("DELETE FROM policy_sources WHERE source_id = :s"), {"s": source_id})
        db.commit()


def _fail_if_called(*_args, **_kwargs):  # pragma: no cover - guard
    raise AssertionError("no source should have been executed in this scenario")


def _stub_run(monkeypatch, *, entries: int, pages_read: int, pages_available: int, error_kind=None):
    """Return a fake ``execute_source_run`` yielding one source outcome."""

    def fake(db, source, **_kwargs):
        outcome = runner.SourceRunOutcome(
            source_id=source.source_id,
            status="no_update" if entries == 0 else "success",
            pages_fetched=pages_read,
            list_entries=entries,
            pages_available=pages_available,
            error_kind=error_kind,
            error="list page returned no candidate documents" if entries == 0 else None,
        )
        return backfill.RunReport(
            source_id=source.source_id, run_id="test-run", status=outcome.status, outcome=outcome
        )

    monkeypatch.setattr(backfill, "execute_source_run", fake)
    monkeypatch.setattr(
        backfill, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False, "scope": "none"})()
    )


def test_empty_page_beyond_declared_count_is_a_real_archive_end(db, catalog, monkeypatch):
    """The site declared 3 screens; asking for page 4 is genuinely past the end."""
    _clear_states(db)
    db.add(
        PolicySourceState(
            source_id=SOURCE_IDS[0], consecutive_failures=0, cursor={"backfill": {"page": 4, "exhausted": False}}
        )
    )
    db.commit()
    _stub_run(monkeypatch, entries=0, pages_read=1, pages_available=3, error_kind="empty_list")

    report = backfill.run_batch(db, catalog, config=BackfillConfig.from_settings(
        max_sources=1, source_ids=(SOURCE_IDS[0],), pages_per_batch=1))

    assert report.sources[0].stop_reason == "archive_end"
    cursor = backfill.read_cursor(db.get(PolicySourceState, SOURCE_IDS[0]))
    assert cursor["exhausted"] is True
    _clear_states(db)


def test_empty_page_inside_declared_range_blocks_cursor_instead_of_ending_archive(db, catalog, monkeypatch):
    """A 200-with-zero-links page inside a 22-screen column is a broken rule, not the end.

    This is the exact failure that would otherwise hide years of history: the old
    code marked the cursor exhausted and the source was never read again.
    """
    _clear_states(db)
    db.add(
        PolicySourceState(
            source_id=SOURCE_IDS[0], consecutive_failures=0, cursor={"backfill": {"page": 2, "exhausted": False}}
        )
    )
    db.commit()
    _stub_run(monkeypatch, entries=0, pages_read=1, pages_available=22, error_kind="empty_list")

    report = backfill.run_batch(db, catalog, config=BackfillConfig.from_settings(
        max_sources=1, source_ids=(SOURCE_IDS[0],), pages_per_batch=1))

    assert report.sources[0].stop_reason == "page_empty_unverified"
    assert report.sources[0].exhausted is False
    cursor = backfill.read_cursor(db.get(PolicySourceState, SOURCE_IDS[0]))
    assert cursor["page"] == 2, "cursor must stay on the unread page so the hole is retried"
    assert cursor.get("exhausted") is False
    assert "gap_reason" in cursor
    _clear_states(db)


def test_unknown_page_count_never_claims_archive_end(db, catalog, monkeypatch):
    """With no declared page count there is no evidence the archive ended."""
    _clear_states(db)
    db.add(
        PolicySourceState(
            source_id=SOURCE_IDS[0], consecutive_failures=0, cursor={"backfill": {"page": 5, "exhausted": False}}
        )
    )
    db.commit()
    _stub_run(monkeypatch, entries=0, pages_read=1, pages_available=0, error_kind="empty_list")

    report = backfill.run_batch(db, catalog, config=BackfillConfig.from_settings(
        max_sources=1, source_ids=(SOURCE_IDS[0],), pages_per_batch=1))

    assert report.sources[0].exhausted is False
    assert report.sources[0].stop_reason == "page_empty_unverified"
    _clear_states(db)


def test_repeated_empty_pages_park_the_cursor_instead_of_looping_forever(db, catalog, monkeypatch):
    """Three empty rounds stop the loop; history is still re-readable after a reset.

    Parking is chosen over skipping on purpose: the page is never marked exhausted,
    so nothing is silently lost, but the queue stops re-reading a page whose list
    rule is plainly broken.
    """
    _clear_states(db)
    db.add(
        PolicySourceState(
            source_id=SOURCE_IDS[0], consecutive_failures=0, cursor={"backfill": {"page": 4, "exhausted": False}}
        )
    )
    db.commit()
    _stub_run(monkeypatch, entries=0, pages_read=1, pages_available=0, error_kind="empty_list")
    config = BackfillConfig.from_settings(max_sources=1, source_ids=(SOURCE_IDS[0],), pages_per_batch=1)

    for _ in range(2):
        report = backfill.run_batch(db, catalog, config=config)
        assert report.sources[0].stop_reason == "page_empty_unverified"

    report = backfill.run_batch(db, catalog, config=config)
    assert report.sources[0].stop_reason == "parked_after_empty_pages"
    state = db.get(PolicySourceState, SOURCE_IDS[0])
    cursor = backfill.read_cursor(state)
    assert "backfill_blocked" in cursor
    assert cursor["page"] == 4
    assert cursor.get("exhausted") is False, "parking must not claim the archive ended"

    # A parked source is skipped, not re-read on every subsequent batch.
    monkeypatch.setattr(backfill, "execute_source_run", _fail_if_called)
    report = backfill.run_batch(db, catalog, config=config)
    assert report.sources == []
    assert report.skipped[0]["reason"] == "backfill_parked"

    # ... and a successful page clears the streak so the source behaves normally.
    cursor.pop("backfill_blocked")
    backfill.write_cursor(state, cursor)
    db.commit()
    monkeypatch.undo()
    _stub_run(monkeypatch, entries=5, pages_read=1, pages_available=0, error_kind=None)
    report = backfill.run_batch(db, catalog, config=config)
    assert report.sources[0].stop_reason == "batch_complete"
    cursor = backfill.read_cursor(db.get(PolicySourceState, SOURCE_IDS[0]))
    assert "gap_streak" not in cursor
    assert "backfill_blocked" not in cursor
    _clear_states(db)
