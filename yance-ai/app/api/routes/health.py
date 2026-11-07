import os

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


@router.get('/api/v1/system/version')
def runtime_version(db: Session = Depends(get_db)) -> dict:
    """Read deployment identity and the database revision independently."""
    revisions = db.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    return {"application_version": settings.app_version,
            "source_revision": os.environ.get("APP_SOURCE_REVISION", "unrecorded"),
            "database_revisions": sorted(revisions)}
