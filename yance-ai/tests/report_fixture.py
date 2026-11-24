"""Synthetic ready artifact for payment-domain tests, not a policy-quality fixture."""
import hashlib
import uuid
from datetime import UTC, datetime

from app.core.db import SessionLocal
from app.models.models import Company, Deliverable, Task
from app.services.report.pdf import generate_match_report_pdf
from app.services.report.schema import (
    OpportunityReportCard,
    build_report_document,
    report_document_to_content_json,
)


def ready_report(company_id):
    with SessionLocal() as db:
        company = db.get(Company, uuid.UUID(str(company_id)))
        task = Task(
            tenant_id=company.tenant_id,
            company_id=company.id,
            task_type="policy_scan",
            title="合成支付合同报告",
            status="delivered",
        )
        db.add(task)
        db.flush()
        opportunity_id = uuid.uuid4()
        policy_id = uuid.uuid4()
        profile_version_id = uuid.uuid4()
        scan_id = uuid.uuid4()
        card = OpportunityReportCard(
            opportunity_id=opportunity_id,
            policy_id=policy_id,
            policy_version_id=uuid.uuid4(),
            profile_version_id=profile_version_id,
            policy_title="合成支付合同政策",
            eligibility_status="NEED_MORE_INFORMATION",
            eligibility_summary="合成夹具：仅用于支付合同测试，不是业务质量样本。",
            gaps=["合成夹具缺口"],
            citations=[],
            next_step="本夹具仅验证支付与下载契约；业务扫描请使用真实 ReportCard 产物。",
        )
        document = build_report_document(
            company_id=company.id,
            profile_version_id=profile_version_id,
            scan_id=scan_id,
            cards=[card],
            generated_at=datetime.now(UTC),
        )
        content = report_document_to_content_json(document)
        content["synthetic_payment_contract_only"] = True
        data = generate_match_report_pdf(company, [], [], report_document=document)
        report = Deliverable(
            tenant_id=company.tenant_id,
            task_id=task.id,
            company_id=company.id,
            deliverable_type="policy_scan",
            title="合成支付合同报告",
            content_json=content,
            frozen_pdf=data,
            frozen_pdf_sha256=hashlib.sha256(data).hexdigest(),
            status="generated",
        )
        db.add(report)
        db.commit()
        return str(report.id), str(task.id), data
