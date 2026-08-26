from __future__ import annotations

import sys

from .paths import default_paths


def main() -> int:
    from PyQt5 import QtWidgets

    from .plugins import discover_plugins
    from .ui.main_window import MainWindow

    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow(default_paths())
    for plugin in discover_plugins():
        plugin.register(window)
    window.show()
    return int(application.exec_())


if __name__ == "__main__":
    raise SystemExit(main())
