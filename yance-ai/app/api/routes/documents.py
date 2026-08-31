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
from app.models.models import Company, Document, UserRole
from app.schemas.schemas import (
    DocumentComplete,
    DocumentCreate,
    DocumentOut,
    PresignedUploadOut,
)
from app.services.oss import OSSStorage, get_oss_storage

router = APIRouter(prefix="/documents", tags=["document"])


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:180] or "upload.bin"


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
    document.status = "uploaded"
    document.checksum_sha256 = payload.checksum_sha256
    db.commit()
    db.refresh(document)
    return document
