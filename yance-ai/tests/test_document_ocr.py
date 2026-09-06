import io

import pytest
from pypdf import PdfWriter

from app.services.documents.ocr import OCRResult, TesseractOCRProvider
from app.services.documents.parsers import parse_document
from app.services.documents.security import DocumentIngestionError


class StubOCRProvider:
    def extract_pdf(self, payload: bytes) -> OCRResult:
        assert payload.startswith(b"%PDF-")
        return OCRResult(
            pages=["企业名称：上海衍策科技有限公司\n所属行业：人工智能软件"],
            provider="stub-ocr",
            languages="chi_sim+eng",
        )


def test_image_only_pdf_uses_structured_ocr_provider():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    stream = io.BytesIO()
    writer.write(stream)

    parsed = parse_document("scan.pdf", stream.getvalue(), ocr_provider=StubOCRProvider())

    assert parsed.parser == "ocr:stub-ocr"
    assert parsed.page_count == 1
    assert parsed.metadata == {
        "ocr": True,
        "ocr_provider": "stub-ocr",
        "ocr_languages": "chi_sim+eng",
        "pages_with_text": 1,
    }
    assert parsed.spans[0].locator == {"page": 1}
    assert "上海衍策科技" in parsed.text


def test_missing_ocr_runtime_is_explicitly_retryable(monkeypatch):
    monkeypatch.setattr("app.services.documents.ocr.shutil.which", lambda _name: None)
    with pytest.raises(DocumentIngestionError) as error:
        TesseractOCRProvider().extract_pdf(b"%PDF-placeholder")
    assert error.value.code == "ocr_required"
    assert error.value.retryable is True
