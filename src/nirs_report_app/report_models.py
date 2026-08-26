from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .analysis.laterality import LateralityResult


@dataclass(frozen=True, slots=True)
class ChannelSeries:
    channel: int
    hbo: np.ndarray
    hbr: np.ndarray
    state: str = "valid"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoiSummary:
    roi_id: str
    display_name: str
    hbo: np.ndarray
    hbr: np.ndarray
    integral: float | None
    centroid: float | None
    slope: float | None
    valid_channels: int
    expected_channels: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PlotPoint:
    roi_id: str
    integral: float
    centroid: float


@dataclass(frozen=True, slots=True)
class ReportViewModel:
    title: str
    time_seconds: np.ndarray
    channel_series: dict[int, ChannelSeries]
    roi_summaries: tuple[RoiSummary, ...]
    plot_points: tuple[PlotPoint, ...]
    laterality: LateralityResult | None = None
    prepost_result: Any | None = None
    regional_result: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    analysis_config: dict[str, Any] = field(default_factory=dict)
    quality_summary: tuple[str, ...] = ()
    exclusions: tuple[Any, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        time = np.asarray(self.time_seconds, dtype=float)
        for channel in self.channel_series.values():
            if len(channel.hbo) != len(time) or len(channel.hbr) != len(time):
                raise ValueError(f"Channel {channel.channel} length does not match time axis")
        summaries = {summary.roi_id: summary for summary in self.roi_summaries}
        for point in self.plot_points:
            summary = summaries.get(point.roi_id)
            if summary is None:
                raise ValueError(f"Plot point {point.roi_id} has no ROI summary")
            if summary.integral is None or summary.centroid is None:
                raise ValueError(f"Plot point {point.roi_id} represents an invalid ROI summary")
            if not np.isclose(point.integral, summary.integral) or not np.isclose(
                point.centroid, summary.centroid
            ):
                raise ValueError(f"Plot point {point.roi_id} does not match ROI summary")
