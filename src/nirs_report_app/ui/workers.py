from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from PyQt5 import QtCore


class StudyAnalysisWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, int)
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        items: Sequence[Any],
        analyze: Callable[[Any], Any],
        *,
        destination: Path | None = None,
        finalize: Callable[[list[Any], Path], None] | None = None,
    ) -> None:
        super().__init__()
        self._items = tuple(items)
        self._analyze = analyze
        self._destination = Path(destination) if destination is not None else None
        self._finalize = finalize
        self._cancel_requested = False

    @QtCore.pyqtSlot()
    def cancel(self) -> None:
        self._cancel_requested = True

    @QtCore.pyqtSlot()
    def run(self) -> None:
        results: list[Any] = []
        try:
            for index, item in enumerate(self._items, start=1):
                if self._cancel_requested:
                    self.cancelled.emit()
                    return
                results.append(self._analyze(item))
                self.progress.emit(index, len(self._items))
                if self._cancel_requested:
                    self.cancelled.emit()
                    return
            if self._finalize is not None and self._destination is not None:
                self._finalize(results, self._destination)
            self.completed.emit(results)
        except Exception as error:  # noqa: BLE001 - worker boundary sends failure to UI
            self.failed.emit(str(error))
        finally:
            self.finished.emit()
