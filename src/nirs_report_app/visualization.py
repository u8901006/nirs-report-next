from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .report_models import ReportViewModel, RoiSummary

HBO_COLOR = "#D6455D"
HBR_COLOR = "#148FBD"
TASK_COLOR = "#E8EEF5"
PAGE_WIDTH_INCHES = 3508 / 300
PAGE_HEIGHT_INCHES = 2480 / 300


def _configure_report_font() -> None:
    for font_path in (
        Path("C:/Windows/Fonts/msjh.ttc"),
        Path("C:/Windows/Fonts/mingliu.ttc"),
    ):
        if font_path.is_file():
            font_manager.fontManager.addfont(str(font_path))
            family = font_manager.FontProperties(fname=str(font_path)).get_name()
            matplotlib.rcParams["font.family"] = [family, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return


_configure_report_font()


@dataclass(frozen=True, slots=True)
class ReportDashboardRenderer:
    width_inches: float = PAGE_WIDTH_INCHES
    height_inches: float = PAGE_HEIGHT_INCHES
    dpi: int = 300

    def _figure(
        self,
        *,
        width_inches: float | None = None,
        height_inches: float | None = None,
        dpi: int | None = None,
    ) -> Figure:
        return plt.figure(
            figsize=(width_inches or self.width_inches, height_inches or self.height_inches),
            dpi=dpi or self.dpi,
            facecolor="#F4F6F8",
        )

    @staticmethod
    def _style_axis(axis: Axes) -> None:
        axis.set_facecolor("white")
        axis.grid(axis="y", color="#E4E8ED", linewidth=0.5)
        for spine in axis.spines.values():
            spine.set_color("#C7CDD4")
            spine.set_linewidth(0.7)
        axis.tick_params(labelsize=6, colors="#4B5563", length=2)

    @staticmethod
    def _plot_signals(axis: Axes, time: np.ndarray, hbo: np.ndarray, hbr: np.ndarray) -> None:
        axis.plot(time, hbo, color=HBO_COLOR, linewidth=0.9, label="HbO")
        axis.plot(time, hbr, color=HBR_COLOR, linewidth=0.8, label="HbR")
        axis.axhline(0.0, color="#8B949E", linestyle=":", linewidth=0.55)

    def _channel_axis(
        self,
        figure: Figure,
        bounds: tuple[float, float, float, float],
        model: ReportViewModel,
        channel_number: int,
        y_limits: tuple[float, float] | None,
    ) -> Axes:
        axis = figure.add_axes(bounds, label=f"channel:{channel_number}")
        self._style_axis(axis)
        channel = model.channel_series.get(channel_number)
        if channel is None or channel.state in {"missing", "invalid"}:
            axis.set_facecolor(
                "#EEF0F2" if channel is None or channel.state == "missing" else "#FCE8E8"
            )
            label = (
                f"缺少 CH{channel_number:02d}"
                if channel is None or channel.state == "missing"
                else f"無效 CH{channel_number:02d}"
            )
            axis.text(
                0.5,
                0.5,
                label,
                ha="center",
                va="center",
                transform=axis.transAxes,
                fontsize=7,
                color="#68717A",
            )
            axis.set_xticks([])
            axis.set_yticks([])
            return axis
        self._plot_signals(axis, model.time_seconds, channel.hbo, channel.hbr)
        if y_limits is not None:
            axis.set_ylim(*y_limits)
        axis.set_title(f"CH{channel_number:02d}", loc="left", fontsize=7, pad=1, color="#253247")
        if channel.state == "partial":
            for spine in axis.spines.values():
                spine.set_color("#D28A18")
                spine.set_linewidth(1.2)
        return axis

    @staticmethod
    def _shared_limits(model: ReportViewModel) -> tuple[float, float]:
        finite_values: list[np.ndarray] = []
        for channel in model.channel_series.values():
            if channel.state in {"valid", "partial", "excluded_by_user"}:
                finite_values.extend(
                    (channel.hbo[np.isfinite(channel.hbo)], channel.hbr[np.isfinite(channel.hbr)])
                )
        finite_values = [values for values in finite_values if values.size]
        if not finite_values:
            return (-1.0, 1.0)
        values = np.concatenate(finite_values)
        extent = max(abs(float(np.min(values))), abs(float(np.max(values))), 1e-9)
        return (-1.08 * extent, 1.08 * extent)

    @staticmethod
    def _grid_positions(
        x: float,
        y: float,
        width: float,
        height: float,
        rows: tuple[tuple[int, ...], ...],
    ) -> dict[int, tuple[float, float, float, float]]:
        gap_x = 0.008
        gap_y = 0.018
        row_height = (height - gap_y * (len(rows) - 1)) / len(rows)
        positions: dict[int, tuple[float, float, float, float]] = {}
        maximum_columns = max(len(row) for row in rows)
        column_width = (width - gap_x * (maximum_columns - 1)) / maximum_columns
        for row_index, row in enumerate(rows):
            row_y = y + (len(rows) - row_index - 1) * (row_height + gap_y)
            for column_index, channel in enumerate(row):
                positions[channel] = (
                    x + column_index * (column_width + gap_x),
                    row_y,
                    column_width,
                    row_height,
                )
        return positions

    def _roi_axis(
        self,
        figure: Figure,
        bounds: tuple[float, float, float, float],
        model: ReportViewModel,
        summary: RoiSummary,
    ) -> Axes:
        axis = figure.add_axes(bounds, label=f"roi:{summary.roi_id}")
        self._style_axis(axis)
        axis.set_title(
            summary.display_name, loc="left", fontsize=9, fontweight="bold", color="#253247"
        )
        self._plot_signals(axis, model.time_seconds, summary.hbo, summary.hbr)
        integral = "NA" if summary.integral is None else f"{summary.integral:.2f}"
        centroid = "NA" if summary.centroid is None else f"{summary.centroid:.2f} s"
        slope = "NA" if summary.slope is None else f"{summary.slope:.4f}"
        axis.text(
            0.01,
            -0.27,
            f"Integral {integral}   Centroid {centroid}   Slope {slope}   有效 {summary.valid_channels}/{summary.expected_channels} 通道",
            transform=axis.transAxes,
            fontsize=7,
            color="#374151",
        )
        if summary.warnings:
            axis.text(
                0.99,
                1.02,
                " · ".join(summary.warnings),
                transform=axis.transAxes,
                ha="right",
                fontsize=6,
                color="#A15C00",
            )
        return axis

    def render_overview(
        self,
        model: ReportViewModel,
        *,
        width_inches: float | None = None,
        height_inches: float | None = None,
        dpi: int | None = None,
    ) -> Figure:
        figure = self._figure(width_inches=width_inches, height_inches=height_inches, dpi=dpi)
        figure.text(0.04, 0.955, model.title, fontsize=15, fontweight="bold", color="#17243A")
        figure.text(
            0.04, 0.925, "研究用 fNIRS 血行動力分析｜非臨床診斷工具", fontsize=7, color="#667085"
        )
        figure.text(
            0.17,
            0.885,
            "右前額葉 Right PFC",
            ha="center",
            fontsize=9,
            fontweight="bold",
            color="#253247",
        )
        figure.text(
            0.505,
            0.885,
            "前額中區 Anterior Frontal",
            ha="center",
            fontsize=9,
            fontweight="bold",
            color="#253247",
        )
        figure.text(
            0.84,
            0.885,
            "左前額葉 Left PFC",
            ha="center",
            fontsize=9,
            fontweight="bold",
            color="#253247",
        )

        layouts = (
            self._grid_positions(0.05, 0.54, 0.24, 0.31, ((1, 2), (3, 4))),
            self._grid_positions(0.31, 0.54, 0.39, 0.31, ((5, 6, 7, 8), (9, 10, 11))),
            self._grid_positions(0.72, 0.54, 0.24, 0.31, ((12, 13), (14, 15))),
        )
        y_limits = self._shared_limits(model)
        for layout in layouts:
            for channel, bounds in layout.items():
                self._channel_axis(figure, bounds, model, channel, y_limits)

        summaries = {summary.roi_id: summary for summary in model.roi_summaries}
        for roi_id, bounds in (
            ("anterior_frontal", (0.06, 0.30, 0.47, 0.17)),
            ("lateral_frontal", (0.06, 0.075, 0.47, 0.17)),
        ):
            summary = summaries.get(roi_id)
            if summary is not None:
                self._roi_axis(figure, bounds, model, summary)

        plot_axis = figure.add_axes((0.59, 0.105, 0.35, 0.35), label="plot-map")
        self._style_axis(plot_axis)
        plot_axis.set_title(
            "Integral–Centroid Plot Map", loc="left", fontsize=10, fontweight="bold"
        )
        plot_axis.set_xlabel("Integral", fontsize=8)
        plot_axis.set_ylabel("Centroid (s)", fontsize=8)
        markers = (("anterior_frontal", "s", "#3977B8"), ("lateral_frontal", "o", "#E06A45"))
        for roi_id, marker, color in markers:
            point = next((item for item in model.plot_points if item.roi_id == roi_id), None)
            if point is not None:
                plot_axis.scatter(
                    point.integral, point.centroid, marker=marker, color=color, s=42, label=roi_id
                )
                plot_axis.annotate(
                    roi_id.replace("_", " "),
                    (point.integral, point.centroid),
                    xytext=(5, 4),
                    textcoords="offset points",
                    fontsize=7,
                )
        plot_axis.axvline(0.0, color="#AAB1B9", linewidth=0.5)
        plot_axis.axhline(0.0, color="#AAB1B9", linewidth=0.5)
        plot_axis.set_ylim(bottom=0.0)
        figure.text(
            0.59,
            0.06,
            "Integral–Centroid Plot Map 僅為血行動力反應摘要，不構成臨床診斷或療效判定。",
            fontsize=6.5,
            color="#667085",
        )
        return figure

    def _advanced_figure(self, title: str, **dimensions: float | None) -> Figure:
        figure = self._figure(**dimensions)
        figure.text(0.06, 0.93, title, fontsize=16, fontweight="bold", color="#17243A")
        figure.text(
            0.06, 0.89, "研究用結果｜估計值、樣本數與警告須合併解讀", fontsize=8, color="#667085"
        )
        return figure

    def render_laterality(
        self,
        model: ReportViewModel,
        *,
        width_inches: float | None = None,
        height_inches: float | None = None,
        dpi: int | None = None,
    ) -> Figure:
        figure = self._advanced_figure(
            "側化指標 Laterality Index",
            width_inches=width_inches,
            height_inches=height_inches,
            dpi=dpi,
        )
        result = model.laterality
        if result is None:
            figure.text(0.06, 0.72, "尚未執行 LI 分析", fontsize=14, color="#667085")
            return figure
        value = "無法計算" if result.value is None else f"LI = {result.value:.3f}"
        figure.text(0.08, 0.72, f"L = {result.left:.3f}", fontsize=15)
        figure.text(0.35, 0.72, f"R = {result.right:.3f}", fontsize=15)
        figure.text(0.62, 0.72, value, fontsize=18, fontweight="bold", color="#244F76")
        direction = result.direction.value if result.direction is not None else "未分類"
        figure.text(0.62, 0.65, f"分類：{direction}｜切點 ±{result.threshold:.2f}", fontsize=10)
        if result.warnings:
            figure.text(
                0.08, 0.48, "警告：" + " · ".join(result.warnings), fontsize=11, color="#A15C00"
            )
        axis = figure.add_axes((0.15, 0.2, 0.7, 0.16), label="laterality-scale")
        axis.set_xlim(-1.0, 1.0)
        axis.set_yticks([])
        axis.axvspan(-result.threshold, result.threshold, color=TASK_COLOR)
        axis.axvline(0, color="#59636E", linewidth=0.8)
        if result.value is not None:
            axis.scatter([result.value], [0], color="#D6455D", s=70, zorder=3)
        axis.set_xlabel("Right dominant  ←  LI  →  Left dominant")
        return figure

    def render_prepost(
        self,
        model: ReportViewModel,
        *,
        width_inches: float | None = None,
        height_inches: float | None = None,
        dpi: int | None = None,
    ) -> Figure:
        figure = self._advanced_figure(
            "NIRS/fNIRS 前後測差異", width_inches=width_inches, height_inches=height_inches, dpi=dpi
        )
        result = model.prepost_result
        if result is None or result.pairs.empty:
            figure.text(0.06, 0.72, "沒有可用的前後測配對資料", fontsize=14, color="#667085")
            return figure
        deltas = result.pairs["delta"].to_numpy(float)
        figure.text(
            0.07, 0.80, f"平均差 = {float(np.mean(deltas)):.3f}", fontsize=17, fontweight="bold"
        )
        figure.text(0.07, 0.74, f"完整配對 {result.paired_n}/{result.total_subjects}", fontsize=10)
        axis = figure.add_axes((0.12, 0.18, 0.76, 0.46), label="prepost-pairs")
        for row in result.pairs.itertuples(index=False):
            axis.plot(
                [0, 1], [float(row.pre), float(row.post)], marker="o", alpha=0.65, color="#3977B8"
            )
        axis.set_xticks([0, 1], ["Pre", "Post"])
        axis.set_ylabel("Metric value")
        self._style_axis(axis)
        if result.exclusions:
            warnings = " · ".join(f"{item.subject_id}: {item.code}" for item in result.exclusions)
            figure.text(0.07, 0.08, "排除：" + warnings, fontsize=8, color="#A15C00")
        return figure

    def render_regional(
        self,
        model: ReportViewModel,
        *,
        width_inches: float | None = None,
        height_inches: float | None = None,
        dpi: int | None = None,
    ) -> Figure:
        figure = self._advanced_figure(
            "腦區活化差異", width_inches=width_inches, height_inches=height_inches, dpi=dpi
        )
        result = model.regional_result
        if result is None or not result.contrasts:
            figure.text(0.06, 0.72, "尚未執行腦區差異分析", fontsize=14, color="#667085")
            return figure
        axis = figure.add_axes((0.24, 0.18, 0.68, 0.58), label="regional-forest")
        labels: list[str] = []
        estimates: list[float] = []
        errors: list[list[float]] = []
        for index, contrast in enumerate(result.contrasts):
            estimate = contrast.result.estimate
            display = "無法計算" if estimate is None else f"{estimate:.3f}"
            figure.text(0.06, 0.76 - index * 0.06, f"{contrast.label} = {display}", fontsize=10)
            if estimate is not None:
                labels.append(contrast.label)
                estimates.append(estimate)
                ci = contrast.result.confidence_interval
                errors.append([0.0, 0.0] if ci is None else [estimate - ci[0], ci[1] - estimate])
            if contrast.result.warnings:
                figure.text(
                    0.06,
                    0.73 - index * 0.06,
                    " · ".join(contrast.result.warnings),
                    fontsize=7,
                    color="#A15C00",
                )
        if estimates:
            y = np.arange(len(estimates))
            asymmetric = np.asarray(errors).T
            axis.errorbar(estimates, y, xerr=asymmetric, fmt="o", color="#3977B8", capsize=3)
            axis.set_yticks(y, labels)
        axis.axvline(0.0, color="#59636E", linewidth=0.8)
        axis.set_xlabel(f"Estimate (multiplicity correction: {result.correction})")
        self._style_axis(axis)
        return figure


def render_overview(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_overview(model, **kwargs)


def render_laterality(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_laterality(model, **kwargs)


def render_prepost(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_prepost(model, **kwargs)


def render_regional(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_regional(model, **kwargs)
