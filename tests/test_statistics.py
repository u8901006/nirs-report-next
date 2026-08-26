import numpy as np
import pandas as pd
import warnings

from nirs_report_app.statistics import (
    adjust_pvalues,
    fit_mixed_model,
    one_sample_test,
    paired_test,
)


def test_paired_test_reports_post_minus_pre_and_cohens_dz() -> None:
    result = paired_test(np.array([1.0, 2.0, 3.0]), np.array([2.0, 4.0, 6.0]))

    assert result.estimate == 2.0
    assert result.effect_size == 2.0
    assert result.n_included == 3
    assert result.method == "paired t-test"


def test_one_sample_test_removes_nonfinite_values() -> None:
    result = one_sample_test(np.array([0.2, 0.4, np.nan]), null_value=0.0)

    assert result.estimate == 0.30000000000000004
    assert result.n_included == 2
    assert result.n_excluded == 1


def test_holm_adjustment_matches_hand_calculation() -> None:
    adjusted = adjust_pvalues([0.01, 0.04, 0.03], method="holm")
    np.testing.assert_allclose(adjusted, [0.03, 0.06, 0.06])


def test_fdr_adjustment_matches_hand_calculation() -> None:
    adjusted = adjust_pvalues([0.01, 0.04, 0.03], method="fdr_bh")
    np.testing.assert_allclose(adjusted, [0.03, 0.04, 0.04])


def test_paired_constant_difference_reports_zero_variance_without_runtime_warning() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = paired_test(np.array([1.0, 2.0, 3.0]), np.array([2.0, 3.0, 4.0]))

    assert captured == []
    assert result.estimate == 1.0
    assert result.statistic is None
    assert result.p_value is None
    assert "W_ZERO_VARIANCE" in result.warnings


def test_mixed_model_reports_positive_group_time_interaction() -> None:
    rows: list[dict[str, float | str]] = []
    for subject in range(12):
        group_code = 1.0 if subject >= 6 else 0.0
        baseline = 10.0 + subject * 0.1
        rows.append(
            {
                "subject_id": f"S{subject:02d}",
                "group_code": group_code,
                "time_code": 0.0,
                "metric_value": baseline,
            }
        )
        rows.append(
            {
                "subject_id": f"S{subject:02d}",
                "group_code": group_code,
                "time_code": 1.0,
                "metric_value": baseline + 0.2 + group_code * 2.0 + (subject % 3) * 0.03,
            }
        )

    result = fit_mixed_model(
        pd.DataFrame(rows),
        "metric_value ~ group_code * time_code",
        group_column="subject_id",
    )

    assert result.converged
    assert result.n_subjects == 12
    assert result.coefficients["group_code:time_code"] > 1.5
