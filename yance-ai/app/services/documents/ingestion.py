import hashlib
from datetime import timedelta

import structlog
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Document,
    DocumentChunk,
    DocumentContent,
    DocumentFactCandidate,
    DocumentIngestionRun,
    now_utc,
)
from app.services.documents.intelligence import (
    EXTRACTION_VERSION,
    chunk_document,
    extract_company_intelligence,
)
from app.services.documents.parsers import PARSER_VERSION, parse_document
from app.services.documents.security import (
    ClamAVScanner,
    DocumentIngestionError,
    verify_signature,
)

logger = structlog.get_logger(__name__)


def queue_ingestion(
    db: Session, document: Document, *, requested_by=None, force: bool = False
) -> DocumentIngestionRun:
    latest = db.scalar(
        select(DocumentIngestionRun)
        .where(
            DocumentIngestionRun.document_id == document.id,
            DocumentIngestionRun.tenant_id == document.tenant_id,
        )
        .order_by(DocumentIngestionRun.attempt.desc())
        .limit(1)
    )
    if latest and latest.status in {"queued", "processing"}:
        return latest
    if latest and latest.status == "completed" and not force:
        return latest
    attempt = (latest.attempt if latest else 0) + 1
    if attempt > settings.document_ingestion_max_attempts:
        raise DocumentIngestionError(
            "attempt_limit", "Document ingestion retry limit has been reached"
        )
    run = DocumentIngestionRun(
        tenant_id=document.tenant_id,
        document_id=document.id,
        requested_by=requested_by,
        attempt=attempt,
        status="queued",
        parser_version=PARSER_VERSION,
    )
    document.status = "quarantined"
    document.ingestion_status = "pending"
    document.ingestion_error = None
    db.add(run)
    db.flush()
    return run


