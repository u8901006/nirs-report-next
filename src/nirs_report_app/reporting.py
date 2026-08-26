from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .analysis.features import FeatureResult
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
