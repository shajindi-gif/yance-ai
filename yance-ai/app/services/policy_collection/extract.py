"""HTML extraction for Chinese government policy pages.

The extractor is deliberately conservative about dates: a policy publication
date is only accepted from an explicit label inside the document body
(``发布日期`` / ``成文日期`` / ``发文字号`` block) or a document-level ``<meta>``
tag. Navigation dates, list-page timestamps and "当前时间" widgets are ignored,
because their presence was the previous pipeline's main source of wrong dates.

Only the standard library is used so the layer stays unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".wps",
    ".et",
    ".zip",
    ".rar",
    ".7z",
    ".txt",
    ".csv",
    ".ofd",
}

CONTENT_CONTAINER_HINTS = (
    "trs_editor",
    "pages_content",
    "zoom",
    "article",
    "content",
    "xxgk",
    "detail",
    "main-text",
    "view",
    "body-box",
)

NAV_NOISE = re.compile(
    r"^(首页|返回|上一篇|下一篇|打印|关闭|分享|收藏|字体|网站地图|无障碍|登录|注册|更多)"
)

# Column landing pages and topic portals that look exactly like a document link
# in list templates. Matched by full title only, so a real policy whose title
# merely contains one of these phrases is kept.
LIST_NAV_TITLES = frozenset(
    {
        "政府信息公开",
        "政府信息公开指南",
        "政府信息公开年报",
        "政府信息公开制度",
        "信息公开指南",
        "信息公开年报",
        "科技型企业培育",
        "政策咨询",
        "网站地图",
        "联系我们",
        "在线咨询",
        "申报专题",
        "政策文件",
        "政策法规",
        "政策解读",
        "规范性文件",
        "通知公告",
        "工作动态",
        "业务专题",
        "查看更多",
        "更多",
    }
)

DATE_PATTERNS = (
    re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?"),
    re.compile(r"(20\d{2})(\d{2})(\d{2})"),
)

DATE_LABELS = (
    "发布时间",
    "发布日期",
    "成文日期",
    "发文日期",
    "印发日期",
    "公布日期",
    "日期",
)

_DOC_NUMBER_RE = re.compile(
    r"[\u4e00-\u9fa5]{1,12}[〔\[［(（]\s*20\d{2}\s*[〕\]］)）]\s*\d{1,4}\s*号"
)

_SKIP_TAGS = {"script", "style", "noscript", "iframe", "template"}

_CDATA_OPEN = re.compile(r"<!\[CDATA\[", re.IGNORECASE)
_CDATA_CLOSE = re.compile(r"\]\]>")
# HTML comments may wrap whole list rows. HTMLParser treats everything from an
# unterminated ``<!--`` to EOF as comment text, which silently swallows the rest
# of the page; removing comment bodies up front keeps link extraction stable.
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# TRS/Hanweb column pages carry their rows inside
# ``<script type="text/xml"><datastore><record>...<li><a href=...>``. A parser
# sees only raw script text there and the whole list disappears, so non-JS
# script islands are unwrapped before parsing.
_DATA_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.DOTALL | re.IGNORECASE)
_JS_TYPES = (
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "module",
    "text/ecmascript",
    "application/ecmascript",
)
_TYPE_ATTR = re.compile(r"type\s*=\s*[\"']?([^\"'\s>]+)", re.IGNORECASE)


def _unwrap_data_scripts(html: str) -> str:
    def repl(match: re.Match[str]) -> str:
        attrs, body = match.group(1) or "", match.group(2) or ""
        type_match = _TYPE_ATTR.search(attrs)
        if type_match and type_match.group(1).lower() not in _JS_TYPES:
            return body
        if not type_match and "<a " not in body.lower():
            return match.group(0)
        return match.group(0)

    return _DATA_SCRIPT.sub(repl, html)

# `_strip_cdata` runs before parsing.
def _strip_cdata(html: str) -> str:
    """Unwrap ``<![CDATA[ ... ]]>`` islands so the markup inside is parsed.

    Several provincial/municipal CMS templates (TRS, Hanweb) emit list rows as
    ``<record><![CDATA[<li><a href=...>标题</a></li>]]></record>``. Python's
    HTMLParser treats everything between ``<![CDATA[`` and ``]]>`` as an opaque
    declaration, so without this step the entire list vanishes and the source
    looks permanently empty.
    """
    html = _unwrap_data_scripts(html)
    if "<![CDATA[" in html or "<![cdata[" in html:
        html = _CDATA_CLOSE.sub("", _CDATA_OPEN.sub("", html))
    return _COMMENT.sub("", html)


def parse_cn_date(value: str | None) -> date | None:
    if not value:
        return None
    for pattern in DATE_PATTERNS:
        match = pattern.search(value)
        if not match:
            continue
        try:
            year, month, day = (int(part) for part in match.groups())
            return date(year, month, day)
        except ValueError:
            continue
    return None


def extract_doc_number(text: str) -> str | None:
    match = _DOC_NUMBER_RE.search(text[:5000])
    return re.sub(r"\s+", "", match.group(0)) if match else None


@dataclass
class RawLink:
    href: str
    text: str
    title_attr: str | None = None
    tail: str = ""
    lead: str = ""

    @property
    def label(self) -> str:
        return _clean(self.text) or _clean(self.title_attr or "")


def _clean(value: str | None) -> str:
    text = unescape(value or "")
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


class _PageParser(HTMLParser):
    """Collect links, container text and document-level metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[RawLink] = []
        self.meta: dict[str, str] = {}
        self.title_text: list[str] = []
        self.page_text: list[str] = []
        self.container_texts: dict[str, list[str]] = {}
        self._stack: list[str] = []  # open container keys
        self._skip = 0
        self._in_title = False
        self._in_a = False
        self._current: RawLink | None = None
        self._capture_tail = False
        self._recent_text = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in _SKIP_TAGS:
            self._skip += 1
            return
        if tag == "meta":
            name = (attributes.get("name") or attributes.get("property") or "").lower()
            content = attributes.get("content")
            if name and content:
                self.meta[name] = _clean(content)
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self._in_a = True
            self._capture_tail = False
            self._current = RawLink(
                href=attributes.get("href", ""),
                text="",
                title_attr=attributes.get("title"),
                lead=self._recent_text[-120:],
            )
        if self._skip:
            return
        key = _container_key(attributes)
        if key:
            self._stack.append(key)
            self.container_texts.setdefault(key, [])
        elif self._stack:
            self._stack.append("")  # keep depth alignment for non-container tags

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            if self._skip:
                self._skip -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._in_a and self._current is not None:
            self.links.append(self._current)
            self._current = None
            self._in_a = False
            self._capture_tail = True
        if self._stack:
            self._stack.pop()

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title_text.append(data)
            return
        text = _clean(data)
        if not text:
            return
        self.page_text.append(text)
        if self._in_a and self._current is not None:
            self._current.text += text
            return
        self._recent_text = f"{self._recent_text} {text}".strip()[-200:]
        if self._capture_tail and self.links:
            # Text directly after a link on list pages often carries its date.
            if len(self.links[-1].tail) < 40:
                self.links[-1].tail = f"{self.links[-1].tail} {text}".strip()
        for key in self._stack:
            if key:
                self.container_texts[key].append(text)


