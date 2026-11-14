"""Deliver exactly the generated version; never rebuild historical evidence on GET."""
import hashlib

from fastapi import HTTPException

from app.models.models import Deliverable


def report_bytes(deliverable: Deliverable) -> bytes:
    data = deliverable.frozen_pdf
    if not data or not deliverable.frozen_pdf_sha256:
        raise HTTPException(409, "该历史报告未保存固定版本，请联系支持核对原交付文件；原订单和权益保留，请勿重复付款")
    if hashlib.sha256(data).hexdigest() != deliverable.frozen_pdf_sha256:
        raise HTTPException(409, "报告文件校验失败，请联系支持恢复原版本，请勿重复付款")
    return data
