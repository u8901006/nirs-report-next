import numpy as np
import pytest

from nirs_report_app.analysis.laterality import (
    LateralityDirection,
    bootstrap_li,
    calculate_li,
)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [(3.0, 1.0, 0.5), (1.0, 3.0, -0.5), (2.0, 2.0, 0.0)],
)
def test_li_uses_left_minus_right_ratio(left: float, right: float, expected: float) -> None:
    assert calculate_li(left, right).value == expected


def test_li_classifies_values_around_configured_threshold() -> None:
    assert calculate_li(3.0, 1.0).direction is LateralityDirection.LEFT
    assert calculate_li(1.0, 3.0).direction is LateralityDirection.RIGHT
    assert calculate_li(1.05, 0.95).direction is LateralityDirection.BILATERAL


def test_li_rejects_near_zero_denominator() -> None:
    result = calculate_li(1.0, -1.0)

    assert result.value is None
    assert result.direction is None
    assert "W_LI_DENOMINATOR_SMALL" in result.warnings


def test_li_with_opposite_signs_has_no_direction_classification() -> None:
    result = calculate_li(2.0, -0.5)

    assert result.value == 1.6666666666666667
    assert result.direction is None
    assert "W_LI_OPPOSITE_SIGNS" in result.warnings


def test_li_rejects_non_finite_input() -> None:
    result = calculate_li(np.nan, 1.0)

    assert result.value is None
    assert "E_LI_NONFINITE" in result.warnings


def test_bootstrap_li_is_deterministic_for_same_seed() -> None:
    left = np.array([3.0, 4.0, 5.0, 4.0])
    right = np.array([1.0, 2.0, 1.0, 2.0])

    first = bootstrap_li(left, right, repetitions=500, seed=7)
    second = bootstrap_li(left, right, repetitions=500, seed=7)

    assert first.confidence_interval == second.confidence_interval
    assert first.valid_replicates == 500
    assert first.total_replicates == 500


def test_bootstrap_li_requires_paired_equal_length_samples() -> None:
    with pytest.raises(ValueError, match="same non-zero length"):
        bootstrap_li(np.array([1.0, 2.0]), np.array([1.0]), repetitions=10)
