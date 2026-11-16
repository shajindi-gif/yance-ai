"""Verify a payable order has its own tenant/resource-bound immutable delivery."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Deliverable, Order
from app.services.report.snapshot import report_bytes


def require_order_report(db: Session, order: Order) -> Deliverable | None:
    if order.resource_type != 'report':
        return None
    report = db.scalar(select(Deliverable).where(
        Deliverable.id == order.report_deliverable_id,
        Deliverable.tenant_id == order.tenant_id,
        Deliverable.company_id == order.resource_id,
        Deliverable.deliverable_type == 'policy_scan',
        Deliverable.status.in_(['generated', 'delivered', 'accepted']),
    ))
    if report is None or not (report.content_json or {}).get('total_matches', 0):
        raise HTTPException(409, detail={
            'code': 'order_delivery_not_ready',
            'message': '该订单尚未绑定可交付的固定报告，暂不能继续付款。订单记录保留，请联系支持核对；请勿重新付款。',
        })
    report_bytes(report)
    return report
