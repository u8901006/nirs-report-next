from __future__ import annotations

from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable


@runtime_checkable
class NirsPlugin(Protocol):
    """Extension contract for optional UI or analysis features."""

    name: str

    def register(self, application: object) -> None: ...


def discover_plugins() -> list[NirsPlugin]:
    plugins: list[NirsPlugin] = []
    for entry_point in entry_points(group="nirs_report.plugins"):
        candidate = entry_point.load()()
        if not isinstance(candidate, NirsPlugin):
            raise TypeError(f"Plugin {entry_point.name!r} does not implement NirsPlugin")
        plugins.append(candidate)
    return plugins
