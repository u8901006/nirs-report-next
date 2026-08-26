from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class AnalysisSettings:
    task_start: str = "30"
    task_end: str = "90"
    measure_end: str = "160"
    y_upper_limit: str = "4"
    y_lower_limit: str = "-4"
    isFigureReport: bool = False
    isOpenReport: bool = False
    filter_num: int = 0
    last_open_dir: str = ""


@dataclass(slots=True)
class ReportSettings:
    report_title: str = ""
    report_sub_title: str = ""
    isShowDoctor: bool = True
    isShowOpinion: bool = True
    isShowBirthAndAge: bool = True


def load_settings(path: Path, model: type[T]) -> T:
    defaults = model()
    if not path.exists():
        return defaults
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return defaults
    if not isinstance(loaded, dict):
        return defaults
    allowed = {field.name for field in fields(defaults)}
    values = asdict(defaults)
    values.update({key: value for key, value in loaded.items() if key in allowed})
    return model(**values)


def save_settings(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(asdict(value), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
