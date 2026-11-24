"""Parse the documents the collector actually downloaded.

Why this exists: the six-state coverage matrix distinguishes "collected the raw
page" from "parsed". Without a parser pass over the *real* stored bytes, the
"parsed" column is a guess. This script is read-only — it never writes a policy
row, never calls a model — so it is safe to run against the raw store at any
time and its output can be quoted as evidence.

Usage::

    python scripts/park_policy/parse_dry_run.py [--root crawler_output/policy_raw]
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.policy_collection.extract import extract_document_page

TEXT_EXTENSIONS = {".html", ".htm"}
OPAQUE_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".ofd", ".zip"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="parse real collected documents (read-only)")
    parser.add_argument("--root", default="crawler_output/policy_raw")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--show", type=int, default=0, help="print N parsed samples")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_absolute():
        root = REPO_ROOT / root
    if not root.exists():
        print(f"原始库不存在: {root}", file=sys.stderr)
        return 2

    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        source_id = path.relative_to(root).parts[0]
        suffix = path.suffix.lower()
        row = {
            "source_id": source_id,
            "file": str(path.relative_to(root)),
            "extension": suffix,
            "bytes": path.stat().st_size,
        }
        if suffix in TEXT_EXTENSIONS:
            try:
                html = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                row.update(status="read_error", reason=str(exc))
                rows.append(row)
                continue
            page = extract_document_page(html, url=f"file://{path}")
            row.update(
                status="parsed",
                title=page.title[:120],
                doc_number=page.doc_number,
                published_at=page.published_at.isoformat() if page.published_at else None,
                text_chars=page.text_chars,
                attachments=len(page.attachments),
                attachment_files=[
                    a.filename for a in page.attachments[:5]
                ],
            )
            # A page with almost no text is a parse failure, not a policy.
            if page.text_chars < 200:
                row["status"] = "parsed_thin"
        elif suffix in OPAQUE_EXTENSIONS:
            row.update(status="attachment_stored_not_parsed")
        else:
            row.update(status="unknown_extension")
        rows.append(row)

    by_status = collections.Counter(r["status"] for r in rows)
    by_source = collections.defaultdict(collections.Counter)
    for row in rows:
        by_source[row["source_id"]][row["status"]] += 1

    parsed = [r for r in rows if r["status"] == "parsed"]
    with_doc_no = [r for r in parsed if r.get("doc_number")]
    with_date = [r for r in parsed if r.get("published_at")]
    with_attachment = [r for r in parsed if r.get("attachments")]

    summary = {
        "root": str(root),
        "files_total": len(rows),
        "bytes_total": sum(r["bytes"] for r in rows),
        "by_status": dict(by_status),
        "by_source": {k: dict(v) for k, v in sorted(by_source.items())},
        "parse_quality": {
            "parsed_documents": len(parsed),
            "with_doc_number": len(with_doc_no),
            "with_publish_date": len(with_date),
            "with_attachments": len(with_attachment),
            "thin_text": by_status.get("parsed_thin", 0),
        },
        "honesty_notes": [
            "已解析 != 已入库 != 已进入检索：本脚本不写数据库。",
            "PDF/Word/OFD 仅完成原文留存，未做确定性解析，因此不计入已解析。",
            "parsed_thin 表示正文过短，按解析失败处理，不得当作有效政策。",
        ],
    }

    if args.json:
        print(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
        return 0

    print(f"原始库: {summary['root']}")
    print(f"文件总数: {summary['files_total']}  总字节: {summary['bytes_total']:,}")
    print(f"状态分布: {summary['by_status']}")
    print("\n解析质量:")
    for key, value in summary["parse_quality"].items():
        print(f"  {key}: {value}")
    print("\n按来源:")
    for source, counts in summary["by_source"].items():
        print(f"  {source}: {counts}")

    if args.show:
        print("\n样本:")
        for row in parsed[: args.show]:
            print(f"  [{row['source_id']}] {row.get('title')}")
            print(f"    文号={row.get('doc_number')} 日期={row.get('published_at')} "
                  f"正文={row.get('text_chars')}字 附件={row.get('attachments')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
