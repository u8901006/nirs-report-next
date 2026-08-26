from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from ..analysis.models import BUILTIN_ROIS


class ChannelGrid(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()

    _REGIONS = (
        ("右前額葉 Right PFC", ((1, 2), (3, 4))),
        ("前額中區 Anterior Frontal", ((5, 6, 7, 8), (9, 10, 11))),
        ("左前額葉 Left PFC", ((12, 13), (14, 15))),
    )

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._states = {channel: "valid" for channel in range(1, 16)}
        self._buttons: dict[int, QtWidgets.QToolButton] = {}
        root = QtWidgets.QVBoxLayout(self)
        regions = QtWidgets.QHBoxLayout()
        for title, rows in self._REGIONS:
            group = QtWidgets.QGroupBox(title)
            grid = QtWidgets.QGridLayout(group)
            for row_index, row in enumerate(rows):
                for column_index, channel in enumerate(row):
                    button = QtWidgets.QToolButton()
                    button.setText(f"CH{channel:02d}\n有效")
                    button.setCheckable(True)
                    button.setChecked(True)
                    button.setMinimumSize(72, 48)
                    button.setProperty("channel", channel)
                    button.setProperty("montage_position", (title, row_index, column_index))
                    button.clicked.connect(self._selection_changed)
                    grid.addWidget(button, row_index, column_index)
                    self._buttons[channel] = button
            regions.addWidget(group)
        root.addLayout(regions)
        self.status_label = QtWidgets.QLabel()
        root.addWidget(self.status_label)
        self._refresh_status()

    def channel_button(self, channel: int) -> QtWidgets.QToolButton:
        return self._buttons[channel]

    @property
    def selected_channels(self) -> tuple[int, ...]:
        return tuple(
            channel
            for channel, button in self._buttons.items()
            if button.isChecked() and self._states[channel] in {"valid", "partial"}
        )

    def set_selected_channels(self, channels: set[int]) -> None:
        for channel, button in self._buttons.items():
            button.setChecked(channel in channels and button.isEnabled())
        self._selection_changed()

    def set_channel_state(self, channel: int, state: str) -> None:
        if state not in {"valid", "partial", "missing", "invalid", "excluded_by_user"}:
            raise ValueError(f"Unknown channel state: {state}")
        self._states[channel] = state
        button = self._buttons[channel]
        labels = {
            "valid": "有效",
            "partial": "部分有效 !",
            "missing": "缺少",
            "invalid": "無效 ×",
            "excluded_by_user": "已排除",
        }
        colors = {
            "valid": "#FFFFFF",
            "partial": "#FFF4D6",
            "missing": "#ECEFF2",
            "invalid": "#FCE6E6",
            "excluded_by_user": "#F2F2F2",
        }
        button.setText(f"CH{channel:02d}\n{labels[state]}")
        button.setStyleSheet(
            f"QToolButton {{ background: {colors[state]}; border: 1px solid #AAB2BD; }}"
        )
        unavailable = state in {"missing", "invalid", "excluded_by_user"}
        button.setEnabled(not unavailable)
        if unavailable:
            button.setChecked(False)
        self._selection_changed()

    def roi_count(self, roi_id: str) -> tuple[int, int]:
        definition = BUILTIN_ROIS[roi_id]
        selected = set(self.selected_channels)
        return (len(selected.intersection(definition.channels)), len(definition.channels))

    @property
    def li_available(self) -> bool:
        right, _ = self.roi_count("right_pfc")
        left, _ = self.roi_count("left_pfc")
        return right > 0 and left > 0

    def _selection_changed(self) -> None:
        self._refresh_status()
        self.selectionChanged.emit()

    def _refresh_status(self) -> None:
        count = len(self.selected_channels)
        self.status_label.setText(f"有效 {count}/15 通道")
