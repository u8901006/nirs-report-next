from __future__ import annotations

import sys
from collections.abc import Sequence

from .paths import default_paths


def _smoke_test() -> int:
    from .reporting import build_advanced_report
    from .services import NirsAnalysisService
    from .visualization import ReportDashboardRenderer

    paths = default_paths()
    paths.ensure_runtime_directories()
    _ = (NirsAnalysisService, ReportDashboardRenderer, build_advanced_report)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--smoke-test" in arguments:
        return _smoke_test()

    from PyQt5 import QtWidgets

    from .plugins import discover_plugins
    from .ui.main_window import MainWindow

    qt_arguments = [sys.argv[0], *arguments]
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(qt_arguments)
    window = MainWindow(default_paths())
    for plugin in discover_plugins():
        plugin.register(window)
    window.show()
    return int(application.exec_())


if __name__ == "__main__":
    raise SystemExit(main())
