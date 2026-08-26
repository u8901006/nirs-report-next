import numpy as np

from nirs_report_app.analysis.features import (
    calculate_features,
    centroid_index,
    positive_integral,
)


def test_positive_integral_excludes_negative_values() -> None:
    values = np.array([-2.0, 1.0, 1.0])
    assert positive_integral(values, 1.0) == 1.5


def test_centroid_returns_missing_marker_for_zero_signal() -> None:
    assert centroid_index(np.zeros(10), 0.1) == -1


def test_feature_keys_match_legacy_application() -> None:
    signal = np.ones(200)
    result = calculate_features(signal, signal, 10, 3, 9, 16)
    assert set(result.as_legacy_dict()) == {
        "front_centroid_value",
        "front_centroid_idx",
        "front_integral",
        "side_centroid_value",
        "side_centroid_idx",
        "side_integral",
    }
