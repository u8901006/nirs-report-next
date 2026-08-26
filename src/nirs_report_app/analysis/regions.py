from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class RegionSignals:
    front_hbo: np.ndarray
    front_hbr: np.ndarray
    side_hbo: np.ndarray
    side_hbr: np.ndarray


def roi_nanmean(frame: pd.DataFrame, channels: tuple[int, ...]) -> np.ndarray:
    columns = [f"ch{number}" for number in channels if f"ch{number}" in frame.columns]
    if not columns:
        return np.zeros(len(frame), dtype=float)
    stack = np.vstack([frame[column].to_numpy(dtype=float) for column in columns])
    return np.nan_to_num(np.nanmean(stack, axis=0), nan=0.0)


def compute_region_signals(
    hbo: pd.DataFrame,
    hbr: pd.DataFrame,
    legacy_format: bool,
) -> RegionSignals:
    right_forehead = (1, 2, 3, 4)
    middle_forehead = (5, 6, 7, 8, 9, 10, 11)
    left_forehead = (12, 13, 14, 15)
    scale = 1000.0 if legacy_format else 1.0
    right_hbo = roi_nanmean(hbo, right_forehead)
    left_hbo = roi_nanmean(hbo, left_forehead)
    right_hbr = roi_nanmean(hbr, right_forehead)
    left_hbr = roi_nanmean(hbr, left_forehead)
    return RegionSignals(
        roi_nanmean(hbo, middle_forehead) * scale,
        roi_nanmean(hbr, middle_forehead) * scale,
        np.nan_to_num(np.nanmean(np.vstack([right_hbo, left_hbo]), axis=0), nan=0.0)
        * scale,
        np.nan_to_num(np.nanmean(np.vstack([right_hbr, left_hbr]), axis=0), nan=0.0)
        * scale,
    )
