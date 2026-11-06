"""Binary documents that arrive as a list entry must not be stored as HTML text.

Real failure this pins down: cnipa publishes the document itself as the list item
(``downfile.jsp?...filename=x.pdf``).  The runner decoded the PDF as UTF-8 and wrote
250k characters of binary into ``policies.content``; the first NUL byte then aborted
the whole batch with ``PostgreSQL text fields cannot contain NUL (0x00) bytes``.
"""

from __future__ import annotations

import pytest

from app.services.policies.ingestion import clean_policy_text
from app.services.policy_collection.runner import PolicyCollectionRunner


def _detect(url: str, content_type: str | None) -> str | None:
    """Call the detector directly: it is pure, so no session or store is needed."""
    return PolicyCollectionRunner._binary_document_name(None, url, content_type)


@pytest.mark.parametrize(
    "url,content_type",
    [
        ("https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&filename=a.pdf", None),
        ("https://www.gov.cn/zhengce/wenjian.pdf", "text/html"),
        ("https://example.gov.cn/attach/notice.docx", None),
        ("https://example.gov.cn/dl?showname=%E9%80%9A%E7%9F%A5.ofd", None),
        ("https://example.gov.cn/api/doc", "application/pdf; charset=binary"),
        (
            "https://example.gov.cn/api/doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
def test_binary_document_is_detected(url, content_type):
    assert _detect(url, content_type), f"{url} / {content_type} should be a document"


@pytest.mark.parametrize(
    "url,content_type",
    [
        ("https://www.gov.cn/zhengce/content/202601/t20260101_1.htm", "text/html; charset=utf-8"),
        ("https://www.gov.cn/zhengce/", "text/html"),
        ("https://example.gov.cn/news?page=2", "text/html"),
        ("https://example.gov.cn/index.html", None),
        # octet-stream alone proves nothing: plenty of HTML is served that way.
        ("https://example.gov.cn/api/doc", "application/octet-stream"),
    ],
)
def test_html_pages_are_left_alone(url, content_type):
    assert _detect(url, content_type) is None


def test_nul_bytes_and_control_chars_are_stripped_before_persisting():
    # A NUL anywhere in the payload would otherwise abort the whole transaction.
    raw = "第一条 为促进\x00发展\n第二条 支持\x07研发\x1f。"
    cleaned = clean_policy_text(raw)
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned
    assert "\x1f" not in cleaned
    assert "第一条 为促进发展" in cleaned
    assert cleaned.count("\n") == 1
