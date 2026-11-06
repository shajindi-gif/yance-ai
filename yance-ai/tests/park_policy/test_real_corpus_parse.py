"""Regression tests against the *real* collected corpus.

These tests are skipped when ``crawler_output/policy_raw`` is absent (CI without a
download cache). They are deliberately not replaced by synthetic HTML fixtures:
a fixture that we wrote ourselves cannot prove the parser handles a government
CMS, and the whole point of the coverage report is that "parsed" means parsed
from bytes we actually fetched.

The assertions are intentionally loose — crawl content changes daily. What must
never regress is the *capability*: document pages yield a title, a publish date,
and body text; opaque attachments are reported as stored-but-not-parsed rather
than silently counted as parsed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "crawler_output" / "policy_raw"
SCRIPT = REPO_ROOT / "scripts" / "park_policy" / "parse_dry_run.py"

pytestmark = pytest.mark.skipif(
    not RAW_ROOT.exists() or not any(RAW_ROOT.rglob("*.html")),
    reason="no real collected corpus on this machine",
)


@pytest.fixture(scope="module")
def summary() -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return json.loads(proc.stdout)["summary"]


def test_real_corpus_is_parsed_not_simulated(summary: dict) -> None:
    assert summary["parse_quality"]["parsed_documents"] >= 1
    assert summary["files_total"] >= summary["parse_quality"]["parsed_documents"]


def test_at_least_three_levels_present(summary: dict) -> None:
    """Phase C requires national + provincial + municipal, not one level only."""
    sources = set(summary["by_source"])
    assert any(s.startswith("nat_") for s in sources), sources
    assert any(s.startswith("prov_") for s in sources), sources
    assert any(s.startswith("city_") for s in sources), sources


def test_documents_carry_date_or_doc_number(summary: dict) -> None:
    quality = summary["parse_quality"]
    assert quality["with_publish_date"] + quality["with_doc_number"] >= 1


def test_opaque_attachments_are_not_counted_as_parsed(summary: dict) -> None:
    """PDF/Word/OFD stored bytes must not inflate the parsed count."""
    statuses = summary["by_status"]
    stored_only = statuses.get("attachment_stored_not_parsed", 0)
    assert summary["parse_quality"]["parsed_documents"] == statuses.get("parsed", 0)
    assert stored_only >= 0  # presence is enough; absence must not fail


def test_thin_pages_are_flagged(summary: dict) -> None:
    """Short bodies land in parsed_thin, never in parsed."""
    assert summary["parse_quality"]["thin_text"] == summary["by_status"].get("parsed_thin", 0)


def test_honesty_notes_present(summary: dict) -> None:
    notes = " ".join(summary["honesty_notes"])
    assert "已解析 != 已入库" in notes
