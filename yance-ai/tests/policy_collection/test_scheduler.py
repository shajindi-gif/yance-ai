"""Incremental scheduler guards.

The scheduler is the only component that stays running, so its guards are what the
"24/7" claim actually rests on. Every test here asserts a way the loop must *stop*
or *continue* — never a way it should download more.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal
from app.models.policy_collection import PolicySourceState
from app.services.policy_collection import scheduler
from app.services.policy_collection.catalog import load_catalog
from app.services.policy_collection.service import RunReport

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


@pytest.fixture()
def state_path(tmp_path):
    return tmp_path / "scheduler_state.json"


@pytest.fixture(autouse=True)
def _collection_enabled(monkeypatch):
    """The master switch is off by default; guards are what is under test here."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "policy_collection_enabled", True)


def _clear(db) -> None:
    db.execute(text("DELETE FROM policy_sources WHERE source_id = ANY(:ids)"), {"ids": list(SOURCE_IDS)})
    db.commit()


def _config(state_path, **overrides):
    return scheduler.SchedulerConfig.from_settings(state_path=state_path, **overrides)


def _report(source_id: str, *, status="success", new=1):
    return RunReport(source_id=source_id, run_id="t", status=status, outcome=_Outcome(new=new))


class _Outcome:
    def __init__(self, *, new=0, updated=0, failed=0, pages=1):
        self.new_documents = new
        self.updated_documents = updated
        self.failed_documents = failed
        self.pages_fetched = pages


def _no_sources(_catalog, _db, *, now=None):
    return []


def test_global_pause_returns_without_any_request(db, catalog, state_path, monkeypatch):
    _clear(db)
    monkeypatch.setattr(
        scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": True, "scope": "global"})()
    )
    monkeypatch.setattr(scheduler, "due_sources", _no_sources)
    monkeypatch.setattr(scheduler, "execute_source_run", lambda *_a, **_k: pytest.fail("must not fetch"))

    result = scheduler.run_cycle(db, catalog, config=_config(state_path))

    assert result.stop_reason == "paused"
    assert result.ran == []


def test_low_disk_stops_the_cycle_before_downloading(db, catalog, state_path, monkeypatch):
    _clear(db)
    monkeypatch.setattr(
        scheduler,
        "storage_guard",
        lambda *_a, **_k: type(
            "G", (), {"ok": False, "as_dict": lambda self: {"ok": False, "free_mb": 100, "reason": "low"}}
        )(),
    )
    monkeypatch.setattr(
        scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False, "scope": "none"})()
    )
    monkeypatch.setattr(scheduler, "execute_source_run", lambda *_a, **_k: pytest.fail("must not fetch"))

    result = scheduler.run_cycle(db, catalog, config=_config(state_path))

    assert result.stop_reason == "storage_full"
    assert result.storage["free_mb"] == 100


def test_source_limit_leaves_the_rest_due_for_the_next_cycle(db, catalog, state_path, monkeypatch):
    _clear(db)
    due = [s for s in catalog.sources if s.enabled][:4]

    def fake_due(_catalog, _db, *, now=None):
        return list(due)

    ran: list[str] = []

    def fake_execute(_db, source, *, trigger="scheduler", **_kwargs):
        ran.append(source.source_id)
        return _report(source.source_id)

    monkeypatch.setattr(scheduler, "due_sources", fake_due)
    monkeypatch.setattr(scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False})())
    monkeypatch.setattr(
        scheduler, "storage_guard", lambda *_a, **_k: type("G", (), {"ok": True, "as_dict": lambda self: {"ok": True}})()
    )
    monkeypatch.setattr(scheduler, "execute_source_run", fake_execute)

    result = scheduler.run_cycle(db, catalog, config=_config(state_path, max_sources_per_cycle=2), include_recheck=False)

    assert len(ran) == 2
    assert result.stop_reason == "max_sources"
    assert result.due_before == 4


def test_one_exploding_source_does_not_stop_the_cycle(db, catalog, state_path, monkeypatch):
    _clear(db)
    due = [s for s in catalog.sources if s.enabled][:3]

    def fake_execute(_db, source, *, trigger="scheduler", **_kwargs):
        if source is due[0]:
            raise RuntimeError("adapter exploded")
        return _report(source.source_id)

    monkeypatch.setattr(scheduler, "due_sources", lambda *_a, **_k: list(due))
    monkeypatch.setattr(scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False})())
    monkeypatch.setattr(
        scheduler, "storage_guard", lambda *_a, **_k: type("G", (), {"ok": True, "as_dict": lambda self: {"ok": True}})()
    )
    monkeypatch.setattr(scheduler, "execute_source_run", fake_execute)

    result = scheduler.run_cycle(db, catalog, config=_config(state_path, max_sources_per_cycle=5), include_recheck=False)

    statuses = [row["status"] for row in result.ran]
    assert "exception" in statuses
    assert statuses.count("success") == 2
    assert result.stop_reason == "completed"


