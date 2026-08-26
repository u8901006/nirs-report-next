from __future__ import annotations

from dataclasses import dataclass, replace
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.formula.api import mixedlm
from statsmodels.stats.multitest import multipletests


@dataclass(frozen=True, slots=True)
class StatisticalResult:
    estimate: float | None
    standard_error: float | None
    confidence_interval: tuple[float, float] | None
    statistic: float | None
    p_value: float | None
    adjusted_p_value: float | None
    effect_size: float | None
    n_included: int
    n_excluded: int
    method: str
    warnings: tuple[str, ...] = ()

    def with_adjusted_p(self, value: float) -> "StatisticalResult":
        return replace(self, adjusted_p_value=float(value))


@dataclass(frozen=True, slots=True)
class MixedModelResult:
    coefficients: dict[str, float]
    standard_errors: dict[str, float]
    p_values: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    converged: bool
    n_observations: int
    n_subjects: int
    formula: str
    warnings: tuple[str, ...] = ()


def _finite(values: np.ndarray) -> tuple[np.ndarray, int]:
    array = np.asarray(values, dtype=float)
    valid = array[np.isfinite(array)]
    return valid, int(array.size - valid.size)


def _mean_result(values: np.ndarray, null_value: float, method: str) -> StatisticalResult:
    valid, excluded = _finite(values)
    if valid.size < 2:
        return StatisticalResult(
            float(valid.mean()) if valid.size else None,
            None,
            None,
            None,
            None,
            None,
            None,
            int(valid.size),
            excluded,
            method,
            ("E_INSUFFICIENT_SAMPLE",),
        )
    estimate = float(valid.mean() - null_value)
    sd = float(np.std(valid, ddof=1))
    if np.isclose(sd, 0.0, atol=1e-12, rtol=0.0):
        return StatisticalResult(
            estimate,
            0.0,
            (estimate, estimate),
            None,
            None,
            None,
            None,
            int(valid.size),
            excluded,
            method,
            ("W_ZERO_VARIANCE",),
        )
    se = sd / np.sqrt(valid.size)
    test = stats.ttest_1samp(valid, popmean=null_value)
    critical = float(stats.t.ppf(0.975, valid.size - 1))
    ci = (estimate - critical * se, estimate + critical * se)
    effect = estimate / sd if sd > 0 else None
    return StatisticalResult(
        estimate,
        float(se),
        (float(ci[0]), float(ci[1])),
        float(test.statistic),
        float(test.pvalue),
        None,
        float(effect) if effect is not None else None,
        int(valid.size),
        excluded,
        method,
    )


def one_sample_test(values: np.ndarray, *, null_value: float = 0.0) -> StatisticalResult:
    return _mean_result(values, null_value, "one-sample t-test")


def paired_test(pre: np.ndarray, post: np.ndarray, *, method: str = "paired_t") -> StatisticalResult:
    pre_values = np.asarray(pre, dtype=float)
    post_values = np.asarray(post, dtype=float)
    if pre_values.shape != post_values.shape:
        raise ValueError("Pre and post arrays must have the same shape")
    paired = np.isfinite(pre_values) & np.isfinite(post_values)
    differences = post_values[paired] - pre_values[paired]
    excluded = int(pre_values.size - paired.sum())
    if method == "wilcoxon":
        if differences.size == 0:
            return StatisticalResult(
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                0,
                excluded,
                "Wilcoxon signed-rank",
                ("E_INSUFFICIENT_SAMPLE",),
            )
        test = stats.wilcoxon(differences)
        positive = np.sum(differences > 0)
        negative = np.sum(differences < 0)
        effect = (positive - negative) / differences.size
        return StatisticalResult(
            float(np.median(differences)),
            None,
            None,
            float(test.statistic),
            float(test.pvalue),
            None,
            float(effect),
            int(differences.size),
            excluded,
            "Wilcoxon signed-rank",
        )
    result = _mean_result(differences, 0.0, "paired t-test")
    return replace(result, n_excluded=excluded)


def welch_test(first: np.ndarray, second: np.ndarray) -> StatisticalResult:
    a, excluded_a = _finite(first)
    b, excluded_b = _finite(second)
    if a.size < 2 or b.size < 2:
        return StatisticalResult(
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            int(a.size + b.size),
            excluded_a + excluded_b,
            "Welch t-test",
            ("E_INSUFFICIENT_SAMPLE",),
        )
    estimate = float(a.mean() - b.mean())
    variance = a.var(ddof=1) / a.size + b.var(ddof=1) / b.size
    se = float(np.sqrt(variance))
    numerator = variance**2
    denominator = (a.var(ddof=1) / a.size) ** 2 / (a.size - 1) + (
        b.var(ddof=1) / b.size
    ) ** 2 / (b.size - 1)
    degrees = numerator / denominator
    critical = float(stats.t.ppf(0.975, degrees))
    test = stats.ttest_ind(a, b, equal_var=False)
    pooled = np.sqrt(((a.size - 1) * a.var(ddof=1) + (b.size - 1) * b.var(ddof=1)) / (a.size + b.size - 2))
    correction = 1 - 3 / (4 * (a.size + b.size) - 9)
    effect = correction * estimate / pooled if pooled > 0 else None
    return StatisticalResult(
        estimate,
        se,
        (estimate - critical * se, estimate + critical * se),
        float(test.statistic),
        float(test.pvalue),
        None,
        float(effect) if effect is not None else None,
        int(a.size + b.size),
        excluded_a + excluded_b,
        "Welch t-test",
    )


def adjust_pvalues(p_values: list[float] | np.ndarray, *, method: str = "holm") -> np.ndarray:
    values = np.asarray(p_values, dtype=float)
    if values.size == 0:
        return values
    return np.asarray(multipletests(values, method=method)[1], dtype=float)


def fit_mixed_model(
    data: pd.DataFrame,
    formula: str,
    *,
    group_column: str,
) -> MixedModelResult:
    required = {group_column}
    if not required.issubset(data.columns):
        raise ValueError(f"Missing mixed-model group column: {group_column}")
    captured: list[warnings.WarningMessage] = []
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fitted = mixedlm(formula, data=data, groups=data[group_column]).fit(
                reml=False,
                method="lbfgs",
                maxiter=500,
                disp=False,
            )
        confidence = fitted.conf_int()
        return MixedModelResult(
            {str(key): float(value) for key, value in fitted.params.items()},
            {str(key): float(value) for key, value in fitted.bse.items()},
            {str(key): float(value) for key, value in fitted.pvalues.items()},
            {
                str(key): (float(confidence.loc[key, 0]), float(confidence.loc[key, 1]))
                for key in fitted.params.index
            },
            bool(fitted.converged),
            int(fitted.nobs),
            int(data[group_column].nunique()),
            formula,
            ("W_MODEL_CONVERGENCE",)
            if (not fitted.converged or captured)
            else (),
        )
    except Exception as error:  # statsmodels exposes several fit-specific exception types
        return MixedModelResult(
            {},
            {},
            {},
            {},
            False,
            len(data),
            int(data[group_column].nunique()),
            formula,
            ("W_MODEL_CONVERGENCE", f"MODEL_ERROR:{type(error).__name__}"),
        )
