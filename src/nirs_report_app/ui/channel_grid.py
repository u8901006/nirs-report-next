from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from ..analysis.models import BUILTIN_ROIS

_STATE_LABELS = {
    "valid": "有效",
    "partial": "部分 !",
    "missing": "缺少",
    "invalid": "無效 ×",
    "excluded_by_user": "排除",
}
_STATE_TOOLTIPS = {
    "valid": "資料有效。點一下可排除這個通道。",
    "partial": "只有部分資料有效。點一下可排除這個通道。",
    "missing": "檔案裡沒有這個通道。",
    "invalid": "這個通道的資料無效。",
    "excluded_by_user": "已排除。",
}


class ChannelGrid(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()

    # (property title, display label, first grid column, rows of channels)
    _REGIONS = (
        ("右前額葉 Right PFC", "右前額葉", 0, ((1, 2), (3, 4))),
        ("前額中區 Anterior Frontal", "前額中區", 3, ((5, 6, 7, 8), (9, 10, 11))),
        ("左前額葉 Left PFC", "左前額葉", 8, ((12, 13), (14, 15))),
    )

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._states = {channel: "valid" for channel in range(1, 16)}
        self._buttons: dict[int, QtWidgets.QToolButton] = {}
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        grid.setColumnMinimumWidth(2, 8)
        grid.setColumnMinimumWidth(7, 8)
        for title, label, first_column, rows in self._REGIONS:
            heading = QtWidgets.QLabel(label)
            heading.setObjectName("fieldLabel")
            heading.setToolTip(title)
            grid.addWidget(heading, 0, first_column, 1, max(len(row) for row in rows))
            for row_index, row in enumerate(rows):
                for column_index, channel in enumerate(row):
                    button = QtWidgets.QToolButton()
                    button.setObjectName("channelButton")
                    button.setCheckable(True)
                    button.setChecked(True)
                    button.setMinimumSize(38, 40)
                    button.setSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
                    )
                    button.setProperty("channel", channel)
                    button.setProperty("montage_position", (title, row_index, column_index))
                    button.clicked.connect(self._selection_changed)
                    grid.addWidget(button, row_index + 1, first_column + column_index)
                    self._buttons[channel] = button
        root.addLayout(grid)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("hint")
        root.addWidget(self.status_label)
        self._selection_changed()

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
        if state not in _STATE_LABELS:
            raise ValueError(f"Unknown channel state: {state}")
        self._states[channel] = state
        button = self._buttons[channel]
        unavailable = state in {"missing", "invalid", "excluded_by_user"}
        button.setEnabled(not unavailable)
        if unavailable:
            button.setChecked(False)
        button.setProperty("state", state)
        button.style().unpolish(button)
        button.style().polish(button)
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
        self._refresh_buttons()
        self._refresh_status()
        self.selectionChanged.emit()

    def _refresh_buttons(self) -> None:
        """Keep each button's words in step with what will actually be analysed."""
        for channel, button in self._buttons.items():
            state = self._states[channel]
            switched_off = state in {"valid", "partial"} and not button.isChecked()
            shown = "excluded_by_user" if switched_off else state
            button.setText(f"{channel:02d}\n{_STATE_LABELS[shown]}")
            button.setToolTip(
                f"CH{channel:02d}：已排除。再點一下可恢復。"
                if switched_off
                else f"CH{channel:02d}：{_STATE_TOOLTIPS[state]}"
            )

    def _refresh_status(self) -> None:
        count = len(self.selected_channels)
        self.status_label.setText(f"有效 {count}/15 通道")
