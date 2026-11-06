"""The global pause must be a one-command, no-restart, reversible action.

The env switch (``policy_collection_paused``) needs a process restart, which is not
something to ask of someone at 2am watching a crawl misbehave.  These tests pin the
file-based flag: it is read on every cycle, it fails closed when unreadable, and
clearing it resumes scheduling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.policy_collection import ops


@pytest.fixture()
def flag(tmp_path, monkeypatch):
    path = tmp_path / "PAUSED"
    monkeypatch.setattr(ops, "pause_flag_path", lambda: path)
    monkeypatch.setattr(ops.settings, "policy_collection_paused", False)
    return path


def test_no_flag_means_not_paused(flag):
    assert ops.read_pause_flag() is None
    assert ops.pause_state().paused is False


def test_writing_the_flag_pauses_with_the_recorded_reason(flag):
    ops.write_pause_flag("site maintenance")
    assert flag.exists()
    state = ops.pause_state()
    assert state.paused is True
    assert state.scope == "global"
    assert "site maintenance" in state.reason


def test_clearing_the_flag_resumes(flag):
    ops.write_pause_flag("x")
    assert ops.clear_pause_flag() is True
    assert ops.pause_state().paused is False
    # Second clear is a no-op, not an error.
    assert ops.clear_pause_flag() is False


def test_unreadable_flag_fails_closed(flag, monkeypatch):
    ops.write_pause_flag("x")

    def boom(*_a, **_k):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", boom)
    state = ops.pause_state()
    assert state.paused is True, "an unreadable pause flag must not silently resume crawling"


def test_env_switch_still_wins(flag, monkeypatch):
    monkeypatch.setattr(ops.settings, "policy_collection_paused", True)
    state = ops.pause_state()
    assert state.paused is True
    assert "policy_collection_paused" in state.reason
