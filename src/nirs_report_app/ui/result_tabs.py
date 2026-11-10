from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PyQt5 import QtCore, QtWidgets

from ..report_models import ReportViewModel
from ..visualization import ReportDashboardRenderer
from .report_preview import ReportPreview


class FigureResultPage(QtWidgets.QWidget):
    def __init__(self, empty_text: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.empty_label = QtWidgets.QLabel(empty_text)
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.empty_label)
        self.canvas: FigureCanvasQTAgg | None = None

    def set_figure(self, figure) -> None:
        if self.canvas is not None:
            old_figure = self.canvas.figure
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            plt.close(old_figure)
        self.empty_label.hide()
        self.canvas = FigureCanvasQTAgg(figure)
        self.layout.addWidget(self.canvas)


class ResultTabs(QtWidgets.QTabWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.overview = FigureResultPage("完成分析後顯示總覽")
        self.laterality = FigureResultPage("需要左右 PFC 有效資料才能執行 LI")
        self.prepost = FigureResultPage("匯入含 pre/post 的研究清單以建立前後測結果")
        self.regional = FigureResultPage("選擇至少兩個獨立 ROI 以比較腦區差異")
        self.report_preview = ReportPreview()
        for name, widget in (
            ("總覽", self.overview),
            ("側化 LI", self.laterality),
            ("前後測", self.prepost),
            ("腦區差異", self.regional),
            ("報告預覽", self.report_preview),
        ):
            self.addTab(widget, name)

    def set_view_model(self, model: ReportViewModel) -> None:
        renderer = ReportDashboardRenderer(
            width_inches=9.0, height_inches=5.5, dpi=100, show_title=False
        )
        self.overview.set_figure(
            renderer.render_overview(model, width_inches=9.0, height_inches=5.5, dpi=100)
        )
        if model.laterality is not None:
            self.laterality.set_figure(
                renderer.render_laterality(model, width_inches=9.0, height_inches=5.5, dpi=100)
            )
        if model.prepost_result is not None:
            self.prepost.set_figure(
                renderer.render_prepost(model, width_inches=9.0, height_inches=5.5, dpi=100)
            )
        if model.regional_result is not None:
            self.regional.set_figure(
                renderer.render_regional(model, width_inches=9.0, height_inches=5.5, dpi=100)
            )
        self.report_preview.set_view_model(model)
