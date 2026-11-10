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
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image

from .analysis.features import FeatureResult
from .messages import DIRECTION_TEXT, describe_warning, describe_warnings, roi_label
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


REPORT_FONT = "Microsoft JhengHei"
INK = RGBColor(0x17, 0x24, 0x3A)
MUTED = RGBColor(0x56, 0x62, 0x75)
WARNING = RGBColor(0xA1, 0x5C, 0x00)
RULE_HEX = "C9D1DB"
HEADER_FILL_HEX = "EEF2F6"

PAGE_WIDTH = Mm(297)
PAGE_HEIGHT = Mm(210)
MARGIN_X = Mm(16)
MARGIN_TOP = Mm(20)
MARGIN_BOTTOM = Mm(17)
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X
CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
CAPTION_ALLOWANCE = Mm(12)

DISCLAIMER = (
    "fNIRS 為間接血行動力指標，可能受動作、頭皮血流與全身性生理訊號影響。"
    "本報告僅供研究與教育用途，不得作為單獨臨床診斷依據。"
)

CONFIG_LABELS = {
    "sample_rate": "取樣頻率 (Hz)",
    "task_start": "作業開始 (秒)",
    "task_end": "作業結束 (秒)",
    "measure_end": "測量結束 (秒)",
    "baseline_end": "基線結束 (秒)",
    "filter_size": "平滑視窗",
    "bootstrap_seed": "Bootstrap 亂數種子",
}

SIGNATURE_BLANK = "＿" * 10


def _format_numeric(value: float | None, decimals: int) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def _set_style_font(
    style,
    *,
    size: float,
    bold: bool = False,
    color: RGBColor = INK,
) -> None:
    style.font.name = REPORT_FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = color
    fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attribute in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(attribute), None)
    for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        fonts.set(qn(attribute), REPORT_FONT)


def _set_document_style(document: Document) -> None:
    styles = document.styles
    _set_style_font(styles["Normal"], size=10)
    styles["Normal"].paragraph_format.space_after = Pt(4)
    _set_style_font(styles["Heading 1"], size=12, bold=True)
    heading = styles["Heading 1"].paragraph_format
    heading.space_before = Pt(14)
    heading.space_after = Pt(5)
    heading.keep_with_next = True
    for name in ("Header", "Footer"):
        _set_style_font(styles[name], size=8, color=MUTED)
        styles[name].paragraph_format.tab_stops.clear_all()

    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = PAGE_WIDTH
    section.page_height = PAGE_HEIGHT
    section.top_margin = MARGIN_TOP
    section.bottom_margin = MARGIN_BOTTOM
    section.left_margin = MARGIN_X
    section.right_margin = MARGIN_X
    section.header_distance = Mm(9)
    section.footer_distance = Mm(8)


def _add_run(
    paragraph,
    text: str,
    *,
    size: float | None = None,
    bold: bool | None = None,
    color: RGBColor | None = None,
):
    run = paragraph.add_run(text)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    return run


def _add_field(paragraph, instruction: str) -> None:
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), instruction)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "1"
    run.append(text)
    field.append(run)
    paragraph._p.append(field)


def _add_bottom_rule(paragraph) -> None:
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "17243A")
    borders.append(bottom)
    properties.append(borders)


def _set_running_header_footer(document: Document, title: str, patient: PatientInfo) -> None:
    section = document.sections[0]
    header = section.header.paragraphs[0]
    header.paragraph_format.tab_stops.add_tab_stop(CONTENT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    identity = " · ".join(
        part
        for part in (
            patient.patient_id,
            patient.measurement_date.isoformat() if patient.measurement_date else "",
        )
        if part
    )
    header.add_run(f"{title}\t{identity}")

    footer = section.footer.paragraphs[0]
    footer.paragraph_format.tab_stops.add_tab_stop(CONTENT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    footer.add_run("僅供研究與教育用途，不作單獨臨床診斷依據\t第 ")
    _add_field(footer, "PAGE")
    footer.add_run(" / ")
    _add_field(footer, "NUMPAGES")
    footer.add_run(" 頁")


def _set_table_rules(table, *, box: bool = False) -> None:
    """Draw horizontal hairlines only; a boxed table gets its outer frame instead."""
    properties = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    edges = ("top", "left", "bottom", "right") if box else ("top", "bottom", "insideH")
    for edge in edges:
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), RULE_HEX)
        borders.append(element)
    properties.append(borders)


def _set_column_widths(table, widths: tuple[int, ...]) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for row in table.rows:
        for cell, width in zip(row.cells, widths, strict=True):
            cell.width = width


