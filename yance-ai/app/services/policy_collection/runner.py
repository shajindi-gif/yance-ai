"""Single-source collection runner.

Design constraints honoured here
--------------------------------
* **No queue, no new micro-service.** One call = one bounded unit of work that
  the existing task system (APScheduler / CLI) can retry safely. All database
  writes are idempotent (see ``store``), so a retried run costs no duplicates and
  no embedding budget.
* **Per-hop URL control.** Every request (list page, detail page, redirect,
  attachment) goes through :class:`SafeFetcher`, which re-validates the hop
  against the source's allow-list, blocks private/metadata addresses and honours
  ``robots.txt`` plus per-host spacing.
* **Evidence before conclusions.** The raw page is written to disk before any
  parsing happens; if that write fails the document is *not* reported as
  complete evidence.
* **Three-way truth for "0 new items".** ``no_update`` (list fetched, nothing
  unseen) is reported separately from ``failed`` (list could not be fetched) and
  ``blocked`` (robots / SSRF / HTTP refusal) so an operator can tell a quiet day
  from a broken rule.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from app.services.documents.parsers import DocumentIngestionError, parse_document

from .adapters import ListUnavailable, resolve_adapter
from .catalog import SourceDefinition
from .classify import classify
from .extract import extract_document_page
from .fetch import FetchResult, SafeFetcher
from .fingerprint import normalize_text
from .rawstore import RawEvidenceStore
from .store import AttachmentPayload, DocumentPayload, PolicyStore, StoreResult, WindowPayload
from .urlguard import TargetPolicy

logger = logging.getLogger(__name__)

MIN_DOCUMENT_CHARS = 80
# A publication date in the future is almost always a parse mistake (year in an
# attachment name, a planned date in the body) - keep the page, drop the date.
MAX_FUTURE_PUBLISH_DAYS = 30
LIST_PURPOSES = {"list"}


@dataclass(frozen=True)
class CollectionLimits:
    max_pages_per_source: int = 3
    max_items_per_source: int = 20
    max_detail_bytes: int = 5_000_000
    max_attachment_bytes: int = 25_000_000
    max_attachments_per_doc: int = 12
    min_host_interval_seconds: float = 2.0
    request_timeout_seconds: float = 20.0
    max_retries: int = 2
    respect_robots: bool = True
    attachment_parse_enabled: bool = True

    @classmethod
    def from_settings(cls, settings) -> CollectionLimits:
        return cls(
            max_pages_per_source=settings.policy_collection_max_pages_per_source,
            max_items_per_source=settings.policy_collection_max_items_per_source,
            max_detail_bytes=settings.policy_collection_max_detail_bytes,
            max_attachment_bytes=settings.policy_collection_max_attachment_bytes,
            max_attachments_per_doc=settings.policy_collection_max_attachments_per_doc,
            min_host_interval_seconds=settings.policy_collection_min_host_interval_seconds,
            request_timeout_seconds=settings.policy_collection_request_timeout_seconds,
            max_retries=settings.policy_collection_max_retries,
            respect_robots=settings.policy_collection_respect_robots,
            attachment_parse_enabled=settings.policy_collection_attachment_parse_enabled,
        )


@dataclass
class ItemOutcome:
    url: str
    title: str = ""
    status: str = "stored"  # stored / unchanged / new_version / repost / parse_failed / fetch_failed
    change: str | None = None
    policy_id: str | None = None
    version: int | None = None
    error_kind: str | None = None
    error: str | None = None
    attachments_saved: int = 0
    attachments_failed: int = 0
    evidence_complete: bool = True


@dataclass
class SourceRunOutcome:
    source_id: str
    status: str  # success / no_update / partial / failed / blocked / paused
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trigger: str = "manual"
    pages_fetched: int = 0
    list_entries: int = 0
    new_documents: int = 0
    updated_documents: int = 0
    unchanged_documents: int = 0
    repost_documents: int = 0
    failed_documents: int = 0
    attachments_saved: int = 0
    attachments_failed: int = 0
    items: list[ItemOutcome] = field(default_factory=list)
    error_kind: str | None = None
    error: str | None = None
    adapter_used: str | None = None
    adapter_note: str | None = None
    duration_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.status in {"success", "no_update", "partial"}

    @property
    def zero_reason(self) -> str | None:
        """Why a run produced nothing new.

        A dashboard showing "0 new" must not conflate three different situations:
        nothing changed, the list rule stopped matching (``empty_list``), or the
        site failed. Only the first one means "the source is quiet".
        """
        if self.new_documents or self.updated_documents or self.repost_documents:
            return None
        if self.error_kind in {"empty_list", "selector_miss"}:
            return "rule_broken"
        if self.status in {"failed", "blocked"} or self.error_kind in {
            "all_documents_failed",
            "runner_exception",
            "robots",
            "blocked",
            "network",
            "timeout",
        }:
            return "fetch_failed"
        if self.status == "paused":
            return "paused"
        return "no_change"

    def summary(self) -> dict:
        return {
            "source_id": self.source_id,
            "run_id": self.run_id,
            "status": self.status,
            "pages_fetched": self.pages_fetched,
            "list_entries": self.list_entries,
            "new": self.new_documents,
            "updated": self.updated_documents,
            "unchanged": self.unchanged_documents,
            "repost": self.repost_documents,
            "failed": self.failed_documents,
            "attachments_saved": self.attachments_saved,
            "attachments_failed": self.attachments_failed,
            "error_kind": self.error_kind,
            "error": self.error,
            "adapter_used": self.adapter_used,
            "adapter_note": self.adapter_note,
            "duration_ms": self.duration_ms,
        }


def _looks_like_document(title: str) -> bool:
    """Cheap pre-filter so navigation links never become policies.

    Deliberately broad: the content classifier decides the document kind later.
    We only drop obvious non-documents (column names, "more", image links).
    """
    stripped = title.strip()
    if len(stripped) < 8:
        return False
    noisy = ("更多", "首页", "上一页", "下一页", "返回", "登录", "注册", "网站地图", "English")
    if any(token == stripped for token in noisy):
        return False
    # Column/boilerplate titles that appear on every government portal. They pass
    # the length check, so they must be rejected by keyword or they get ingested
    # as "policies" whose body is a navigation page.
    # Deliberately narrow: only portal boilerplate that can never be a policy.
    # Words like "政策解读" or "年度报告" are excluded on purpose because they
    # legitimately appear inside real document titles.
    column_tokens = (
        "政府信息公开指南",
        "政府信息公开制度",
        "政府信息公开年报",
        "政府信息公开目录",
        "主动公开基本目录",
        "法定主动公开内容",
        "依申请公开",
        "机关简介",
        "无障碍浏览",
        "网站声明",
        "联系我们",
        "网站地图",
    )
    return not any(token in stripped for token in column_tokens)


class PolicyCollectionRunner:
    def __init__(
        self,
        *,
        store: PolicyStore,
        raw_store: RawEvidenceStore,
        limits: CollectionLimits | None = None,
        user_agent: str = "YancePolicyCollector/3.0",
        fetcher_factory=None,
        sleep=time.sleep,
        clock=time.monotonic,
    ) -> None:
        self.store = store
        self.raw_store = raw_store
        self.limits = limits or CollectionLimits()
        self.user_agent = user_agent
        self._fetcher_factory = fetcher_factory
        self._sleep = sleep
        self._clock = clock

    # ------------------------------------------------------------------ #
    # fetcher
    # ------------------------------------------------------------------ #
    def _build_fetcher(self, source: SourceDefinition, *, max_bytes: int) -> SafeFetcher:
        if self._fetcher_factory is not None:
            return self._fetcher_factory(source=source, max_bytes=max_bytes, limits=self.limits)
        policy = TargetPolicy(
            allowed_domains=tuple(source.allowed_domains) or (source.entry_host,),
            allowed_ports=tuple({80, 443, *source.allow_non_standard_ports}),
        )
        return SafeFetcher(
            target_policy=policy,
            user_agent=self.user_agent,
            max_bytes=max_bytes,
            timeout_seconds=self.limits.request_timeout_seconds,
            min_interval_seconds=max(
                self.limits.min_host_interval_seconds, source.request_interval_seconds
            ),
            max_retries=self.limits.max_retries,
            respect_robots=self.limits.respect_robots,
        )

    # ------------------------------------------------------------------ #
    # main entry
    # ------------------------------------------------------------------ #
    def run_source(
        self,
        source: SourceDefinition,
        *,
        trigger: str = "manual",
        run_id: str | None = None,
        max_items: int | None = None,
    ) -> SourceRunOutcome:
        started = self._clock()
        outcome = SourceRunOutcome(source_id=source.source_id, status="failed", trigger=trigger)
        if run_id:
            outcome.run_id = run_id
        if source.level not in {"national", "provincial", "municipal"}:
            outcome.status = "failed"
            outcome.error_kind = "invalid_source"
            outcome.error = f"unsupported level: {source.level}"
            return outcome
        if not source.enabled:
            outcome.status = "paused"
            outcome.error_kind = "disabled"
            outcome.error = source.notes or "source disabled in catalog"
            return outcome

        item_cap = min(max_items or self.limits.max_items_per_source, source.max_documents_per_run)
        fetcher = self._build_fetcher(source, max_bytes=self.limits.max_detail_bytes)

        try:
            entries = self._collect_entries(source, fetcher, outcome)
            if entries is None:  # list page unreachable
                outcome.duration_ms = int((self._clock() - started) * 1000)
                return outcome
            if not entries:
                outcome.status = "no_update"
                outcome.error_kind = "empty_list"
                outcome.error = "list page returned no candidate documents"
                outcome.duration_ms = int((self._clock() - started) * 1000)
                return outcome

            for entry_url, title_hint, date_hint in entries[:item_cap]:
                item = self._process_document(
                    source,
                    fetcher,
                    entry_url,
                    title_hint=title_hint,
                    date_hint=date_hint,
                    run_id=uuid.UUID(outcome.run_id),
                )
                outcome.items.append(item)
                self._tally(outcome, item)

            if outcome.failed_documents and (outcome.new_documents or outcome.updated_documents):
                outcome.status = "partial"
            elif outcome.failed_documents and not (
                outcome.new_documents or outcome.updated_documents or outcome.unchanged_documents
            ):
                outcome.status = "failed"
                outcome.error_kind = "all_documents_failed"
                outcome.error = "every candidate document failed to fetch or parse"
            elif outcome.new_documents or outcome.updated_documents or outcome.repost_documents:
                outcome.status = "success"
            else:
                outcome.status = "no_update"
        except Exception as exc:  # defensive: a runner bug must not kill the scheduler
            logger.exception("policy collection crashed for %s", source.source_id)
            outcome.status = "failed"
            outcome.error_kind = "runner_exception"
            outcome.error = f"{type(exc).__name__}: {exc}"
        finally:
            outcome.duration_ms = int((self._clock() - started) * 1000)
        return outcome

    # ------------------------------------------------------------------ #
    # list pages
    # ------------------------------------------------------------------ #
    def _collect_entries(
        self, source: SourceDefinition, fetcher: SafeFetcher, outcome: SourceRunOutcome
    ) -> list[tuple[str, str, object]] | None:
        """Fetch the list page(s) through the adapter registered for this source."""
        page_limit = min(self.limits.max_pages_per_source, max(1, source.max_pages))
        adapter = resolve_adapter(source)
        try:
            fetched = adapter.fetch(fetcher, source, max_pages=page_limit)
        except ListUnavailable as exc:
            self._record_fetch_failure(outcome, exc.result)
            if exc.note:
                outcome.error = f"{outcome.error}: {exc.note}" if outcome.error else exc.note
            return None

        outcome.pages_fetched += fetched.pages_fetched
        outcome.adapter_used = fetched.adapter_used
        if fetched.note:
            outcome.adapter_note = fetched.note

        entries: list[tuple[str, str, object]] = []
        seen: set[str] = set()
        for entry in fetched.entries:
            key = entry.url
            if key in seen or not _looks_like_document(entry.title):
                continue
            seen.add(key)
            entries.append((entry.url, entry.title, entry.date_hint))

        if not entries:
            outcome.status = "no_update"
            outcome.error_kind = "empty_list"
            outcome.error = (
                "list page returned no candidate documents "
                f"(adapter={fetched.adapter_used}, pages={fetched.pages_fetched})"
            )
            return []
        outcome.list_entries = len(entries)
        return entries

    @staticmethod
    def _record_fetch_failure(outcome: SourceRunOutcome, result: FetchResult) -> None:
        if result.robots_denied:
            outcome.status = "blocked"
            outcome.error_kind = "robots"
        elif result.error_kind == "blocked":
            outcome.status = "blocked"
            outcome.error_kind = "blocked"
        elif result.error_kind == "too_large":
            outcome.status = "failed"
            outcome.error_kind = "too_large"
        elif result.error_kind in {"timeout", "network"}:
            outcome.status = "failed"
            outcome.error_kind = result.error_kind
        else:
            outcome.status = "failed"
            outcome.error_kind = result.error_kind or "http"
        outcome.error = result.error or f"http {result.status_code}"

    # ------------------------------------------------------------------ #
    # detail pages
    # ------------------------------------------------------------------ #
    def _process_document(
        self,
        source: SourceDefinition,
        fetcher: SafeFetcher,
        url: str,
        *,
        title_hint: str,
        date_hint,
        run_id: uuid.UUID | None,
    ) -> ItemOutcome:
        item = ItemOutcome(url=url, title=title_hint)
        result = fetcher.get(url, purpose="document")
        if not result.ok:
            item.status = "fetch_failed"
            item.error_kind = result.error_kind or ("http" if result.status_code else "unknown")
            item.error = result.error or f"http {result.status_code}"
            item.evidence_complete = False
            return item
        fetched_at = datetime.now(UTC)
        try:
            stored = self.raw_store.save(
                source_id=source.source_id,
                url=result.final_url,
                payload=result.content,
                content_type=result.content_type,
                fetched_at=fetched_at,
            )
        except OSError as exc:
            # Evidence cannot be secured -> do not pretend the document is完整证据.
            logger.warning("raw evidence write failed for %s: %s", url, exc)
            stored = None

        html = result.text
        page = extract_document_page(html, result.final_url)
        title = page.title or title_hint
        text = page.text
        published_at = page.published_at or date_hint
        rejected_date = None
        if published_at and published_at > date.today() + timedelta(days=MAX_FUTURE_PUBLISH_DAYS):
            # Never let a bad date become a policy deadline or a filter value.
            rejected_date = published_at.isoformat()
            logger.warning(
                "rejected implausible publish date %s for %s (source=%s)",
                rejected_date,
                result.final_url,
                source.source_id,
            )
            published_at = None
            item.error_kind = "publish_date_suspect"
        if len(normalize_text(text)) < MIN_DOCUMENT_CHARS:
            item.status = "parse_failed"
            item.title = title
            item.error_kind = "empty_content"
            item.error = f"extracted text too short ({len(text)} chars)"
            item.evidence_complete = stored is not None
            self._store_evidence_only(source, result, stored, page, run_id, item)
            return item

        classification = classify(title, text)
        attachments = self._collect_attachments(source, fetcher, page.attachments)
        windows = tuple(
            WindowPayload(
                label=window.batch,
                start_date=window.start,
                end_date=window.end,
                entry_url=None,
                evidence_text=window.evidence,
            )
            for window in classification.application_windows
        )
        payload = DocumentPayload(
            source=source,
            run_id=run_id,
            url=result.final_url,
            requested_url=url,
            title=title or url,
            text=text,
            classification=classification,
            published_at=published_at,
            doc_number=page.doc_number,
            issuer=source.authority,
            http_meta={
                "content_type": result.content_type,
                "byte_size": len(result.content),
                "host": source.entry_host,
                "attempts": result.attempts,
                "redirects": result.redirects,
                "elapsed_ms": result.elapsed_ms,
                **({"publish_date_rejected": rejected_date} if rejected_date else {}),
            },
            http_status=result.status_code,
            content_sha256=stored.sha256
            if stored
            else hashlib.sha256(result.content).hexdigest(),
            storage_path=stored.path if stored else None,
            evidence_complete=stored is not None,
            attachments=tuple(attachments),
            windows=windows,
        )
        try:
            store_result: StoreResult = self.store.save_document(payload)
        except Exception as exc:
            logger.exception("persist failed for %s", url)
            item.status = "parse_failed"
            item.error_kind = "store_error"
            item.error = f"{type(exc).__name__}: {exc}"
            return item

        item.title = title
        item.policy_id = str(store_result.policy_id)
        item.version = store_result.version
        item.change = store_result.change.value
        item.attachments_saved = store_result.attachments_saved
        item.attachments_failed = store_result.attachments_failed
        item.evidence_complete = stored is not None
        item.status = _status_for(store_result.change)
        return item

    def _store_evidence_only(
        self,
        source: SourceDefinition,
        result: FetchResult,
        stored,
        page,
        run_id: uuid.UUID | None,
        item: ItemOutcome,
    ) -> None:
        """Keep the raw page of an unparseable document for later manual review."""
        logger.info(
            "policy unparsed document kept as evidence: source=%s url=%s path=%s",
            source.source_id,
            result.final_url,
            stored.path if stored else None,
        )

    # ------------------------------------------------------------------ #
    # attachments
    # ------------------------------------------------------------------ #
    def _collect_attachments(self, source, fetcher, links) -> list[AttachmentPayload]:
        payloads: list[AttachmentPayload] = []
        for link in list(links)[: self.limits.max_attachments_per_doc]:
            result = fetcher.get(link.url, purpose="attachment")
            if not result.ok:
                payloads.append(
                    AttachmentPayload(
                        url=link.url,
                        filename=link.filename,
                        parse_status="failed",
                        error=result.error or f"http {result.status_code}",
                    )
                )
                continue
            if len(result.content) > self.limits.max_attachment_bytes:
                payloads.append(
                    AttachmentPayload(
                        url=link.url,
                        filename=link.filename,
                        content_type=result.content_type,
                        byte_size=len(result.content),
                        parse_status="failed",
                        error="attachment exceeds size limit",
                    )
                )
                continue
            try:
                stored = self.raw_store.save(
                    source_id=source.source_id,
                    url=result.final_url,
                    payload=result.content,
                    content_type=result.content_type,
                    fetched_at=datetime.now(UTC),
                )
            except OSError as exc:
                payloads.append(
                    AttachmentPayload(
                        url=link.url,
                        filename=link.filename,
                        content_type=result.content_type,
                        byte_size=len(result.content),
                        parse_status="failed",
                        error=f"storage error: {exc}",
                    )
                )
                continue

            parse_status = "stored"
            parser_name = None
            extracted_chars = 0
            error = None
            if self.limits.attachment_parse_enabled:
                try:
                    parsed = parse_document(link.filename or "attachment", result.content)
                    parse_status = "parsed"
                    parser_name = parsed.parser
                    extracted_chars = len(parsed.text)
                except DocumentIngestionError as exc:
                    # DocumentIngestionError carries ``code``/``safe_message``; a
                    # corrupt attachment must degrade to "stored, unparsed" rather
                    # than abort the whole source run.
                    parse_status = "failed" if exc.code != "unsupported_type" else "unsupported"
                    error = f"{exc.code}: {exc.safe_message}"
                except Exception as exc:  # pragma: no cover - parser edge cases
                    parse_status = "failed"
                    error = f"{type(exc).__name__}: {exc}"
            payloads.append(
                AttachmentPayload(
                    url=result.final_url,
                    filename=link.filename,
                    content_type=result.content_type,
                    byte_size=len(result.content),
                    content_sha256=stored.sha256,
                    storage_path=stored.path,
                    parser_name=parser_name,
                    parse_status=parse_status,
                    extracted_text_chars=extracted_chars,
                    error=error,
                )
            )
        return payloads

    # ------------------------------------------------------------------ #
    @staticmethod
    def _tally(outcome: SourceRunOutcome, item: ItemOutcome) -> None:
        outcome.attachments_saved += item.attachments_saved
        outcome.attachments_failed += item.attachments_failed
        if item.status == "stored":
            outcome.new_documents += 1
        elif item.status in {"new_version", "updated"}:
            outcome.updated_documents += 1
        elif item.status == "unchanged":
            outcome.unchanged_documents += 1
        elif item.status == "repost":
            outcome.repost_documents += 1
        else:
            outcome.failed_documents += 1


def _status_for(change) -> str:
    value = change.value
    if value == "new":
        return "stored"
    if value in {"new_version", "repost_updated"}:
        return "new_version"
    if value in {"repost_new_source"}:
        return "repost"
    return "unchanged"


def run_sources(
    sources: Sequence[SourceDefinition],
    *,
    store: PolicyStore,
    raw_store: RawEvidenceStore,
    limits: CollectionLimits | None = None,
    user_agent: str = "YancePolicyCollector/3.0",
    trigger: str = "cron",
    stop_on_failure_streak: int = 5,
    max_sources: int | None = None,
) -> list[SourceRunOutcome]:
    """Run several sources sequentially; a failure streak trips the breaker."""
    runner = PolicyCollectionRunner(
        store=store, raw_store=raw_store, limits=limits, user_agent=user_agent
    )
    outcomes: list[SourceRunOutcome] = []
    streak = 0
    for source in sources:
        if max_sources is not None and len(outcomes) >= max_sources:
            break
        outcome = runner.run_source(source, trigger=trigger)
        outcomes.append(outcome)
        if outcome.status in {"failed", "blocked"}:
            streak += 1
            if stop_on_failure_streak and streak >= stop_on_failure_streak:
                logger.warning(
                    "policy collection circuit breaker tripped after %s consecutive failures",
                    streak,
                )
                break
        else:
            streak = 0
    return outcomes
