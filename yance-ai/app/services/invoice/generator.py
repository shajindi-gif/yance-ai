"""增值税普通发票 PDF 生成器（HTML → PDF via weasyprint）"""

import os
from datetime import datetime

from app.models.models import Invoice

_INVOICE_OUTPUT_DIR = "/app/invoices"

INVOICE_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 10mm; }
  body { font-family: "PingFang SC","Microsoft YaHei","SimHei",sans-serif; font-size: 12px; color: #222; }
  .invoice-box { border: 2px solid #c0392b; padding: 0; width: 100%; }
  .header { background: #c0392b; color: #fff; text-align: center; padding: 12px 0; font-size: 24px; font-weight: bold; letter-spacing: 6px; }
  .header .sub { font-size: 11px; letter-spacing: 2px; margin-top: 4px; }
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
  .footer { margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 10px; color: #888; }
  .seal { float: right; width: 90px; text-align: center; margin-top: -30px; margin-right: 20px; }
</style>
</head>
<body>
<div class="invoice-box">
  <div class="header">
    {invoice_type_name}
    <div class="sub">发票代码：{invoice_code} &emsp; 发票号码：{invoice_no}</div>
  </div>

  <div class="info-row">
    <div class="info-item"><div class="label">购买方名称</div><div class="value">{title}</div></div>
    <div class="info-item"><div class="label">纳税人识别号</div><div class="value">{tax_number}</div></div>
  </div>
  <div class="info-row">
    <div class="info-item"><div class="label">地址、电话</div><div class="value">{address_phone}</div></div>
    <div class="info-item"><div class="label">开户行及账号</div><div class="value">{bank_account}</div></div>
  </div>

  <table class="items">
    <thead>
      <tr>
        <th style="width:28%">货物或应税劳务、服务名称</th>
        <th style="width:14%">规格型号</th>
        <th style="width:8%">单位</th>
        <th style="width:8%">数量</th>
        <th style="width:12%">单价</th>
        <th style="width:14%">金额</th>
        <th style="width:8%">税率</th>
        <th style="width:8%">税额</th>
      </tr>
    </thead>
    <tbody>
      {items_rows}
    </tbody>
  </table>

  <div class="total-row">
    <div class="total-item" style="flex:2"><div class="label">合计</div></div>
    <div class="total-item"><div class="label">金额（不含税）</div><div class="value">&yen;{amount}</div></div>
    <div class="total-item"><div class="label">税额</div><div class="value">&yen;{tax_amount}</div></div>
    <div class="total-item"><div class="label">价税合计（大写）</div><div class="value">{total_cn}</div></div>
    <div class="total-item"><div class="label">（小写）</div><div class="value">&yen;{total_amount}</div></div>
  </div>

  <div class="info-row">
    <div class="info-item" style="flex:2"><div class="label">销售方名称</div><div class="value">{seller_name}</div></div>
    <div class="info-item" style="flex:2"><div class="label">纳税人识别号</div><div class="value">{seller_tax_number}</div></div>
  </div>

  <div class="info-row">
    <div class="info-item" style="flex:2"><div class="label">备注</div><div class="value">由 yance.ai 系统自动生成 · 开票日期：{date}</div></div>
    <div class="info-item" style="flex:1"></div>
  </div>

  <div class="seal">
    <div style="border:2px solid #c0392b; border-radius:50%; width:70px; height:70px; line-height:70px; margin:auto; font-size:11px; color:#c0392b; font-weight:bold">发票专用章</div>
  </div>
</div>
<div class="footer">
  yance.ai 智能发票系统 &copy; {year} · 本发票由系统自动生成，仅供内部对账使用<br>
  如需正式税务发票，请联系客服
</div>
</body>
</html>"""


def _number_to_cn(amount: float) -> str:
    """金额阿拉伯数字 → 中文大写"""
    digits = "零壹贰叁肆伍陆柒捌玖"
    radices = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]
    big_radices = ["", "万", "亿"]
    decimals = ["角", "分"]

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

    invoice_type_names = {
        "vat_normal": "增值税普通发票",
        "vat_special": "增值税专用发票",
        "vat_electronic": "增值税电子普通发票",
    }

    items = invoice.items_json or []
    items_rows = ""
    for item in items:
        items_rows += (
            f"<tr>"
            f"<td>{item.get('name', '')}</td>"
            f"<td>{item.get('spec', '')}</td>"
            f"<td>{item.get('unit', '')}</td>"
            f"<td>{item.get('qty', 1)}</td>"
            f"<td>{item.get('price', 0):.2f}</td>"
            f"<td>{item.get('amount', 0):.2f}</td>"
            f"<td>{item.get('tax_rate', 0)}%</td>"
            f"<td>{item.get('tax', 0):.2f}</td>"
            f"</tr>"
        )

    html_content = INVOICE_HTML_TEMPLATE.format(
        invoice_type_name=invoice_type_names.get(invoice.invoice_type, "增值税普通发票"),
        invoice_code=invoice.invoice_code or "-",
        invoice_no=invoice.invoice_no or "-",
        title=invoice.title,
        tax_number=invoice.tax_number,
        address_phone=invoice.address_phone or "",
        bank_account=invoice.bank_account or "",
        items_rows=items_rows,
        amount=f"{invoice.amount:.2f}",
        tax_amount=f"{invoice.tax_amount:.2f}",
        total_cn=_number_to_cn(invoice.total_amount),
        total_amount=f"{invoice.total_amount:.2f}",
        seller_name=invoice.seller_name or "上海衍策引擎人工智能科技有限公司",
        seller_tax_number=invoice.seller_tax_number or "91310104MAKDCJH00L",
        date=datetime.now().strftime("%Y年%m月%d日"),
        year=datetime.now().year,
    )

    pdf_filename = f"invoice_{invoice.invoice_no or invoice.id}.pdf"
    pdf_path = os.path.join(_INVOICE_OUTPUT_DIR, pdf_filename)

    # Write HTML temp file
    html_path = os.path.join(_INVOICE_OUTPUT_DIR, f"_tmp_{invoice.id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
    except ImportError:
        # Fallback: use playwright
        import subprocess
        subprocess.run(
            ["python", "-m", "weasyprint", html_path, pdf_path],
            check=True, capture_output=True, timeout=30,
        )

    # Cleanup temp HTML
    try:
        os.remove(html_path)
    except OSError:
        pass

    return pdf_path
