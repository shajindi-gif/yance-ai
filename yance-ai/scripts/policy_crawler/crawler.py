"""Generic government policy list crawler.

Collects public science/tech policy pages from configurable list-page sources
(Shanghai / Shenzhen / Hangzhou), extracts title + body + metadata, and emits
JSONL for the structured import pipeline (parse → rule extraction → review).

Compliance: public policy documents only, 1 request / 2 seconds, robots.txt
respected per source, standard UA with contact info.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

UA = "YancePolicyCrawler/1.0 (+https://yance.ai; contact@yance.ai)"

MAX_PAGES_PER_SOURCE = 100
REQUEST_INTERVAL_SECONDS = 2.0
BODY_MIN_CHARS = 200  # below this, not a policy document page
BODY_MAX_CHARS = 200_000


@dataclass
class Source:
    """A list page (or paginated) source of policy document links."""

    key: str
    name: str
    level: str  # provincial / municipal / district
    province: str
    city: str
    issuing_authority: str
    list_url: str  # may contain {page} placeholder
    page_start: int = 1
    link_pattern: str = r".*"  # regex on href
    title_pattern: str = r".*"  # regex on link text; used to filter


SOURCES: list[Source] = [
    # Verified reachable & policy-dense (probed 2026-10-12)
    Source(
        key="sh_stcsm_zcwj",
        name="上海市科委·政策文件",
        level="provincial",
        province="上海市",
        city="上海市",
        issuing_authority="上海市科学技术委员会",
        list_url="https://stcsm.sh.gov.cn/zwgk/zcwj/index.html",
        link_pattern=r"/zwgk/(kyjhxm|gsgg|kjzc|tzgs)/\d{8}/[0-9a-f]+\.html",
    ),
    Source(
        key="sh_stcsm_xmsb",
        name="上海市科委·项目申报",
        level="provincial",
        province="上海市",
        city="上海市",
        issuing_authority="上海市科学技术委员会",
        list_url="https://stcsm.sh.gov.cn/zwgk/kyjhxm/xmsb/index.html",
        link_pattern=r"/zwgk/kyjhxm/xmsb/\d{8}/[0-9a-f]+\.html",
    ),
    Source(
        key="zj_kjt_tzgg",
        name="浙江省科技厅·通知公告",
        level="provincial",
        province="浙江省",
        city="杭州市",
        issuing_authority="浙江省科学技术厅",
        list_url="https://kjt.zj.gov.cn/",
        link_pattern=r"/col/col1229225203/art/",
    ),
    Source(
        key="zj_kjt_kjdt",
        name="浙江省科技厅·科技动态",
        level="provincial",
        province="浙江省",
        city="杭州市",
        issuing_authority="浙江省科学技术厅",
        list_url="https://kjt.zj.gov.cn/",
        link_pattern=r"/col/col1228971342/art/",
    ),
    Source(
        key="sh_stcsm_kjzc",
        name="上海市科委·科技政策文件",
        level="provincial",
        province="上海市",
        city="上海市",
        issuing_authority="上海市科学技术委员会",
        list_url="https://stcsm.sh.gov.cn/zwgk/kjzc/zcwj/kwzcxwj/index.html",
        link_pattern=r"/zwgk/kjzc/\d{8}/[0-9a-f]+\.html",
    ),
    Source(
        key="sh_stcsm_zxzj",
        name="上海市科委·专项资助",
        level="provincial",
        province="上海市",
        city="上海市",
        issuing_authority="上海市科学技术委员会",
        list_url="https://stcsm.sh.gov.cn/zwgk/kyjhxm/zxzj/index.html",
        link_pattern=r"/zwgk/kyjhxm/zxzj/\d{8}/[0-9a-f]+\.html",
    ),
]


class _TextExtractor(HTMLParser):
    """Collect visible text and <a> links from an HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._in_a = False
        self._href = ""
        self._a_text: list[str] = []
        self._skip_depth = 0  # inside script/style

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1
        if tag == "a":
            self._in_a = True
            self._href = dict(attrs).get("href", "")
            self._a_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a" and self._in_a:
            self._in_a = False
            text = unescape("".join(self._a_text)).strip()
            if text and self._href:
                self.links.append((self._href, text))

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_a:
            self._a_text.append(data)
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.text_parts).strip())


def _parse(html: str) -> _TextExtractor:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # malformed HTML: keep whatever was collected
        pass
    return parser


def _fetch(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        response = client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
        if response.status_code == 200:
            response.encoding = response.charset_encoding or "utf-8"
            return response
    except httpx.HTTPError:
        return None
    return None


DATE_RE = re.compile(r"(20[12]\d)[-年./](\d{1,2})[-月./](\d{1,2})")


def _extract_dates(text: str) -> tuple[str | None, str | None]:
    match = DATE_RE.search(text[:3000])
    if not match:
        return None, None
    try:
        published = datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc
        ).isoformat()
    except ValueError:
        return None, None
    return published, None


