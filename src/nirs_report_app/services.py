from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis.features import FeatureResult, calculate_features, centroid_index, positive_integral
from .analysis.filters import mean_filter
from .analysis.laterality import LateralityResult, calculate_li
from .analysis.loader import LoadedNirsData, load_nirs_workbook
from .analysis.metrics import baseline_corrected_mean, recovery_slope
from .analysis.models import BUILTIN_ROIS, RoiSignal
from .analysis.prepost import PairingResult, pair_pre_post
from .analysis.quality import aggregate_roi
from .analysis.regions import RegionSignals, compute_region_signals
from .analysis.regional import RegionalComparisonResult, compare_regions
from .dataset import ManifestIssue, load_manifest
from .report_models import ChannelSeries, PlotPoint, ReportViewModel, RoiSummary


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    data: LoadedNirsData
    regions: RegionSignals
    features: FeatureResult
    roi_signals_hbo: dict[str, RoiSignal] = field(default_factory=dict)
    roi_signals_hbr: dict[str, RoiSignal] = field(default_factory=dict)
    roi_metrics: dict[str, "RoiMetricSummary"] = field(default_factory=dict)
    laterality: LateralityResult | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoiMetricSummary:
    baseline_corrected_mean: float
    positive_integral: float
    signed_integral: float
    centroid_time: float | None
    recovery_slope: float


@dataclass(frozen=True, slots=True)
class SingleAnalysisRequest:
    path: Path
    task_start: float
    task_end: float
    measure_end: float
    baseline_start: float = 0.0
    baseline_end: float | None = None
    filter_size: int = 0
    distance_mm: float = 30.0
    excluded_channels: tuple[int, ...] = ()
    li_threshold: float = 0.10


@dataclass(frozen=True, slots=True)
class StudyAnalysisRequest:
    manifest_path: Path
    task_start: float
    task_end: float
    measure_end: float
    baseline_start: float = 0.0
    baseline_end: float | None = None
    filter_size: int = 0
    distance_mm: float = 30.0


@dataclass(frozen=True, slots=True)
class StudyAnalysisResult:
    subject_level_results: pd.DataFrame
    single_results: dict[tuple[str, str, str], AnalysisResult]
    pairing: PairingResult | None
    regional: RegionalComparisonResult | None
    errors: tuple[ManifestIssue, ...]


def build_report_view_model(
    result: AnalysisResult,
    *,
    title: str = "NIRS 分析報告",
) -> ReportViewModel:
    scale = 1000.0 if result.data.legacy_format else 1.0
    channel_series: dict[int, ChannelSeries] = {}
    for channel in range(1, 16):
        column = f"ch{channel}"
        if column not in result.data.hbo.columns or column not in result.data.hbr.columns:
            channel_series[channel] = ChannelSeries(
                channel,
                np.full(len(result.data.time_seconds), np.nan),
                np.full(len(result.data.time_seconds), np.nan),
                "missing",
                ("W_CHANNEL_MISSING",),
            )
            continue
        hbo = pd.to_numeric(result.data.hbo[column], errors="coerce").to_numpy(float) * scale
        hbr = pd.to_numeric(result.data.hbr[column], errors="coerce").to_numpy(float) * scale
        finite = np.isfinite(hbo) & np.isfinite(hbr)
        if not finite.any():
            state = "invalid"
        elif not finite.all():
            state = "partial"
        else:
            state = "valid"
        channel_series[channel] = ChannelSeries(channel, hbo, hbr, state)

    roi_summaries: list[RoiSummary] = []
    plot_points: list[PlotPoint] = []
    for roi_id, definition in BUILTIN_ROIS.items():
        hbo_signal = result.roi_signals_hbo[roi_id]
        hbr_signal = result.roi_signals_hbr[roi_id]
        metric = result.roi_metrics[roi_id]
        summary = RoiSummary(
            roi_id,
            definition.name,
            hbo_signal.values,
            hbr_signal.values,
            metric.positive_integral if np.isfinite(metric.positive_integral) else None,
            metric.centroid_time,
            metric.recovery_slope if np.isfinite(metric.recovery_slope) else None,
            hbo_signal.valid_channel_count,
            hbo_signal.expected_channel_count,
            hbo_signal.warnings,
        )
        roi_summaries.append(summary)
        if summary.integral is not None and summary.centroid is not None:
            plot_points.append(PlotPoint(roi_id, summary.integral, summary.centroid))
    return ReportViewModel(
        title=title,
        time_seconds=result.data.time_seconds,
        channel_series=channel_series,
        roi_summaries=tuple(roi_summaries),
        plot_points=tuple(plot_points),
        laterality=result.laterality,
        analysis_config={"sample_rate": result.data.sample_rate},
        quality_summary=result.warnings,
    )


