"""Synthetic ready artifact for payment-domain tests, not a policy-quality fixture."""
import hashlib
import uuid

from app.core.db import SessionLocal
from app.models.models import Company, Deliverable, Task
from app.services.report.pdf import generate_match_report_pdf


def ready_report(company_id):
    with SessionLocal() as db:
        company = db.get(Company, uuid.UUID(str(company_id)))
        task = Task(tenant_id=company.tenant_id, company_id=company.id,
                    task_type="policy_scan", title="合成支付合同报告", status="delivered")
        db.add(task)
        db.flush()
        data = generate_match_report_pdf(company, [], [])
        report = Deliverable(tenant_id=company.tenant_id, task_id=task.id,
            company_id=company.id, deliverable_type="policy_scan", title="合成支付合同报告",
            content_json={"total_matches": 1, "synthetic_payment_contract_only": True},
            frozen_pdf=data, frozen_pdf_sha256=hashlib.sha256(data).hexdigest(), status="generated")
        db.add(report)
        db.commit()
        return str(report.id), str(task.id), data
