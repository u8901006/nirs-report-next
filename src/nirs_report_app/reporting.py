from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from .analysis.features import FeatureResult
from .report_models import ReportViewModel
from .settings import ReportSettings


@dataclass(frozen=True, slots=True)
class PatientInfo:
    patient_id: str = ""
    name: str = ""
    gender: str = ""
    birth_date: date | None = None
    measurement_date: date | None = None
    doctor: str = ""
    opinion: str = ""


def _add_centered_heading(document: Document, text: str, size: int) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(size)


def build_report(
    destination: Path,
    settings: ReportSettings,
    patient: PatientInfo,
    features: FeatureResult,
    image_paths: list[Path] | None = None,
) -> Path:
    document = Document()
    _add_centered_heading(document, settings.report_title, 20)
    _add_centered_heading(document, settings.report_sub_title, 14)

    table = document.add_table(rows=0, cols=2)
    for label, value in (
        ("個案編號", patient.patient_id),
        ("姓名", patient.name),
        ("性別", patient.gender),
        ("測量日期", patient.measurement_date.isoformat() if patient.measurement_date else ""),
    ):
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
    if settings.isShowBirthAndAge:
        cells = table.add_row().cells
        cells[0].text = "出生日期"
        cells[1].text = patient.birth_date.isoformat() if patient.birth_date else ""

    result = document.add_table(rows=1, cols=3)
    result.rows[0].cells[0].text = "區域"
    result.rows[0].cells[1].text = "積分值"
    result.rows[0].cells[2].text = "重心時間"
    for label, integral, centroid in (
        ("前額中區", features.front_integral, features.front_centroid_value),
        ("前額側區", features.side_integral, features.side_centroid_value),
    ):
        cells = result.add_row().cells
        cells[0].text = label
        cells[1].text = str(integral)
        cells[2].text = str(centroid)

    for image_path in image_paths or []:
        if image_path.exists():
            document.add_picture(str(image_path))
    if settings.isShowDoctor:
        document.add_paragraph(f"醫師：{patient.doctor}")
    if settings.isShowOpinion:
        document.add_paragraph(f"判讀意見：{patient.opinion}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination)
    return destination


def _format_numeric(value: float | None, decimals: int) -> str:
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _set_document_style(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Microsoft JhengHei"
    normal.font.size = Pt(9)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)


def _add_key_value_table(document: Document, rows: tuple[tuple[str, str], ...]) -> None:
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value


def _analysis_config_digest(config: Mapping[str, object]) -> str:
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_advanced_report(
    destination: Path,
    settings: ReportSettings,
    patient: PatientInfo,
    view_model: ReportViewModel,
    rendered_pages: Mapping[str, Path],
) -> Path:
    """Build the research report from the same validated values used by GUI and exports."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    _set_document_style(document)
    _add_centered_heading(document, settings.report_title or view_model.title, 20)
    if settings.report_sub_title:
        _add_centered_heading(document, settings.report_sub_title, 13)
    document.add_paragraph("fNIRS 血行動力研究分析")

    _add_key_value_table(
        document,
        (
            ("個案／受試者編號", patient.patient_id),
            ("姓名", patient.name),
            ("性別", patient.gender),
            (
                "測量日期",
                patient.measurement_date.isoformat() if patient.measurement_date else "",
            ),
        ),
    )

    document.add_heading("ROI 結果摘要", level=1)
    result_table = document.add_table(rows=1, cols=7)
    result_table.style = "Table Grid"
    headers = ("ROI", "Integral", "Centroid (s)", "Slope", "有效通道", "預期通道", "警告")
    for cell, header in zip(result_table.rows[0].cells, headers, strict=True):
        cell.text = header
    for summary in view_model.roi_summaries:
        cells = result_table.add_row().cells
        values = (
            summary.display_name,
            _format_numeric(summary.integral, 2),
            _format_numeric(summary.centroid, 2),
            _format_numeric(summary.slope, 4),
            str(summary.valid_channels),
            str(summary.expected_channels),
            " · ".join(summary.warnings),
        )
        for cell, value in zip(cells, values, strict=True):
            cell.text = value

    if view_model.laterality is not None:
        document.add_heading("側化指標 LI", level=1)
        result = view_model.laterality
        _add_key_value_table(
            document,
            (
                ("Left PFC", _format_numeric(result.left, 3)),
                ("Right PFC", _format_numeric(result.right, 3)),
                ("LI", _format_numeric(result.value, 3)),
                ("分類", result.direction.value if result.direction is not None else "無法計算"),
                ("警告", " · ".join(result.warnings)),
            ),
        )

    document.add_heading("品質控管", level=1)
    quality_text = " · ".join(view_model.quality_summary) or "未記錄品質警告"
    document.add_paragraph(quality_text)
    for exclusion in view_model.exclusions:
        document.add_paragraph(str(exclusion), style="List Bullet")

    page_order = ("overview", "laterality", "prepost", "regional")
    captions = {
        "overview": "圖 1　通道矩陣、ROI 平均波形及 Integral–Centroid Plot Map",
        "laterality": "圖 2　側化指標 LI",
        "prepost": "圖 3　前後測差異",
        "regional": "圖 4　腦區活化差異",
    }
    inserted = 0
    for page_name in page_order:
        image_path = rendered_pages.get(page_name)
        if image_path is None or not Path(image_path).is_file():
            continue
        document.add_page_break()
        document.add_picture(str(image_path), width=Inches(10.3))
        paragraph = document.add_paragraph(captions[page_name])
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        inserted += 1

    document.add_page_break()
    document.add_heading("分析方法與追溯資訊", level=1)
    config_rows = tuple(
        (str(key), json.dumps(value, ensure_ascii=False, default=str))
        for key, value in sorted(view_model.analysis_config.items())
    )
    provenance_rows = tuple(
        (f"provenance.{key}", json.dumps(value, ensure_ascii=False, default=str))
        for key, value in sorted(view_model.provenance.items())
    )
    _add_key_value_table(
        document,
        (
            *config_rows,
            *provenance_rows,
            ("analysis_config_sha256", _analysis_config_digest(view_model.analysis_config)),
            ("rendered_page_count", str(inserted)),
        ),
    )
    document.add_heading("限制與聲明", level=1)
    document.add_paragraph(
        "fNIRS 為間接血行動力指標，可能受動作、頭皮血流與全身性生理訊號影響。"
        "本報告僅供研究與教育用途，不得作為單獨臨床診斷依據。"
    )
    document.add_paragraph("所有估計值、警告、排除項目與分析設定應合併解讀。")

    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=".docx",
        dir=destination.parent,
        delete=False,
    ) as temporary_handle:
        temporary = Path(temporary_handle.name)
    try:
        document.save(temporary)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination
