"""付款凭证 PDF 生成器（HTML → PDF via weasyprint）

本凭证仅作为已付款订单的对账凭证，不是税务发票。
正式税务发票需通过人工开票流程（用户提交开票申请 → 核实后开具）。
"""

import os
from datetime import datetime
from string import Template

from app.models.models import Invoice
from app.services.safe_rendering import deny_external_url_fetcher, escape_html

_INVOICE_OUTPUT_DIR = "/app/invoices"

INVOICE_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 10mm; }
  body { font-family: "PingFang SC","Microsoft YaHei","SimHei",sans-serif; font-size: 12px; color: #222; }
  .invoice-box { border: 2px solid #1e4e8c; padding: 0; width: 100%; }
  .header { background: #1e4e8c; color: #fff; text-align: center; padding: 12px 0; font-size: 22px; font-weight: bold; letter-spacing: 6px; }
  .header .sub { font-size: 11px; letter-spacing: 2px; margin-top: 4px; }
  .not-invoice { text-align: center; color: #1e4e8c; border-bottom: 1px solid #ccc; padding: 5px 0; font-size: 11px; font-weight: bold; }
  .info-row { display: flex; border-bottom: 1px solid #ccc; }
  .info-row:last-child { border-bottom: none; }
  .info-item { flex: 1; padding: 8px 6px; border-right: 1px solid #ccc; min-height: 28px; }
  .info-item:last-child { border-right: none; }
  .label { color: #888; font-size: 10px; margin-bottom: 2px; }
  .value { font-size: 13px; font-weight: 500; }
  table.items { width: 100%; border-collapse: collapse; }
  table.items th { background: #f5f5f5; border: 1px solid #ccc; padding: 6px; text-align: center; font-size: 11px; }
  table.items td { border: 1px solid #ccc; padding: 6px; text-align: center; font-size: 11px; }
  .total-row { display: flex; border-top: 1px solid #ccc; }
  .total-item { flex: 1; padding: 8px 6px; border-right: 1px solid #ccc; }
  .total-item:last-child { border-right: none; }
  .footer { margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 10px; color: #555; }
  .footer .strong { font-size: 11px; color: #1e4e8c; font-weight: bold; }
</style>
</head>
<body>
<div class="invoice-box">
  <div class="header">
    电子付款凭证
    <div class="sub">凭证编号：$invoice_no &emsp; 开具日期：$date</div>
  </div>
  <div class="not-invoice">本凭证为已付款订单对账凭证，非税务发票</div>

  <div class="info-row">
    <div class="info-item"><div class="label">购买方名称</div><div class="value">$title</div></div>
    <div class="info-item"><div class="label">关联订单号</div><div class="value">$order_no</div></div>
  </div>
  <div class="info-row">
    <div class="info-item"><div class="label">购买方备注信息</div><div class="value">$address_phone</div></div>
    <div class="info-item"><div class="label">支付方式</div><div class="value">在线支付</div></div>
  </div>

  <table class="items">
    <thead>
      <tr>
        <th style="width:40%">服务名称</th>
        <th style="width:14%">单位</th>
        <th style="width:10%">数量</th>
        <th style="width:18%">单价</th>
        <th style="width:18%">金额</th>
      </tr>
    </thead>
    <tbody>
      $items_rows
    </tbody>
  </table>

  <div class="total-row">
    <div class="total-item" style="flex:2"><div class="label">合计</div></div>
    <div class="total-item"><div class="label">价税合计（大写）</div><div class="value">$total_cn</div></div>
    <div class="total-item"><div class="label">（小写）</div><div class="value">&yen;$total_amount</div></div>
  </div>

  <div class="info-row">
    <div class="info-item" style="flex:2"><div class="label">销售方名称</div><div class="value">$seller_name</div></div>
    <div class="info-item" style="flex:2"><div class="label">联系方式</div><div class="value">contact@yance.ai</div></div>
  </div>

  <div class="info-row">
    <div class="info-item" style="flex:2"><div class="label">备注</div><div class="value">由 yance.ai 系统自动生成 · 开具日期：$date</div></div>
    <div class="info-item" style="flex:1"></div>
  </div>
</div>
<div class="footer">
  <span class="strong">重要提示：本文件为付款凭证（对账用途），不具备税务发票效力，不得作为报销或抵扣凭证使用。</span><br>
  如需开具正式税务发票（增值税电子普通发票），请通过订单页提交开票申请或联系 contact@yance.ai，我们将在核实付款信息后开具。<br>
  yance.ai &copy; $year
</div>
</body>
</html>"""


def _number_to_cn(amount: float) -> str:
    """金额阿拉伯数字 → 中文大写"""
    digits = "零壹贰叁肆伍陆柒捌玖"
    radices = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]

    yuan = int(amount)
    jiao = int(round(amount * 10)) % 10
    fen = int(round(amount * 100)) % 10

    if yuan == 0 and jiao == 0 and fen == 0:
        return "零元整"

    # Integer part
    parts = []
    zero_flag = False
    for i, c in enumerate(reversed(str(yuan))):
        d = int(c)
        if d == 0:
            zero_flag = True
        else:
            if zero_flag:
                parts.append("零")
                zero_flag = False
            parts.append(digits[d] + radices[i])
    # Clean up trailing zeros at unit boundaries
    result_chars = list(reversed(parts))

    # Handle 万/亿 boundaries
    cn_str = "".join(result_chars)
    if yuan > 0:
        cn_str += "元"
    else:
        cn_str = ""

    # Decimals
    if jiao == 0 and fen == 0:
        cn_str += "整"
    else:
        if jiao > 0:
            cn_str += digits[jiao] + "角"
        if fen > 0:
            cn_str += digits[fen] + "分"
        elif jiao > 0:
            cn_str += ""

    return cn_str


async def generate_invoice_pdf(invoice: Invoice) -> str:
    """Generate PDF invoice and return file path. Returns existing path if already generated."""
    if invoice.pdf_path and os.path.exists(invoice.pdf_path):
        return invoice.pdf_path

    os.makedirs(_INVOICE_OUTPUT_DIR, exist_ok=True)

    items = invoice.items_json or []
    items_rows = ""
    for item in items:
        items_rows += (
            f"<tr>"
            f"<td>{escape_html(item.get('name', ''))}</td>"
            f"<td>{escape_html(item.get('unit', '项'))}</td>"
            f"<td>{escape_html(item.get('qty', 1))}</td>"
            f"<td>{item.get('price', 0):.2f}</td>"
            f"<td>{item.get('amount', 0):.2f}</td>"
            f"</tr>"
        )

    html_content = Template(INVOICE_HTML_TEMPLATE).substitute(
        invoice_no=escape_html(invoice.invoice_no or "-"),
        order_no=escape_html(getattr(invoice, "order_no", None) or getattr(invoice, "order_id", "") or "-"),
        title=escape_html(invoice.title),
        address_phone=escape_html(invoice.address_phone or "-"),
        items_rows=items_rows,
        total_cn=_number_to_cn(invoice.total_amount),
        total_amount=f"{invoice.total_amount:.2f}",
        seller_name=escape_html(invoice.seller_name),
        date=datetime.now().strftime("%Y年%m月%d日"),
        year=datetime.now().year,
    )

    pdf_filename = f"invoice_{invoice.id}.pdf"
    pdf_path = os.path.join(_INVOICE_OUTPUT_DIR, pdf_filename)

    from weasyprint import HTML

    HTML(string=html_content, url_fetcher=deny_external_url_fetcher).write_pdf(pdf_path)

    return pdf_path
