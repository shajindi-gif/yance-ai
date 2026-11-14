"""Tests for the harvest -> catalog write-back script.

The script edits hand-maintained YAML in place (comments, ordering and block
scalars must survive), so the risky properties are: only the three allowed
fields change, and replaying the same harvest is a no-op.  Both are asserted
here against a synthetic catalog, no network and no database involved.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

APP_ROOT = Path(__file__).resolve().parents[2]

CATALOG = """\
# hand-written comment that must survive the write-back
sources:
  - source_id: good_source
    name: 正常来源
    level: national
    channel: policy_document
    entry_url: https://example.gov.cn/a/
    allowed_domains: [example.gov.cn]
    adapter: generic_list
    check_interval_hours: 24
    enabled: true
    verification_state: registered
    notes: 手工备注

  - source_id: prose_source
    name: 折行备注来源
    level: provincial
    channel: policy_document
    entry_url: https://example.gov.cn/b/
    allowed_domains: [example.gov.cn]
    adapter: generic_list
    check_interval_hours: 24
    enabled: true
    verification_state: registered
    notes: >-
      这是手工写的折行说明，
      脚本不得往块标量里追加内容。
"""

HARVEST = {
    "sources": [
        {
            "source_id": "good_source",
            "list_ok": True,
            "list_error": None,
            "entries": 12,
            "docs": [{"parsed": True}],
        },
        {
            "source_id": "prose_source",
            "list_ok": True,
            "list_error": None,
            "entries": 7,
            "docs": [{"parsed": True}],
        },
    ]
}


@pytest.fixture()
def script():
    path = APP_ROOT / "scripts" / "policy_collection" / "record_verification.py"
    spec = importlib.util.spec_from_file_location("record_verification_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    (catalog_dir / "national.yaml").write_text(CATALOG, encoding="utf-8")
    harvest = tmp_path / "harvest.json"
    harvest.write_text(json.dumps(HARVEST), encoding="utf-8")
    return catalog_dir, harvest


def _run(script, catalog_dir: Path, harvest: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "record_verification.py",
            "--from",
            str(harvest),
            "--catalog",
            str(catalog_dir),
        ],
    )
    assert script.main() == 0


def test_writeback_updates_state_and_keeps_comment(tmp_path, script, monkeypatch):
    catalog_dir, harvest = _write_fixture(tmp_path)
    before = (catalog_dir / "national.yaml").read_text(encoding="utf-8")

    _run(script, catalog_dir, harvest, monkeypatch)

    after = (catalog_dir / "national.yaml").read_text(encoding="utf-8")
    assert after != before
    assert "# hand-written comment that must survive the write-back" in after

    doc = yaml.safe_load(after)
    by_id = {s["source_id"]: s for s in doc["sources"]}
    assert by_id["good_source"]["verification_state"] == "document_verified"
    assert by_id["good_source"]["last_verified_at"]
    assert "列表 12 条" in by_id["good_source"]["notes"]
    assert "手工备注" in by_id["good_source"]["notes"]

    # folded block scalar is prose: state may change, the prose itself may not be appended to
    assert by_id["prose_source"]["verification_state"] == "document_verified"
    assert "脚本不得往块标量里追加内容" in after
    assert "列表 7 条" not in after


def test_replay_is_idempotent(tmp_path, script, monkeypatch):
    catalog_dir, harvest = _write_fixture(tmp_path)
    _run(script, catalog_dir, harvest, monkeypatch)
    first = (catalog_dir / "national.yaml").read_text(encoding="utf-8")

    _run(script, catalog_dir, harvest, monkeypatch)
    second = (catalog_dir / "national.yaml").read_text(encoding="utf-8")

    assert first == second, "replaying the same harvest must not rewrite the catalog"


def test_failure_kinds_are_not_mislabelled(tmp_path, script, monkeypatch):
    catalog_dir, _ = _write_fixture(tmp_path)
    harvest = tmp_path / "harvest_fail.json"
    harvest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "good_source",
                        "list_ok": False,
                        "list_error": "http 404",
                        "entries": 0,
                        "docs": [],
                    },
                    {
                        "source_id": "prose_source",
                        "list_ok": True,
                        "list_error": None,
                        "entries": 0,
                        "docs": [],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    _run(script, catalog_dir, harvest, monkeypatch)

    by_id = {
        s["source_id"]: s
        for s in yaml.safe_load((catalog_dir / "national.yaml").read_text(encoding="utf-8"))[
            "sources"
        ]
    }
    assert by_id["good_source"]["verification_state"] == "unreachable"
    # a zero-entry list is an adapter problem, not a 404 and not "verified"
    assert by_id["prose_source"]["verification_state"] == "registered"
    # folded prose is never appended to: the diagnosis stays in the harvest JSON
    assert "列表 0 条" not in by_id["prose_source"]["notes"]


def test_transient_timeout_leaves_catalog_untouched(tmp_path, script, monkeypatch):
    """A timeout says nothing about the source, so it must not become a note.

    Writing "待复测" into the hand-maintained catalog would leave a permanent
    contradiction behind the next successful run; the harvest JSON is the
    place for a one-off network blip.
    """
    catalog_dir, _ = _write_fixture(tmp_path)
    before = (catalog_dir / "national.yaml").read_text(encoding="utf-8")
    harvest = tmp_path / "harvest_timeout.json"
    harvest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "good_source",
                        "list_ok": False,
                        "list_error": "timeout: The read operation timed out",
                        "entries": 0,
                        "docs": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    _run(script, catalog_dir, harvest, monkeypatch)

    assert (catalog_dir / "national.yaml").read_text(encoding="utf-8") == before