def _container_key(attributes: dict) -> str | None:
    identifier = (attributes.get("id") or "").lower()
    classes = (attributes.get("class") or "").lower()
    blob = f"{identifier} {classes}"
    for hint in CONTENT_CONTAINER_HINTS:
        if hint in blob:
            return hint
    return None


@dataclass
class ListEntry:
    url: str
    title: str
    date_hint: date | None = None
    context: str = ""


_META_REFRESH = re.compile(
    r"<meta[^>]+http-equiv\s*=\s*[\"']?refresh[\"']?[^>]*content\s*=\s*[\"']?\s*\d*\s*;?\s*url=([^\">\s]+)",
    re.IGNORECASE,
)
_SCRIPT_STYLE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>", re.DOTALL | re.IGNORECASE
)
_JS_REDIRECT = (
    re.compile(r"(?:window\.)?location(?:\.href)?\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE),
    re.compile(r"(?:window\.)?location\.replace\(\s*[\"']([^\"']+)[\"']", re.IGNORECASE),
)


def detect_client_redirect(html: str, base_url: str) -> str | None:
    """Return the target of a client-side redirect page, else ``None``.

    Many government columns answer the canonical URL with a tiny shell that only
    redirects (``<meta http-equiv=refresh>`` or ``window.location = './tzgg_18371/'``).
    Treating that shell as the list page yields zero entries forever, which looks
    exactly like a broken rule. We only honour the redirect when the document is
    genuinely thin, so a real page that mentions ``location.href`` in its JS is
    never mistaken for one.
    """
    stripped = _COMMENT.sub("", _strip_cdata(html))
    # Judge "thinness" on visible text only. A redirect shell usually drags in the
    # whole CMS bundle, and that source code would otherwise push the document past
    # the size guard and hide a perfectly valid redirect.
    visible = _SCRIPT_STYLE.sub(" ", stripped)
    text_only = re.sub(r"<[^>]+>", " ", visible)
    if len(re.sub(r"\s+", "", text_only)) > 200:
        return None
    if len(re.findall(r"<a\b", stripped, re.IGNORECASE)) > 3:
        return None
    target = None
    meta = _META_REFRESH.search(stripped)
    if meta:
        target = meta.group(1)
    else:
        for pattern in _JS_REDIRECT:
            found = pattern.search(stripped)
            if found:
                target = found.group(1)
                break
    if not target:
        return None
    target = target.strip().strip("\"'")
    if not target or target.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    return urljoin(base_url, target)


def site_suffix(host: str) -> str:
    """Return the site suffix used to keep sibling sub-domains in one source.

    ``www.mof.gov.cn`` -> ``mof.gov.cn`` so ``jkw.mof.gov.cn`` articles published
    by a subordinate department still belong to the ministry's list page. Only
    applied when the host actually starts with ``www.``; otherwise the caller
    keeps strict host equality, which avoids pulling unrelated departments into
    a city bureau's source.
    """
    lowered = (host or "").lower()
    if lowered.startswith("www."):
        rest = lowered[4:]
        if rest.count(".") >= 1:
            return rest
    return lowered


def extract_list_entries(
    html: str,
    base_url: str,
    *,
    link_pattern: str | None = None,
    same_host_only: bool = True,
    min_title_chars: int = 6,
    allow_sibling_subdomains: bool = True,
) -> list[ListEntry]:
    """Extract candidate document links from a list page or search result page."""
    html = _strip_cdata(html)
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    base_host = (urlparse(base_url).hostname or "").lower()
    suffix = site_suffix(base_host) if allow_sibling_subdomains else ""
    pattern = re.compile(link_pattern) if link_pattern else None
    entries: list[ListEntry] = []
    seen: set[str] = set()
    for link in parser.links:
        if not link.href or link.href.startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, link.href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if same_host_only:
            host = (parsed.hostname or "").lower()
            if host != base_host and not (
                suffix and (host == suffix or host.endswith("." + suffix))
            ):
                continue
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in ATTACHMENT_EXTENSIONS):
            continue
        # Directory-style links ("/gfxwj/", "./", "../") are column navigation,
        # never a document, and following them would manufacture fake policies
        # out of section landing pages.
        if path.endswith("/") or path in {"", "/"}:
            continue
        title = link.label
        if len(title) < min_title_chars:
            continue
        if title.strip() in LIST_NAV_TITLES:
            continue
        target = absolute.split("#", 1)[0]
        if pattern and not (pattern.search(target) or pattern.search(title)):
            continue
        if target in seen:
            continue
        seen.add(target)
        # Date may sit before or after the anchor depending on the template; both
        # are page-layout hints only and never override the article page's own
        # publication date.
        date_hint = parse_cn_date(link.tail) or parse_cn_date(link.lead)
        entries.append(
            ListEntry(
                url=target,
                title=title,
                date_hint=date_hint,
                context=f"{link.lead[-60:]} {link.tail[:60]}".strip(),
            )
        )
    return entries


