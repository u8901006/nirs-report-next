from __future__ import annotations

import hashlib
import json

import pandas as pd
from PIL import Image
from test_visualization import make_view_model

from nirs_report_app.exporting import export_result_bundle


def test_export_bundle_is_atomic_numeric_reproducible_and_300_dpi(tmp_path) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"fixed-source-content")
    destination = tmp_path / "analysis-output"
    model = make_view_model()
    model.provenance["source_files"] = [str(source)]

    subject_rows = pd.DataFrame(
        {
            "subject_id": ["S01", "S02"],
            "metric_value": [1.25, float("nan")],
        }
    )
    statistical_rows = pd.DataFrame(
        {"contrast": ["post-pre"], "estimate": [0.75], "p_value": [0.04]}
    )
    exclusions = pd.DataFrame({"subject_id": ["S02"], "code": ["E_PAIR_INCOMPLETE"]})

    result = export_result_bundle(
        destination,
        model,
        subject_level_results=subject_rows,
        statistical_results=statistical_rows,
        exclusions_and_warnings=exclusions,
    )

    assert result == destination
    assert {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    } == {
        "analysis_config.json",
        "exclusions_and_warnings.csv",
        "figures/laterality.png",
        "figures/overview.png",
        "statistical_results.csv",
        "subject_level_results.xlsx",
    }
    imported = pd.read_excel(destination / "subject_level_results.xlsx")
    assert pd.api.types.is_numeric_dtype(imported["metric_value"])
    assert pd.isna(imported.loc[1, "metric_value"])

    config = json.loads((destination / "analysis_config.json").read_text(encoding="utf-8"))
    assert config["analysis_config"]["bootstrap_seed"] == 20260826
    assert (
        config["provenance"]["source_files"][0]["sha256"]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )

    with Image.open(destination / "figures" / "overview.png") as image:
        assert image.size == (3508, 2480)
        assert image.info["dpi"][0] == pytest_approx(300.0, abs=1.0)

    assert not (tmp_path / ".analysis-output.tmp").exists()


def pytest_approx(value: float, **kwargs: float):
    import pytest

    return pytest.approx(value, **kwargs)
