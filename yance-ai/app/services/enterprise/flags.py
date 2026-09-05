from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import FeatureFlag, TenantFeatureFlag


def effective_flags(db: Session, tenant_id) -> dict[str, bool]:
    rows = db.execute(
        select(FeatureFlag, TenantFeatureFlag)
        .outerjoin(
            TenantFeatureFlag,
            (TenantFeatureFlag.feature_flag_id == FeatureFlag.id)
            & (TenantFeatureFlag.tenant_id == tenant_id),
        )
        .where(FeatureFlag.status == "active")
        .order_by(FeatureFlag.key)
    ).all()
    return {
        flag.key: override.enabled if override is not None else flag.enabled_by_default
        for flag, override in rows
    }
