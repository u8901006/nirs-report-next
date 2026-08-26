import numpy as np
import pandas as pd

from nirs_report_app.analysis.models import QualityStatus, RoiDefinition
from nirs_report_app.analysis.quality import aggregate_roi


def test_missing_channel_is_reported_without_zero_waveform() -> None:
    frame = pd.DataFrame({"ch1": [1.0, 2.0, 3.0]})
    result = aggregate_roi(frame, RoiDefinition("right_pfc", "Right PFC", (1, 2)))

    assert result.valid_channels == (1,)
    assert result.missing_channels == (2,)
    assert result.status is QualityStatus.DEGRADED
    assert "W_CHANNEL_MISSING" in result.warnings
    np.testing.assert_allclose(result.values, [1.0, 2.0, 3.0])


def test_roi_without_valid_channels_is_invalid_and_nan() -> None:
    frame = pd.DataFrame(index=range(3))
    result = aggregate_roi(frame, RoiDefinition("right_pfc", "Right PFC", (1, 2)))

    assert result.status is QualityStatus.INVALID
    assert result.valid_channels == ()
    assert "E_ROI_EMPTY" in result.warnings
    assert np.isnan(result.values).all()


def test_roi_timepoint_requires_half_of_selected_channels() -> None:
    frame = pd.DataFrame({"ch1": [1.0, np.nan], "ch2": [3.0, np.nan], "ch3": [5.0, 7.0]})
    result = aggregate_roi(frame, RoiDefinition("roi", "ROI", (1, 2, 3)))

    np.testing.assert_allclose(result.values[0], 3.0)
    assert np.isnan(result.values[1])
    assert result.status is QualityStatus.DEGRADED


def test_user_excluded_channels_do_not_count_as_missing() -> None:
    frame = pd.DataFrame({"ch1": [1.0, 2.0], "ch2": [4.0, 6.0]})
    result = aggregate_roi(
        frame,
        RoiDefinition("roi", "ROI", (1, 2)),
        excluded_channels=(2,),
    )

    assert result.valid_channels == (1,)
    assert result.excluded_channels == (2,)
    assert result.missing_channels == ()
    np.testing.assert_allclose(result.values, [1.0, 2.0])
