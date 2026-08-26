from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path

    @property
    def app_settings(self) -> Path:
        return self.root / "settings.ini"

    @property
    def report_settings(self) -> Path:
        return self.root / "Report_settings.ini"

    @property
    def images(self) -> Path:
        return self.root / "img"

    @property
    def reports(self) -> Path:
        return self.root / "report"

    def ensure_runtime_directories(self) -> None:
        self.images.mkdir(parents=True, exist_ok=True)
        self.reports.mkdir(parents=True, exist_ok=True)


def default_paths() -> AppPaths:
    return AppPaths(Path.cwd())
