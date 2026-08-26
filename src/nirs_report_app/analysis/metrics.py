from __future__ import annotations

import numpy as np


def baseline_corrected_mean(
    values: np.ndarray,
    baseline_window: slice,
    task_window: slice,
) -> float:
    signal = np.asarray(values, dtype=float)
    baseline = signal[baseline_window]
    task = signal[task_window]
    if baseline.size == 0 or task.size == 0:
        return float("nan")
    if not np.isfinite(baseline).any() or not np.isfinite(task).any():
        return float("nan")
    return float(np.nanmean(task) - np.nanmean(baseline))


def recovery_slope(values: np.ndarray, time_seconds: np.ndarray) -> float:
    signal = np.asarray(values, dtype=float)
    time = np.asarray(time_seconds, dtype=float)
    if signal.shape != time.shape:
        raise ValueError("Signal and time arrays must have the same shape")
    valid = np.isfinite(signal) & np.isfinite(time)
    if valid.sum() < 3 or np.unique(time[valid]).size < 2:
        return float("nan")
    return float(np.polyfit(time[valid], signal[valid], 1)[0])
