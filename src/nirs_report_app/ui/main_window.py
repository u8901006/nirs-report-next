from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
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
from .theme import APP_STYLESHEET, set_primary

_SOURCE_SUFFIXES = frozenset({".xlsx", ".xls", ".csv"})
_SIDEBAR_WIDTH = 420
_SOURCE_PLACEHOLDERS = (
    "把 NIRS Excel 拖到視窗裡，或按「選擇資料」",
    "把研究清單（CSV／XLSX）拖到視窗裡，或按「選擇資料」",
)


def guess_measurement_date(path: Path) -> date | None:
    """Read the measurement day from an export named like ``250808_0845_….xlsx``."""
    match = re.match(r"(\d{2})(\d{2})(\d{2})(?!\d)", Path(path).name)
    if match is None:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(2000 + year, month, day)
    except ValueError:
        return None


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

    # ---- layout -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle("NIRS 分析報告")
        self.setMinimumSize(1280, 800)
        self.resize(1500, 920)
        self.setAcceptDrops(True)
        self.setStyleSheet(APP_STYLESHEET)

        root = QtWidgets.QWidget(self)
        columns = QtWidgets.QHBoxLayout(root)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)
        columns.addWidget(self._build_sidebar())
        edge = QtWidgets.QFrame()
        edge.setObjectName("sidebarEdge")
        columns.addWidget(edge)
        columns.addWidget(self._build_result_pane(), 1)
        self.setCentralWidget(root)

        self.analysis_mode.currentIndexChanged.connect(self._mode_changed)
        self.file_edit.textChanged.connect(self._source_changed)
        self.channel_grid.selectionChanged.connect(self._update_channel_state)
        self._mode_changed(self.analysis_mode.currentIndex())
        self._update_channel_state()

    @staticmethod
    def _step_title(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("stepTitle")
        return label

    @staticmethod
    def _field(label: str, widget: QtWidgets.QWidget) -> QtWidgets.QVBoxLayout:
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(2)
        caption = QtWidgets.QLabel(label)
        caption.setObjectName("fieldLabel")
        column.addWidget(caption)
        column.addWidget(widget)
        return column

    def _build_sidebar(self) -> QtWidgets.QWidget:
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(_SIDEBAR_WIDTH)
        outer = QtWidgets.QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QtWidgets.QWidget()
        body.setObjectName("sidebarBody")
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("NIRS 分析報告")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        # 1 資料
        layout.addWidget(self._step_title("1　資料"))
        self.analysis_mode = QtWidgets.QComboBox()
        self.analysis_mode.addItems(("單次量測", "研究資料集"))
        layout.addWidget(self.analysis_mode)
        file_row = QtWidgets.QHBoxLayout()
        self.file_edit = QtWidgets.QLineEdit()
        self.file_edit.setObjectName("dropTarget")
        browse_button = QtWidgets.QPushButton("選擇資料")
        browse_button.clicked.connect(self._browse)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse_button)
        layout.addLayout(file_row)

        # 2 個案
        layout.addWidget(self._step_title("2　個案"))
        self.patient_id = QtWidgets.QLineEdit()
        self.patient_name = QtWidgets.QLineEdit()
        self.gender = QtWidgets.QComboBox()
        self.gender.addItems(("", "男", "女", "其他"))
        self.measurement_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.measurement_date.setCalendarPopup(True)
        self.measurement_date.setDisplayFormat("yyyy-MM-dd")
        self.doctor = QtWidgets.QLineEdit()
        self.opinion = QtWidgets.QPlainTextEdit()
        self.opinion.setPlaceholderText("會印在報告第一頁。留白則印出空白框供手寫。")
        self.opinion.setFixedHeight(64)
        self.opinion.setTabChangesFocus(True)
        patient = QtWidgets.QGridLayout()
        patient.setHorizontalSpacing(10)
        patient.setVerticalSpacing(6)
        patient.addLayout(self._field("編號", self.patient_id), 0, 0)
        patient.addLayout(self._field("姓名", self.patient_name), 0, 1)
        patient.addLayout(self._field("性別", self.gender), 1, 0)
        patient.addLayout(self._field("量測日期", self.measurement_date), 1, 1)
        patient.addLayout(self._field("醫師", self.doctor), 2, 0, 1, 2)
        patient.addLayout(self._field("判讀意見", self.opinion), 3, 0, 1, 2)
        layout.addLayout(patient)

        # 3 作業時間
        layout.addWidget(self._step_title("3　作業時間"))
        self.task_start = QtWidgets.QDoubleSpinBox()
        self.task_end = QtWidgets.QDoubleSpinBox()
        self.measure_end = QtWidgets.QDoubleSpinBox()
        for widget in (self.task_start, self.task_end, self.measure_end):
            widget.setRange(0, 3600)
            widget.setDecimals(2)
            widget.setSuffix(" 秒")
        self.filter_size = QtWidgets.QSpinBox()
        self.filter_size.setRange(0, 99)
        self.filter_size.setToolTip("移動平均的點數。0 表示不平滑。")
        timing = QtWidgets.QGridLayout()
        timing.setHorizontalSpacing(10)
        timing.setVerticalSpacing(6)
        timing.addLayout(self._field("作業開始", self.task_start), 0, 0)
        timing.addLayout(self._field("作業結束", self.task_end), 0, 1)
        timing.addLayout(self._field("測量結束", self.measure_end), 1, 0)
        timing.addLayout(self._field("平滑視窗", self.filter_size), 1, 1)
        layout.addLayout(timing)

        # 4 通道
        layout.addWidget(self._step_title("4　通道"))
        self.channel_hint = QtWidgets.QLabel("點一下通道可以排除或恢復。畫面左邊是受測者的右腦。")
        self.channel_hint.setObjectName("hint")
        self.channel_hint.setWordWrap(True)
        layout.addWidget(self.channel_hint)
        self.channel_grid = ChannelGrid()
        layout.addWidget(self.channel_grid)
        self.li_status = QtWidgets.QLabel()
        self.li_status.setObjectName("hint")
        self.li_status.setWordWrap(True)
        layout.addWidget(self.li_status)
        layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        footer = QtWidgets.QVBoxLayout()
        footer.setContentsMargins(20, 10, 20, 16)
        self.analyze_button = QtWidgets.QPushButton("執行分析")
        self.analyze_button.setObjectName("analyzeButton")
        self.analyze_button.clicked.connect(self._analyze)
        footer.addWidget(self.analyze_button)
        outer.addLayout(footer)
        return sidebar

    def _build_result_pane(self) -> QtWidgets.QWidget:
        pane = QtWidgets.QWidget()
        pane.setObjectName("resultPane")
        outer = QtWidgets.QVBoxLayout(pane)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QtWidgets.QVBoxLayout()
        content.setContentsMargins(20, 14, 20, 14)
        content.setSpacing(10)
        actions = QtWidgets.QHBoxLayout()
        self.source_label = QtWidgets.QLabel("尚未選擇資料")
        self.source_label.setObjectName("hint")
        actions.addWidget(self.source_label, 1)
        self.export_button = QtWidgets.QPushButton("匯出資料包")
        self.export_button.setEnabled(False)
        self.export_button.setToolTip("先執行分析，才能匯出")
        self.export_button.clicked.connect(self._export_bundle)
        actions.addWidget(self.export_button)
        self.report_button = QtWidgets.QPushButton("產生 Word 報告")
        self.report_button.setEnabled(False)
        self.report_button.setToolTip("先執行分析，才能產生報告")
        self.report_button.clicked.connect(self._create_report)
        actions.addWidget(self.report_button)
        content.addLayout(actions)
        self.result_tabs = ResultTabs()
        content.addWidget(self.result_tabs, 1)
        outer.addLayout(content, 1)

        strip = QtWidgets.QFrame()
        strip.setObjectName("statusStrip")
        strip_layout = QtWidgets.QHBoxLayout(strip)
        strip_layout.setContentsMargins(20, 6, 20, 6)
        self.result_label = QtWidgets.QLabel("尚未分析｜非臨床診斷工具")
        self.result_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        strip_layout.addWidget(self.result_label, 1)
        outer.addWidget(strip)
        self._set_next_step(analysed=False)
        return pane

    def _set_next_step(self, *, analysed: bool) -> None:
        """Exactly one solid button at a time: analyse first, then make the report."""
        set_primary(self.analyze_button, not analysed)
        set_primary(self.report_button, analysed)

    # ---- settings and input -----------------------------------------------------

    def _load_settings_into_ui(self) -> None:
        self.task_start.setValue(float(self.analysis_settings.task_start))
        self.task_end.setValue(float(self.analysis_settings.task_end))
        self.measure_end.setValue(float(self.analysis_settings.measure_end))
        self.filter_size.setValue(int(self.analysis_settings.filter_num))
        self.doctor.setText(self.analysis_settings.last_doctor)

    def _mode_changed(self, index: int) -> None:
        study = index == 1
        self.file_edit.setPlaceholderText(_SOURCE_PLACEHOLDERS[index])
        self.channel_grid.setEnabled(not study)
        self.channel_hint.setText(
            "研究資料集會使用每個檔案的全部通道。"
            if study
            else "點一下通道可以排除或恢復。畫面左邊是受測者的右腦。"
        )

    def _source_changed(self, text: str) -> None:
        path = Path(text) if text else None
        self.source_label.setText(path.name if path is not None else "尚未選擇資料")
        if path is None:
            return
        measured = guess_measurement_date(path)
        if measured is not None:
            self.measurement_date.setDate(QtCore.QDate(measured.year, measured.month, measured.day))

    def _browse(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "選擇 NIRS 資料",
            self.analysis_settings.last_open_dir,
            "NIRS 資料 (*.xlsx *.xls *.csv)",
        )
        if filename:
            self.file_edit.setText(filename)

    @staticmethod
    def _dropped_source(event) -> Path | None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in _SOURCE_SUFFIXES:
                return path
        return None

    def dragEnterEvent(self, event) -> None:
        if self._dropped_source(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = self._dropped_source(event)
        if path is not None:
            self.file_edit.setText(str(path))
            event.acceptProposedAction()

    def _patient_info(self) -> PatientInfo:
        measured = self.measurement_date.date()
        return PatientInfo(
            patient_id=self.patient_id.text().strip(),
            name=self.patient_name.text().strip(),
            gender=self.gender.currentText(),
            measurement_date=date(measured.year(), measured.month(), measured.day()),
            doctor=self.doctor.text().strip(),
            opinion=self.opinion.toPlainText().strip(),
        )

    # ---- actions ----------------------------------------------------------------

    def _run_analysis(self) -> None:
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
            return
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

    def _analyze(self) -> None:
        if not self.file_edit.text().strip():
            QtWidgets.QMessageBox.information(self, "還沒選資料", "請先在「1 資料」選一個檔案。")
            return
        self.result_label.setText("分析中…")
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self._run_analysis()
        except Exception as error:  # noqa: BLE001 - Qt boundary converts errors to a dialog
            QtWidgets.QApplication.restoreOverrideCursor()
            self.result_label.setText("分析失敗｜非臨床診斷工具")
            QtWidgets.QMessageBox.warning(self, "分析失敗", str(error))
            return
        try:
            self._show_result()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _show_result(self) -> None:
        self.view_model = build_report_view_model(self.result, title="NIRS 分析報告")
        # Record the timing the charts shade and the report appendix lists.
        self.view_model = replace(
            self.view_model,
            analysis_config={
                **self.view_model.analysis_config,
                "task_start": self.task_start.value(),
                "task_end": self.task_end.value(),
                "measure_end": self.measure_end.value(),
                "filter_size": self.filter_size.value(),
            },
        )
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
        self.result_tabs.setCurrentIndex(0)
        self.result_label.setText(
            f"分析完成｜有效 {len(self.channel_grid.selected_channels)}/15 通道｜"
            f"品質警告 {len(self.view_model.quality_summary)} 項｜非臨床診斷工具"
        )
        for button in (self.export_button, self.report_button):
            button.setEnabled(True)
            button.setToolTip("")
        self._set_next_step(analysed=True)

    def _create_report(self) -> None:
        if self.view_model is None:
            QtWidgets.QMessageBox.information(self, "提示", "請先完成分析")
            return
        patient = self._patient_info()
        stem = "-".join(
            part
            for part in ("NIRS", patient.patient_id, f"{patient.measurement_date:%Y%m%d}")
            if part
        )
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "儲存報告",
            str(self.paths.reports / f"{stem}.docx"),
            "Word (*.docx)",
        )
        if not destination:
            return
        wanted = self.result_tabs.report_preview.checked_figure_keys()
        renderer = ReportDashboardRenderer(show_title=False)
        render_jobs = {"overview": renderer.render_overview}
        if self.view_model.laterality is not None:
            render_jobs["laterality"] = renderer.render_laterality
        if self.view_model.prepost_result is not None:
            render_jobs["prepost"] = renderer.render_prepost
        if self.view_model.regional_result is not None:
            render_jobs["regional"] = renderer.render_regional
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            pages: dict[str, Path] = {}
            for name, render in render_jobs.items():
                if name not in wanted:
                    continue
                figure = render(self.view_model)
                image_path = self.paths.images / f"report-{name}.png"
                figure.savefig(image_path, dpi=300, facecolor="white")
                plt.close(figure)
                pages[name] = image_path
            build_advanced_report(
                Path(destination), self.report_settings, patient, self.view_model, pages
            )
        except PermissionError:
            QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QMessageBox.warning(
                self,
                "無法儲存報告",
                "這個檔案可能正在 Word 裡開著。請先關掉它，或換一個檔名再存一次。",
            )
            return
        except Exception as error:  # noqa: BLE001 - Qt boundary converts errors to a dialog
            QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QMessageBox.warning(self, "無法產生報告", str(error))
            return
        QtWidgets.QApplication.restoreOverrideCursor()
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
            f"側化 LI 可計算：右 {right[0]}/{right[1]}、左 {left[0]}/{left[1]}"
            if self.channel_grid.li_available
            else "側化 LI 無法計算：左右前額葉都要有至少一個有效通道"
        )

    def closeEvent(self, event) -> None:
        self.analysis_settings.task_start = str(self.task_start.value())
        self.analysis_settings.task_end = str(self.task_end.value())
        self.analysis_settings.measure_end = str(self.measure_end.value())
        self.analysis_settings.filter_num = self.filter_size.value()
        self.analysis_settings.last_doctor = self.doctor.text().strip()
        if self.file_edit.text():
            self.analysis_settings.last_open_dir = str(Path(self.file_edit.text()).parent)
        save_settings(self.paths.app_settings, self.analysis_settings)
        super().closeEvent(event)
