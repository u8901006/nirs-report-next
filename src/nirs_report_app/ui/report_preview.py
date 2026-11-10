from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtGui, QtWidgets

from ..messages import describe_warning
from ..report_models import ReportViewModel
from ..reporting import DISCLAIMER
from ..visualization import ReportDashboardRenderer

# Page name shown in the list -> key used for report figures.
FIGURE_PAGES = {
    "總覽": "overview",
    "側化 LI": "laterality",
    "前後測": "prepost",
    "腦區差異": "regional",
}
# Rendered at twice the 100% size so zooming in stays sharp.
_PREVIEW_DPI = 160


class ReportPreview(QtWidgets.QWidget):
    _MANDATORY = frozenset({"品質控管", "方法與聲明"})

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: ReportViewModel | None = None
        self._pixmaps: dict[str, QtGui.QPixmap] = {}
        root = QtWidgets.QVBoxLayout(self)
        body = QtWidgets.QHBoxLayout()
        side = QtWidgets.QVBoxLayout()
        hint = QtWidgets.QLabel("勾選的頁面會放進 Word 報告")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        side.addWidget(hint)
        self.page_list = QtWidgets.QListWidget()
        side.addWidget(self.page_list, 1)
        side_holder = QtWidgets.QWidget()
        side_holder.setLayout(side)
        side_holder.setMaximumWidth(220)
        side.setContentsMargins(0, 0, 0, 0)
        self.preview_label = QtWidgets.QLabel("完成分析後顯示報告頁面")
        self.preview_label.setObjectName("emptyState")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.preview_label.setMargin(24)
        self.preview_scroll = QtWidgets.QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_scroll.setWidget(self.preview_label)
        body.addWidget(side_holder)
        body.addWidget(self.preview_scroll, 1)
        root.addLayout(body, 1)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("縮放"))
        self.zoom = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom.setRange(60, 200)
        self.zoom.setValue(100)
        controls.addWidget(self.zoom, 1)
        self.zoom_label = QtWidgets.QLabel("100%")
        controls.addWidget(self.zoom_label)
        self.export_selected_button = QtWidgets.QPushButton("另存這一頁的圖")
        self.export_selected_button.setEnabled(False)
        controls.addWidget(self.export_selected_button)
        root.addLayout(controls)
        self.zoom.valueChanged.connect(self._zoom_changed)
        self.page_list.currentRowChanged.connect(self._page_selected)
        self.export_selected_button.clicked.connect(self._export_selected)

    def set_view_model(self, model: ReportViewModel) -> None:
        self._model = model
        self._pixmaps.clear()
        pages = ["總覽"]
        if model.laterality is not None:
            pages.append("側化 LI")
        if model.prepost_result is not None:
            pages.append("前後測")
        if model.regional_result is not None:
            pages.append("腦區差異")
        pages.extend(("品質控管", "方法與聲明"))
        self.page_list.clear()
        for name in pages:
            item = QtWidgets.QListWidgetItem(name)
            item.setCheckState(QtCore.Qt.Checked)
            if name in self._MANDATORY:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsUserCheckable)
                item.setToolTip("必要頁面，不可移除")
            self.page_list.addItem(item)
        self.export_selected_button.setEnabled(False)
        self._show_text("點左邊的頁面名稱來預覽")

    def page_names(self) -> list[str]:
        return [self.page_list.item(index).text() for index in range(self.page_list.count())]

    def is_page_mandatory(self, name: str) -> bool:
        return name in self._MANDATORY

    def checked_figure_keys(self) -> set[str]:
        """Figure pages the user left ticked, as the keys the report builder uses."""
        keys: set[str] = set()
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            key = FIGURE_PAGES.get(item.text())
            if key is not None and item.checkState() == QtCore.Qt.Checked:
                keys.add(key)
        return keys

    def _current_name(self) -> str | None:
        item = self.page_list.currentItem()
        return item.text() if item is not None else None

    def _render_figure(self, key: str, *, dpi: int, full_page: bool = False):
        renderer = ReportDashboardRenderer(show_title=False)
        render = getattr(renderer, f"render_{key}")
        if full_page:
            return render(self._model, dpi=dpi)
        return render(self._model, width_inches=9.0, height_inches=6.36, dpi=dpi)

    def _page_pixmap(self, name: str) -> QtGui.QPixmap:
        if name not in self._pixmaps:
            figure = self._render_figure(FIGURE_PAGES[name], dpi=_PREVIEW_DPI)
            buffer = BytesIO()
            figure.savefig(buffer, format="png", dpi=_PREVIEW_DPI, facecolor="white")
            plt.close(figure)
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(buffer.getvalue(), "PNG")
            self._pixmaps[name] = pixmap
        return self._pixmaps[name]

    def _show_text(self, text: str) -> None:
        self.preview_label.setPixmap(QtGui.QPixmap())
        self.preview_label.setText(text)

    def _refresh(self) -> None:
        name = self._current_name()
        if name is None or self._model is None:
            return
        if name in FIGURE_PAGES:
            pixmap = self._page_pixmap(name)
            width = max(1, round(pixmap.width() * self.zoom.value() / 200))
            self.preview_label.setPixmap(
                pixmap.scaledToWidth(width, QtCore.Qt.SmoothTransformation)
            )
        elif name == "品質控管":
            warnings = [describe_warning(code) for code in self._model.quality_summary]
            self._show_text("品質控管\n\n" + ("\n".join(warnings) or "未記錄品質警告"))
        else:
            self._show_text(f"方法與聲明\n\n分析設定與追溯資訊列在報告附錄。\n\n{DISCLAIMER}")

    def _page_selected(self, row: int) -> None:
        name = self._current_name()
        self.export_selected_button.setEnabled(row >= 0)
        self.export_selected_button.setToolTip(
            "" if name in FIGURE_PAGES else "這一頁是文字，沒有圖可以另存"
        )
        self._refresh()

    def _zoom_changed(self, value: int) -> None:
        self.zoom_label.setText(f"{value}%")
        self._refresh()

    def _export_selected(self) -> None:
        name = self._current_name()
        if name not in FIGURE_PAGES or self._model is None:
            QtWidgets.QMessageBox.information(self, "提示", "這一頁是文字，沒有圖可以另存。")
            return
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "另存圖片", f"NIRS-{FIGURE_PAGES[name]}.png", "PNG (*.png)"
        )
        if not destination:
            return
        figure = self._render_figure(FIGURE_PAGES[name], dpi=300, full_page=True)
        try:
            figure.savefig(Path(destination), dpi=300, facecolor="white")
        except OSError as error:
            QtWidgets.QMessageBox.warning(self, "無法儲存", f"圖片沒有存成功：{error}")
        finally:
            plt.close(figure)
