import numpy as np
import pandas as pd

from nirs_report_app.analysis.loader import load_nirs_workbook


def test_loads_filtered_delta_hb_workbook(tmp_path) -> None:
    path = tmp_path / "modern.xlsx"
    frame = pd.DataFrame(
        {
            "Time (sec)": [0.0, 0.1, 0.2],
            "HbO ch1": [0.0, 0.01, 0.02],
            "HbR ch1": [0.0, 0.02, 0.04],
        }
    )
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(writer, sheet_name="Filtered ΔHb", index=False)
    loaded = load_nirs_workbook(path)
    assert not loaded.legacy_format
    assert loaded.sample_rate == 10.0
    assert loaded.hbo.columns.tolist() == ["Time (sec)", "ch1"]


def test_loads_legacy_hbo_hbr_workbook(tmp_path) -> None:
    path = tmp_path / "legacy.xlsx"
    frame = pd.DataFrame({"Time": [0.0, 0.5], "ch1": [1.0, 2.0]})
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(writer, sheet_name="HbO", index=False)
        frame.to_excel(writer, sheet_name="HbR", index=False)
    loaded = load_nirs_workbook(path)
    assert loaded.legacy_format
    assert np.isclose(loaded.sample_rate, 2.0)
