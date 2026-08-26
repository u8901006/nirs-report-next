import numpy as np
import pytest

from nirs_report_app.analysis.filters import mean_filter, median_filter


def test_filters_preserve_length_and_edges() -> None:
    values = np.array([1.0, 2.0, 100.0, 4.0, 5.0])
    assert median_filter(values, 3).tolist() == [1.0, 2.0, 4.0, 5.0, 5.0]
    assert len(mean_filter(values, 3)) == len(values)


@pytest.mark.parametrize("window", [0, 2, 4])
def test_filter_requires_positive_odd_window(window: int) -> None:
    with pytest.raises(ValueError):
        mean_filter(np.array([1.0, 2.0]), window)