class NirsAnalysisService:
    @staticmethod
    def _slice(start: float, end: float, sample_rate: float, length: int) -> slice:
        first = int(round(start * sample_rate))
        last = int(round(end * sample_rate))
        if first < 0 or last > length or first >= last:
            raise ValueError(f"E_WINDOW_OUT_OF_RANGE: {start}–{end} seconds")
        return slice(first, last)

    @staticmethod
    def _filter_regions(regions: RegionSignals, filter_size: int) -> RegionSignals:
        if filter_size <= 1:
            return regions
        if filter_size % 2 == 0:
            filter_size += 1

        def filtered(values: np.ndarray | None) -> np.ndarray | None:
            return mean_filter(values, filter_size) if values is not None else None

        return RegionSignals(
            mean_filter(regions.front_hbo, filter_size),
            mean_filter(regions.front_hbr, filter_size),
            mean_filter(regions.side_hbo, filter_size),
            mean_filter(regions.side_hbr, filter_size),
            filtered(regions.right_pfc_hbo),
            filtered(regions.right_pfc_hbr),
            filtered(regions.left_pfc_hbo),
            filtered(regions.left_pfc_hbr),
        )

    def analyze_single(self, request: SingleAnalysisRequest) -> AnalysisResult:
        data = load_nirs_workbook(request.path, request.distance_mm)
        regions = compute_region_signals(data.hbo, data.hbr, data.legacy_format)
        regions = self._filter_regions(regions, request.filter_size)
        features = calculate_features(
            regions.front_hbo,
            regions.side_hbo,
            data.sample_rate,
            request.task_start,
            request.task_end,
            request.measure_end,
        )
        scale = 1000.0 if data.legacy_format else 1.0
        hbo_signals: dict[str, RoiSignal] = {}
        hbr_signals: dict[str, RoiSignal] = {}
        for roi_id, definition in BUILTIN_ROIS.items():
            hbo = aggregate_roi(
                data.hbo,
                definition,
                excluded_channels=request.excluded_channels,
            )
            hbr = aggregate_roi(
                data.hbr,
                definition,
                excluded_channels=request.excluded_channels,
            )
            if scale != 1.0:
                hbo = replace(hbo, values=hbo.values * scale)
                hbr = replace(hbr, values=hbr.values * scale)
            if request.filter_size > 1:
                size = request.filter_size + 1 if request.filter_size % 2 == 0 else request.filter_size
                hbo = replace(hbo, values=mean_filter(hbo.values, size))
                hbr = replace(hbr, values=mean_filter(hbr.values, size))
            hbo_signals[roi_id] = hbo
            hbr_signals[roi_id] = hbr

        baseline_end = request.baseline_end if request.baseline_end is not None else request.task_start
        baseline_window = self._slice(
            request.baseline_start, baseline_end, data.sample_rate, len(data.time_seconds)
        )
        task_window = self._slice(
            request.task_start, request.task_end, data.sample_rate, len(data.time_seconds)
        )
        recovery_window = self._slice(
            request.task_end, request.measure_end, data.sample_rate, len(data.time_seconds)
        )
        metrics: dict[str, RoiMetricSummary] = {}
        for roi_id, signal in hbo_signals.items():
            task_values = signal.values[task_window]
            centroid = centroid_index(task_values, 1 / data.sample_rate)
            centroid_time = (
                request.task_start + centroid / data.sample_rate if centroid >= 0 else None
            )
            metrics[roi_id] = RoiMetricSummary(
                baseline_corrected_mean(signal.values, baseline_window, task_window),
                positive_integral(task_values, 1 / data.sample_rate),
                positive_integral(task_values, 1 / data.sample_rate, exclude_negative=False),
                centroid_time,
                recovery_slope(
                    signal.values[recovery_window], data.time_seconds[recovery_window]
                ),
            )
        laterality = calculate_li(
            metrics["left_pfc"].baseline_corrected_mean,
            metrics["right_pfc"].baseline_corrected_mean,
            request.li_threshold,
        )
        warnings = tuple(
            dict.fromkeys(
                warning
                for signal in (*hbo_signals.values(), *hbr_signals.values())
                for warning in signal.warnings
            )
        )
        return AnalysisResult(
            data,
            regions,
            features,
            hbo_signals,
            hbr_signals,
            metrics,
            laterality,
            warnings,
        )

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
        return self.analyze_single(
            SingleAnalysisRequest(
                path=path,
                task_start=task_start,
                task_end=task_end,
                measure_end=measure_end,
                baseline_end=task_start,
                filter_size=filter_size,
                distance_mm=distance_mm,
            )
        )

    def analyze_study(self, request: StudyAnalysisRequest) -> StudyAnalysisResult:
        manifest = load_manifest(request.manifest_path)
        if not manifest.is_valid:
            return StudyAnalysisResult(pd.DataFrame(), {}, None, None, manifest.errors)
        singles: dict[tuple[str, str, str], AnalysisResult] = {}
        rows: list[dict[str, object]] = []
        errors: list[ManifestIssue] = []
        for row_number, record in enumerate(manifest.records, start=2):
            try:
                single = self.analyze_single(
                    SingleAnalysisRequest(
                        path=record.file_path,
                        task_start=record.task_start
                        if record.task_start is not None
                        else request.task_start,
                        task_end=record.task_end if record.task_end is not None else request.task_end,
                        measure_end=record.measure_end
                        if record.measure_end is not None
                        else request.measure_end,
                        baseline_start=record.baseline_start
                        if record.baseline_start is not None
                        else request.baseline_start,
                        baseline_end=record.baseline_end
                        if record.baseline_end is not None
                        else request.baseline_end,
                        filter_size=request.filter_size,
                        distance_mm=request.distance_mm,
                    )
                )
            except Exception as error:  # file boundary records and continues batch processing
                errors.append(
                    ManifestIssue(row_number, "E_ANALYSIS_FILE", f"{record.file_path}: {error}")
                )
                continue
            key = (record.subject_id, record.session, record.condition)
            singles[key] = single
            for roi_id, metric in single.roi_metrics.items():
                signal = single.roi_signals_hbo[roi_id]
                rows.append(
                    {
                        "subject_id": record.subject_id,
                        "group": record.group,
                        "session": record.session,
                        "condition": record.condition,
                        "roi": roi_id,
                        "chromophore": "HbO",
                        "metric_name": "baseline_corrected_mean",
                        "metric_value": metric.baseline_corrected_mean,
                        "valid_channel_count": signal.valid_channel_count,
                        "expected_channel_count": signal.expected_channel_count,
                        "quality_status": signal.status.value,
                        "warning_codes": ";".join(signal.warnings),
                        "source_file": str(record.file_path),
                    }
                )
        subject_frame = pd.DataFrame(rows)
        pairing = None
        regional = None
        if not subject_frame.empty:
            anterior = subject_frame[subject_frame["roi"] == "anterior_frontal"]
            pairing = pair_pre_post(anterior)
            baseline_rows = subject_frame[subject_frame["session"] == "pre"]
            if baseline_rows["roi"].nunique() >= 2:
                regional = compare_regions(
                    baseline_rows,
                    tuple(
                        roi
                        for roi in ("right_pfc", "anterior_frontal", "left_pfc")
                        if roi in set(baseline_rows["roi"])
                    ),
                )
        return StudyAnalysisResult(subject_frame, singles, pairing, regional, tuple(errors))
