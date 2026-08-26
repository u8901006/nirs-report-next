from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class LateralityDirection(str, Enum):
    LEFT = "left-dominant"
    RIGHT = "right-dominant"
    BILATERAL = "bilateral"


@dataclass(frozen=True, slots=True)
class LateralityResult:
    left: float
    right: float
    value: float | None
    direction: LateralityDirection | None
    threshold: float
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BootstrapLiResult:
    point_estimate: float | None
    confidence_interval: tuple[float, float] | None
    valid_replicates: int
    total_replicates: int
    seed: int
    warnings: tuple[str, ...] = ()


def calculate_li(left: float, right: float, threshold: float = 0.10) -> LateralityResult:
    left_value = float(left)
    right_value = float(right)
    if threshold < 0:
        raise ValueError("Laterality threshold must be non-negative")
    if not np.isfinite(left_value) or not np.isfinite(right_value):
        return LateralityResult(
            left_value,
            right_value,
            None,
            None,
            threshold,
            ("E_LI_NONFINITE",),
        )

    denominator = left_value + right_value
    guard = max(1e-12, 1e-6 * (abs(left_value) + abs(right_value)))
    if abs(denominator) <= guard:
        return LateralityResult(
            left_value,
            right_value,
            None,
            None,
            threshold,
            ("W_LI_DENOMINATOR_SMALL",),
        )

    value = (left_value - right_value) / denominator
    if left_value * right_value < 0:
        return LateralityResult(
            left_value,
            right_value,
            value,
            None,
            threshold,
            ("W_LI_OPPOSITE_SIGNS",),
        )

    if value > threshold:
        direction = LateralityDirection.LEFT
    elif value < -threshold:
        direction = LateralityDirection.RIGHT
    else:
        direction = LateralityDirection.BILATERAL
    return LateralityResult(left_value, right_value, value, direction, threshold)


def bootstrap_li(
    left_samples: np.ndarray,
    right_samples: np.ndarray,
    *,
    repetitions: int = 5000,
    seed: int = 20260826,
) -> BootstrapLiResult:
    left = np.asarray(left_samples, dtype=float)
    right = np.asarray(right_samples, dtype=float)
    if left.ndim != 1 or right.ndim != 1 or left.size == 0 or left.size != right.size:
        raise ValueError("Left and right samples must have the same non-zero length")
    if repetitions <= 0:
        raise ValueError("Bootstrap repetitions must be positive")
    paired = np.isfinite(left) & np.isfinite(right)
    left = left[paired]
    right = right[paired]
    if left.size == 0:
        return BootstrapLiResult(None, None, 0, repetitions, seed, ("E_LI_NONFINITE",))

    point = calculate_li(float(left.mean()), float(right.mean())).value
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(repetitions):
        indices = rng.integers(0, left.size, size=left.size)
        result = calculate_li(float(left[indices].mean()), float(right[indices].mean()))
        if result.value is not None:
            values.append(result.value)
    if not values:
        return BootstrapLiResult(
            point,
            None,
            0,
            repetitions,
            seed,
            ("W_LI_DENOMINATOR_SMALL",),
        )
    lower, upper = np.percentile(np.asarray(values), [2.5, 97.5])
    return BootstrapLiResult(
        point,
        (float(lower), float(upper)),
        len(values),
        repetitions,
        seed,
    )
