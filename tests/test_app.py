from __future__ import annotations

from nirs_report_app.app import main


def test_smoke_test_mode_initializes_core_without_starting_gui(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["--smoke-test"]) == 0
    assert (tmp_path / "img").is_dir()
    assert (tmp_path / "report").is_dir()