@dataclass
class AttachmentLink:
    url: str
    filename: str
    extension: str


@dataclass
class DocumentPage:
    url: str
    title: str
    text: str
    published_at: date | None = None
    doc_number: str | None = None
    attachments: list[AttachmentLink] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    text_chars: int = 0


def extract_main_text(html: str) -> tuple[str, dict[str, list[str]]]:
    """Prefer the densest content container; fall back to de-navigated body text."""
    html = _strip_cdata(html)
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    best_key, best_lines = None, []
    for key, lines in parser.container_texts.items():
        joined = "\n".join(lines)
        if len(joined) > len("\n".join(best_lines)):
            best_key, best_lines = key, lines
    body_lines = parser.page_text
    chosen = best_lines if best_key and len("\n".join(best_lines)) >= 300 else body_lines
    kept = []
    for line in chosen:
        if NAV_NOISE.match(line) and len(line) < 40:
            continue
        if len(line) <= 2:
            continue
        kept.append(line)
    return "\n".join(kept), parser.container_texts


def _date_from_labels(text: str) -> date | None:
    head = text[:3000]
    for label in DATE_LABELS:
        for match in re.finditer(label, head):
            window = head[match.end() : match.end() + 32]
            parsed = parse_cn_date(window)
            if parsed:
                return parsed
    return None