def _shade(cell, fill_hex: str) -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def _write_cell(
    cell,
    text: str,
    *,
    size: float | None = None,
    bold: bool | None = None,
    color: RGBColor | None = None,
    align: WD_ALIGN_PARAGRAPH | None = None,
) -> None:
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(2)
    if align is not None:
        paragraph.alignment = align
    _add_run(paragraph, text, size=size, bold=bold, color=color)


def _add_data_table(
    document: Document,
    headers: tuple[str, ...],
    rows: list[tuple[str, ...]],
    widths: tuple[int, ...],
    numeric_columns: frozenset[int] = frozenset(),
    note_columns: frozenset[int] = frozenset(),
):
    table = document.add_table(rows=1, cols=len(headers))
    _set_table_rules(table)
    for index, (cell, header) in enumerate(zip(table.rows[0].cells, headers, strict=True)):
        _shade(cell, HEADER_FILL_HEX)
        _write_cell(
            cell,
            header,
            size=9,
            bold=True,
            align=WD_ALIGN_PARAGRAPH.RIGHT if index in numeric_columns else None,
        )
    for values in rows:
        cells = table.add_row().cells
        for index, (cell, value) in enumerate(zip(cells, values, strict=True)):
            if index in note_columns:
                _write_cell(cell, value, size=8.5, color=WARNING)
            elif index in numeric_columns:
                _write_cell(cell, value, align=WD_ALIGN_PARAGRAPH.RIGHT)
            else:
                _write_cell(cell, value)
    _set_column_widths(table, widths)
    return table


def _add_identity_strip(document: Document, settings: ReportSettings, patient: PatientInfo) -> None:
    fields = [
        ("個案／受試者編號", patient.patient_id),
        ("姓名", patient.name),
        ("性別", patient.gender),
        ("測量日期", patient.measurement_date.isoformat() if patient.measurement_date else ""),
    ]
    if settings.isShowBirthAndAge and patient.birth_date is not None:
        fields.append(("出生日期", patient.birth_date.isoformat()))
    if settings.isShowDoctor:
        fields.append(("醫師", patient.doctor))
    table = document.add_table(rows=2, cols=len(fields))
    for index, (label, value) in enumerate(fields):
        _write_cell(table.rows[0].cells[index], label, size=8, color=MUTED)
        _write_cell(table.rows[1].cells[index], value or "—", size=11, bold=True)
    width = int(CONTENT_WIDTH / len(fields))
    _set_column_widths(table, (width,) * len(fields))


def _add_opinion_block(document: Document, settings: ReportSettings, patient: PatientInfo) -> None:
    if settings.isShowOpinion:
        document.add_heading("判讀意見", level=1)
        table = document.add_table(rows=1, cols=1)
        _set_table_rules(table, box=True)
        _write_cell(table.rows[0].cells[0], patient.opinion)
        if not patient.opinion:
            height = OxmlElement("w:trHeight")
            height.set(qn("w:val"), str(int(Mm(26).twips)))
            height.set(qn("w:hRule"), "atLeast")
            table.rows[0]._tr.get_or_add_trPr().append(height)
        _set_column_widths(table, (CONTENT_WIDTH,))
    if settings.isShowDoctor:
        signature = document.add_paragraph()
        signature.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        signature.paragraph_format.space_before = Pt(16)
        doctor = patient.doctor or SIGNATURE_BLANK
        _add_run(signature, f"醫師：{doctor}　　簽章：{SIGNATURE_BLANK}")


def _fit_picture(image_path: Path) -> tuple[int, int]:
    """Scale a picture to the text area so the picture and its caption share one page."""
    with Image.open(image_path) as image:
        pixel_width, pixel_height = image.size
    aspect = pixel_width / pixel_height
    available_height = CONTENT_HEIGHT - CAPTION_ALLOWANCE
    width = min(int(CONTENT_WIDTH), int(available_height * aspect))
    return width, int(width / aspect)


