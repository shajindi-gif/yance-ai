import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol

import pymupdf

from app.core.config import settings
from app.services.documents.security import DocumentIngestionError


@dataclass(frozen=True)
class OCRResult:
    pages: list[str]
    provider: str
    languages: str


class OCRProvider(Protocol):
    def extract_pdf(self, payload: bytes) -> OCRResult: ...


class TesseractOCRProvider:
    name = "tesseract"

    def __init__(self) -> None:
        languages = settings.document_ocr_languages
        if not re.fullmatch(r"[A-Za-z0-9_+.-]+", languages):
            raise DocumentIngestionError("ocr_configuration", "OCR language configuration is invalid")
        self.languages = languages
        if not 72 <= settings.document_ocr_dpi <= 400:
            raise DocumentIngestionError("ocr_configuration", "OCR DPI configuration is invalid")

    def extract_pdf(self, payload: bytes) -> OCRResult:
        executable = shutil.which("tesseract")
        if not executable:
            raise DocumentIngestionError(
                "ocr_required",
                "OCR runtime is unavailable; retry after OCR is configured",
                retryable=True,
            )
        try:
            document = pymupdf.open(stream=payload, filetype="pdf")
        except Exception as exc:
            raise DocumentIngestionError("pdf_parse_failed", "PDF content could not be opened for OCR") from exc
        try:
            if document.page_count > settings.document_ocr_max_pages:
                raise DocumentIngestionError(
                    "ocr_page_limit", "PDF exceeds the configured OCR page limit"
                )
            scale = settings.document_ocr_dpi / 72
            matrix = pymupdf.Matrix(scale, scale)
            pages: list[str] = []
            for page in document:
                pixels = int(page.rect.width * scale) * int(page.rect.height * scale)
                if pixels > settings.document_ocr_max_pixels_per_page:
                    raise DocumentIngestionError(
                        "ocr_pixel_limit", "A PDF page exceeds the configured OCR render limit"
                    )
                png = page.get_pixmap(matrix=matrix, alpha=False).tobytes("png")
                try:
                    completed = subprocess.run(
                        [
                            executable,
                            "stdin",
                            "stdout",
                            "-l",
                            self.languages,
                            "--dpi",
                            str(settings.document_ocr_dpi),
                        ],
                        input=png,
                        capture_output=True,
                        timeout=settings.document_ocr_page_timeout_seconds,
                        check=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise DocumentIngestionError(
                        "ocr_timeout", "OCR timed out; retry with a smaller document", retryable=True
                    ) from exc
                if completed.returncode != 0:
                    raise DocumentIngestionError(
                        "ocr_failed", "OCR could not extract this PDF", retryable=True
                    )
                pages.append(completed.stdout.decode("utf-8", errors="replace"))
            return OCRResult(pages=pages, provider=self.name, languages=self.languages)
        finally:
            document.close()


def get_ocr_provider() -> OCRProvider | None:
    if not settings.document_ocr_enabled:
        return None
    if settings.document_ocr_provider == "tesseract":
        return TesseractOCRProvider()
    raise DocumentIngestionError("ocr_configuration", "OCR provider is not supported")