def extract_document_page(html: str, url: str) -> DocumentPage:
    html = _strip_cdata(html)
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    text, _ = extract_main_text(html)
    meta_title = parser.meta.get("articletitle") or parser.meta.get("title") or ""
    title = _clean(meta_title) or _clean("".join(parser.title_text))
    title = re.split(r"[_|｜—]", title)[0].strip() or title
    published = None
    for key in ("pubdate", "publishdate", "article:published_time", "firstpublishedtime"):
        if parser.meta.get(key):
            published = parse_cn_date(parser.meta[key])
            if published:
                break
    if not published:
        published = _date_from_labels(text)
    attachments: list[AttachmentLink] = []
    seen: set[str] = set()
    for link in parser.links:
        absolute = urljoin(url, link.href)
        path = urlparse(absolute).path
        suffix = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path.rsplit("/", 1)[-1] else ""
        if suffix not in ATTACHMENT_EXTENSIONS:
            continue
        filename = link.label or path.rsplit("/", 1)[-1]
        if not any(filename.lower().endswith(ext) for ext in ATTACHMENT_EXTENSIONS):
            filename = f"{filename}{suffix}" if not filename.lower().endswith(suffix) else filename
        key = absolute.split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        attachments.append(AttachmentLink(url=key, filename=_clean(filename)[:200], extension=suffix))
    return DocumentPage(
        url=url,
        title=title,
        text=text,
        published_at=published,
        doc_number=extract_doc_number(text),
        attachments=attachments,
        meta=parser.meta,
        text_chars=len(text),
    )


_PAGE_COUNT_PATTERNS = (
    re.compile(r"createPageHTML\s*\(\s*(\d+)"),
    re.compile(r"(?:countPage|totalPage|recordCount|pageCount)\s*[=:]\s*['\"]?(\d+)", re.I),
    re.compile(r"共\s*(\d+)\s*页"),
)


def detect_page_count(html: str, *, cap: int) -> int:
    for pattern in _PAGE_COUNT_PATTERNS:
        match = pattern.search(html)
        if match:
            try:
                return max(1, min(int(match.group(1)), cap))
            except ValueError:
                continue
    return 1


_PAGINATION_HREF_RE = re.compile(
    r"""href\s*=\s*["']?([^"'\s>]*?)(\d+)\.(html?|shtml|jhtml)""", re.I
)