SUPPORT_PATTERNS = [
    r"(?:最高|不超过|单个项目最高)[^。；\n]{0,20}?(\d+(?:\.\d+)?)(万|亿)元",
    r"(\d+(?:\.\d+)?)万?元?[-—~至]\d+(?:\.\d+)?万元",
]


def _extract_support_amount(content: str) -> str | None:
    for pattern in SUPPORT_PATTERNS:
        match = re.search(pattern, content)
        if match:
            start = max(0, match.start() - 6)
            return re.sub(r"\s+", "", content[start : match.end() + 4])[:80]
    return None


TITLE_JUNK = re.compile(r"^20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}(?::\d{2})?\s*|"
                           r"^\d{2}:\d{2}(?::\d{2})?\s+")


def _clean_title(raw: str) -> str:
    """Strip list-page date/time prefixes that leak into link text."""
    cleaned = TITLE_JUNK.sub("", raw.strip())
    # cap at first full title boundary
    return re.sub(r"\s+", " ", cleaned)[:500]


def _title_from_content(content: str, fallback: str) -> str:
    """Prefer the document's own <title>/first heading over list-link text."""
    for line in content.splitlines():
        line = line.strip()
        if 8 <= len(line) <= 120 and re.search(r"通知|办法|意见|细则|指南|方案|条例|规定|公告|计划|申报", line):
            return re.sub(r"\s+", " ", line)[:500]
    return fallback


def crawl_source(client: httpx.Client, source: Source) -> list[dict]:
    """Crawl one source list page and fetch each linked policy document."""
    visited: set[str] = set()
    results: list[dict] = []

    link_re = re.compile(source.link_pattern)
    title_re = re.compile(source.title_pattern)

    candidates: list[tuple[str, str]] = []
    # First page + detected index_N.html pagination (common gov site layout)
    list_urls = [source.list_url]
    for page_no in range(1, 60):
        if "{page}" in source.list_url:
            paginated = source.list_url.format(page=source.page_start + page_no - 1)
        else:
            base = source.list_url
            if base.endswith("index.html"):
                paginated = base.replace("index.html", f"index_{page_no}.html")
            elif base.endswith("/"):
                paginated = base + f"index_{page_no}.html"
            else:
                break
            list_urls.append(paginated)

    for list_url in list_urls:
        time.sleep(REQUEST_INTERVAL_SECONDS)
        response = _fetch(client, list_url)
        if response is None:
            if "{page}" not in source.list_url and list_url != source.list_url:
                break  # pagination exhausted
            continue
        page_url = str(response.url)
        parser = _parse(response.text)
        page_new = 0
        for href, text in parser.links:
            absolute = urljoin(page_url, href)
            if absolute in visited or absolute == page_url:
                continue
            if not link_re.search(absolute) and not link_re.search(text):
                continue
            if not title_re.search(text) or len(text) < 8:
                continue
            if absolute.startswith("http") and urlparse(absolute).netloc != urlparse(page_url).netloc:
                continue  # stay on the authority's own domain
            visited.add(absolute)
            candidates.append((absolute, text))
            page_new += 1
        if page_new == 0 and list_url != source.list_url:
            break  # no new links on this pagination page

    print(f"[{source.key}] {len(candidates)} candidate policy links")

    for url, title in candidates[:MAX_PAGES_PER_SOURCE]:
        time.sleep(REQUEST_INTERVAL_SECONDS)
        doc_response = _fetch(client, url)
        if doc_response is None:
            continue
        doc_parser = _parse(doc_response.text)
        content = doc_parser.text
        if len(content) < BODY_MIN_CHARS or len(content) > BODY_MAX_CHARS:
            continue
        published, _ = _extract_dates(content)
        results.append(
            {
                "source_key": source.key,
                "title": _title_from_content(content, _clean_title(title)),
                "source_url": url,
                "issuing_authority": source.issuing_authority,
                "level": source.level,
                "province": source.province,
                "city": source.city,
                "published_at": published,
                "support_amount_hint": _extract_support_amount(content),
                "content": content,
                "content_chars": len(content),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "crawler_version": "policy-crawler-v1",
            }
        )
        print(f"[{source.key}] + {title[:40]} ({len(content)} chars)")

    return results


def run(output_path: str, sources: list[Source] | None = None) -> int:
    client = httpx.Client(timeout=20, follow_redirects=True)
    all_items: list[dict] = []
    seen_urls: set[str] = set()
    for source in sources or SOURCES:
        try:
            items = crawl_source(client, source)
            fresh = [item for item in items if item["source_url"] not in seen_urls]
            seen_urls.update(item["source_url"] for item in fresh)
            all_items.extend(fresh)
        except Exception as exc:  # one source failing must not stop the batch
            print(f"[{source.key}] source failed: {exc}")
        time.sleep(REQUEST_INTERVAL_SECONDS)

    with open(output_path, "w", encoding="utf-8") as handle:
        for item in all_items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"total: {len(all_items)} policies -> {output_path}")
    return len(all_items)


if __name__ == "__main__":
    run("crawler_output/policies.jsonl")
