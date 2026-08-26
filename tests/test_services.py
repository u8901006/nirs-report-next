from pathlib import Path

import numpy as np
import pandas as pd

from nirs_report_app.analysis.models import QualityStatus
from nirs_report_app.services import (
    NirsAnalysisService,
    SingleAnalysisRequest,
    build_report_view_model,
)


def _write_legacy_workbook(
    path: Path,
    *,
    left_gain: float = 2.0,
    global_gain: float = 1.0,
    missing_ch4: bool = False,
) -> None:
    time = np.arange(0.0, 6.0)
    hbo: dict[str, np.ndarray] = {"Time": time}
    hbr: dict[str, np.ndarray] = {"Time": time}
    for channel in range(1, 16):
        if missing_ch4 and channel == 4:
            continue
        gain = global_gain * (left_gain if channel >= 12 else 1.0)
        hbo[f"ch{channel}"] = np.array([0.0, 0.0, gain, gain * 2, gain, 0.0])
        hbr[f"ch{channel}"] = -0.25 * hbo[f"ch{channel}"]
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(hbo).to_excel(writer, sheet_name="HbO", index=False)
        pd.DataFrame(hbr).to_excel(writer, sheet_name="HbR", index=False)


def test_single_analysis_reports_degraded_roi_and_laterality(tmp_path: Path) -> None:
    path = tmp_path / "single.xlsx"
    _write_legacy_workbook(path, missing_ch4=True)

    result = NirsAnalysisService().analyze_single(
        SingleAnalysisRequest(
            path=path,
            baseline_start=0.0,
            baseline_end=2.0,
            task_start=2.0,
            task_end=5.0,
            measure_end=6.0,
        )
    )

    right = result.roi_signals_hbo["right_pfc"]
    assert right.status is QualityStatus.DEGRADED
    assert right.valid_channels == (1, 2, 3)
    assert right.missing_channels == (4,)
    assert result.laterality.value is not None
    assert result.laterality.value > 0
    assert result.features.front_integral > 0


def test_legacy_analyze_method_preserves_core_contract(tmp_path: Path) -> None:
    path = tmp_path / "legacy.xlsx"
    _write_legacy_workbook(path)

    result = NirsAnalysisService().analyze(
        path,
        task_start=2.0,
        task_end=5.0,
        measure_end=6.0,
    )

    assert result.data.sample_rate == 1.0
    assert result.regions.front_hbo.shape == (6,)
    assert result.features.front_integral > 0


def test_report_view_model_uses_single_analysis_values(tmp_path: Path) -> None:
    path = tmp_path / "view-model.xlsx"
    _write_legacy_workbook(path, missing_ch4=True)
    result = NirsAnalysisService().analyze_single(
        SingleAnalysisRequest(
            path=path,
            baseline_start=0.0,
            baseline_end=2.0,
            task_start=2.0,
            task_end=5.0,
            measure_end=6.0,
        )
    )

    model = build_report_view_model(result, title="研究報告")

    assert model.title == "研究報告"
    assert len(model.channel_series) == 15
    assert model.channel_series[4].state == "missing"
    assert {summary.roi_id for summary in model.roi_summaries} == {
        "right_pfc",
        "anterior_frontal",
        "left_pfc",
        "lateral_frontal",
    }
    lateral = next(item for item in model.roi_summaries if item.roi_id == "lateral_frontal")
    point = next(item for item in model.plot_points if item.roi_id == "lateral_frontal")
    assert point.integral == lateral.integral
    assert point.centroid == lateral.centroid


def test_study_analysis_builds_subject_level_rows_and_pairs(tmp_path: Path) -> None:
    manifest_rows = []
    for subject in ("S01", "S02"):
        for session, gain in (("pre", 1.0), ("post", 2.0)):
            path = tmp_path / f"{subject}-{session}.xlsx"
            _write_legacy_workbook(path, global_gain=gain)
            manifest_rows.append(
                {
                    "subject_id": subject,
                    "file_path": path.name,
                    "session": session,
                    "group": "all",
                    "condition": "task",
                }
            )
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(manifest_rows).to_csv(manifest, index=False)

    from nirs_report_app.services import StudyAnalysisRequest

    result = NirsAnalysisService().analyze_study(
        StudyAnalysisRequest(
            manifest_path=manifest,
            baseline_start=0.0,
            baseline_end=2.0,
            task_start=2.0,
            task_end=5.0,
            measure_end=6.0,
        )
    )

    assert result.errors == ()
    assert len(result.single_results) == 4
    assert len(result.subject_level_results) == 16
    assert result.pairing is not None
    assert result.pairing.paired_n == 2
    np.testing.assert_allclose(result.pairing.pairs["delta"], [4000 / 3, 4000 / 3])
