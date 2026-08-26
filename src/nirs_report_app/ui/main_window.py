from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from ..paths import AppPaths
from ..reporting import PatientInfo, build_report
from ..services import AnalysisResult, NirsAnalysisService
from ..settings import AnalysisSettings, ReportSettings, load_settings, save_settings


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.paths.ensure_runtime_directories()
        self.analysis_settings = load_settings(paths.app_settings, AnalysisSettings)
        self.report_settings = load_settings(paths.report_settings, ReportSettings)
        self.service = NirsAnalysisService()
        self.result: AnalysisResult | None = None
        self._setup_ui()
        self._load_settings_into_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("NIRS 分析報告")
        self.resize(900, 520)
        root = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(root)

        file_row = QtWidgets.QHBoxLayout()
        self.file_edit = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton("選擇 NIRS Excel")
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
        layout.addLayout(form)

        actions = QtWidgets.QHBoxLayout()
        analyze_button = QtWidgets.QPushButton("分析")
        report_button = QtWidgets.QPushButton("產生報告")
        analyze_button.clicked.connect(self._analyze)
        report_button.clicked.connect(self._create_report)
        actions.addWidget(analyze_button)
        actions.addWidget(report_button)
        layout.addLayout(actions)

        self.result_label = QtWidgets.QLabel("尚未分析")
        self.result_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.result_label)
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
            "Excel (*.xlsx *.xls)",
        )
        if filename:
            self.file_edit.setText(filename)

    def _analyze(self) -> None:
        try:
            self.result = self.service.analyze(
                Path(self.file_edit.text()),
                task_start=self.task_start.value(),
                task_end=self.task_end.value(),
                measure_end=self.measure_end.value(),
                filter_size=self.filter_size.value(),
            )
        except Exception as error:  # noqa: BLE001 - Qt boundary converts errors to a dialog
            QtWidgets.QMessageBox.warning(self, "分析失敗", str(error))
            return
        feature = self.result.features
        self.result_label.setText(
            f"前額中區：積分 {feature.front_integral}，重心 {feature.front_centroid_value}\n"
            f"前額側區：積分 {feature.side_integral}，重心 {feature.side_centroid_value}"
        )

    def _create_report(self) -> None:
        if self.result is None:
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
        build_report(
            Path(destination),
            self.report_settings,
            PatientInfo(measurement_date=datetime.now().astimezone().date()),
            self.result.features,
        )
        QtWidgets.QMessageBox.information(self, "完成", f"報告已儲存：{destination}")

    def closeEvent(self, event) -> None:
        self.analysis_settings.task_start = str(self.task_start.value())
        self.analysis_settings.task_end = str(self.task_end.value())
        self.analysis_settings.measure_end = str(self.measure_end.value())
        self.analysis_settings.filter_num = self.filter_size.value()
        if self.file_edit.text():
            self.analysis_settings.last_open_dir = str(Path(self.file_edit.text()).parent)
        save_settings(self.paths.app_settings, self.analysis_settings)
        super().closeEvent(event)
