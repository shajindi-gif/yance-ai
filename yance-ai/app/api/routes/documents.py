import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import (
    Company,
    Document,
    DocumentContent,
    DocumentFactCandidate,
    DocumentIngestionRun,
    UserRole,
    now_utc,
)
from app.schemas.schemas import (
    CompanyProfileData,
    DocumentCandidateReview,
    DocumentCandidateReviewResult,
    DocumentComplete,
    DocumentCreate,
    DocumentDetail,
    DocumentIngestRequest,
    DocumentOut,
    DocumentUrlImport,
    PresignedUploadOut,
)
from app.services.analytics.events import record_event
from app.services.billing.usage import QuotaExceeded, ensure_capacity
from app.services.company_profiles import get_or_create_company_profile, profile_completeness
from app.services.documents.ingestion import ingestion_counts, process_ingestion, queue_ingestion
from app.services.documents.security import DocumentIngestionError
from app.services.documents.url_fetcher import SafeURLFetcher, get_safe_url_fetcher
from app.services.enterprise.audit import record_audit
from app.services.oss import OSSStorage, get_oss_storage

router = APIRouter(prefix="/documents", tags=["document"])

ALLOWED_UPLOAD_TYPES = {
    ".csv": {"application/csv", "application/vnd.ms-excel", "text/csv"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:180] or "upload.bin"


def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    extension = Path(filename).suffix.lower()
    if content_type.lower() not in ALLOWED_UPLOAD_TYPES.get(extension, set()):
        raise HTTPException(status_code=415, detail="Unsupported document type")
    if size_bytes > settings.document_upload_max_bytes:
        raise HTTPException(status_code=413, detail="Document exceeds the upload size limit")


@router.get("", response_model=list[DocumentOut])
def list_documents(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.tenant_id == principal.tenant_id)
            .order_by(Document.created_at.desc())
        ).all()
    )


def _url_error_status(error: DocumentIngestionError) -> int:
    if error.code == "url_size_limit":
        return 413
    if error.code == "url_content_type":
        return 415
    if error.retryable:
        return 502
    return 400


