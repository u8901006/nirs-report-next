from __future__ import annotations

import matplotlib
import numpy as np

matplotlib.use("Agg")

from nirs_report_app.analysis.laterality import LateralityResult, calculate_li
from nirs_report_app.analysis.prepost import PairExclusion, PairingResult
from nirs_report_app.analysis.regional import RegionalComparisonResult, RegionalContrast
from nirs_report_app.report_models import ChannelSeries, PlotPoint, ReportViewModel, RoiSummary
from nirs_report_app.statistics import StatisticalResult
from nirs_report_app.visualization import ReportDashboardRenderer


def make_view_model(*, valid_laterality: bool = True) -> ReportViewModel:
    time = np.linspace(0.0, 9.0, 10)
    channels = {
        channel: ChannelSeries(
            channel,
            np.sin(time / 3 + channel / 10),
            -0.3 * np.sin(time / 3 + channel / 10),
            "missing" if channel == 4 else "valid",
            ("W_CHANNEL_MISSING",) if channel == 4 else (),
        )
        for channel in range(1, 16)
    }
    summaries = (
        RoiSummary(
            "anterior_frontal",
            "Anterior Frontal Lobe",
            np.sin(time / 3),
            -0.3 * np.sin(time / 3),
            12.5,
            4.25,
            -0.0123,
            7,
            7,
        ),
        RoiSummary(
            "lateral_frontal",
            "Lateral Frontal Lobe",
            np.cos(time / 4),
            -0.2 * np.cos(time / 4),
            8.0,
            5.5,
            -0.004,
            7,
            8,
            ("W_ROI_DEGRADED",),
        ),
    )
    if valid_laterality:
        laterality = calculate_li(3.0, 1.0)
    else:
        laterality = LateralityResult(
            1.0,
            -1.0,
            None,
            None,
            0.10,
            ("W_LI_DENOMINATOR_SMALL",),
        )
    return ReportViewModel(
        title="NIRS 分析報告",
        time_seconds=time,
        channel_series=channels,
        roi_summaries=summaries,
        plot_points=(
            PlotPoint("anterior_frontal", 12.5, 4.25),
            PlotPoint("lateral_frontal", 8.0, 5.5),
        ),
        laterality=laterality,
        analysis_config={"bootstrap_seed": 20260826},
        quality_summary=("W_CHANNEL_MISSING",),
    )


def test_overview_has_fixed_montage_roi_cards_and_matching_plot_points() -> None:
    model = make_view_model()
    figure = ReportDashboardRenderer().render_overview(model)

    labels = {axis.get_label() for axis in figure.axes}
    assert {f"channel:{channel}" for channel in range(1, 16)} <= labels
    assert {"roi:anterior_frontal", "roi:lateral_frontal", "plot-map"} <= labels
    assert {text.get_text() for text in figure.texts} >= {
        "右前額葉 Right PFC",
        "前額中區 Anterior Frontal",
        "左前額葉 Left PFC",
    }

    missing_axis = next(axis for axis in figure.axes if axis.get_label() == "channel:4")
    assert "缺少 CH04" in {text.get_text() for text in missing_axis.texts}
    assert not missing_axis.lines

    plot_axis = next(axis for axis in figure.axes if axis.get_label() == "plot-map")
    plotted = {
        tuple(float(value) for value in collection.get_offsets()[0])
        for collection in plot_axis.collections
        if len(collection.get_offsets())
    }
    assert plotted == {(12.5, 4.25), (8.0, 5.5)}


def test_advanced_pages_show_estimates_and_invalid_warning_text() -> None:
    renderer = ReportDashboardRenderer()
    valid_model = make_view_model()

    li_figure = renderer.render_laterality(valid_model)
    assert any("LI = 0.500" in text.get_text() for text in li_figure.texts)

    invalid_model = make_view_model(valid_laterality=False)
    invalid_figure = renderer.render_laterality(invalid_model)
    assert any("W_LI_DENOMINATOR_SMALL" in text.get_text() for text in invalid_figure.texts)

    prepost = PairingResult(
        pairs=np_to_frame([["S01", 1.0, 2.0, 1.0]], ["subject_id", "pre", "post", "delta"]),
        total_subjects=2,
        paired_n=1,
        exclusions=(PairExclusion("S02", "E_PAIR_INCOMPLETE", "missing post"),),
    )
    prepost_model = replace_model(valid_model, prepost_result=prepost)
    prepost_figure = renderer.render_prepost(prepost_model)
    assert any("平均差 = 1.000" in text.get_text() for text in prepost_figure.texts)
    assert any("E_PAIR_INCOMPLETE" in text.get_text() for text in prepost_figure.texts)

    result = StatisticalResult(
        estimate=0.4,
        standard_error=0.1,
        confidence_interval=(0.2, 0.6),
        statistic=4.0,
        p_value=0.02,
        adjusted_p_value=0.04,
        effect_size=0.8,
        n_included=10,
        n_excluded=0,
        method="paired t-test",
    )
    regional = RegionalComparisonResult(
        contrasts=(RegionalContrast("left_pfc", "right_pfc", result),),
        correction="holm",
    )
    regional_model = replace_model(valid_model, regional_result=regional)
    regional_figure = renderer.render_regional(regional_model)
    assert any("left_pfc - right_pfc = 0.400" in text.get_text() for text in regional_figure.texts)


def np_to_frame(rows: list[list[object]], columns: list[str]):
    import pandas as pd

    return pd.DataFrame(rows, columns=columns)


def replace_model(model: ReportViewModel, **changes: object) -> ReportViewModel:
    from dataclasses import replace

    return replace(model, **changes)
