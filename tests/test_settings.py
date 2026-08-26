from nirs_report_app.settings import AnalysisSettings, load_settings, save_settings


def test_settings_round_trip(tmp_path) -> None:
    path = tmp_path / "settings.ini"
    expected = AnalysisSettings(task_start="12", filter_num=7)
    save_settings(path, expected)
    assert load_settings(path, AnalysisSettings) == expected


def test_corrupt_settings_fall_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "settings.ini"
    path.write_text("not json", encoding="utf-8")
    assert load_settings(path, AnalysisSettings) == AnalysisSettings()
