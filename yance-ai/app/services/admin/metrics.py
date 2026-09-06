from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Date, cast, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.models import (
    AgentRun,
    AgentRunError,
    AnalyticsEvent,
    Application,
    ApplicationArtifact,
    Company,
    DemoScenario,
    Document,
    DocumentIngestionRun,
    EvalDatasetVersion,
    EvalRun,
    Feedback,
    Order,
    Policy,
    PolicyScan,
    Tenant,
    User,
    WorkflowRun,
)

FUNNEL_STEPS = (
    ("signup_completed", "注册完成"),
    ("company_profile_completed", "企业画像完成"),
    ("policy_scan_completed", "政策扫描完成"),
    ("application_created", "创建申报项目"),
    ("document_generated", "生成申报文件"),
    ("payment_completed", "完成支付"),
)


def _count(db: Session, model, *criteria) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)


def _real_tenant_count(db: Session, model, *criteria) -> int:
    if model is Tenant:
        return _count(db, Tenant, Tenant.is_demo.is_(False), *criteria)
    return int(
        db.scalar(
            select(func.count())
            .select_from(model)
            .join(Tenant, model.tenant_id == Tenant.id)
            .where(Tenant.is_demo.is_(False), *criteria)
        )
        or 0
    )


def _money(value) -> float:
    return float(value or Decimal("0"))


def _real_policy_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Policy)
            .outerjoin(Tenant, Policy.tenant_id == Tenant.id)
            .where(or_(Policy.tenant_id.is_(None), Tenant.is_demo.is_(False)))
        )
        or 0
    )


def investor_metrics(db: Session) -> dict:
    now = datetime.now(UTC)
    active_since = now - timedelta(days=30)
    total_runs = _real_tenant_count(db, AgentRun)
    llm_cost = _money(
        db.scalar(
            select(func.coalesce(func.sum(AgentRun.cost_usd), 0))
            .join(Tenant, AgentRun.tenant_id == Tenant.id)
            .where(Tenant.is_demo.is_(False))
        )
    )

    revenue_rows = db.execute(
        select(Order.currency, func.coalesce(func.sum(Order.amount), 0))
        .join(Tenant, Order.tenant_id == Tenant.id)
        .where(Order.status == "paid", Tenant.is_demo.is_(False))
        .group_by(Order.currency)
        .order_by(Order.currency)
    ).all()
    funnel_counts = dict(
        db.execute(
            select(AnalyticsEvent.name, func.count(distinct(AnalyticsEvent.tenant_id)))
            .join(Tenant, AnalyticsEvent.tenant_id == Tenant.id)
            .where(
                AnalyticsEvent.name.in_([name for name, _ in FUNNEL_STEPS]),
                AnalyticsEvent.source == "server",
                Tenant.is_demo.is_(False),
            )
            .group_by(AnalyticsEvent.name)
        ).all()
    )
    funnel = []
    previous = None
    for event_name, label in FUNNEL_STEPS:
        organizations = int(funnel_counts.get(event_name, 0))
        conversion = None if previous in {None, 0} else round(organizations / previous, 4)
        funnel.append(
            {
                "event": event_name,
                "label": label,
                "organizations": organizations,
                "conversion_from_previous": conversion,
            }
        )
        previous = organizations

    trend_rows = db.execute(
        select(
            cast(AgentRun.created_at, Date).label("day"),
            func.count(AgentRun.id),
            func.count(AgentRun.id).filter(AgentRun.status == "completed"),
            func.count(AgentRun.id).filter(AgentRun.status == "failed"),
            func.coalesce(func.sum(AgentRun.cost_usd), 0),
        )
        .join(Tenant, AgentRun.tenant_id == Tenant.id)
        .where(AgentRun.created_at >= active_since, Tenant.is_demo.is_(False))
        .group_by("day")
        .order_by("day")
    ).all()
    trend_by_day = {
        row[0]: {
            "date": row[0].isoformat(),
            "runs": int(row[1]),
            "successful": int(row[2]),
            "failed": int(row[3]),
            "cost_usd": _money(row[4]),
        }
        for row in trend_rows
    }
    trend = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date()
        trend.append(
            trend_by_day.get(
                day,
                {"date": day.isoformat(), "runs": 0, "successful": 0, "failed": 0, "cost_usd": 0},
            )
        )

    reviewed_evaluation_runs = int(
        db.scalar(
            select(func.count(distinct(EvalRun.eval_type)))
            .join(EvalDatasetVersion, EvalDatasetVersion.id == EvalRun.dataset_version_id)
            .join(Tenant, EvalRun.tenant_id == Tenant.id)
            .where(
                EvalRun.status == "completed",
                EvalRun.is_demo.is_(False),
                EvalDatasetVersion.review_status == "reviewed",
                Tenant.is_demo.is_(False),
            )
        )
        or 0
    )
    totals = {
        "total_users": _real_tenant_count(db, User),
        "active_users_30d": int(
            db.scalar(
                select(func.count(distinct(AnalyticsEvent.user_id)))
                .join(Tenant, AnalyticsEvent.tenant_id == Tenant.id)
                .where(
                    AnalyticsEvent.occurred_at >= active_since,
                    AnalyticsEvent.user_id.is_not(None),
                    AnalyticsEvent.source == "server",
                    Tenant.is_demo.is_(False),
                )
            )
            or 0
        ),
        "organizations": _real_tenant_count(db, Tenant),
        "companies": _real_tenant_count(db, Company),
        "policy_scans": _real_tenant_count(db, PolicyScan),
        "applications": _real_tenant_count(db, Application),
        "reports_generated": _real_tenant_count(
            db,
            AnalyticsEvent,
            AnalyticsEvent.name == "report_generated",
            AnalyticsEvent.source == "server",
        ),
        "agent_runs": total_runs,
        "successful_runs": _real_tenant_count(db, AgentRun, AgentRun.status == "completed"),
        "failed_runs": _real_tenant_count(db, AgentRun, AgentRun.status == "failed"),
        "documents_generated": _real_tenant_count(db, ApplicationArtifact),
        "poc_accounts": _real_tenant_count(db, Tenant, Tenant.account_stage == "poc"),
        "paying_customers": int(
            db.scalar(
                select(func.count(distinct(Order.tenant_id)))
                .join(Tenant, Order.tenant_id == Tenant.id)
                .where(Order.status == "paid", Tenant.is_demo.is_(False))
            )
            or 0
        ),
        "llm_cost_usd": round(llm_cost, 6),
        "cost_per_run_usd": round(llm_cost / total_runs, 6) if total_runs else None,
    }
    return {
        "generated_at": now.isoformat(),
        "scope": "platform",
        "window": {"active_users": "trailing_30_days", "trend": "trailing_30_days"},
        "totals": totals,
        "revenue_by_currency": [
            {"currency": currency, "amount": _money(amount)} for currency, amount in revenue_rows
        ],
        "funnel": funnel,
        "agent_trend_30d": trend,
        "definitions": {
            "active_users_30d": "Distinct users with a server-owned analytics event in the trailing 30 days.",
            "reports_generated": "Server-owned report_generated events; there is no standalone Report table.",
            "documents_generated": "Persisted ApplicationArtifact versions.",
            "poc_accounts": "Tenants explicitly classified with account_stage=poc.",
            "paying_customers": "Distinct tenants with at least one paid Order.",
            "revenue": "Sum of paid Order amounts, separated by currency.",
            "llm_cost_usd": "Sum of persisted AgentRun.cost_usd; deterministic runs record zero.",
            "cost_per_run_usd": "Total persisted AgentRun cost divided by all Agent Runs.",
            "funnel": "Distinct organizations with each server-owned milestone event; not cohort-normalized.",
            "demo_exclusion": "Tenants marked is_demo=true are excluded from all investor metrics.",
        },
        "availability": {
            "evaluation_metrics": reviewed_evaluation_runs == 5,
            "subscription_mrr": False,
            "retention": False,
            "api_latency_history": False,
        },
    }


