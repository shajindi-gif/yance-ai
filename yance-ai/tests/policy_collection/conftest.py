"""Shared hygiene for the database-backed policy_collection tests.

Several tests build documents from synthetic URLs (``example.gov.cn``,
``test.invalid``, ...) and synthetic source ids (``tst_*``). That is harmless for the
tests themselves but fatal for anything that reads the same database afterwards: a
capacity measurement, a keyword-search smoke run or a backfill statistics query would
count synthetic documents as collected policy.

Two lessons are baked into this fixture:

* **Deletion order matters.** ``opportunities`` references ``policy_versions`` with a
  plain foreign key, so deleting a synthetic policy first raised IntegrityError and
  rolled the *whole* cleanup back — which is how residue survived earlier cleanup
  attempts while looking clean.
* **Each step commits on its own.** One blocked table must not prevent the rest of the
  purge, and a real failure is printed once rather than swallowed.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

# Sources that exist only inside tests. Their evidence rows have no stored raw file,
# so leaving them behind inflates both document counts and "missing evidence" stats.
SYNTHETIC_SOURCE_PATTERNS = (r"tst\_%", r"test\_%", r"stub\_%")

SYNTHETIC_URL_PATTERNS = (
    "https://example.gov.cn/%",
    "https://www.example.gov.cn/%",
    "http://example.gov.cn/%",
    "https://test.invalid/%",
    "http://test.invalid/%",
    "https://test.local/%",
    "https://example.invalid/%",
)


def _like_clause(column: str, patterns: tuple[str, ...], prefix: str) -> tuple[str, dict]:
    clause = " OR ".join(f"{column} LIKE :{prefix}{i}" for i in range(len(patterns)))
    params = {f"{prefix}{i}": pattern for i, pattern in enumerate(patterns)}
    return clause, params


def _purge_synthetic_documents() -> None:
    from app.core.db import SessionLocal

    url_clause, url_params = _like_clause("source_url", SYNTHETIC_URL_PATTERNS, "p")
    source_clause, source_params = _like_clause("source_id", SYNTHETIC_SOURCE_PATTERNS, "s")
    synthetic_policy_ids = f"SELECT id FROM policies WHERE {url_clause}"

    steps = (
        # opportunities holds a plain FK to policy_versions; without this the policy
        # delete aborts and nothing below it runs.
        (
            f"DELETE FROM opportunities WHERE policy_id IN ({synthetic_policy_ids})",
            url_params,
        ),
        ("DELETE FROM policy_raw_evidence WHERE policy_id IN (" + synthetic_policy_ids + ")", url_params),
        (f"DELETE FROM policies WHERE {url_clause}", url_params),
        (f"DELETE FROM policy_raw_evidence WHERE {source_clause}", source_params),
        (f"DELETE FROM policy_collection_runs WHERE {source_clause}", source_params),
        (f"DELETE FROM policy_sources WHERE {source_clause}", source_params),
    )

    session = SessionLocal()
    failures: list[str] = []
    try:
        for statement, params in steps:
            try:
                session.execute(text(statement), params)
                session.commit()
            except Exception as exc:  # noqa: BLE001 - cleanup must never mask a test result
                session.rollback()
                failures.append(f"{statement.split(' FROM ')[1][:40]}: {type(exc).__name__}")
    finally:
        session.close()
    if failures:
        print("policy_collection cleanup incomplete: " + "; ".join(failures))


@pytest.fixture(autouse=True)
def _no_synthetic_residue():
    _purge_synthetic_documents()
    yield
    _purge_synthetic_documents()