def claim_next_ingestion(db: Session) -> DocumentIngestionRun | None:
    now = now_utc()
    run = db.scalar(
        select(DocumentIngestionRun)
        .where(
            or_(
                DocumentIngestionRun.status == "queued",
                (
                    (DocumentIngestionRun.status == "processing")
                    & (DocumentIngestionRun.lease_expires_at < now)
                ),
            )
        )
        .order_by(DocumentIngestionRun.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not run:
        return None
    run.status = "processing"
    run.claimed_at = now
    run.started_at = run.started_at or now
    run.lease_expires_at = now + timedelta(seconds=settings.document_ingestion_lease_seconds)
    document = db.scalar(
        select(Document).where(
            Document.id == run.document_id, Document.tenant_id == run.tenant_id
        )
    )
    if document:
        document.ingestion_status = "processing"
    db.commit()
    db.refresh(run)
    return run


def _finish_error(
    db: Session,
    run: DocumentIngestionRun,
    document: Document,
    error: DocumentIngestionError,
) -> DocumentIngestionRun:
    now = now_utc()
    run.status = "ocr_required" if error.code == "ocr_required" else "failed"
    run.error_code = error.code
    run.safe_message = error.safe_message
    run.finished_at = now
    run.lease_expires_at = None
    run.metrics_json = {"retryable": error.retryable}
    document.ingestion_status = run.status
    document.ingestion_error = error.safe_message
    if error.code == "ocr_required":
        document.status = "needs_review"
    elif error.code in {
        "malware_detected",
        "signature_mismatch",
        "binary_text",
        "office_structure_invalid",
        "archive_entry_limit",
        "archive_expansion_limit",
        "archive_compression_ratio",
        "encrypted_archive",
        "encrypted_pdf",
    }:
        document.status = "rejected"
    else:
        document.status = "quarantined"
    db.commit()
    logger.warning(
        "document_ingestion_failed",
        run_id=str(run.id),
        tenant_id=str(run.tenant_id),
        document_id=str(document.id),
        error_code=error.code,
        retryable=error.retryable,
    )
    return run


def process_ingestion(
    db: Session,
    run_id,
    storage,
    *,
    scanner: ClamAVScanner | None = None,
    claimed: bool = False,
) -> DocumentIngestionRun:
    run = db.scalar(
        select(DocumentIngestionRun)
        .where(DocumentIngestionRun.id == run_id)
        .with_for_update()
    )
    if not run:
        raise LookupError("Document ingestion run not found")
    document = db.scalar(
        select(Document).where(
            Document.id == run.document_id, Document.tenant_id == run.tenant_id
        )
    )
    if not document:
        raise LookupError("Document not found")
    if run.status == "completed":
        return run
    now = now_utc()
    if (
        run.status == "processing"
        and run.lease_expires_at
        and run.lease_expires_at > now
        and not claimed
    ):
        return run
    run.status = "processing"
    run.started_at = run.started_at or now
    run.claimed_at = run.claimed_at or now
    run.lease_expires_at = now + timedelta(seconds=settings.document_ingestion_lease_seconds)
    document.ingestion_status = "processing"
    db.commit()
    try:
        payload = storage.read_bytes(document.object_key, settings.document_upload_max_bytes)
        if document.size_bytes is not None and len(payload) != document.size_bytes:
            raise DocumentIngestionError(
                "object_size_changed", "Stored document size changed after upload"
            )
        verify_signature(document.filename, document.content_type, payload)
        scan = (scanner or ClamAVScanner()).scan(payload)
        parsed = parse_document(document.filename, payload)
        chunks = chunk_document(parsed)
        candidates = extract_company_intelligence(parsed) if document.company_id else []

        content = db.scalar(
            select(DocumentContent).where(
                DocumentContent.document_id == document.id,
                DocumentContent.tenant_id == document.tenant_id,
            )
        )
        text_sha256 = hashlib.sha256(parsed.text.encode()).hexdigest()
        if not content:
            content = DocumentContent(
                tenant_id=document.tenant_id,
                document_id=document.id,
                parser=parsed.parser,
                parser_version=PARSER_VERSION,
                text=parsed.text,
                text_sha256=text_sha256,
                character_count=len(parsed.text),
                page_count=parsed.page_count,
                language="zh-or-mixed",
                metadata_json=parsed.metadata,
            )
            db.add(content)
        else:
            content.parser = parsed.parser
            content.parser_version = PARSER_VERSION
            content.text = parsed.text
            content.text_sha256 = text_sha256
            content.character_count = len(parsed.text)
            content.page_count = parsed.page_count
            content.metadata_json = parsed.metadata

        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.tenant_id == document.tenant_id,
            )
        )
        for chunk in chunks:
            db.add(DocumentChunk(tenant_id=document.tenant_id, document_id=document.id, **chunk))

        existing_hashes = set(
            db.scalars(
                select(DocumentFactCandidate.candidate_hash).where(
                    DocumentFactCandidate.document_id == document.id,
                    DocumentFactCandidate.tenant_id == document.tenant_id,
                )
            ).all()
        )
        for candidate in candidates:
            if candidate.candidate_hash in existing_hashes:
                continue
            db.add(
                DocumentFactCandidate(
                    tenant_id=document.tenant_id,
                    document_id=document.id,
                    company_id=document.company_id,
                    field_key=candidate.field_key,
                    value_json={"value": candidate.value},
                    confidence=candidate.confidence,
                    evidence_excerpt=candidate.evidence_excerpt,
                    source_locator_json=candidate.source_locator,
                    extraction_method="deterministic",
                    extraction_version=EXTRACTION_VERSION,
                    candidate_hash=candidate.candidate_hash,
                )
            )

        finished = now_utc()
        document.checksum_sha256 = hashlib.sha256(payload).hexdigest()
        document.status = "active"
        document.ingestion_status = "completed"
        document.ingestion_error = None
        document.ingested_at = finished
        document.metadata_json = {
            **(document.metadata_json or {}),
            "security_scan": {"status": scan.status, "engine": scan.engine},
            "parser": parsed.parser,
            "parser_version": PARSER_VERSION,
        }
        run.status = "completed"
        run.finished_at = finished
        run.lease_expires_at = None
        run.error_code = None
        run.safe_message = None
        run.metrics_json = {
            "bytes": len(payload),
            "characters": len(parsed.text),
            "chunks": len(chunks),
            "fact_candidates": len(candidates),
            "malware_scan": scan.status,
        }
        db.commit()
        db.refresh(run)
        logger.info(
            "document_ingestion_completed",
            run_id=str(run.id),
            tenant_id=str(run.tenant_id),
            document_id=str(document.id),
            parser=parsed.parser,
            character_count=len(parsed.text),
            chunk_count=len(chunks),
            candidate_count=len(candidates),
        )
        return run
    except DocumentIngestionError as error:
        db.rollback()
        run = db.scalar(select(DocumentIngestionRun).where(DocumentIngestionRun.id == run_id))
        document = db.scalar(
            select(Document).where(
                Document.id == run.document_id, Document.tenant_id == run.tenant_id
            )
        )
        return _finish_error(db, run, document, error)
    except Exception:
        db.rollback()
        run = db.scalar(select(DocumentIngestionRun).where(DocumentIngestionRun.id == run_id))
        document = db.scalar(
            select(Document).where(
                Document.id == run.document_id, Document.tenant_id == run.tenant_id
            )
        )
        return _finish_error(
            db,
            run,
            document,
            DocumentIngestionError(
                "ingestion_internal_error",
                "Document ingestion failed unexpectedly; retry is available",
                retryable=True,
            ),
        )


def latest_run(db: Session, document: Document) -> DocumentIngestionRun | None:
    return db.scalar(
        select(DocumentIngestionRun)
        .where(
            DocumentIngestionRun.document_id == document.id,
            DocumentIngestionRun.tenant_id == document.tenant_id,
        )
        .order_by(DocumentIngestionRun.attempt.desc())
        .limit(1)
    )


def ingestion_counts(db: Session, document: Document) -> dict[str, int]:
    return {
        "chunks": db.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.tenant_id == document.tenant_id,
            )
        )
        or 0,
        "fact_candidates": db.scalar(
            select(func.count())
            .select_from(DocumentFactCandidate)
            .where(
                DocumentFactCandidate.document_id == document.id,
                DocumentFactCandidate.tenant_id == document.tenant_id,
            )
        )
        or 0,
    }
