from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtWidgets

from ..exporting import export_result_bundle
from ..paths import AppPaths
from ..report_models import ReportViewModel
from ..reporting import PatientInfo, build_advanced_report
from ..services import (
    AnalysisResult,
    NirsAnalysisService,
    SingleAnalysisRequest,
    StudyAnalysisRequest,
    build_report_view_model,
)
from ..settings import AnalysisSettings, ReportSettings, load_settings, save_settings
from ..visualization import ReportDashboardRenderer
from .channel_grid import ChannelGrid
from .result_tabs import ResultTabs


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.paths.ensure_runtime_directories()
        self.analysis_settings = load_settings(paths.app_settings, AnalysisSettings)
        self.report_settings = load_settings(paths.report_settings, ReportSettings)
        self.service = NirsAnalysisService()
        self.result: AnalysisResult | None = None
        self.study_result = None
        self.view_model: ReportViewModel | None = None
        self._setup_ui()
        self._load_settings_into_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("NIRS 分析報告")
        self.setMinimumSize(1280, 800)
        self.resize(1500, 920)
        root = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(root)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("NIRS 分析報告")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #17243A;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QtWidgets.QLabel("分析模式"))
        self.analysis_mode = QtWidgets.QComboBox()
        self.analysis_mode.addItems(("單次量測", "研究資料集"))
        header.addWidget(self.analysis_mode)
        self.export_button = QtWidgets.QPushButton("匯出資料包")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_bundle)
        header.addWidget(self.export_button)
        layout.addLayout(header)

        file_row = QtWidgets.QHBoxLayout()
        self.file_edit = QtWidgets.QLineEdit()
        self.file_edit.setPlaceholderText("選擇 NIRS Excel；研究模式可選 manifest CSV/XLSX")
        browse_button = QtWidgets.QPushButton("選擇資料")
        browse_button.clicked.connect(self._browse)
        file_row.addWidget(self.file_edit)
        file_row.addWidget(browse_button)
        layout.addLayout(file_row)

        form = QtWidgets.QFormLayout()
        self.task_start = QtWidgets.QDoubleSpinBox()
        self.task_end = QtWidgets.QDoubleSpinBox()
        self.measure_end = QtWidgets.QDoubleSpinBox()
        for widget in (self.task_start, self.task_end, self.measure_end):
            widget.setRange(0, 3600)
            widget.setDecimals(2)
        self.filter_size = QtWidgets.QSpinBox()
        self.filter_size.setRange(0, 99)
        form.addRow("作業開始（秒）", self.task_start)
        form.addRow("作業結束（秒）", self.task_end)
        form.addRow("測量結束（秒）", self.measure_end)
        form.addRow("平滑視窗", self.filter_size)
        settings_box = QtWidgets.QGroupBox("分析設定")
        settings_box.setLayout(form)
        layout.addWidget(settings_box)

        self.channel_grid = ChannelGrid()
        layout.addWidget(self.channel_grid)

        actions = QtWidgets.QHBoxLayout()
        self.analyze_button = QtWidgets.QPushButton("執行分析")
        self.report_button = QtWidgets.QPushButton("產生 Word 報告")
        self.report_button.setEnabled(False)
        self.analyze_button.clicked.connect(self._analyze)
        self.report_button.clicked.connect(self._create_report)
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.report_button)
        actions.addStretch(1)
        self.li_status = QtWidgets.QLabel()
        actions.addWidget(self.li_status)
        layout.addLayout(actions)

        self.result_tabs = ResultTabs()
        layout.addWidget(self.result_tabs, 1)
        self.result_label = QtWidgets.QLabel("尚未分析｜非臨床診斷工具")
        self.result_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.result_label)
        self.channel_grid.selectionChanged.connect(self._update_channel_state)
        self._update_channel_state()
        self.setCentralWidget(root)

    def _load_settings_into_ui(self) -> None:
        self.task_start.setValue(float(self.analysis_settings.task_start))
        self.task_end.setValue(float(self.analysis_settings.task_end))
        self.measure_end.setValue(float(self.analysis_settings.measure_end))
        self.filter_size.setValue(int(self.analysis_settings.filter_num))

    def _browse(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "選擇 NIRS Excel",
            self.analysis_settings.last_open_dir,
            "NIRS 資料 (*.xlsx *.xls *.csv)",
        )
        if filename:
            self.file_edit.setText(filename)

    def _analyze(self) -> None:
        try:
            if self.analysis_mode.currentIndex() == 1:
                self.study_result = self.service.analyze_study(
                    StudyAnalysisRequest(
                        manifest_path=Path(self.file_edit.text()),
                        task_start=self.task_start.value(),
                        task_end=self.task_end.value(),
                        measure_end=self.measure_end.value(),
                        baseline_end=self.task_start.value(),
                        filter_size=self.filter_size.value(),
                    )
                )
                if not self.study_result.single_results:
                    details = " · ".join(
                        f"{issue.code}: {issue.message}" for issue in self.study_result.errors
                    )
                    raise ValueError(details or "研究資料集沒有可分析的檔案")
                self.result = next(iter(self.study_result.single_results.values()))
            else:
                self.study_result = None
                self.result = self.service.analyze_single(
                    SingleAnalysisRequest(
                        path=Path(self.file_edit.text()),
                        task_start=self.task_start.value(),
                        task_end=self.task_end.value(),
                        measure_end=self.measure_end.value(),
                        baseline_end=self.task_start.value(),
                        filter_size=self.filter_size.value(),
                        excluded_channels=tuple(
                            channel
                            for channel in range(1, 16)
                            if channel not in self.channel_grid.selected_channels
                        ),
                    )
                )
        except Exception as error:  # noqa: BLE001 - Qt boundary converts errors to a dialog
            QtWidgets.QMessageBox.warning(self, "分析失敗", str(error))
            return
        self.view_model = build_report_view_model(self.result, title="NIRS 分析報告")
        if self.study_result is not None:
            pairing = self.study_result.pairing
            if pairing is not None and pairing.paired_n == 0:
                pairing = None
            regional = self.study_result.regional
            if regional is not None and not regional.contrasts:
                regional = None
            pair_exclusions = (
                self.study_result.pairing.exclusions
                if self.study_result.pairing is not None
                else ()
            )
            self.view_model = replace(
                self.view_model,
                prepost_result=pairing,
                regional_result=regional,
                exclusions=tuple(self.study_result.errors) + tuple(pair_exclusions),
                metadata={
                    **self.view_model.metadata,
                    "study_file_count": len(self.study_result.single_results),
                },
            )
        for channel, series in self.view_model.channel_series.items():
            self.channel_grid.set_channel_state(channel, series.state)
        self.result_tabs.set_view_model(self.view_model)
        self.result_label.setText(
            f"分析完成｜有效 {len(self.channel_grid.selected_channels)}/15 通道｜"
            f"品質警告 {len(self.view_model.quality_summary)} 項｜非臨床診斷工具"
        )
        self.export_button.setEnabled(True)
        self.report_button.setEnabled(True)

    def _create_report(self) -> None:
        if self.view_model is None:
            QtWidgets.QMessageBox.information(self, "提示", "請先完成分析")
            return
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "儲存報告",
            str(self.paths.reports / f"NIRS-{datetime.now().astimezone():%Y%m%d}.docx"),
            "Word (*.docx)",
        )
        if not destination:
            return
        renderer = ReportDashboardRenderer()
        pages: dict[str, Path] = {}
        render_jobs = {"overview": renderer.render_overview(self.view_model)}
        if self.view_model.laterality is not None:
            render_jobs["laterality"] = renderer.render_laterality(self.view_model)
        if self.view_model.prepost_result is not None:
            render_jobs["prepost"] = renderer.render_prepost(self.view_model)
        if self.view_model.regional_result is not None:
            render_jobs["regional"] = renderer.render_regional(self.view_model)
        for name, figure in render_jobs.items():
            image_path = self.paths.images / f"report-{name}.png"
            figure.savefig(image_path, dpi=300, facecolor="white")
            plt.close(figure)
            pages[name] = image_path
        build_advanced_report(
            Path(destination),
            self.report_settings,
            PatientInfo(measurement_date=datetime.now().astimezone().date()),
            self.view_model,
            pages,
        )
        QtWidgets.QMessageBox.information(self, "完成", f"報告已儲存：{destination}")

    def _export_bundle(self) -> None:
        if self.view_model is None:
            return
        destination = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "選擇匯出資料夾的上層位置",
            str(self.paths.reports),
        )
        if not destination:
            return
        bundle = Path(destination) / f"NIRS-{datetime.now().astimezone():%Y%m%d-%H%M%S}"
        try:
            export_result_bundle(
                bundle,
                self.view_model,
                subject_level_results=(
                    self.study_result.subject_level_results
                    if self.study_result is not None
                    else None
                ),
            )
        except Exception as error:  # noqa: BLE001 - Qt boundary converts errors to a dialog
            QtWidgets.QMessageBox.warning(self, "匯出失敗", str(error))
            return
        QtWidgets.QMessageBox.information(self, "完成", f"資料包已儲存：{bundle}")

    def _update_channel_state(self) -> None:
        right = self.channel_grid.roi_count("right_pfc")
        left = self.channel_grid.roi_count("left_pfc")
        self.li_status.setText(
            f"LI：Right {right[0]}/{right[1]}、Left {left[0]}/{left[1]}"
            if self.channel_grid.li_available
            else "LI 無法執行：左右 PFC 均需有效通道"
        )

    def closeEvent(self, event) -> None:
        self.analysis_settings.task_start = str(self.task_start.value())
        self.analysis_settings.task_end = str(self.task_end.value())
        self.analysis_settings.measure_end = str(self.measure_end.value())
        self.analysis_settings.filter_num = self.filter_size.value()
        if self.file_edit.text():
            self.analysis_settings.last_open_dir = str(Path(self.file_edit.text()).parent)
        save_settings(self.paths.app_settings, self.analysis_settings)
        super().closeEvent(event)
