from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .report_models import ReportViewModel
from .visualization import ReportDashboardRenderer


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _source_provenance(model: ReportViewModel) -> dict[str, Any]:
    provenance = {key: value for key, value in model.provenance.items() if key != "source_files"}
    sources: list[dict[str, Any]] = []
    for raw_path in model.provenance.get("source_files", []):
        source = Path(raw_path).expanduser().resolve()
        record: dict[str, Any] = {"path": str(raw_path), "resolved_path": str(source)}
        if source.is_file():
            record["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        else:
            record["sha256"] = None
            record["warning"] = "E_SOURCE_NOT_FOUND"
        sources.append(record)
    provenance["source_files"] = sources
    return provenance


def _write_figure(figure, destination: Path, *, dpi: int) -> None:
    figure.savefig(destination, dpi=dpi, format="png", facecolor=figure.get_facecolor())
    plt.close(figure)


def export_result_bundle(
    destination: Path,
    model: ReportViewModel,
    *,
    subject_level_results: pd.DataFrame | None = None,
    statistical_results: pd.DataFrame | None = None,
    exclusions_and_warnings: pd.DataFrame | None = None,
    renderer: ReportDashboardRenderer | None = None,
) -> Path:
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"Export destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    renderer = renderer or ReportDashboardRenderer(dpi=300)
    subject_rows = subject_level_results if subject_level_results is not None else pd.DataFrame()
    statistic_rows = statistical_results if statistical_results is not None else pd.DataFrame()
    exclusion_rows = (
        exclusions_and_warnings if exclusions_and_warnings is not None else pd.DataFrame()
    )
    try:
        figures = temporary / "figures"
        figures.mkdir()
        subject_rows.to_excel(temporary / "subject_level_results.xlsx", index=False)
        statistic_rows.to_csv(temporary / "statistical_results.csv", index=False, na_rep="NA")
        exclusion_rows.to_csv(temporary / "exclusions_and_warnings.csv", index=False, na_rep="NA")
        config = {
            "analysis_config": model.analysis_config,
            "quality_summary": list(model.quality_summary),
            "provenance": _source_provenance(model),
        }
        (temporary / "analysis_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, default=_json_value),
            encoding="utf-8",
        )

        pages = {"overview": renderer.render_overview(model)}
        if model.laterality is not None:
            pages["laterality"] = renderer.render_laterality(model)
        if model.prepost_result is not None:
            pages["prepost"] = renderer.render_prepost(model)
        if model.regional_result is not None:
            pages["regional"] = renderer.render_regional(model)
        for name, figure in pages.items():
            _write_figure(figure, figures / f"{name}.png", dpi=300)
        temporary.rename(destination)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return destination
