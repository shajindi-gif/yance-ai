from fastapi import APIRouter

from app.api.routes import (
    admin,
    admin_evals,
    agents,
    analytics,
    auth,
    commerce,
    companies,
    demo_match,
    documents,
    payments,
    policies,
    policy_engine,
    reports,
    tasks,
    telemetry,
    tenants,
    workflow,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(admin_evals.router)
api_router.include_router(analytics.router)
api_router.include_router(agents.router)
api_router.include_router(tenants.router)
api_router.include_router(companies.router)
api_router.include_router(documents.router)
api_router.include_router(policies.router)
api_router.include_router(workflow.router)
api_router.include_router(commerce.router)
api_router.include_router(payments.router)
api_router.include_router(payments.bank_router)
api_router.include_router(telemetry.router)
api_router.include_router(reports.router)
api_router.include_router(demo_match.router)
api_router.include_router(tasks.router)
api_router.include_router(policy_engine.router)
