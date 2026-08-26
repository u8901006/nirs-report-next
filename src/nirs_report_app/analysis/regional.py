from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

from ..statistics import StatisticalResult, adjust_pvalues, paired_test


@dataclass(frozen=True, slots=True)
class RegionalContrast:
    first_roi: str
    second_roi: str
    result: StatisticalResult

    @property
    def label(self) -> str:
        return f"{self.first_roi} - {self.second_roi}"

    @property
    def adjusted_p_value(self) -> float | None:
        return self.result.adjusted_p_value


@dataclass(frozen=True, slots=True)
class RegionalComparisonResult:
    contrasts: tuple[RegionalContrast, ...]
    correction: str


def compare_regions(
    rows: pd.DataFrame,
    rois: tuple[str, ...],
    *,
    correction: str = "holm",
) -> RegionalComparisonResult:
    roi_set = set(rois)
    if "lateral_frontal" in roi_set and roi_set.intersection({"left_pfc", "right_pfc"}):
        raise ValueError("The derived lateral_frontal ROI cannot be independent of its components")
    pivot = rows[rows["roi"].isin(rois)].pivot_table(
        index="subject_id",
        columns="roi",
        values="metric_value",
        aggfunc="first",
    )
    contrasts: list[RegionalContrast] = []
    p_values: list[float] = []
    for first, second in combinations(rois, 2):
        paired = pivot[[first, second]].dropna() if {first, second}.issubset(pivot.columns) else pd.DataFrame()
        if paired.empty:
            result = paired_test([], [])
        else:
            result = paired_test(paired[second].to_numpy(), paired[first].to_numpy())
        contrasts.append(RegionalContrast(first, second, result))
        p_values.append(result.p_value if result.p_value is not None else 1.0)
    adjusted = adjust_pvalues(p_values, method=correction)
    output = tuple(
        RegionalContrast(item.first_roi, item.second_roi, item.result.with_adjusted_p(value))
        for item, value in zip(contrasts, adjusted, strict=True)
    )
    return RegionalComparisonResult(output, correction)