def system_health(db: Session) -> dict:
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    stale_running = _real_tenant_count(
        db,
        AgentRun,
        AgentRun.status == "running",
        AgentRun.lease_expires_at.is_not(None),
        AgentRun.lease_expires_at < now,
    )
    return {
        "checked_at": now.isoformat(),
        "database": "ready",
        "agent_queue": {
            "queued": _real_tenant_count(db, AgentRun, AgentRun.status == "queued"),
            "running": _real_tenant_count(db, AgentRun, AgentRun.status == "running"),
            "stale_running": stale_running,
            "failed_24h": _real_tenant_count(
                db, AgentRun, AgentRun.status == "failed", AgentRun.updated_at >= day_ago
            ),
        },
        "workflow_runs": {
            "running": _real_tenant_count(db, WorkflowRun, WorkflowRun.status == "running"),
            "failed_24h": _real_tenant_count(
                db, WorkflowRun, WorkflowRun.status == "failed", WorkflowRun.updated_at >= day_ago
            ),
        },
        "documents": {
            "pending_ingestion": _real_tenant_count(
                db, Document, Document.ingestion_status.in_(["pending", "processing"])
            ),
            "failed_ingestion": _real_tenant_count(
                db, Document, Document.ingestion_status == "failed"
            ),
        },
        "errors_24h": _real_tenant_count(
            db, AgentRunError, AgentRunError.occurred_at >= day_ago
        ),
        "open_feedback": _real_tenant_count(
            db, Feedback, Feedback.status.in_(["open", "reviewing"])
        ),
        "api_latency_history": {
            "available": False,
            "reason": "Not persisted; inspect structured logs.",
        },
    }


def admin_overview(db: Session) -> dict:
    metrics = investor_metrics(db)
    completed_evals = _real_tenant_count(db, EvalRun, EvalRun.status == "completed")
    return {
        "generated_at": metrics["generated_at"],
        "totals": metrics["totals"],
        "revenue_by_currency": metrics["revenue_by_currency"],
        "funnel": metrics["funnel"],
        "agent_trend_30d": metrics["agent_trend_30d"],
        "system_health": system_health(db),
        "resources": {
            "users": _real_tenant_count(db, User),
            "organizations": _real_tenant_count(db, Tenant),
            "companies": _real_tenant_count(db, Company),
            "agent_runs": _real_tenant_count(db, AgentRun),
            "workflow_runs": _real_tenant_count(db, WorkflowRun),
            "documents": _real_tenant_count(db, Document),
            "document_ingestion_runs": _real_tenant_count(db, DocumentIngestionRun),
            "policies": _real_policy_count(db),
            "errors": _real_tenant_count(db, AgentRunError),
            "billing": _real_tenant_count(db, Order),
            "feedback": _real_tenant_count(db, Feedback),
            "analytics": _real_tenant_count(db, AnalyticsEvent),
            "evals": _real_tenant_count(db, EvalRun),
            "demo_scenarios": _count(db, DemoScenario),
        },
        "capabilities": {
            "evals": {
                "available": completed_evals > 0,
                "message": None if completed_evals else "No evaluation data yet.",
            },
            "subscriptions": {
                "available": False,
                "message": "Subscription metrics not implemented.",
            },
        },
    }
