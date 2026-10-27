from app.models.models import Product


def purchase_status(product: Product) -> dict:
    """New-order capability, independent of historical entitlement fulfilment.

    New SKUs must wire and verify their own delivery path before being enabled.
    This does not assert supplier configuration or real-business quality.
    """
    available = (
        product.active and product.code == "POLICY_REPORT" and product.entitlement_type == "report"
    )
    if available:
        reason = None
    elif product.code == "FREE_POLICY_MATCH":
        reason = "免费体验无需下单，请进入企业工作区。"
    else:
        reason = "该产品的独立交付尚待验收，暂不接受新订单；已有订单与权益保留。"
    return {"purchase_available": bool(available), "purchase_unavailable_reason": reason}
