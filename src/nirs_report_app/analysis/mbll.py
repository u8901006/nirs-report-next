from __future__ import annotations

import numpy as np
import pandas as pd


def differential_pathlength_factor(wavelength_nm: int) -> float:
    if wavelength_nm == 760:
        return 6.0
    if wavelength_nm == 850:
        return 5.2
    return 5.5


def inverse_mbll(
    delta_a_760: np.ndarray,
    delta_a_850: np.ndarray,
    distance_mm: float,
) -> np.ndarray:
    if distance_mm <= 0:
        raise ValueError("distance_mm must be positive")
    path_760 = differential_pathlength_factor(760) * distance_mm
    path_850 = differential_pathlength_factor(850) * distance_mm
    extinction = np.array([[0.147, 3.396], [0.586, 1.790]], dtype=float)
    absorbance = np.vstack(
        [np.asarray(delta_a_760, dtype=float) / path_760,
         np.asarray(delta_a_850, dtype=float) / path_850]
    )
    return np.linalg.solve(extinction, absorbance) * 1000.0


def convert_timeseries_matrix(
    delta_a_850: pd.DataFrame,
    delta_a_760: pd.DataFrame,
    time_seconds: np.ndarray,
    distance_mm: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(delta_a_850) != len(delta_a_760) or len(delta_a_850) != len(time_seconds):
        raise ValueError("Absorbance matrices and time axis must have equal lengths")
    labels = delta_a_850.columns.tolist()
    hbo_rows: list[np.ndarray] = []
    hbr_rows: list[np.ndarray] = []
    for index in range(len(delta_a_850)):
        concentrations = inverse_mbll(
            delta_a_760.iloc[index].to_numpy(dtype=float),
            delta_a_850.iloc[index].to_numpy(dtype=float),
            distance_mm,
        )
        hbo_rows.append(concentrations[0])
        hbr_rows.append(concentrations[1])
    hbo = pd.DataFrame(hbo_rows, columns=labels)
    hbr = pd.DataFrame(hbr_rows, columns=labels)
    hbo.insert(0, "Time (sec)", time_seconds)
    hbr.insert(0, "Time (sec)", time_seconds)
    return hbo, hbr
