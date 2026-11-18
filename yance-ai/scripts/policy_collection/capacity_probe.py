#!/usr/bin/env python
"""Measure the real cost of one thousand documents, from documents we really stored.

The point is to refuse to quote a completion date from a guess. Everything printed
here is computed from files on disk, rows in the database of the environment the
script runs against, and a timed re-parse of the stored HTML:

* bytes per document (html) and per attachment — measured from the stored files that
  the evidence table points at, not from an average of whatever happens to be on disk;
* parse wall time per document — measured by parsing stored originals again;
* embedding tokens per document — estimated from character counts with an explicit
  ratio, and priced only if a per-million-token price is supplied. The script never
  invents a price, so an unbudgeted run reports tokens and no money;
* projected 10k-corpus footprint and the free-space verdict for the target host.

Rows written by repository tests (``tst_*``/``test_*``/``stub_*`` sources) are excluded:
they carry no stored raw file, so including them would flatter both the document count
and the per-document byte figures.

Usage::

    python scripts/policy_collection/capacity_probe.py --json
    python scripts/policy_collection/capacity_probe.py --price-per-mtok 0.5 --disk-free-gb 13
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import func, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models.models import PolicyChunk, PolicyVersion  # noqa: E402
from app.models.policy_collection import PolicyAttachment, PolicyRawEvidence  # noqa: E402
from app.services.policy_collection.extract import extract_document_page  # noqa: E402

# Conservative mixed Chinese/English ratio: official Chinese documents average roughly
# 1 token per 1.6 characters with common tokenizers. One constant, so a reviewer changes
# a number instead of disputing an opaque estimate.
CHARS_PER_TOKEN = 1.6
TEST_SOURCE_PREFIXES = ("tst_", "test_", "stub_")


def _is_test_source(source_id: str | None) -> bool:
    return bool(source_id) and source_id.startswith(TEST_SOURCE_PREFIXES)


def _percentile(values: list[int], ratio: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * ratio))]


def _measure_parse(rows, *, limit: int) -> dict:
    """Re-parse stored originals to get a real per-document parse cost."""
    timings: list[float] = []
    chars: list[int] = []
    failures = 0
    considered = 0
    for row in rows[:limit]:
        if not row.storage_path:
            continue
        path = Path(row.storage_path)
        if not path.is_file():
            continue
        considered += 1
        try:
            html = path.read_text("utf-8", errors="replace")
        except OSError:
            failures += 1
            continue
        started = time.perf_counter()
        try:
            page = extract_document_page(html, row.final_url or row.url_normalized)
            # DocumentPage exposes ``text``/``text_chars``; reading a non-existent
            # ``content`` attribute would mark every parse as failed.
            chars.append(int(page.text_chars or len(page.text or "")))
        except Exception:  # noqa: BLE001 - a parse failure is a measurement, not a crash
            failures += 1
        timings.append(time.perf_counter() - started)
    return {
        "considered_files": considered,
        "timed_parses": len(timings),
        "parse_failures": failures,
        "parse_seconds_mean": round(statistics.fmean(timings), 4) if timings else None,
        "parsed_chars_mean": round(statistics.fmean(chars), 1) if chars else 0,
    }


def measure(*, parse_samples: int = 40) -> dict:
    db = SessionLocal()
    try:
        all_sources = [row[0] for row in db.execute(select(PolicyRawEvidence.source_id).distinct()).all()]
        real_sources = [source_id for source_id in all_sources if not _is_test_source(source_id)]

        real_policy_ids = [
            row[0]
            for row in db.execute(
                select(PolicyRawEvidence.policy_id)
                .distinct()
                .where(
                    PolicyRawEvidence.source_id.in_(real_sources),
                    PolicyRawEvidence.policy_id.is_not(None),
                )
            ).all()
        ] if real_sources else []

        def _count_versions():
            if not real_policy_ids:
                return 0, 0
            return (
                db.scalar(
                    select(func.count()).select_from(PolicyVersion).where(PolicyVersion.policy_id.in_(real_policy_ids))
                )
                or 0,
                db.scalar(
                    select(func.coalesce(func.sum(func.length(PolicyVersion.content)), 0)).where(
                        PolicyVersion.policy_id.in_(real_policy_ids)
                    )
                )
                or 0,
            )

        version_count, version_chars = _count_versions()
        chunk_count = (
            db.scalar(select(func.count()).select_from(PolicyChunk).where(PolicyChunk.policy_id.in_(real_policy_ids)))
            if real_policy_ids
            else 0
        ) or 0
        chunk_chars = (
            db.scalar(
                select(func.coalesce(func.sum(func.length(PolicyChunk.content)), 0)).where(
                    PolicyChunk.policy_id.in_(real_policy_ids)
                )
            )
            if real_policy_ids
            else 0
        ) or 0
        attachment_count = (
            db.scalar(
                select(func.count()).select_from(PolicyAttachment).where(
                    PolicyAttachment.policy_id.in_(real_policy_ids)
                )
            )
            if real_policy_ids
            else 0
        ) or 0
        attachment_bytes_db = (
            db.scalar(
                select(func.coalesce(func.sum(PolicyAttachment.byte_size), 0)).where(
                    PolicyAttachment.policy_id.in_(real_policy_ids)
                )
            )
            if real_policy_ids
            else 0
        ) or 0
        attachment_paths = (
            [
                row[0]
                for row in db.execute(
                    select(PolicyAttachment.storage_path).where(
                        PolicyAttachment.policy_id.in_(real_policy_ids),
                        PolicyAttachment.storage_path.is_not(None),
                    )
                ).all()
            ]
            if real_policy_ids
            else []
        )

        evidence_rows = db.execute(
            select(
                PolicyRawEvidence.purpose,
                PolicyRawEvidence.storage_path,
                PolicyRawEvidence.byte_size,
                PolicyRawEvidence.final_url,
                PolicyRawEvidence.url_normalized,
            ).where(PolicyRawEvidence.source_id.in_(real_sources))
        ).all() if real_sources else []
        evidence_count = len(evidence_rows)
        evidence_bytes = sum(int(row.byte_size or 0) for row in evidence_rows)
        evidence_without_file = sum(1 for row in evidence_rows if not row.storage_path)
        total_public_versions = db.scalar(
            select(func.count()).select_from(PolicyVersion).where(PolicyVersion.tenant_id.is_(None))
        ) or 0
        tenant_versions = db.scalar(
            select(func.count()).select_from(PolicyVersion).where(PolicyVersion.tenant_id.is_not(None))
        ) or 0
    finally:
        db.close()

    raw_sizes = [Path(path).stat().st_size for path in [row.storage_path for row in evidence_rows] if path and Path(path).is_file()]
    attachment_sizes = [Path(path).stat().st_size for path in attachment_paths if Path(path).is_file()]
    parse_stats = _measure_parse(
        [row for row in evidence_rows if row.purpose == "document"], limit=parse_samples
    )

    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "sources_measured": len(real_sources),
        "test_sources_excluded": sorted(set(all_sources) - set(real_sources)),
        "public_versions_from_real_sources": int(version_count),
        "all_public_versions_in_db": int(total_public_versions),
        "tenant_versions": int(tenant_versions),
        "chars_per_version_mean": round(version_chars / version_count, 1) if version_count else 0,
        "version_chars_total": int(version_chars),
        "chunks": int(chunk_count),
        "chunks_per_version": round(chunk_count / version_count, 2) if version_count else 0,
        "chunk_chars_mean": round(chunk_chars / chunk_count, 1) if chunk_count else 0,
        "evidence_rows": evidence_count,
        "evidence_rows_without_stored_file": evidence_without_file,
        "evidence_bytes_total": evidence_bytes,
        "evidence_bytes_mean": round(evidence_bytes / evidence_count, 1) if evidence_count else 0,
        "attachments_in_db": int(attachment_count),
        "attachment_bytes_db_total": int(attachment_bytes_db),
        "attachment_files_on_disk": len(attachment_sizes),
        "attachment_bytes_on_disk": sum(attachment_sizes),
        "attachment_bytes_mean": round(statistics.fmean(attachment_sizes), 1) if attachment_sizes else 0,
        "raw_files_on_disk": len(raw_sizes),
        "raw_bytes_total": sum(raw_sizes),
        "raw_bytes_mean": round(statistics.fmean(raw_sizes), 1) if raw_sizes else 0,
        "raw_bytes_p90": _percentile(raw_sizes, 0.9),
        "parse": parse_stats,
    }


def project(
    measured: dict,
    *,
    target: int,
    price_per_mtok: float | None,
    disk_free_gb: float | None,
    workers: float = 1.0,
) -> dict:
    docs = measured["public_versions_from_real_sources"] or 0
    html_per_doc = measured["raw_bytes_mean"] or measured["evidence_bytes_mean"] or 0
    att_per_doc = (measured["attachment_bytes_on_disk"] / docs) if docs else 0
    chars_per_doc = measured["chars_per_version_mean"] or 0
    tokens_per_doc = int(chars_per_doc / CHARS_PER_TOKEN) if chars_per_doc else 0
    parse_seconds = measured["parse"].get("parse_seconds_mean") or 0

    tokens_total = tokens_per_doc * target
    cost = round(tokens_total / 1_000_000 * price_per_mtok, 2) if price_per_mtok is not None else None

    # Parse time is the CPU side only. A real backfill is dominated by politeness
    # delays, so both numbers are quoted and labelled.
    parse_hours = (parse_seconds * target / max(workers, 1)) / 3600
    min_interval = float(getattr(settings, "policy_collection_min_interval_seconds", 1.0) or 1.0)
    per_page_delay = float(getattr(settings, "policy_collection_per_page_delay_seconds", 0.0) or 0.0)
    request_hours = (target / max(workers, 1)) * (min_interval + per_page_delay) / 3600

    verdict = None
    if disk_free_gb is not None:
        need_gb = (html_per_doc + att_per_doc) * target / 1024 / 1024 / 1024
        verdict = {
            "projected_gb": round(need_gb, 2),
            "free_gb_supplied": disk_free_gb,
            "fits": need_gb <= disk_free_gb,
            "headroom_gb": round(disk_free_gb - need_gb, 2),
        }
    return {
        "target_documents": target,
        "html_mb_total": round(html_per_doc * target / 1024 / 1024, 1),
        "attachments_gb_total": round(att_per_doc * target / 1024 / 1024 / 1024, 3),
        "chars_per_document": chars_per_doc,
        "tokens_per_document_est": tokens_per_doc,
        "embedding_tokens_total_est": tokens_total,
        "embedding_cost_at_price": cost,
        "price_per_mtok_supplied": price_per_mtok,
        "parse_hours_cpu_only": round(parse_hours, 2),
        "request_floor_hours_politeness": round(request_hours, 1),
        "disk_verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="measured capacity and cost projection")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--price-per-mtok", type=float, default=None)
    parser.add_argument("--disk-free-gb", type=float, default=None)
    parser.add_argument("--parse-samples", type=int, default=40)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    measured = measure(parse_samples=args.parse_samples)
    projection = project(
        measured, target=args.target, price_per_mtok=args.price_per_mtok, disk_free_gb=args.disk_free_gb
    )
    payload = {"measured": measured, "projection": projection}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print("== measured from stored evidence ==")
    for key, value in measured.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub, sub_value in value.items():
                print(f"    {sub}: {sub_value}")
        else:
            print(f"  {key}: {value}")
    print(f"== projection to {args.target} documents ==")
    for key, value in projection.items():
        if isinstance(value, dict) and value:
            print(f"  {key}:")
            for sub, sub_value in value.items():
                print(f"    {sub}: {sub_value}")
        else:
            print(f"  {key}: {value}")
    if args.price_per_mtok is None:
        print("  note: no price supplied, so no cost is claimed (never estimate a bill)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
