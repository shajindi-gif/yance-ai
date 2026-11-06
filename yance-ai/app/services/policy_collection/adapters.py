"""List-page adapters.

One generic adapter covers most provincial/municipal list pages; a couple of
sites publish their list through an official JSON endpoint behind a JS loader,
and those get a *deterministic* adapter rather than a headless browser (the brief
says: browser rendering only when there is no other way).

``jpaas`` covers the Hanweb/JPAAS CMS used by several Zhejiang divisions.  The
column page ships a ``<script src=".../unitbuild.js" webId=... queryData="...">``
tag; we read those parameters and call the same JSON endpoint the page calls.
That keeps the request count identical to a human browsing the page and avoids
executing third-party JavaScript.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlencode, urljoin, urlparse

from .catalog import SourceDefinition
from .extract import (
    ListEntry,
    detect_client_redirect,
    detect_page_count,
    extract_list_entries,
    paginate_urls,
    parse_cn_date,
)

logger = logging.getLogger(__name__)

_UNITBUILD_RE = re.compile(r"<script[^>]*unitbuild\.js[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r"(\w+)\s*=\s*\"([^\"]*)\"")
_JPAAS_FRAGMENT = "jpaas-publish-server/front/page/build/unit"
_CREATE_PAGE_RE = re.compile(r"createPageHTML\(\s*\"[^\"]*\"\s*,\s*\"[^\"]*\"\s*,\s*(\d+)")

DEFAULT_PAGE_SIZE = 15


@dataclass
class ListFetch:
    entries: list[ListEntry]
    pages_fetched: int
    adapter_used: str
    note: str | None = None


class ListAdapter:
    name = "generic_list"

    def fetch(self, fetcher, source: SourceDefinition, *, max_pages: int) -> ListFetch:
        raise NotImplementedError


class GenericListAdapter(ListAdapter):
    """Plain HTML list pages with optional ``?page=N`` pagination."""

    name = "generic_list"

    def fetch(self, fetcher, source: SourceDefinition, *, max_pages: int) -> ListFetch:
        entries: list[ListEntry] = []
        seen: set[str] = set()
        pages = 0
        urls = [source.entry_url]
        page_cap = max(1, min(max_pages, source.max_pages))
        index = 0
        while index < len(urls) and pages < page_cap:
            url = urls[index]
            index += 1
            result = fetcher.get(url, purpose="list")
            if not result.ok:
                if pages == 0:
                    raise ListUnavailable(result)
                logger.info("list page %s failed mid-pagination: %s", url, result.error)
                break
            pages += 1
            html = result.text

            # Column URLs frequently answer with a redirect shell
            # (meta refresh / location assignment). Follow it explicitly so the
            # source keeps a deterministic, auditable hop chain.
            hops = 0
            while hops < 2:
                redirect_to = detect_client_redirect(html, result.final_url)
                if not redirect_to or redirect_to == result.final_url:
                    break
                hops += 1
                followed = fetcher.get(redirect_to, purpose="list")
                if not followed.ok:
                    logger.info(
                        "client redirect %s -> %s blocked or failed: %s",
                        source.source_id, redirect_to, followed.error,
                    )
                    break
                result, html = followed, followed.text
                if pages == 1 and not entries:
                    urls = [followed.final_url]
                    index = 0
                if redirect_to != followed.final_url:
                    logger.info(
                        "client redirect chain %s -> %s -> %s",
                        source.source_id, redirect_to, followed.final_url,
                    )

            if _JPAAS_FRAGMENT in html:
                # The page is a JS shell; switch to the CMS JSON endpoint.
                jpaas = JpaasListAdapter()
                fetched = jpaas.fetch(fetcher, source, max_pages=page_cap)
                return ListFetch(
                    entries=fetched.entries,
                    pages_fetched=pages + fetched.pages_fetched,
                    adapter_used=jpaas.name,
                    note="auto-detected JPAAS CMS, used official JSON endpoint",
                )

            batch = extract_list_entries(
                html, result.final_url, link_pattern=source.link_pattern
            )
            for entry in batch:
                if entry.url in seen:
                    continue
                seen.add(entry.url)
                entries.append(entry)
            if pages == 1:
                total_pages = detect_page_count(html, cap=page_cap)
                if total_pages > 1:
                    urls.extend(
                        paginate_urls(
                            source.entry_url,
                            total_pages,
                            page_parameter=source.page_parameter,
                        )
                    )
        return ListFetch(entries=entries, pages_fetched=pages, adapter_used=self.name)


class JpaasListAdapter(ListAdapter):
    """Hanweb/JPAAS CMS column: resolve ``unitbuild.js`` params, call the JSON API."""

    name = "site_specific"
    max_pages_supported = 1

    def fetch(self, fetcher, source: SourceDefinition, *, max_pages: int) -> ListFetch:
        page = fetcher.get(source.entry_url, purpose="list")
        if not page.ok:
            raise ListUnavailable(page)
        params = _jpaas_params(page.text)
        if not params:
            return ListFetch(entries=[], pages_fetched=1, adapter_used=self.name,
                             note="JPAAS markers not found")
        base = _origin(source.entry_url)
        api_url = urljoin(base, "/api-gateway/jpaas-publish-server/front/page/build/unit")
        # Reuse the safe fetcher: it re-validates host/IP, robots and rate limits
        # exactly like any other request. Query string is built by hand because
        # SafeFetcher.get takes a plain URL.
        query = urlencode(params)
        url = f"{api_url}?{query}"
        if len(url) > 2000:
            raise ListUnavailable(page, note="JPAAS query string too long")
        response = fetcher.get(url, purpose="list")
        if not response.ok:
            raise ListUnavailable(response)
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise ListUnavailable(response, note=f"non-JSON API response: {exc}") from exc
        body = payload.get("data") or {}
        html = body.get("html") or ""
        entries = extract_list_entries(html, source.entry_url)
        for entry in entries:
            entry.url = urljoin(source.entry_url, entry.url)
        return ListFetch(
            entries=entries,
            pages_fetched=2,
            adapter_used=self.name,
            note="JPAAS JSON endpoint" if entries else "JPAAS JSON endpoint returned no rows",
        )


class OpenApiListAdapter(ListAdapter):
    """Official JSON list endpoints, opt-in per source through ``api`` config.

    Two shapes are supported:

    * ``entry_url`` is the JSON endpoint itself and returns ``{items: [...]}``
      (the original behaviour, kept for compatibility);
    * ``api`` describes a search endpoint plus the static parameters a browser
      would send. The request is assembled here so no page JavaScript runs and
      the hop count stays identical to a single human page view per page.
    """

    name = "open_api"

    def fetch(self, fetcher, source: SourceDefinition, *, max_pages: int) -> ListFetch:
        api = dict(source.api or {})
        if not api:
            return self._fetch_simple_json(fetcher, source)
        return self._fetch_configured(fetcher, source, api, max_pages=max_pages)

    def _fetch_simple_json(self, fetcher, source: SourceDefinition) -> ListFetch:
        result = fetcher.get(source.entry_url, purpose="list")
        if not result.ok:
            raise ListUnavailable(result)
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise ListUnavailable(result, note=f"expected JSON: {exc}") from exc
        items = payload if isinstance(payload, list) else payload.get("items") or []
        entries = _entries_from_items(items, base_url=result.final_url)
        return ListFetch(entries=entries, pages_fetched=1, adapter_used=self.name)

    def _fetch_configured(
        self, fetcher, source: SourceDefinition, api: dict, *, max_pages: int
    ) -> ListFetch:
        params: dict[str, str] = {str(k): str(v) for k, v in (api.get("params") or {}).items()}
        page_param = str(api.get("page_param") or "page")
        page_size = int(api.get("page_size") or params.get(api.get("page_size_param") or "pageSize") or 20)
        page_size_param = str(api.get("page_size_param") or "pageSize")
        first_page = int(api.get("first_page") or 1)
        page_budget = max(1, min(max_pages, int(api.get("max_pages") or 1), source.max_pages))

        key_pattern = api.get("key_from_page")
        if key_pattern:
            page = fetcher.get(source.entry_url, purpose="list")
            if not page.ok:
                raise ListUnavailable(page)
            match = re.search(str(key_pattern), page.text)
            if not match:
                raise ListUnavailable(page, note="API key/params not found on the list page")
            params[str(api.get("key_param") or "key")] = match.group(1)

        endpoint = str(api.get("url") or source.entry_url)
        items_path = str(api.get("items_path") or "items")
        entries: list[ListEntry] = []
        pages = 0
        for offset in range(page_budget):
            params[page_param] = str(first_page + offset)
            if page_size:
                params[page_size_param] = str(page_size)
            url = f"{endpoint}?{urlencode(params)}"
            response = fetcher.get(url, purpose="list")
            if not response.ok:
                if pages == 0:
                    raise ListUnavailable(response)
                break
            pages += 1
            try:
                payload = json.loads(response.text)
            except json.JSONDecodeError as exc:
                if pages == 1:
                    raise ListUnavailable(response, note=f"expected JSON: {exc}") from exc
                break
            items = _dig(payload, items_path)
            if not isinstance(items, list) or not items:
                break
            entries.extend(
                _entries_from_items(
                    items,
                    base_url=str(api.get("base_url") or source.entry_url),
                    title_field=str(api.get("title_field") or "title"),
                    url_field=str(api.get("url_field") or "url"),
                    date_field=str(api.get("date_field") or "docDate"),
                )
            )
            if page_size and len(items) < page_size:
                break
        note = None if entries else "endpoint returned no rows"
        return ListFetch(entries=entries, pages_fetched=pages, adapter_used=self.name, note=note)


def _dig(payload, path: str):
    current = payload
    for part in [piece for piece in path.split(".") if piece]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


def _entries_from_items(
    items,
    *,
    base_url: str,
    title_field: str = "title",
    url_field: str = "url",
    date_field: str = "date",
) -> list[ListEntry]:
    entries: list[ListEntry] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        raw_url = item.get(url_field) or item.get("link") or item.get("href")
        if not raw_url or not isinstance(raw_url, str):
            continue
        entries.append(
            ListEntry(
                url=urljoin(base_url, raw_url.strip()),
                title=str(item.get(title_field) or item.get("title") or "").strip(),
                date_hint=parse_cn_date(
                    str(item.get(date_field) or item.get("date") or item.get("published_at") or "")
                ),
            )
        )
    return entries


class PortalAdapter(GenericListAdapter):
    """Portal home pages: same parsing, but an empty list is not an error."""

    name = "portal"

    def fetch(self, fetcher, source: SourceDefinition, *, max_pages: int) -> ListFetch:
        fetched = super().fetch(fetcher, source, max_pages=max_pages)
        if not fetched.entries:
            fetched.note = "portal page contained no document links; needs a column URL"
        return fetched


class RssListAdapter(GenericListAdapter):
    name = "rss"


class ListUnavailable(Exception):
    """Raised when the first list page cannot be fetched at all."""

    def __init__(self, result, note: str | None = None) -> None:
        super().__init__(note or result.error or f"http {result.status_code}")
        self.result = result
        self.note = note


_REGISTRY: dict[str, ListAdapter] = {
    "generic_list": GenericListAdapter(),
    "site_specific": JpaasListAdapter(),
    "open_api": OpenApiListAdapter(),
    "portal": PortalAdapter(),
    "rss": RssListAdapter(),
}


def resolve_adapter(source: SourceDefinition) -> ListAdapter:
    return _REGISTRY.get(source.adapter, _REGISTRY["generic_list"])


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _jpaas_params(html: str) -> dict[str, str] | None:
    tag = _UNITBUILD_RE.search(html)
    if not tag:
        return None
    attrs = {key: value for key, value in _ATTR_RE.findall(tag.group(0))}
    raw = attrs.get("queryData")
    if not raw:
        return None
    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        logger.info("unparsable jpaas queryData: %s", raw[:120])
        return None
    if not isinstance(parsed, dict):
        return None
    return {str(key): str(value) for key, value in parsed.items()}
