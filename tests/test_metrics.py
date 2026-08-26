import numpy as np

from nirs_report_app.analysis.metrics import baseline_corrected_mean, recovery_slope


def test_baseline_corrected_mean_subtracts_windows() -> None:
    values = np.array([1.0, 1.0, 3.0, 5.0])
    assert baseline_corrected_mean(values, slice(0, 2), slice(2, 4)) == 3.0


def test_baseline_corrected_mean_returns_nan_for_empty_window() -> None:
    values = np.array([1.0, 2.0])
    assert np.isnan(baseline_corrected_mean(values, slice(0, 0), slice(0, 2)))


def test_recovery_slope_uses_seconds() -> None:
    signal = np.array([3.0, 2.0, 1.0])
    time_seconds = np.array([0.0, 0.5, 1.0])
    assert recovery_slope(signal, time_seconds) == -2.0


def test_recovery_slope_requires_three_valid_samples() -> None:
    signal = np.array([3.0, np.nan, 1.0])
    time_seconds = np.array([0.0, 0.5, 1.0])
    assert np.isnan(recovery_slope(signal, time_seconds))
