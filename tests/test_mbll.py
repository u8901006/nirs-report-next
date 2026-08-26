import numpy as np

from nirs_report_app.analysis.mbll import differential_pathlength_factor, inverse_mbll


def test_recovered_pathlength_factors() -> None:
    assert differential_pathlength_factor(760) == 6.0
    assert differential_pathlength_factor(850) == 5.2
    assert differential_pathlength_factor(800) == 5.5


def test_inverse_mbll_shape_and_zero_baseline() -> None:
    result = inverse_mbll(np.zeros(3), np.zeros(3), 30)
    assert result.shape == (2, 3)
    assert np.allclose(result, 0)
