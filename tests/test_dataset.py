from pathlib import Path

import pandas as pd

from nirs_report_app.dataset import load_manifest


def test_load_manifest_resolves_relative_paths(tmp_path: Path) -> None:
    workbook = tmp_path / "subject.xlsx"
    workbook.touch()
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {
                "subject_id": "S01",
                "file_path": "subject.xlsx",
                "session": "pre",
                "group": "all",
                "condition": "task",
            }
        ]
    ).to_csv(manifest, index=False)

    result = load_manifest(manifest)

    assert result.is_valid
    assert result.records[0].file_path == workbook.resolve()
    assert result.records[0].subject_id == "S01"


def test_load_manifest_reports_duplicate_study_keys(tmp_path: Path) -> None:
    workbook = tmp_path / "subject.xlsx"
    workbook.touch()
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {"subject_id": "S01", "file_path": "subject.xlsx", "session": "pre"},
            {"subject_id": "S01", "file_path": "subject.xlsx", "session": "pre"},
        ]
    ).to_csv(manifest, index=False)

    result = load_manifest(manifest)

    assert not result.is_valid
    assert any(issue.code == "E_DUPLICATE_STUDY_KEY" for issue in result.errors)


def test_load_manifest_reports_required_columns(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{"subject_id": "S01"}]).to_csv(manifest, index=False)

    result = load_manifest(manifest)

    assert not result.is_valid
    assert any(issue.code == "E_MANIFEST_COLUMNS" for issue in result.errors)


def test_load_manifest_reports_unreadable_file(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [{"subject_id": "S01", "file_path": "absent.xlsx", "session": "pre"}]
    ).to_csv(manifest, index=False)

    result = load_manifest(manifest)

    assert not result.is_valid
    assert result.errors[0].row == 2
    assert result.errors[0].code == "E_SOURCE_FILE"
