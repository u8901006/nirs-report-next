from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class StudyRecord:
    subject_id: str
    file_path: Path
    session: str
    group: str = "all"
    condition: str = "task"
    measurement_date: date | None = None
    task_start: float | None = None
    task_end: float | None = None
    baseline_start: float | None = None
    baseline_end: float | None = None
    measure_end: float | None = None


@dataclass(frozen=True, slots=True)
class ManifestIssue:
    row: int | None
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ManifestResult:
    records: tuple[StudyRecord, ...]
    errors: tuple[ManifestIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return float(value)


def load_manifest(path: Path) -> ManifestResult:
    manifest_path = Path(path).resolve()
    if manifest_path.suffix.lower() in {".xlsx", ".xls"}:
        frame = pd.read_excel(manifest_path)
    else:
        frame = pd.read_csv(manifest_path)
    required = {"subject_id", "file_path", "session"}
    missing_columns = sorted(required - set(frame.columns))
    if missing_columns:
        return ManifestResult(
            (),
            (
                ManifestIssue(
                    None,
                    "E_MANIFEST_COLUMNS",
                    f"Missing required columns: {', '.join(missing_columns)}",
                ),
            ),
        )

    errors: list[ManifestIssue] = []
    records: list[StudyRecord] = []
    seen: dict[tuple[str, str, str], int] = {}
    for index, row in frame.iterrows():
        row_number = int(index) + 2
        subject_id = str(row["subject_id"]).strip()
        session = str(row["session"]).strip()
        condition_value = row.get("condition", "task")
        condition = "task" if pd.isna(condition_value) else str(condition_value).strip() or "task"
        key = (subject_id, session, condition)
        if key in seen:
            errors.append(
                ManifestIssue(
                    row_number,
                    "E_DUPLICATE_STUDY_KEY",
                    f"Duplicate subject/session/condition key first seen on row {seen[key]}",
                )
            )
        else:
            seen[key] = row_number
        raw_file = str(row["file_path"]).strip()
        source = Path(raw_file)
        if not source.is_absolute():
            source = manifest_path.parent / source
        source = source.resolve()
        if not source.is_file():
            errors.append(
                ManifestIssue(row_number, "E_SOURCE_FILE", f"Source workbook is not readable: {source}")
            )
        group_value = row.get("group", "all")
        group = "all" if pd.isna(group_value) else str(group_value).strip() or "all"
        date_value = row.get("measurement_date")
        measurement_date = None
        if date_value is not None and not pd.isna(date_value) and str(date_value).strip():
            measurement_date = pd.Timestamp(date_value).date()
        records.append(
            StudyRecord(
                subject_id=subject_id,
                file_path=source,
                session=session,
                group=group,
                condition=condition,
                measurement_date=measurement_date,
                task_start=_optional_float(row.get("task_start")),
                task_end=_optional_float(row.get("task_end")),
                baseline_start=_optional_float(row.get("baseline_start")),
                baseline_end=_optional_float(row.get("baseline_end")),
                measure_end=_optional_float(row.get("measure_end")),
            )
        )
    return ManifestResult(tuple(records), tuple(errors))
