from __future__ import annotations

import numpy as np


def _window_matrix(values: np.ndarray, window_size: int) -> np.ndarray:
    values = np.asarray(values)
    if window_size <= 0 or window_size % 2 != 1:
        raise ValueError("filter length must be a positive odd number")
    if values.ndim != 1:
        raise ValueError("input must be one-dimensional")
    radius = (window_size - 1) // 2
    matrix = np.empty((len(values), window_size), dtype=values.dtype)
    matrix[:, radius] = values
    for offset in range(radius):
        distance = radius - offset
        matrix[distance:, offset] = values[:-distance]
        matrix[:distance, offset] = values[0]
        matrix[:-distance, -(offset + 1)] = values[distance:]
        matrix[-distance:, -(offset + 1)] = values[-1]
    return matrix


def median_filter(values: np.ndarray, window_size: int) -> np.ndarray:
    return np.median(_window_matrix(values, window_size), axis=1)


def mean_filter(values: np.ndarray, window_size: int) -> np.ndarray:
    return np.mean(_window_matrix(values, window_size), axis=1)
