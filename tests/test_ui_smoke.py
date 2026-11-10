from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt5 import QtWidgets
from test_visualization import make_view_model

from nirs_report_app.paths import AppPaths
from nirs_report_app.ui.channel_grid import ChannelGrid
from nirs_report_app.ui.main_window import MainWindow, guess_measurement_date
from nirs_report_app.ui.report_preview import ReportPreview
from nirs_report_app.ui.workers import StudyAnalysisWorker

_APPLICATION = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
_APPLICATION.setQuitOnLastWindowClosed(False)


def application() -> QtWidgets.QApplication:
    return _APPLICATION


def test_main_window_has_advanced_navigation_and_safe_initial_state(tmp_path) -> None:
    app = application()
    window = MainWindow(AppPaths(tmp_path))
    app.processEvents()

    assert window.minimumWidth() >= 1280
    assert window.minimumHeight() >= 800
    assert [window.result_tabs.tabText(index) for index in range(window.result_tabs.count())] == [
        "總覽",
        "側化 LI",
        "前後測",
        "腦區差異",
        "報告預覽",
    ]
    assert window.analysis_mode.count() == 2
    assert window.channel_grid.status_label.text() == "有效 15/15 通道"
    assert not window.export_button.isEnabled()
    window.close()


def test_channel_grid_retains_missing_positions_and_controls_li_availability() -> None:
    application()
    grid = ChannelGrid()
    original_position = grid.channel_button(4).property("montage_position")

    grid.set_channel_state(4, "missing")
    assert grid.channel_button(4).property("montage_position") == original_position
    assert "缺少" in grid.channel_button(4).text()
    assert grid.roi_count("right_pfc") == (3, 4)

    grid.set_selected_channels({1, 2, 3, 5, 6, 7})
    assert grid.roi_count("anterior_frontal") == (3, 7)
    assert not grid.li_available
    grid.set_selected_channels({1, 2, 3, 12})
    assert grid.li_available


def test_report_preview_keeps_mandatory_pages_and_zoom_contract() -> None:
    application()
    preview = ReportPreview()
    model = make_view_model()
    preview.set_view_model(model)

    assert preview.page_names() == ["總覽", "側化 LI", "品質控管", "方法與聲明"]
    assert preview.is_page_mandatory("品質控管")
    assert preview.is_page_mandatory("方法與聲明")
    assert preview.zoom.minimum() == 60
    assert preview.zoom.maximum() == 200
    assert not preview.export_selected_button.isEnabled()
    preview.page_list.setCurrentRow(0)
    assert preview.export_selected_button.isEnabled()


def test_study_worker_cancels_between_files_without_finalizing_report(tmp_path) -> None:
    application()
    processed: list[str] = []
    destination = tmp_path / "report.docx"

    def analyze(item: str) -> str:
        processed.append(item)
        return item.upper()

    def finalize(results: list[str], path) -> None:
        path.write_text("\n".join(results), encoding="utf-8")

    worker = StudyAnalysisWorker(
        ["first", "second", "third"],
        analyze,
        destination=destination,
        finalize=finalize,
    )
    worker.progress.connect(lambda completed, total: worker.cancel() if completed == 1 else None)
    cancelled: list[bool] = []
    worker.cancelled.connect(lambda: cancelled.append(True))

    worker.run()

    assert processed == ["first"]
    assert cancelled == [True]
    assert not destination.exists()


def test_main_window_routes_study_mode_to_manifest_service(tmp_path, monkeypatch) -> None:
    app = application()
    window = MainWindow(AppPaths(tmp_path))
    manifest = tmp_path / "study.csv"
    manifest.write_text("subject_id,file_path,session\n", encoding="utf-8")
    captured = []

    class FakeService:
        def analyze_study(self, request):
            captured.append(request)
            return SimpleNamespace(
                single_results={("S01", "pre", "task"): object()},
                pairing=None,
                regional=None,
                errors=(),
                subject_level_results=pd.DataFrame(),
            )

    monkeypatch.setattr(
        "nirs_report_app.ui.main_window.build_report_view_model",
        lambda result, **kwargs: make_view_model(),
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: None)
    window.service = FakeService()
    window.analysis_mode.setCurrentIndex(1)
    window.file_edit.setText(str(manifest))
    window.task_start.setValue(1.0)
    window.task_end.setValue(2.0)
    window.measure_end.setValue(3.0)

    window._analyze()
    app.processEvents()

    assert captured[0].manifest_path == manifest
    assert window.export_button.isEnabled()
    window.close()


def test_switched_off_channel_says_excluded_and_can_be_restored() -> None:
    application()
    grid = ChannelGrid()
    button = grid.channel_button(7)
    assert "有效" in button.text()

    button.click()
    assert "排除" in button.text()
    assert "有效" not in button.text()
    assert grid.status_label.text() == "有效 14/15 通道"

    button.click()
    assert "有效" in button.text()


def test_measurement_date_is_read_from_the_export_file_name(tmp_path) -> None:
    from datetime import date

    assert guess_measurement_date(tmp_path / "250808_0845_rTMS.xlsx") == date(2025, 8, 8)
    assert guess_measurement_date(tmp_path / "study.csv") is None
    assert guess_measurement_date(tmp_path / "259999_x.xlsx") is None


def test_patient_fields_reach_the_report_and_date_follows_the_file(tmp_path) -> None:
    from datetime import date

    app = application()
    window = MainWindow(AppPaths(tmp_path))
    window.file_edit.setText(str(tmp_path / "250808_0845_rTMS.xlsx"))
    window.patient_id.setText(" S01 ")
    window.patient_name.setText("測試個案")
    window.gender.setCurrentText("女")
    window.doctor.setText("王醫師")
    window.opinion.setPlainText("活化反應偏低")
    app.processEvents()

    patient = window._patient_info()
    assert patient.patient_id == "S01"
    assert patient.name == "測試個案"
    assert patient.gender == "女"
    assert patient.measurement_date == date(2025, 8, 8)
    assert patient.doctor == "王醫師"
    assert patient.opinion == "活化反應偏低"
    assert window.analyze_button.property("primary") is True
    assert window.report_button.property("primary") is False
    window.close()


def test_report_preview_shows_a_real_page_and_reports_ticked_figures() -> None:
    from PyQt5 import QtCore

    application()
    preview = ReportPreview()
    preview.set_view_model(make_view_model())
    assert preview.checked_figure_keys() == {"overview", "laterality"}

    preview.page_list.setCurrentRow(0)
    width = preview.preview_label.pixmap().width()
    assert width > 500
    preview.zoom.setValue(200)
    assert preview.preview_label.pixmap().width() > width

    preview.page_list.item(1).setCheckState(QtCore.Qt.Unchecked)
    assert preview.checked_figure_keys() == {"overview"}
