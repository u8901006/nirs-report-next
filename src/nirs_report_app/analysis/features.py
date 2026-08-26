from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import cumulative_trapezoid


@dataclass(frozen=True, slots=True)
class FeatureResult:
    front_integral: float
    side_integral: float
    front_centroid_value: float | str
    side_centroid_value: float | str
    front_centroid_idx: int
    side_centroid_idx: int

    def as_legacy_dict(self) -> dict[str, float | str | int]:
        return {
            "front_centroid_value": self.front_centroid_value,
            "front_centroid_idx": self.front_centroid_idx,
            "front_integral": self.front_integral,
            "side_centroid_value": self.side_centroid_value,
            "side_centroid_idx": self.side_centroid_idx,
            "side_integral": self.side_integral,
        }


def positive_integral(values: np.ndarray, dt: float, exclude_negative: bool = True) -> float:
    signal = np.asarray(values, dtype=float).copy()
    if signal.size == 0:
        return 0.0
    if exclude_negative:
        signal[signal < 0] = 0
    return float(cumulative_trapezoid(signal, dx=dt, initial=0)[-1])


def centroid_index(values: np.ndarray, dt: float, exclude_negative: bool = True) -> int:
    signal = np.asarray(values, dtype=float)
    if signal.size == 0:
        return -1
    if exclude_negative:
        signal = np.maximum(signal, 0)
    cumulative = cumulative_trapezoid(signal, dx=dt, initial=0)
    total = cumulative[-1]
    if total == 0:
        return -1
    index = int(np.searchsorted(cumulative, total / 2))
    return index if index < len(signal) else -1


def seconds_to_index(seconds: float, sample_rate: float, shift_left: bool = False) -> int:
    index = round(seconds * sample_rate)
    return index - 1 if shift_left else index


def slice_seconds(
    signal: np.ndarray,
    start_seconds: float,
    end_seconds: float,
    sample_rate: float,
    shift_left_start: bool = False,
) -> tuple[np.ndarray, int]:
    start = seconds_to_index(start_seconds, sample_rate, shift_left_start)
    end = seconds_to_index(end_seconds, sample_rate)
    return np.asarray(signal)[start:end], start


def calculate_features(
    front_hbo: np.ndarray,
    side_hbo: np.ndarray,
    sample_rate: float,
    task_start: float,
    task_end: float,
    measure_end: float,
) -> FeatureResult:
    front_task, _ = slice_seconds(front_hbo, task_start, task_end, sample_rate)
    side_task, _ = slice_seconds(side_hbo, task_start, task_end, sample_rate)
    front_integral = round(positive_integral(front_task, 1 / sample_rate), 2)
    side_integral = round(positive_integral(side_task, 1 / sample_rate), 2)

    anchor = seconds_to_index(task_start, sample_rate)
    front_centroid_signal, _ = slice_seconds(front_hbo, task_start, measure_end, sample_rate)
    side_centroid_signal, _ = slice_seconds(side_hbo, task_start, measure_end, sample_rate)
    front_raw = centroid_index(front_centroid_signal, 1 / sample_rate)
    side_raw = centroid_index(side_centroid_signal, 1 / sample_rate)
    front_index = front_raw + anchor if front_raw != -1 else -1
    side_index = side_raw + anchor if side_raw != -1 else -1
    front_value: float | str = round(front_index / sample_rate, 2) if front_index != -1 else "missing"
    side_value: float | str = round(side_index / sample_rate, 2) if side_index != -1 else "missing"
    return FeatureResult(
        front_integral,
        side_integral,
        front_value,
        side_value,
        front_index,
        side_index,
    )