def test_state_file_records_the_cycle_for_monitoring(db, catalog, state_path, monkeypatch):
    _clear(db)
    monkeypatch.setattr(scheduler, "due_sources", _no_sources)
    monkeypatch.setattr(scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False})())
    monkeypatch.setattr(
        scheduler, "storage_guard", lambda *_a, **_k: type("G", (), {"ok": True, "as_dict": lambda self: {"ok": True}})()
    )

    scheduler.run_cycle(db, catalog, config=_config(state_path), include_recheck=False)

    state = scheduler.scheduler_state(_config(state_path))
    assert state["last_stop_reason"] == "completed"
    assert state["last_cycle_finished_at"]


def test_exhausted_archive_becomes_recheck_candidate_only_after_interval(db, catalog, state_path):
    _clear(db)
    now = datetime.now(UTC)
    db.add(
        PolicySourceState(
            source_id=SOURCE_IDS[0],
            consecutive_failures=0,
            last_check_at=now - timedelta(hours=200),
            cursor={"backfill": {"page": 9, "exhausted": True}},
        )
    )
    db.commit()

    due = scheduler.recheck_due(catalog, db, state_path=state_path, now=now, interval_hours=168)
    assert [s.source_id for s in due] == [SOURCE_IDS[0]]

    fresh = scheduler.recheck_due(catalog, db, state_path=state_path, now=now, interval_hours=500)
    assert fresh == []
    _clear(db)


def test_recheck_is_not_due_for_cursorless_sources(db, catalog, state_path):
    _clear(db)
    db.add(PolicySourceState(source_id=SOURCE_IDS[1], consecutive_failures=0, cursor={}))
    db.commit()

    due = scheduler.recheck_due(catalog, db, state_path=state_path, interval_hours=1)
    assert SOURCE_IDS[1] not in [s.source_id for s in due]
    _clear(db)


def test_alerts_surface_persistent_failure_stale_and_gap(db, catalog, monkeypatch):
    _clear(db)
    now = datetime.now(UTC)
    db.add_all(
        [
            PolicySourceState(
                source_id=SOURCE_IDS[0],
                consecutive_failures=6,
                last_error_kind="http_error",
                last_error="503 service unavailable",
                last_success_at=now - timedelta(hours=100),
                cursor={"backfill": {"page": 3, "gap_reason": "page_empty_unverified"}},
            ),
            PolicySourceState(source_id=SOURCE_IDS[1], consecutive_failures=0),
        ]
    )
    db.commit()
    monkeypatch.setattr(
        scheduler, "storage_guard", lambda *_a, **_k: type("G", (), {"ok": True, "as_dict": lambda self: {"ok": True}})()
    )
    monkeypatch.setattr(
        scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False, "scope": "none"})()
    )

    kinds = {(row["kind"], row.get("source_id")) for row in scheduler.alerts(db, catalog, now=now)}

    assert ("persistent_failure", SOURCE_IDS[0]) in kinds
    assert ("stale_source", SOURCE_IDS[0]) in kinds
    assert ("unverified_page_gap", SOURCE_IDS[0]) in kinds
    assert not any(source_id == SOURCE_IDS[1] for _kind, source_id in kinds if source_id)
    _clear(db)


def test_serve_runs_bounded_cycles_and_honours_the_stop_event(db, catalog, state_path, monkeypatch):
    _clear(db)
    monkeypatch.setattr(scheduler, "due_sources", _no_sources)
    monkeypatch.setattr(scheduler, "pause_state", lambda *_a, **_k: type("P", (), {"paused": False})())
    monkeypatch.setattr(
        scheduler, "storage_guard", lambda *_a, **_k: type("G", (), {"ok": True, "as_dict": lambda self: {"ok": True}})()
    )

    history = scheduler.serve(
        lambda: SessionLocal(),
        lambda: catalog,
        config=_config(state_path, interval_seconds=0.01),
        max_cycles=2,
    )

    assert len(history) == 2
    assert all(row["stop_reason"] == "completed" for row in history)


def test_master_switch_off_short_circuits_without_recording_90_skips(db, catalog, state_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "policy_collection_enabled", False)
    monkeypatch.setattr(scheduler, "execute_source_run", lambda *_a, **_k: pytest.fail("must not fetch"))

    result = scheduler.run_cycle(db, catalog, config=_config(state_path))

    assert result.stop_reason == "collection_disabled"
    assert result.ran == [] and result.skipped == []
