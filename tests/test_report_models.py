import numpy as np
import pytest

from nirs_report_app.analysis.laterality import calculate_li
from nirs_report_app.report_models import PlotPoint, ReportViewModel, RoiSummary


def test_report_view_model_accepts_absent_optional_analysis_pages() -> None:
    summary = RoiSummary(
        roi_id="anterior_frontal",
        display_name="Anterior Frontal Lobe",
        hbo=np.array([0.0, 1.0]),
        hbr=np.array([0.0, -0.2]),
        integral=1.0,
        centroid=1.0,
        slope=-0.1,
        valid_channels=7,
        expected_channels=7,
        warnings=(),
    )
    model = ReportViewModel(
        title="NIRS",
        time_seconds=np.array([0.0, 1.0]),
        channel_series={},
        roi_summaries=(summary,),
        plot_points=(PlotPoint("anterior_frontal", 1.0, 1.0),),
        laterality=None,
    )

    assert model.laterality is None
    assert model.roi_summaries[0].integral == 1.0


def test_report_view_model_rejects_plot_point_that_disagrees_with_summary() -> None:
    summary = RoiSummary(
        roi_id="left_pfc",
        display_name="Left PFC",
        hbo=np.array([0.0, 1.0]),
        hbr=np.array([0.0, -0.2]),
        integral=2.0,
        centroid=1.0,
        slope=0.0,
        valid_channels=4,
        expected_channels=4,
        warnings=(),
    )

    with pytest.raises(ValueError, match="does not match ROI summary"):
        ReportViewModel(
            title="NIRS",
            time_seconds=np.array([0.0, 1.0]),
            channel_series={},
            roi_summaries=(summary,),
            plot_points=(PlotPoint("left_pfc", 99.0, 1.0),),
            laterality=calculate_li(2.0, 1.0),
        )
