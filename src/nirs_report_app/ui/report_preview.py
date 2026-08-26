from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from ..report_models import ReportViewModel


class ReportPreview(QtWidgets.QWidget):
    _MANDATORY = frozenset({"品質控管", "方法與聲明"})

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        body = QtWidgets.QHBoxLayout()
        self.page_list = QtWidgets.QListWidget()
        self.page_list.setMaximumWidth(220)
        self.preview_label = QtWidgets.QLabel("完成分析後顯示報告頁面")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setStyleSheet("background: white; border: 1px solid #D0D5DD;")
        body.addWidget(self.page_list)
        body.addWidget(self.preview_label, 1)
        root.addLayout(body, 1)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("縮放"))
        self.zoom = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom.setRange(60, 200)
        self.zoom.setValue(100)
        controls.addWidget(self.zoom, 1)
        self.zoom_label = QtWidgets.QLabel("100%")
        controls.addWidget(self.zoom_label)
        self.export_selected_button = QtWidgets.QPushButton("匯出選取頁")
        self.export_selected_button.setEnabled(False)
        controls.addWidget(self.export_selected_button)
        root.addLayout(controls)
        self.zoom.valueChanged.connect(lambda value: self.zoom_label.setText(f"{value}%"))
        self.page_list.currentRowChanged.connect(self._page_selected)

    def set_view_model(self, model: ReportViewModel) -> None:
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

    def page_names(self) -> list[str]:
        return [self.page_list.item(index).text() for index in range(self.page_list.count())]

    def is_page_mandatory(self, name: str) -> bool:
        return name in self._MANDATORY

    def _page_selected(self, row: int) -> None:
        self.export_selected_button.setEnabled(row >= 0)
        if row >= 0:
            self.preview_label.setText(f"{self.page_list.item(row).text()}｜{self.zoom.value()}%")
