#!/usr/bin/env python
"""Write real harvest results back into the source catalog (line-level edits).

The catalog is hand-maintained YAML with explanatory notes, so re-serialising it
with PyYAML would destroy comments and formatting. This script edits only the
three fields that a verification run is allowed to own, inside the matching
``- source_id:`` block:

* ``verification_state``
* ``last_verified_at``
* ``notes`` (appended, never replaced wholesale)

State rules (deliberately conservative):

===============  ==========================================================
condition        resulting state
===============  ==========================================================
list ok, doc ok  ``document_verified``
list ok, thin    ``list_verified``      (list parsed, body under threshold)
list ok, 0 items ``(unchanged)``        + note ``empty_list``; a rewrite may be
                                        temporary or a rule break, not a verdict
http 404/410     ``unreachable``
robots denial    ``blocked_by_robots``
timeout/network  ``(unchanged)``        + note; transient by nature
===============  ==========================================================

Run with ``--dry-run`` first. Always keep a copy of ``config/policy_sources``
before writing.

Usage::

    ./.venv/bin/python scripts/policy_collection/record_verification.py \
        --from /tmp/harvest_national.json --from /tmp/harvest_provincial.json --dry-run
    ./.venv/bin/python scripts/policy_collection/record_verification.py --from ... 
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

FIELD_RE = {
    "verification_state": re.compile(r"^(?P<indent>\s*)verification_state:\s*(?P<value>.*)$"),
    "last_verified_at": re.compile(r"^(?P<indent>\s*)last_verified_at:\s*(?P<value>.*)$"),
    "notes": re.compile(r"^(?P<indent>\s*)notes:\s*(?P<value>.*)$"),
}
BLOCK_START = re.compile(r"^(\s*)-\s+source_id:\s*(?P<sid>[A-Za-z0-9_\-]+)\s*$")


def classify(entry: dict) -> tuple[str | None, str]:
    """Return (new_state_or_None, note)."""
    if not entry["list_ok"]:
        err = (entry.get("list_error") or "").lower()
        if "404" in err or "410" in err:
            return "unreachable", f"2026-11-06 干跑实测 http 404，入口已失效，待重定位栏目 URL"
        if "robots" in err:
            return "blocked_by_robots", "2026-11-06 干跑实测 robots.txt 禁止，按规则不采"
        # Transient outcomes (timeout, connection reset) say nothing about the
        # source itself.  Writing them into the catalog would leave a permanent
        # "broken" note that contradicts the next successful run, so the state
        # and the notes stay untouched; the harvest JSON keeps the evidence.
        return None, ""

    if entry["entries"] == 0:
        return None, "2026-11-06 干跑列表页解析出 0 条：静态 HTML 无条目锚点或选择器未命中，需核查适配器"

    parsed = sum(1 for d in entry["docs"] if d["parsed"])
    if parsed:
        return (
            "document_verified",
            f"2026-11-06 干跑：列表 {entry['entries']} 条，取 {len(entry['docs'])} 篇，"
            f"解析成功 {parsed} 篇（未入库）",
        )
    return (
        "list_verified",
        f"2026-11-06 干跑：列表 {entry['entries']} 条可解析，正文过短或需附件解析，待补",
    )


def update_block(lines: list[str], start: int, end: int, new_state: str | None, note: str, stamp: str) -> bool:
    """Edit one source block in place. Returns True when something changed.

    Line endings are preserved: the catalog is hand-edited YAML and a lost
    newline merges three fields into one invalid line. Block scalars
    (``notes: |`` / ``notes: >-``) are left alone entirely, because appending to
    the first line of a folded block corrupts its indentation.
    """
    # Idempotence: re-running against the same harvest must not touch the file.
    # The stamp only refreshes when the state or the note actually changes,
    # otherwise the catalog would look "re-verified" on every replay.
    current_state = current_note = current_time = None
    for idx in range(start + 1, end):
        body = lines[idx].rstrip("\r\n")
        m = FIELD_RE["verification_state"].match(body)
        if m:
            current_state = m.group("value").strip()
            continue
        m = FIELD_RE["notes"].match(body)
        if m:
            current_note = m.group("value").strip()
    # A folded/literal block scalar (``notes: >-``) is hand-written prose that this
    # script must never append to; treat it as already-recorded so replays are no-ops.
    note_is_block = bool(current_note) and current_note.startswith(("|", ">"))
    note_missing = note and not note_is_block and (
        current_note is None or note not in current_note
    )
    needs = bool(new_state and current_state != new_state) or bool(note_missing)
    if not needs:
        return False

    changed = False
    seen_state = seen_time = seen_notes = False
    insert_at = start + 1

    for idx in range(start + 1, end):
        raw = lines[idx]
        body = raw.rstrip("\r\n")
        ending = raw[len(body):] or "\n"
        for name, pattern in FIELD_RE.items():
            match = pattern.match(body)
            if not match:
                continue
            indent = match.group("indent")
            value = match.group("value").strip()
            if name == "verification_state":
                seen_state = True
                if new_state and value != new_state:
                    lines[idx] = f"{indent}verification_state: {new_state}{ending}"
                    changed = True
                insert_at = idx + 1
            elif name == "last_verified_at":
                seen_time = True
                lines[idx] = f'{indent}last_verified_at: "{stamp}"{ending}'
                changed = True
                insert_at = idx + 1
            else:
                seen_notes = True
                insert_at = idx + 1
                if value.startswith(("|", ">")):
                    # Folded block scalar: leave the prose untouched AND insert any
                    # new fields *before* it, otherwise a new line lands between
                    # ``notes: >-`` and its indented body and breaks the YAML.
                    insert_at = idx
                    break
                if value and note not in value:
                    merged = value.rstrip("，, ") + "；" + note
                    lines[idx] = f"{indent}notes: {merged}{ending}"
                    changed = True
            break

    if not seen_state and new_state:
        lines.insert(insert_at, f"    verification_state: {new_state}\n")
        changed = True
        insert_at += 1
    if not seen_time:
        lines.insert(insert_at, f'    last_verified_at: "{stamp}"\n')
        changed = True
        insert_at += 1
    if not seen_notes:
        lines.insert(insert_at, f"    notes: {note}\n")
        changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="record harvest verification back into catalog YAML")
    parser.add_argument("--from", dest="sources", action="append", default=[], help="harvest JSON path")
    parser.add_argument("--catalog", default=str(APP_ROOT / "config" / "policy_sources"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.sources:
        parser.error("--from is required")

    results: dict[str, dict] = {}
    for path in args.sources:
        data = json.loads(Path(path).read_text())
        for entry in data["sources"]:
            results[entry["source_id"]] = entry

    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    total_changed = 0

    for yaml_path in sorted(Path(args.catalog).glob("*.yaml")):
        lines = yaml_path.read_text().splitlines(keepends=True)
        blocks: list[tuple[int, int, str]] = []
        current: tuple[int, str] | None = None
        for idx, line in enumerate(lines):
            match = BLOCK_START.match(line.rstrip("\n"))
            if match:
                if current:
                    blocks.append((current[0], idx, current[1]))
                current = (idx, match.group("sid"))
        if current:
            blocks.append((current[0], len(lines), current[1]))

        file_changed = 0
        # iterate bottom-up so insertions do not shift earlier offsets
        for start, end, sid in reversed(blocks):
            entry = results.get(sid)
            if not entry:
                continue
            new_state, note = classify(entry)
            if update_block(lines, start, end, new_state, note, stamp):
                file_changed += 1

        if file_changed:
            total_changed += file_changed
            if args.dry_run:
                print(f"would update {file_changed} block(s) in {yaml_path.name}")
            else:
                yaml_path.write_text("".join(lines))
                print(f"updated {file_changed} block(s) in {yaml_path.name}")

    print(f"\n{'dry run: ' if args.dry_run else ''}{total_changed} source block(s) touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