@router.post("/url", response_model=DocumentDetail, status_code=201)
def import_document_url(
    payload: DocumentUrlImport,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
    storage: OSSStorage = Depends(get_oss_storage),
    fetcher: SafeURLFetcher = Depends(get_safe_url_fetcher),
):
    company = db.scalar(
        select(Company).where(
            Company.id == payload.company_id, Company.tenant_id == principal.tenant_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        ensure_capacity(db, tenant_id=principal.tenant_id, meter="documents")
        fetched = fetcher.fetch(payload.url)
        ensure_capacity(
            db,
            tenant_id=principal.tenant_id,
            meter="storage_bytes",
            requested=len(fetched.payload),
        )
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.detail()) from exc
    except DocumentIngestionError as exc:
        raise HTTPException(status_code=_url_error_status(exc), detail=exc.safe_message) from exc

    object_key = (
        f"tenants/{principal.tenant_id}/documents/{uuid.uuid4()}/{safe_filename(fetched.filename)}"
    )
    try:
        storage.put_bytes(object_key, fetched.payload, fetched.content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Web document could not be stored") from exc
    document = Document(
        tenant_id=principal.tenant_id,
        company_id=company.id,
        filename=fetched.filename,
        content_type=fetched.content_type,
        object_key=object_key,
        status="quarantined",
        size_bytes=len(fetched.payload),
        source_type="url",
        ingestion_status="pending",
        metadata_json={
            "source_url": fetched.source_url,
            "final_url": fetched.final_url,
            "redirects": fetched.redirects,
        },
    )
    db.add(document)
    db.flush()
    run = queue_ingestion(db, document, requested_by=principal.user.id)
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="document_uploaded",
        event_key=f"document_uploaded:{document.id}",
        properties={"document_id": str(document.id), "source_type": "url"},
    )
    db.commit()
    processed = process_ingestion(db, run.id, storage)
    db.refresh(document)
    record_audit(
        db,
        tenant_id=principal.tenant_id,
        actor_user_id=principal.user.id,
        action="document.url_imported",
        resource_type="document",
        resource_id=str(document.id),
        result="success" if processed.status == "completed" else "failed",
        reason=document.ingestion_error,
        details={
            "source_host": urlsplit(fetched.source_url).hostname,
            "redirects": fetched.redirects,
            "ingestion_status": document.ingestion_status,
        },
    )
    db.commit()
    return _document_detail(db, document)


def _tenant_document(db: Session, document_id: UUID, tenant_id: UUID) -> Document:
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _document_detail(db: Session, document: Document) -> dict:
    content = db.scalar(
        select(DocumentContent).where(
            DocumentContent.document_id == document.id,
            DocumentContent.tenant_id == document.tenant_id,
        )
    )
    candidates = list(
        db.scalars(
            select(DocumentFactCandidate)
            .where(
                DocumentFactCandidate.document_id == document.id,
                DocumentFactCandidate.tenant_id == document.tenant_id,
            )
            .order_by(DocumentFactCandidate.created_at, DocumentFactCandidate.field_key)
        ).all()
    )
    runs = list(
        db.scalars(
            select(DocumentIngestionRun)
            .where(
                DocumentIngestionRun.document_id == document.id,
                DocumentIngestionRun.tenant_id == document.tenant_id,
            )
            .order_by(DocumentIngestionRun.attempt.desc())
        ).all()
    )
    counts = ingestion_counts(db, document)
    content_summary = None
    if content:
        content_summary = {
            "parser": content.parser,
            "parser_version": content.parser_version,
            "text_sha256": content.text_sha256,
            "character_count": content.character_count,
            "page_count": content.page_count,
            "language": content.language,
            "metadata_json": content.metadata_json,
            "preview": content.text[:500],
        }
    return {
        "document": document,
        "content": content_summary,
        "chunk_count": counts["chunks"],
        "candidates": candidates,
        "ingestion_runs": runs,
    }


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return _document_detail(db, _tenant_document(db, document_id, principal.tenant_id))


@router.post("/presign-upload", response_model=PresignedUploadOut, status_code=201)
def presign_upload(
    payload: DocumentCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
    storage: OSSStorage = Depends(get_oss_storage),
) -> PresignedUploadOut:
    validate_upload(payload.filename, payload.content_type, payload.size_bytes)
    try:
        ensure_capacity(db, tenant_id=principal.tenant_id, meter="documents")
        ensure_capacity(
            db,
            tenant_id=principal.tenant_id,
            meter="storage_bytes",
            requested=payload.size_bytes,
        )
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.detail()) from exc
    if payload.checksum_sha256:
        raise HTTPException(
            status_code=400,
            detail="Client-authored checksums are not accepted as verified checksums",
        )
    if payload.company_id and not db.scalar(
        select(Company.id).where(
            Company.id == payload.company_id, Company.tenant_id == principal.tenant_id
        )
    ):
        raise HTTPException(status_code=404, detail="Company not found")
    object_key = (
        f"tenants/{principal.tenant_id}/documents/{uuid.uuid4()}/{safe_filename(payload.filename)}"
    )
    document = Document(
        tenant_id=principal.tenant_id,
        object_key=object_key,
        **payload.model_dump(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return PresignedUploadOut(
        document=document,
        upload_url=storage.presign_put(object_key, payload.content_type),
        expires_in=settings.oss_presign_expire_seconds,
        required_headers={"Content-Type": payload.content_type},
    )


@router.post("/{document_id}/complete", response_model=DocumentOut)
def complete_upload(
    document_id: UUID,
    payload: DocumentComplete,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
    storage: OSSStorage = Depends(get_oss_storage),
) -> Document:
    document = _tenant_document(db, document_id, principal.tenant_id)
    if document.status != "pending_upload":
        if document.status == "rejected":
            raise HTTPException(status_code=409, detail="Rejected document cannot be completed")
        return document
    if not storage.exists(document.object_key):
        raise HTTPException(status_code=409, detail="Object does not exist in OSS")
    actual_size = storage.object_size(document.object_key)
    if actual_size != document.size_bytes or actual_size > settings.document_upload_max_bytes:
        document.status = "rejected"
        db.commit()
        raise HTTPException(status_code=409, detail="Uploaded object size does not match request")
    if payload.checksum_sha256:
        raise HTTPException(
            status_code=400,
            detail="Client-authored checksums are not accepted as verified checksums",
        )
    document.status = "quarantined"
    document.size_bytes = actual_size
    queue_ingestion(db, document, requested_by=principal.user.id)
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="document_uploaded",
        event_key=f"document_uploaded:{document.id}",
        properties={"document_id": str(document.id)},
    )
    db.commit()
    db.refresh(document)
    return document


@router.post("/{document_id}/ingest", response_model=DocumentDetail)
def ingest_document(
    document_id: UUID,
    payload: DocumentIngestRequest,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
    storage: OSSStorage = Depends(get_oss_storage),
):
    document = _tenant_document(db, document_id, principal.tenant_id)
    if document.status == "pending_upload":
        raise HTTPException(status_code=409, detail="Document upload is not complete")
    try:
        run = queue_ingestion(
            db, document, requested_by=principal.user.id, force=payload.force
        )
    except DocumentIngestionError as exc:
        raise HTTPException(status_code=409, detail=exc.safe_message) from exc
    db.commit()
    if run.status == "completed":
        return _document_detail(db, document)
    processed = process_ingestion(db, run.id, storage)
    db.refresh(document)
    if processed.status == "processing":
        return _document_detail(db, document)
    record_audit(
        db,
        tenant_id=principal.tenant_id,
        actor_user_id=principal.user.id,
        action="document.ingestion_executed",
        resource_type="document",
        resource_id=str(document.id),
        result="success" if document.ingestion_status == "completed" else "failed",
        reason=document.ingestion_error,
        details={"ingestion_status": document.ingestion_status},
    )
    db.commit()
    return _document_detail(db, document)


@router.post(
    "/{document_id}/facts/review",
    response_model=DocumentCandidateReviewResult,
)
def review_document_facts(
    document_id: UUID,
    payload: DocumentCandidateReview,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    document = _tenant_document(db, document_id, principal.tenant_id)
    if not document.company_id:
        raise HTTPException(status_code=409, detail="Document is not associated with a company")
    decision_ids = [item.candidate_id for item in payload.decisions]
    if len(set(decision_ids)) != len(decision_ids):
        raise HTTPException(status_code=422, detail="Each candidate may be reviewed only once per request")
    candidates = list(
        db.scalars(
            select(DocumentFactCandidate).where(
                DocumentFactCandidate.id.in_(decision_ids),
                DocumentFactCandidate.document_id == document.id,
                DocumentFactCandidate.company_id == document.company_id,
                DocumentFactCandidate.tenant_id == principal.tenant_id,
            )
        ).all()
    )
    candidate_map = {item.id: item for item in candidates}
    if len(candidate_map) != len(decision_ids):
        raise HTTPException(status_code=404, detail="One or more fact candidates were not found")
    company = db.scalar(
        select(Company).where(
            Company.id == document.company_id, Company.tenant_id == principal.tenant_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    profile = get_or_create_company_profile(db, company)
    draft = dict(profile.draft_json or {})
    accepted = 0
    rejected = 0
    now = now_utc()
    for decision in payload.decisions:
        candidate = candidate_map[decision.candidate_id]
        if candidate.status != "pending_review":
            raise HTTPException(status_code=409, detail="Fact candidate was already reviewed")
        value_json = decision.value_json or candidate.value_json
        if set(value_json) != {"value"}:
            raise HTTPException(status_code=422, detail="Reviewed fact must contain exactly one value")
        if decision.decision == "accept":
            value = value_json["value"]
            if candidate.field_key in {"intellectual_property", "core_products", "projects", "current_needs"}:
                current = draft.get(candidate.field_key) or []
                incoming = value if isinstance(value, list) else [value]
                draft[candidate.field_key] = list(dict.fromkeys([*current, *incoming]))
            else:
                draft[candidate.field_key] = value
            candidate.value_json = {"value": value}
            candidate.status = "accepted"
            accepted += 1
        else:
            candidate.status = "rejected"
            rejected += 1
        candidate.reviewed_by = principal.user.id
        candidate.reviewed_at = now
    try:
        validated = CompanyProfileData.model_validate(draft).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Reviewed facts do not fit the company profile") from exc
    profile.draft_json = validated
    profile.completeness_score = profile_completeness(validated)
    profile.status = "draft"
    company.industry = validated.get("industry")
    company.province = validated.get("province")
    company.city = validated.get("city")
    record_audit(
        db,
        tenant_id=principal.tenant_id,
        actor_user_id=principal.user.id,
        action="document.facts_reviewed",
        resource_type="document",
        resource_id=str(document.id),
        details={"accepted": accepted, "rejected": rejected},
    )
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="company_intelligence_reviewed",
        event_key=f"company_intelligence_reviewed:{document.id}:{now.isoformat()}",
        properties={"document_id": str(document.id), "accepted": accepted, "rejected": rejected},
    )
    db.commit()
    db.refresh(profile)
    return {"accepted": accepted, "rejected": rejected, "profile": profile}
