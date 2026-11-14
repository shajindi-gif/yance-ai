import io
import json
import zipfile

from app.services.applications.artifacts import content_checksum, render_artifact


def _content() -> dict:
    return {
        "title": "人工智能企业研发支持申报工作稿",
        "company_name": "测试企业",
        "executive_summary": "已通过结构化规则检查，等待人工复核。",
        "eligibility": {"status": "POTENTIALLY_ELIGIBLE", "summary": "等待人工复核"},
        "criteria": [{"name": "行业要求", "actual": "人工智能", "status": "PASS"}],
        "requirements": [{"title": "营业执照", "description": "企业证照", "status": "ready"}],
        "evidence": [
            {
                "source_title": "测试政策",
                "article": "第一条",
                "quote": "支持人工智能企业",
                "verified": True,
            }
        ],
        "revision_note": None,
    }


def test_application_artifact_checksum_is_canonical():
    first = _content()
    second = dict(reversed(list(first.items())))
    assert content_checksum(first) == content_checksum(second)


def test_docx_and_xlsx_exports_are_valid_openxml_archives():
    docx, docx_type, _ = render_artifact(_content(), "docx")
    assert docx_type.endswith("wordprocessingml.document")
    with zipfile.ZipFile(io.BytesIO(docx)) as archive:
        assert "word/document.xml" in archive.namelist()
        assert "测试企业" in archive.read("word/document.xml").decode()

    xlsx, xlsx_type, _ = render_artifact(_content(), "xlsx")
    assert xlsx_type.endswith("spreadsheetml.sheet")
    with zipfile.ZipFile(io.BytesIO(xlsx)) as archive:
        assert "xl/worksheets/sheet1.xml" in archive.namelist()
        assert "营业执照" in archive.read("xl/worksheets/sheet1.xml").decode()


def test_json_and_pdf_exports_round_trip():
    json_bytes, json_type, _ = render_artifact(_content(), "json")
    assert json_type == "application/json"
    assert json.loads(json_bytes)["company_name"] == "测试企业"

    pdf, pdf_type, _ = render_artifact(_content(), "pdf")
    assert pdf_type == "application/pdf"
    assert pdf.startswith(b"%PDF-")


def test_openxml_export_escapes_user_content_and_drops_control_characters():
    content = _content()
    content["executive_summary"] = "<script>alert('&')\x00</script>"
    docx, _, _ = render_artifact(content, "docx")
    with zipfile.ZipFile(io.BytesIO(docx)) as archive:
        xml = archive.read("word/document.xml").decode()
    assert "<script>" not in xml
    assert "&lt;script&gt;" in xml
    assert "\x00" not in xml


def test_export_preserves_customer_review_statement():
    content = _content()
    statement = "由客户本人或其授权团队成员复核；衍策不提供人工业务审核。"
    content["disclaimer"] = statement
    for kind, member in [("docx", "word/document.xml"), ("xlsx", "xl/worksheets/sheet1.xml")]:
        data, _, _ = render_artifact(content, kind)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert statement in archive.read(member).decode()
    data, _, _ = render_artifact(content, "json")
    assert json.loads(data)["disclaimer"] == statement
