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
    right_pfc_hbo: np.ndarray | None = None
    right_pfc_hbr: np.ndarray | None = None
    left_pfc_hbo: np.ndarray | None = None
    left_pfc_hbr: np.ndarray | None = None

    @property
    def anterior_frontal_hbo(self) -> np.ndarray:
        return self.front_hbo

    @property
    def anterior_frontal_hbr(self) -> np.ndarray:
        return self.front_hbr

    @property
    def lateral_frontal_hbo(self) -> np.ndarray:
        return self.side_hbo

    @property
    def lateral_frontal_hbr(self) -> np.ndarray:
        return self.side_hbr


def roi_nanmean(frame: pd.DataFrame, channels: tuple[int, ...]) -> np.ndarray:
    columns = [f"ch{number}" for number in channels if f"ch{number}" in frame.columns]
    if not columns:
        return np.full(len(frame), np.nan, dtype=float)
    stack = np.vstack([frame[column].to_numpy(dtype=float) for column in columns])
    valid = np.isfinite(stack)
    counts = valid.sum(axis=0)
    sums = np.where(valid, stack, 0.0).sum(axis=0)
    return np.divide(
        sums,
        counts,
        out=np.full(len(frame), np.nan, dtype=float),
        where=counts > 0,
    )


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
    lateral_hbo = roi_nanmean(hbo, right_forehead + left_forehead)
    lateral_hbr = roi_nanmean(hbr, right_forehead + left_forehead)
    return RegionSignals(
        roi_nanmean(hbo, middle_forehead) * scale,
        roi_nanmean(hbr, middle_forehead) * scale,
        lateral_hbo * scale,
        lateral_hbr * scale,
        right_hbo * scale,
        right_hbr * scale,
        left_hbo * scale,
        left_hbr * scale,
    )