def discover_page_urls(html: str, base_url: str, *, cap: int) -> list[str]:
    """Read the pagination links a list page actually publishes.

    Government list pages are generated by many different CMS templates: the
    suffix may be ``.htm``/``.html``/``.shtml``, the first page may live at
    ``index_1.htm`` rather than ``index_2``, and the directory that owns the
    ``index_N`` files is sometimes one hop below the column URL that redirects
    into it.  Rather than guessing a template we read the links off the page,
    keep the numbering the site itself uses, and stop at ``cap``.
    """
    found: dict[int, str] = {}
    for match in _PAGINATION_HREF_RE.finditer(html):
        prefix, digits, suffix = match.groups()
        try:
            number = int(digits)
        except ValueError:
            continue
        if number < 1:
            continue
        absolute = urljoin(base_url, f"{prefix}{digits}.{suffix}")
        if urlparse(absolute).netloc != urlparse(base_url).netloc:
            continue
        found.setdefault(number, absolute)
    return [found[key] for key in sorted(found)][: max(0, cap)]


_CREATE_PAGE_ARGS_RE = re.compile(
    r"""createPageHTML\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*["']([^"']*)["']\s*,\s*["']([^"']*)["']""",
    re.I,
)


def pagination_urls(
    html: str,
    base_url: str,
    *,
    cap: int,
    page_parameter: str | None = None,
) -> list[str]:
    """Single decision point for "where is page N of this list".

    Three signals are tried in order of reliability:

    1. links the page really publishes (``href="index_1.htm"``);
    2. the CMS template embedded in its own JS (``createPageHTML(23, 0, "index", "htm")``
       on MOF/Hanweb style columns, which never emits real ``<a>`` tags for pages);
    3. a constructed ``index_N.html`` guess, only when nothing else exists.

    Using the page's own template matters: guessing ``.html`` against a column
    that serves ``.htm`` silently yields empty pages, which downstream code
    would otherwise mistake for "this source simply has no more history".
    """
    if page_parameter:
        return paginate_urls(base_url, cap + 1, page_parameter=page_parameter)
    discovered = discover_page_urls(html, base_url, cap=cap)
    if discovered:
        return discovered
    match = _CREATE_PAGE_ARGS_RE.search(html)
    if match:
        total, _current, prefix, suffix = match.groups()
        try:
            total_pages = int(total)
        except ValueError:
            total_pages = 0
        if total_pages > 1 and prefix:
            base = base_url if base_url.endswith("/") else base_url.rsplit("/", 1)[0] + "/"
            # ``createPageHTML(count, current, prefix, suffix)`` numbers the files
            # from 0 = first screen, so screen N lives in ``index_{N-1}``.
            return [
                f"{base}{prefix}_{page - 1}.{suffix or 'html'}"
                for page in range(2, min(total_pages, cap + 1) + 1)
            ]
    return paginate_urls(base_url, cap + 1)


def paginate_urls(
    entry_url: str,
    page_count: int,
    *,
    page_parameter: str | None = None,
    index_pattern: bool = True,
    suffix: str = "html",
    first_page_number: int = 2,
) -> list[str]:
    """Build page URLs for the two common Chinese government list layouts."""
    urls: list[str] = []
    if page_parameter:
        separator = "&" if "?" in entry_url else "?"
        for page in range(2, page_count + 1):
            urls.append(f"{entry_url}{separator}{page_parameter}={page}")
        return urls
    if not index_pattern:
        return urls
    start = max(2, first_page_number)
    if entry_url.endswith("index.html") or entry_url.endswith("index.htm"):
        base = entry_url[: entry_url.rindex("index")]
        urls = [f"{base}index_{page}.{suffix}" for page in range(start, page_count + 1)]
    elif entry_url.endswith("/"):
        urls = [f"{entry_url}index_{page}.{suffix}" for page in range(start, page_count + 1)]
    return urls
