import asyncio
import uuid
from pathlib import Path

import pytest
import weasyprint

from app.models.models import Company, Invoice
from app.services.invoice import generator as invoice_generator
from app.services.report import pdf as report_pdf
from app.services.safe_rendering import deny_external_url_fetcher, escape_html


class CapturingHTML:
    last_string = ""
    last_url_fetcher = None

    def __init__(self, *, string, url_fetcher):
        type(self).last_string = string
        type(self).last_url_fetcher = url_fetcher

    def write_pdf(self, target):
        if hasattr(target, "write"):
            target.write(b"%PDF-safe-test")
        else:
            Path(target).write_bytes(b"%PDF-safe-test")


def test_escape_html_and_url_fetcher_fail_closed():
    assert escape_html('<img src="file:///etc/passwd">') == (
        "&lt;img src=&quot;file:///etc/passwd&quot;&gt;"
    )
    with pytest.raises(ValueError, match="External resource loading is disabled"):
        deny_external_url_fetcher("file:///etc/passwd")


def test_report_renderer_escapes_company_content_and_denies_fetch(monkeypatch):
    monkeypatch.setattr(report_pdf, "HTML", CapturingHTML)
    company = Company(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name='<img src="https://attacker.invalid/collect">',
        metadata_json={"core_tech": "<script>alert(1)</script>"},
    )

    result = report_pdf.generate_match_report_pdf(company, [], [])

    assert result.startswith(b"%PDF")
    assert "<script>alert(1)</script>" not in CapturingHTML.last_string
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in CapturingHTML.last_string
    assert '<img src="https://attacker.invalid/collect">' not in CapturingHTML.last_string
    assert CapturingHTML.last_url_fetcher is deny_external_url_fetcher


def test_invoice_renderer_escapes_fields_and_denies_fetch(monkeypatch, tmp_path):
    monkeypatch.setattr(invoice_generator, "_INVOICE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(weasyprint, "HTML", CapturingHTML)
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        order_id=uuid.uuid4(),
        title='<img src="file:///etc/passwd">',
        tax_number="safe-tax-number",
        items_json=[{"name": "<script>bad()</script>", "amount": 1, "price": 1}],
        amount=1,
        tax_amount=0,
        total_amount=1,
        invoice_type="vat_normal",
        status="generated",
    )

    result_path = asyncio.run(invoice_generator.generate_invoice_pdf(invoice))

    assert Path(result_path).exists()
    assert "<script>bad()</script>" not in CapturingHTML.last_string
    assert "&lt;script&gt;bad()&lt;/script&gt;" in CapturingHTML.last_string
    assert '<img src="file:///etc/passwd">' not in CapturingHTML.last_string
    assert CapturingHTML.last_url_fetcher is deny_external_url_fetcher
