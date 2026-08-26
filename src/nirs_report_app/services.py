from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .analysis.features import FeatureResult, calculate_features
from .analysis.filters import mean_filter
from .analysis.loader import LoadedNirsData, load_nirs_workbook
from .analysis.regions import RegionSignals, compute_region_signals


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    data: LoadedNirsData
    regions: RegionSignals
    features: FeatureResult


class NirsAnalysisService:
    def analyze(
        self,
        path: Path,
        *,
        task_start: float,
        task_end: float,
        measure_end: float,
        filter_size: int = 0,
        distance_mm: float = 30.0,
    ) -> AnalysisResult:
        data = load_nirs_workbook(path, distance_mm)
        regions = compute_region_signals(data.hbo, data.hbr, data.legacy_format)
        if filter_size > 1:
            if filter_size % 2 == 0:
                filter_size += 1
            regions = RegionSignals(
                mean_filter(regions.front_hbo, filter_size),
                mean_filter(regions.front_hbr, filter_size),
                mean_filter(regions.side_hbo, filter_size),
                mean_filter(regions.side_hbr, filter_size),
            )
        features = calculate_features(
            regions.front_hbo,
            regions.side_hbo,
            data.sample_rate,
            task_start,
            task_end,
            measure_end,
        )
        return AnalysisResult(data, regions, features)
