import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import AnalyticsEvent, Company, Document, UserRole
from app.schemas.schemas import (
    DocumentComplete,
    DocumentCreate,
    DocumentOut,
    PresignedUploadOut,
)
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
    return list(db.scalars(select(Document).where(Document.tenant_id == principal.tenant_id)).all())


@router.post("/presign-upload", response_model=PresignedUploadOut, status_code=201)
def presign_upload(
    payload: DocumentCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
    storage: OSSStorage = Depends(get_oss_storage),
) -> PresignedUploadOut:
    validate_upload(payload.filename, payload.content_type, payload.size_bytes)
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
    document = db.scalar(
        select(Document).where(
            Document.id == document_id, Document.tenant_id == principal.tenant_id
        )
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
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
    document.status = "uploaded"
    document.ingestion_status = "pending"
    document.ingestion_error = None
    document.size_bytes = actual_size
    db.add(
        AnalyticsEvent(
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
            name="document_uploaded",
            properties={"document_id": str(document.id)},
        )
    )
    db.commit()
    db.refresh(document)
    return document