def _describe_exclusion(exclusion: object) -> str:
    code = getattr(exclusion, "code", None)
    if code is None:
        return str(exclusion)
    subject = getattr(exclusion, "subject_id", None)
    message = getattr(exclusion, "message", None)
    return "：".join(str(part) for part in (subject, describe_warning(code), message) if part)


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
    """Build the research report from the same validated values used by GUI and exports.

    Page 1 is a one-page summary (identity, numbers, quality, opinion). Figures follow, one
    per page and scaled to the text area. Settings and provenance close the report as an
    appendix.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    _set_document_style(document)
    title = settings.report_title or view_model.title
    _set_running_header_footer(document, title, patient)

    heading = document.add_paragraph()
    heading.paragraph_format.space_after = Pt(0)
    _add_run(heading, title, size=20, bold=True)
    subtitle = document.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(8)
    subtitle_parts = (settings.report_sub_title, "fNIRS 血行動力研究分析")
    _add_run(subtitle, " ｜ ".join(part for part in subtitle_parts if part), size=10, color=MUTED)
    _add_bottom_rule(subtitle)
    _add_identity_strip(document, settings, patient)

    document.add_heading("區域結果摘要", level=1)
    _add_data_table(
        document,
        (
            "區域 ROI",
            "積分值 Integral",
            "重心時間 Centroid (秒)",
            "回復斜率 Slope",
            "有效通道",
            "備註",
        ),
        [
            (
                roi_label(summary.roi_id, summary.display_name),
                _format_numeric(summary.integral, 2),
                _format_numeric(summary.centroid, 2),
                _format_numeric(summary.slope, 4),
                f"{summary.valid_channels} / {summary.expected_channels}",
                describe_warnings(summary.warnings),
            )
            for summary in view_model.roi_summaries
        ],
        widths=(Mm(58), Mm(34), Mm(42), Mm(34), Mm(24), CONTENT_WIDTH - Mm(192)),
        numeric_columns=frozenset({1, 2, 3, 4}),
        note_columns=frozenset({5}),
    )

    if view_model.laterality is not None:
        document.add_heading("側化指標 LI", level=1)
        result = view_model.laterality
        direction = (
            DIRECTION_TEXT.get(result.direction.value, result.direction.value)
            if result.direction is not None
            else "無法計算"
        )
        _add_data_table(
            document,
            ("左前額葉 Left PFC", "右前額葉 Right PFC", "LI", "分類", "備註"),
            [
                (
                    _format_numeric(result.left, 3),
                    _format_numeric(result.right, 3),
                    _format_numeric(result.value, 3),
                    f"{direction}（切點 ±{result.threshold:.2f}）",
                    describe_warnings(result.warnings),
                )
            ],
            widths=(Mm(42), Mm(42), Mm(28), Mm(60), CONTENT_WIDTH - Mm(172)),
            numeric_columns=frozenset({0, 1, 2}),
            note_columns=frozenset({4}),
        )

    document.add_heading("品質控管", level=1)
    document.add_paragraph(describe_warnings(view_model.quality_summary) or "未記錄品質警告")
    for exclusion in view_model.exclusions:
        document.add_paragraph(_describe_exclusion(exclusion), style="List Bullet")

    _add_opinion_block(document, settings, patient)

    page_order = ("overview", "laterality", "prepost", "regional")
    captions = {
        "overview": "通道矩陣、ROI 平均波形及 Integral–Centroid Plot Map",
        "laterality": "側化指標 LI",
        "prepost": "前後測差異",
        "regional": "腦區活化差異",
    }
    inserted = 0
    for page_name in page_order:
        image_path = rendered_pages.get(page_name)
        if image_path is None or not Path(image_path).is_file():
            continue
        inserted += 1
        width, height = _fit_picture(Path(image_path))
        picture = document.add_paragraph()
        picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
        picture.paragraph_format.page_break_before = True
        picture.paragraph_format.keep_with_next = True
        picture.paragraph_format.space_after = Pt(4)
        picture.add_run().add_picture(str(image_path), width=width, height=height)
        caption = document.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _add_run(caption, f"圖 {inserted}　", size=9, bold=True)
        _add_run(caption, captions[page_name], size=9, color=MUTED)

    appendix = document.add_heading("附錄　分析方法與追溯資訊", level=1)
    appendix.paragraph_format.page_break_before = True
    config_rows = [
        (
            CONFIG_LABELS.get(str(key), ""),
            str(key),
            json.dumps(value, ensure_ascii=False, default=str),
        )
        for key, value in sorted(view_model.analysis_config.items())
    ]
    provenance_rows = [
        ("來源追溯", f"provenance.{key}", json.dumps(value, ensure_ascii=False, default=str))
        for key, value in sorted(view_model.provenance.items())
    ]
    table = _add_data_table(
        document,
        ("項目", "鍵", "值"),
        [
            *config_rows,
            *provenance_rows,
            (
                "設定指紋 (SHA-256)",
                "analysis_config_sha256",
                _analysis_config_digest(view_model.analysis_config),
            ),
            ("報告內圖片頁數", "rendered_page_count", str(inserted)),
        ],
        widths=(Mm(60), Mm(70), CONTENT_WIDTH - Mm(130)),
    )
    for row in table.rows[1:]:
        for cell in row.cells[1:]:
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(8.5)
                run.font.color.rgb = MUTED
    document.add_heading("限制與聲明", level=1)
    document.add_paragraph(DISCLAIMER)
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
