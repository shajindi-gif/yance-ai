import hashlib
import io
import json
import zipfile
from html import escape
from typing import Any, Literal

from weasyprint import HTML

ExportFormat = Literal["docx", "pdf", "xlsx", "json"]


def _xml_text(value: Any) -> str:
    clean = "".join(
        character
        for character in str(value)
        if character in {"\t", "\n", "\r"} or ord(character) >= 0x20
    )
    return escape(clean)


def canonical_content(content: dict[str, Any]) -> bytes:
    return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def content_checksum(content: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_content(content)).hexdigest()


def _plain_rows(content: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    rows = [("项目", "标题", str(content.get("title", "")), "")]
    rows.append(("项目", "企业", str(content.get("company_name", "")), ""))
    rows.append(("项目", "摘要", str(content.get("executive_summary", "")), ""))
    rows.append(("资格", "结论", str(content.get("eligibility", {}).get("status", "")), ""))
    rows.append(("资格", "说明", str(content.get("eligibility", {}).get("summary", "")), ""))
    for item in content.get("criteria", []):
        rows.append(
            (
                "资格条件",
                str(item.get("name", "")),
                str(item.get("actual", "")),
                str(item.get("status", "")),
            )
        )
    for item in content.get("requirements", []):
        rows.append(
            (
                "材料",
                str(item.get("title", "")),
                str(item.get("description", "")),
                str(item.get("status", "")),
            )
        )
    for item in content.get("evidence", []):
        rows.append(
            (
                "政策证据",
                str(item.get("article") or item.get("source_title", "")),
                str(item.get("quote", "")),
                "已核验" if item.get("verified") else "未核验",
            )
        )
    if content.get("revision_note"):
        rows.append(("修订", "说明", str(content["revision_note"]), ""))
    return rows


def render_json(content: dict[str, Any]) -> bytes:
    return json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True).encode()


def render_docx(content: dict[str, Any]) -> bytes:
    paragraphs = []
    for category, label, value, status in _plain_rows(content):
        text = " · ".join(part for part in (category, label, value, status) if part)
        paragraphs.append(
            f'<w:p><w:r><w:t xml:space="preserve">{_xml_text(text)}</w:t></w:r></w:p>'
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(paragraphs)}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return output.getvalue()


def render_xlsx(content: dict[str, Any]) -> bytes:
    rows = [("类别", "项目", "内容", "状态"), *_plain_rows(content)]
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            column = chr(64 + column_index)
            cells.append(
                f'<c r="{column}{row_index}" t="inlineStr"><is><t>{_xml_text(value)}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="申报工作区" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def render_pdf(content: dict[str, Any]) -> bytes:
    rows = "".join(
        f"<tr><td>{escape(category)}</td><td>{escape(label)}</td><td>{escape(value)}</td><td>{escape(status)}</td></tr>"
        for category, label, value, status in _plain_rows(content)
    )
    html = f"""
    <html lang="zh-CN"><head><meta charset="utf-8"><style>
      body {{ font-family: sans-serif; margin: 36px; color: #172033; }}
      h1 {{ font-size: 22px; }} table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
      th, td {{ border: 1px solid #d9e0e8; padding: 7px; vertical-align: top; }}
      th {{ background: #f3f6f9; text-align: left; }}
    </style></head><body><h1>{escape(str(content.get("title", "申报工作稿")))}</h1>
    <p>生成方式：确定性证据模板；正式提交前必须人工复核。</p>
    <table><thead><tr><th>类别</th><th>项目</th><th>内容</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table>
    </body></html>
    """
    return HTML(string=html).write_pdf()


def render_artifact(content: dict[str, Any], export_format: ExportFormat) -> tuple[bytes, str, str]:
    renderers = {
        "docx": (
            render_docx,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        "pdf": (render_pdf, "application/pdf"),
        "xlsx": (render_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "json": (render_json, "application/json"),
    }
    renderer, mime_type = renderers[export_format]
    return renderer(content), mime_type, export_format
