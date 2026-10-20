"""Deadline-driven notifications (T-30/14/7/3/1) and notification helpers.

Scans applications with due dates, opportunities whose policy deadline is
approaching, and overdue milestones; emits deduplicated in-app notifications.
Deterministic by design: no LLM, no invented dates — only existing records.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Application, Milestone, Notification, Opportunity, Policy

# Urgency bands, tightest first. A notification is emitted when the remaining
# time first enters a band; the dedup key includes the band so the next tighter
# band produces exactly one new notification.
DEADLINE_BANDS = (30, 14, 7, 3, 1)


def now_utc() -> datetime:
    return datetime.now(UTC)


def _band_for(days_left: float) -> int | None:
    for band in sorted(DEADLINE_BANDS):
        if days_left <= band:
            return band
    return None


def _severity_for(band: int) -> str:
    if band <= 3:
        return "critical"
    if band <= 7:
        return "warning"
    return "info"


def add_notification(
    db: Session,
    *,
    tenant_id,
    kind: str,
    title: str,
    body: str | None = None,
    dedup_key: str,
    severity: str = "info",
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id=None,
) -> bool:
    """Insert a notification unless the dedup key already exists. Returns True on insert."""
    exists = db.scalar(
        select(Notification.id).where(
            Notification.tenant_id == tenant_id, Notification.dedup_key == dedup_key
        )
    )
    if exists:
        return False
    db.add(
        Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            kind=kind,
            severity=severity,
            title=title[:300],
            body=body,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            dedup_key=dedup_key[:200],
        )
    )
    return True


def scan_deadlines(db: Session, *, tenant_id=None, now: datetime | None = None) -> int:
    """Create deadline-band notifications for one tenant (or all tenants). Returns created count."""
    ref = now or now_utc()
    created = 0

    app_stmt = select(Application).where(
        Application.due_at.is_not(None),
        Application.status.notin_(["submitted", "completed", "cancelled"]),
    )
    if tenant_id:
        app_stmt = app_stmt.where(Application.tenant_id == tenant_id)
    for application in db.scalars(app_stmt).all():
        due = application.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        days_left = (due - ref).days + (due - ref).seconds / 86400
        if days_left < 0:
            band = 0  # overdue
        else:
            band = _band_for(days_left)
            if band is None:
                continue
        severity = "critical" if band == 0 else _severity_for(band)
        days_display = max(0, round(days_left))
        label = (
            f"申报「{application.title}」已逾期"
            if band == 0
            else f"申报「{application.title}」还有 {days_display} 天截止"
        )
        key = f"deadline:application:{application.id}:{'overdue' if band == 0 else f'T-{band}'}"
        if add_notification(
            db,
            tenant_id=application.tenant_id,
            kind="deadline",
            severity=severity,
            title=label,
            body=f"截止时间：{due.strftime('%Y-%m-%d %H:%M UTC')}。请确认材料是否已就绪。",
            dedup_key=key,
            entity_type="application",
            entity_id=application.id,
            user_id=application.owner_user_id,
        ):
            created += 1

    opp_stmt = (
        select(Opportunity, Policy)
        .join(Policy, Opportunity.policy_id == Policy.id)
        .where(
            Policy.deadline.is_not(None),
            Opportunity.status.notin_(["dismissed", "expired"]),
        )
    )
    if tenant_id:
        opp_stmt = opp_stmt.where(Opportunity.tenant_id == tenant_id)
    for opportunity, policy in db.execute(opp_stmt).all():
        due = policy.deadline
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        if due < ref:
            continue  # policy window already closed; no nagging for past deadlines
        band = _band_for((due - ref).days + (due - ref).seconds / 86400)
        if band is None:
            continue
        days_left = max(1, round((due - ref).total_seconds() / 86400))
        if add_notification(
            db,
            tenant_id=opportunity.tenant_id,
            kind="deadline",
            severity=_severity_for(band),
            title=f"政策「{opportunity.title}」申报截止还有 {days_left} 天",
            body=f"官方截止：{due.strftime('%Y-%m-%d')}。尚未开始准备可先到机会详情创建申报。",
            dedup_key=f"deadline:opportunity:{opportunity.id}:T-{band}",
            entity_type="opportunity",
            entity_id=opportunity.id,
        ):
            created += 1

    mile_stmt = select(Milestone).where(
        Milestone.due_at.is_not(None),
        Milestone.status.notin_(["done"]),
    )
    if tenant_id:
        mile_stmt = mile_stmt.where(Milestone.tenant_id == tenant_id)
    for milestone in db.scalars(mile_stmt).all():
        due = milestone.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        if due >= ref - timedelta(days=1):
            continue  # overdue notifications only, one per milestone
        application = db.get(Application, milestone.application_id)
        if add_notification(
            db,
            tenant_id=milestone.tenant_id,
            kind="deadline",
            severity="warning",
            title=f"里程碑「{milestone.title}」已逾期",
            body=(
                f"所属申报：{application.title if application else '未知'}。"
                f"计划完成时间 {due.strftime('%Y-%m-%d')}。"
            ),
            dedup_key=f"milestone:overdue:{milestone.id}",
            entity_type="milestone",
            entity_id=milestone.id,
            user_id=milestone.owner_user_id,
        ):
            created += 1

    if created:
        db.commit()
    return created
