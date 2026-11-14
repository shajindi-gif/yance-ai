"""Content-addressed storage for raw policy evidence (original pages / attachments).

Why a dedicated store instead of "just put it in the DB":

* the original bytes must survive a database restore point;
* the file name *is* the content hash, so a re-fetch of an unchanged page costs
  no extra disk and the evidence can be verified years later;
* nothing is ever overwritten: a changed page produces a new hash, keeping the
  old evidence for dispute resolution.

Layout::

    <root>/<source_id>/<YYYY>/<MM>/<sha256[:2]>/<sha256>.<ext>
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

EXTENSIONS = {
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "application/zip": ".zip",
    "application/octet-stream": ".bin",
}

UNSAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True)
class StoredRaw:
    path: str
    sha256: str
    byte_size: int
    reused: bool


def _safe_segment(value: str) -> str:
    cleaned = UNSAFE_SEGMENT.sub("_", value or "")[:80].strip("._")
    return cleaned or "unknown"


def extension_for(content_type: str | None, url: str = "") -> str:
    if content_type:
        base = content_type.split(";", 1)[0].strip().lower()
        if base in EXTENSIONS:
            return EXTENSIONS[base]
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix and re.fullmatch(r"\.[a-z0-9]{1,5}", suffix):
        return suffix
    return ".bin"


class RawEvidenceStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    def path_for(self, source_id: str, sha256: str, extension: str, when: datetime) -> Path:
        return (
            self.root
            / _safe_segment(source_id)
            / f"{when.year:04d}"
            / f"{when.month:02d}"
            / sha256[:2]
            / f"{sha256}{extension}"
        )

    def save(
        self,
        *,
        source_id: str,
        url: str,
        payload: bytes,
        content_type: str | None,
        fetched_at: datetime,
    ) -> StoredRaw:
        digest = hashlib.sha256(payload).hexdigest()
        path = self.path_for(source_id, digest, extension_for(content_type, url), fetched_at)
        if path.exists() and path.stat().st_size == len(payload):
            return StoredRaw(path=str(path), sha256=digest, byte_size=len(payload), reused=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        with open(tmp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        return StoredRaw(path=str(path), sha256=digest, byte_size=len(payload), reused=False)

    def read(self, path: str) -> bytes:
        target = Path(path).resolve()
        root = self.root.resolve()
        if root not in target.parents:
            raise ValueError("raw evidence path escapes the configured root")
        return target.read_bytes()
