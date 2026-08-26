from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .mbll import convert_timeseries_matrix


@dataclass(frozen=True, slots=True)
class LoadedNirsData:
    hbo: pd.DataFrame
    hbr: pd.DataFrame
    time_seconds: np.ndarray
    sample_rate: float
    legacy_format: bool


def _sample_rate(time_seconds: np.ndarray) -> float:
    if len(time_seconds) < 2:
        raise ValueError("NIRS data must contain at least two time samples")
    step = float(time_seconds[1] - time_seconds[0])
    if step <= 0:
        raise ValueError("Time axis must be increasing")
    return 1.0 / step


def load_nirs_workbook(path: Path, distance_mm: float = 30.0) -> LoadedNirsData:
    workbook = pd.ExcelFile(path)
    filtered_sheet = next(
        (name for name in ("Filtered ΔHb", "Padded ΔHb") if name in workbook.sheet_names),
        None,
    )
    if filtered_sheet:
        combined = pd.read_excel(path, sheet_name=filtered_sheet)
        time_seconds = combined["Time (sec)"].to_numpy(dtype=float)
        hbo_columns = [column for column in combined.columns if "HbO" in str(column)]
        hbr_columns = [column for column in combined.columns if "HbR" in str(column)]
        if not hbo_columns or not hbr_columns:
            raise ValueError(f"Sheet {filtered_sheet!r} has no HbO/HbR channels")
        delta_a_850 = pd.DataFrame(
            {f"ch{index}": combined[column] for index, column in enumerate(hbo_columns, 1)}
        )
        delta_a_760 = pd.DataFrame(
            {f"ch{index}": combined[column] for index, column in enumerate(hbr_columns, 1)}
        )
        hbo, hbr = convert_timeseries_matrix(
            delta_a_850, delta_a_760, time_seconds, distance_mm
        )
        return LoadedNirsData(hbo, hbr, time_seconds, _sample_rate(time_seconds), False)

    if {"HbO", "HbR"}.issubset(workbook.sheet_names):
        try:
            hbo = pd.read_excel(path, sheet_name="HbO", header=2)
            hbr = pd.read_excel(path, sheet_name="HbR", header=2)
            if "Time" not in hbo.columns or "Time" not in hbr.columns:
                raise KeyError("legacy header row was not found")
        except KeyError:
            hbo = pd.read_excel(path, sheet_name="HbO")
            hbr = pd.read_excel(path, sheet_name="HbR")
        time_seconds = hbo["Time"].to_numpy(dtype=float)
        return LoadedNirsData(hbo, hbr, time_seconds, _sample_rate(time_seconds), True)

    raise ValueError(
        "Workbook must contain 'Filtered ΔHb'/'Padded ΔHb' or both 'HbO' and 'HbR' sheets"
    )
