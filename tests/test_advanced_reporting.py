from __future__ import annotations

from datetime import date

from docx import Document
from test_visualization import make_view_model

from nirs_report_app.reporting import PatientInfo, build_advanced_report
from nirs_report_app.settings import ReportSettings
from nirs_report_app.visualization import ReportDashboardRenderer


def document_text(document: Document) -> str:
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join([*paragraphs, *cells])


def test_advanced_report_contains_native_research_content_and_images(tmp_path) -> None:
    model = make_view_model()
    overview = tmp_path / "overview.png"
    laterality = tmp_path / "laterality.png"
    renderer = ReportDashboardRenderer()
    renderer.render_overview(model).savefig(overview, dpi=300)
    renderer.render_laterality(model).savefig(laterality, dpi=300)
    destination = tmp_path / "advanced-report.docx"

    build_advanced_report(
        destination,
        ReportSettings(report_title="NIRS 研究分析報告", report_sub_title="受試者結果"),
        PatientInfo(
            patient_id="S01",
            name="測試個案",
            measurement_date=date(2026, 8, 26),
        ),
        model,
        {"overview": overview, "laterality": laterality},
    )

    document = Document(destination)
    text = document_text(document)
    assert "NIRS 研究分析報告" in text
    assert "S01" in text
    assert "W_CHANNEL_MISSING" in text
    assert "僅供研究與教育用途，不得作為單獨臨床診斷依據" in text
    assert "分析方法與追溯資訊" in text
    assert "bootstrap_seed" in text
    assert "20260826" in text
    assert len(document.inline_shapes) == 2


def test_advanced_report_values_match_the_report_view_model(tmp_path) -> None:
    model = make_view_model()
    destination = tmp_path / "consistent.docx"

    build_advanced_report(
        destination,
        ReportSettings(report_title="NIRS"),
        PatientInfo(patient_id="S01"),
        model,
        {},
    )

    text = document_text(Document(destination))
    assert "12.50" in text
    assert "4.25" in text
    assert "-0.0123" in text
    assert "0.500" in text


def test_advanced_report_is_a4_and_every_figure_fits_the_text_area(tmp_path) -> None:
    model = make_view_model()
    overview = tmp_path / "overview.png"
    ReportDashboardRenderer().render_overview(model).savefig(overview, dpi=100)
    destination = tmp_path / "layout.docx"

    build_advanced_report(
        destination, ReportSettings(), PatientInfo(), model, {"overview": overview}
    )

    document = Document(destination)
    section = document.sections[0]
    assert round(section.page_width.mm) == 297
    assert round(section.page_height.mm) == 210
    text_width = section.page_width - section.left_margin - section.right_margin
    text_height = section.page_height - section.top_margin - section.bottom_margin
    assert len(document.inline_shapes) == 1
    for shape in document.inline_shapes:
        assert shape.width <= text_width
        assert shape.height < text_height


def test_advanced_report_has_opinion_signature_and_readable_warnings(tmp_path) -> None:
    model = make_view_model()
    destination = tmp_path / "summary.docx"

    build_advanced_report(
        destination,
        ReportSettings(),
        PatientInfo(patient_id="S01", doctor="王醫師", opinion="前額葉活化反應偏低"),
        model,
        {},
    )

    document = Document(destination)
    text = document_text(document)
    assert "判讀意見" in text
    assert "前額葉活化反應偏低" in text
    assert "醫師：王醫師" in text
    assert "有通道缺少資料（W_CHANNEL_MISSING）" in text
    assert "區域內有效通道不足（W_ROI_DEGRADED）" in text
    assert "左側優勢" in text
    footer_xml = document.sections[0].footer._element.xml
    assert "PAGE" in footer_xml
    assert "NUMPAGES" in footer_xml


def test_advanced_report_hides_opinion_and_doctor_when_switched_off(tmp_path) -> None:
    destination = tmp_path / "plain.docx"

    build_advanced_report(
        destination,
        ReportSettings(isShowDoctor=False, isShowOpinion=False),
        PatientInfo(doctor="王醫師", opinion="不應出現"),
        make_view_model(),
        {},
    )

    text = document_text(Document(destination))
    assert "判讀意見" not in text
    assert "王醫師" not in text
    assert "不應出現" not in text
