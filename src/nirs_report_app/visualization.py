from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .messages import DIRECTION_TEXT, ROI_TEXT, describe_warning, describe_warnings
from .report_models import PlotPoint, ReportViewModel, RoiSummary

HBO_COLOR = "#D6455D"
HBR_COLOR = "#148FBD"
TASK_COLOR = "#DCE8F3"
INK = "#17243A"
MUTED = "#566275"
WARNING_COLOR = "#A15C00"
PAGE_WIDTH_INCHES = 3508 / 300
PAGE_HEIGHT_INCHES = 2480 / 300
# Share of the overview page taken by its own title block; reclaimed when the title is hidden.
_HEADER_SHARE = 0.085

_MONTAGE = (
    ("右前額葉 Right PFC", 0.055, 0.23, ((1, 2), (3, 4))),
    ("前額中區 Anterior Frontal", 0.325, 0.37, ((5, 6, 7, 8), (9, 10, 11))),
    ("左前額葉 Left PFC", 0.735, 0.23, ((12, 13), (14, 15))),
)


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


def _task_window(model: ReportViewModel) -> tuple[float, float] | None:
    """Task start and end in seconds, when the analysis recorded them."""
    try:
        start = float(model.analysis_config["task_start"])
        end = float(model.analysis_config["task_end"])
    except (KeyError, TypeError, ValueError):
        return None
    return (start, end) if end > start else None


@dataclass(frozen=True, slots=True)
class ReportDashboardRenderer:
    width_inches: float = PAGE_WIDTH_INCHES
    height_inches: float = PAGE_HEIGHT_INCHES
    dpi: int = 300
    # The overview carries its own title for stand-alone image exports. Inside the window
    # and the Word report the surrounding page already names it, so they switch it off.
    show_title: bool = True

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
            facecolor="white",
        )

    @staticmethod
    def _style_axis(axis: Axes) -> None:
        axis.set_facecolor("white")
        axis.grid(axis="y", color="#E4E8ED", linewidth=0.5)
        axis.set_axisbelow(True)
        for spine in axis.spines.values():
            spine.set_color("#C7CDD4")
            spine.set_linewidth(0.7)
        axis.tick_params(labelsize=7, colors=MUTED, length=2)

    @staticmethod
    def _shade_task(axis: Axes, task: tuple[float, float] | None) -> None:
        if task is not None:
            axis.axvspan(task[0], task[1], color=TASK_COLOR, linewidth=0, zorder=0)

    @staticmethod
    def _plot_signals(
        axis: Axes, time: np.ndarray, hbo: np.ndarray, hbr: np.ndarray, *, weight: float = 1.0
    ) -> None:
        axis.plot(time, hbo, color=HBO_COLOR, linewidth=0.9 * weight, label="HbO")
        axis.plot(time, hbr, color=HBR_COLOR, linewidth=0.8 * weight, label="HbR")
        axis.axhline(0.0, color="#8B949E", linestyle=":", linewidth=0.55)

    def _channel_axis(
        self,
        figure: Figure,
        bounds: tuple[float, float, float, float],
        model: ReportViewModel,
        channel_number: int,
        y_limits: tuple[float, float] | None,
        *,
        show_x_labels: bool,
        show_y_labels: bool,
    ) -> Axes:
        axis = figure.add_axes(bounds, label=f"channel:{channel_number}")
        self._style_axis(axis)
        channel = model.channel_series.get(channel_number)
        if channel is None or channel.state in {"missing", "invalid"}:
            missing = channel is None or channel.state == "missing"
            axis.set_facecolor("#EEF0F2" if missing else "#FCE8E8")
            axis.text(
                0.5,
                0.5,
                f"{'缺少' if missing else '無效'} CH{channel_number:02d}",
                ha="center",
                va="center",
                transform=axis.transAxes,
                fontsize=8,
                color="#68717A",
            )
            axis.set_xticks([])
            axis.set_yticks([])
            return axis
        self._shade_task(axis, _task_window(model))
        self._plot_signals(axis, model.time_seconds, channel.hbo, channel.hbr)
        if y_limits is not None:
            axis.set_ylim(*y_limits)
        axis.margins(x=0)
        axis.tick_params(labelbottom=show_x_labels, labelleft=show_y_labels)
        excluded = channel.state == "excluded_by_user"
        axis.text(
            0.04,
            0.93,
            f"CH{channel_number:02d}" + ("　已排除" if excluded else ""),
            transform=axis.transAxes,
            va="top",
            fontsize=7.5,
            fontweight="bold",
            color=MUTED if excluded else INK,
        )
        if excluded:
            axis.set_facecolor("#F4F5F7")
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
        gap_x = 0.006
        gap_y = 0.012
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
        *,
        show_x_label: bool,
    ) -> Axes:
        axis = figure.add_axes(bounds, label=f"roi:{summary.roi_id}")
        self._style_axis(axis)
        axis.tick_params(labelsize=7.5)
        axis.set_title(
            ROI_TEXT.get(summary.roi_id, summary.display_name),
            loc="left",
            fontsize=10,
            fontweight="bold",
            color=INK,
            pad=5,
        )
        task = _task_window(model)
        self._shade_task(axis, task)
        self._plot_signals(axis, model.time_seconds, summary.hbo, summary.hbr, weight=1.5)
        axis.margins(x=0)
        if summary.centroid is not None:
            axis.plot(
                [summary.centroid],
                [1.0],
                marker="v",
                markersize=6,
                color=INK,
                linestyle="none",
                transform=axis.get_xaxis_transform(),
                clip_on=False,
                zorder=5,
            )
            axis.axvline(summary.centroid, color=INK, linewidth=0.6, linestyle=(0, (2, 2)))
        integral = "—" if summary.integral is None else f"{summary.integral:.2f}"
        centroid = "—" if summary.centroid is None else f"{summary.centroid:.1f} 秒"
        slope = "—" if summary.slope is None else f"{summary.slope:.4f}"
        axis.text(
            1.0,
            1.045,
            f"積分 {integral}　▼重心 {centroid}　斜率 {slope}　"
            f"有效 {summary.valid_channels}/{summary.expected_channels} 通道",
            transform=axis.transAxes,
            ha="right",
            fontsize=8,
            color=INK,
        )
        if summary.warnings:
            axis.text(
                0.99,
                0.94,
                describe_warnings(summary.warnings),
                transform=axis.transAxes,
                ha="right",
                va="top",
                fontsize=7.5,
                color=WARNING_COLOR,
            )
        axis.set_ylabel("ΔHb", fontsize=8, color=MUTED)
        if show_x_label:
            axis.set_xlabel("時間（秒）", fontsize=8, color=MUTED)
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
        # Positions below are laid out for a page with a title block. Without the title the
        # same layout is stretched upward to use the freed strip.
        stretch = 1.0 if self.show_title else 1.0 / (1.0 - _HEADER_SHARE)

        def place(x: float, y: float, width: float, height: float):
            return (x, y * stretch, width, height * stretch)

        if self.show_title:
            figure.text(0.04, 0.955, model.title, fontsize=15, fontweight="bold", color=INK)
            figure.text(
                0.04, 0.925, "研究用 fNIRS 血行動力分析｜非臨床診斷工具", fontsize=8, color=MUTED
            )

        y_limits = self._shared_limits(model)
        for title, x, width, rows in _MONTAGE:
            figure.text(
                x + width / 2,
                0.878 * stretch,
                title,
                ha="center",
                fontsize=9.5,
                fontweight="bold",
                color=INK,
            )
            positions = self._grid_positions(x, 0.56, width, 0.30, rows)
            for row_index, row in enumerate(rows):
                below = rows[row_index + 1] if row_index + 1 < len(rows) else ()
                for column_index, channel in enumerate(row):
                    self._channel_axis(
                        figure,
                        place(*positions[channel]),
                        model,
                        channel,
                        y_limits,
                        show_x_labels=column_index >= len(below),
                        show_y_labels=column_index == 0,
                    )

        # The key sits in the empty slot beside CH11, so it never covers a trace.
        key = [
            Line2D([], [], color=HBO_COLOR, linewidth=1.6, label="HbO 含氧血紅素"),
            Line2D([], [], color=HBR_COLOR, linewidth=1.6, label="HbR 去氧血紅素"),
        ]
        if _task_window(model) is not None:
            key.append(Patch(facecolor=TASK_COLOR, label="作業區間"))
        figure.legend(
            handles=key,
            loc="center",
            bbox_to_anchor=(0.65, 0.632 * stretch),
            fontsize=7.5,
            frameon=False,
            handlelength=1.4,
            labelcolor=INK,
        )

        summaries = {summary.roi_id: summary for summary in model.roi_summaries}
        for roi_id, bounds, bottom in (
            ("anterior_frontal", (0.065, 0.315, 0.46, 0.15), False),
            ("lateral_frontal", (0.065, 0.085, 0.46, 0.15), True),
        ):
            summary = summaries.get(roi_id)
            if summary is not None:
                self._roi_axis(figure, place(*bounds), model, summary, show_x_label=bottom)

        plot_axis = figure.add_axes(place(0.61, 0.115, 0.345, 0.335), label="plot-map")
        self._style_axis(plot_axis)
        plot_axis.tick_params(labelsize=7.5)
        plot_axis.set_title(
            "積分值與重心時間 Integral–Centroid Plot Map",
            loc="left",
            fontsize=10,
            fontweight="bold",
            color=INK,
            pad=5,
        )
        plot_axis.set_xlabel("積分值 Integral", fontsize=8, color=MUTED)
        plot_axis.set_ylabel("重心時間 Centroid（秒）", fontsize=8, color=MUTED)
        markers = (("anterior_frontal", "s", "#3977B8"), ("lateral_frontal", "o", "#E06A45"))
        labelled: list[tuple[PlotPoint, str]] = []
        for roi_id, marker, color in markers:
            point = next((item for item in model.plot_points if item.roi_id == roi_id), None)
            if point is not None:
                plot_axis.scatter(
                    point.integral, point.centroid, marker=marker, color=color, s=46, label=roi_id
                )
                summary = summaries.get(roi_id)
                labelled.append(
                    (point, ROI_TEXT.get(roi_id, summary.display_name if summary else roi_id))
                )
        plot_axis.axvline(0.0, color="#AAB1B9", linewidth=0.5)
        plot_axis.axhline(0.0, color="#AAB1B9", linewidth=0.5)
        plot_axis.margins(x=0.25, y=0.2)
        plot_axis.set_ylim(bottom=0.0)
        # Label on whichever side has room, so a point near the right edge is not cut off.
        left, right = plot_axis.get_xlim()
        for point, text in labelled:
            on_right_half = point.integral > (left + right) / 2
            plot_axis.annotate(
                text,
                (point.integral, point.centroid),
                xytext=(-8 if on_right_half else 8, 6),
                textcoords="offset points",
                ha="right" if on_right_half else "left",
                fontsize=8,
                color=INK,
            )
        figure.text(
            0.61,
            0.022 * stretch,
            "此圖僅為血行動力反應摘要，不構成臨床診斷或療效判定。",
            fontsize=7.5,
            color=MUTED,
        )
        return figure

    def _advanced_figure(self, title: str, **dimensions: float | None) -> Figure:
        figure = self._figure(**dimensions)
        figure.text(0.06, 0.93, title, fontsize=16, fontweight="bold", color=INK)
        figure.text(
            0.06, 0.89, "研究用結果｜估計值、樣本數與警告須合併解讀", fontsize=9, color=MUTED
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
            figure.text(0.06, 0.72, "尚未執行 LI 分析", fontsize=14, color=MUTED)
            return figure
        value = "無法計算" if result.value is None else f"LI = {result.value:.3f}"
        figure.text(0.08, 0.76, "左前額葉", fontsize=10, color=MUTED)
        figure.text(0.08, 0.70, f"L = {result.left:.3f}", fontsize=17, color=INK)
        figure.text(0.33, 0.76, "右前額葉", fontsize=10, color=MUTED)
        figure.text(0.33, 0.70, f"R = {result.right:.3f}", fontsize=17, color=INK)
        figure.text(0.60, 0.76, "側化指標", fontsize=10, color=MUTED)
        figure.text(0.60, 0.70, value, fontsize=20, fontweight="bold", color="#244F76")
        direction = (
            DIRECTION_TEXT.get(result.direction.value, result.direction.value)
            if result.direction is not None
            else "未分類"
        )
        figure.text(
            0.60,
            0.64,
            f"分類：{direction}｜切點 ±{result.threshold:.2f}",
            fontsize=11,
            color=INK,
        )
        if result.warnings:
            figure.text(
                0.08,
                0.52,
                "警告：" + describe_warnings(result.warnings),
                fontsize=11,
                color=WARNING_COLOR,
            )
        axis = figure.add_axes((0.12, 0.24, 0.76, 0.14), label="laterality-scale")
        axis.set_xlim(-1.0, 1.0)
        axis.set_ylim(-1.0, 1.0)
        axis.set_yticks([])
        for side in ("left", "right", "top"):
            axis.spines[side].set_visible(False)
        axis.spines["bottom"].set_color("#C7CDD4")
        axis.tick_params(labelsize=9, colors=MUTED)
        axis.axvspan(-result.threshold, result.threshold, color=TASK_COLOR, linewidth=0)
        axis.axvline(0, color="#59636E", linewidth=0.8)
        axis.text(0.0, 1.15, "雙側均衡", ha="center", fontsize=9, color=MUTED)
        if result.value is not None:
            axis.scatter([result.value], [0], color=HBO_COLOR, s=110, zorder=3)
        axis.set_xlabel("右側優勢　←　LI　→　左側優勢", fontsize=10, color=INK)
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
            figure.text(0.06, 0.72, "沒有可用的前後測配對資料", fontsize=14, color=MUTED)
            return figure
        deltas = result.pairs["delta"].to_numpy(float)
        figure.text(
            0.07,
            0.80,
            f"平均差 = {float(np.mean(deltas)):.3f}",
            fontsize=17,
            fontweight="bold",
            color=INK,
        )
        figure.text(
            0.07,
            0.74,
            f"完整配對 {result.paired_n}/{result.total_subjects}",
            fontsize=11,
            color=MUTED,
        )
        axis = figure.add_axes((0.12, 0.2, 0.76, 0.46), label="prepost-pairs")
        for row in result.pairs.itertuples(index=False):
            axis.plot(
                [0, 1], [float(row.pre), float(row.post)], marker="o", alpha=0.65, color="#3977B8"
            )
        axis.set_xlim(-0.25, 1.25)
        axis.set_xticks([0, 1], ["前測 Pre", "後測 Post"])
        axis.set_ylabel("指標數值", fontsize=10, color=MUTED)
        self._style_axis(axis)
        axis.tick_params(labelsize=10)
        if result.exclusions:
            warnings = "；".join(
                f"{item.subject_id}：{describe_warning(item.code)}" for item in result.exclusions
            )
            figure.text(0.07, 0.08, "排除：" + warnings, fontsize=9, color=WARNING_COLOR)
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
            figure.text(0.06, 0.72, "尚未執行腦區差異分析", fontsize=14, color=MUTED)
            return figure
        axis = figure.add_axes((0.38, 0.2, 0.54, 0.56), label="regional-forest")
        labels: list[str] = []
        estimates: list[float] = []
        errors: list[list[float]] = []
        for index, contrast in enumerate(result.contrasts):
            estimate = contrast.result.estimate
            display = "無法計算" if estimate is None else f"{estimate:.3f}"
            figure.text(
                0.06, 0.76 - index * 0.07, f"{contrast.label} = {display}", fontsize=11, color=INK
            )
            if estimate is not None:
                labels.append(contrast.label)
                estimates.append(estimate)
                ci = contrast.result.confidence_interval
                errors.append([0.0, 0.0] if ci is None else [estimate - ci[0], ci[1] - estimate])
            if contrast.result.warnings:
                figure.text(
                    0.06,
                    0.73 - index * 0.07,
                    describe_warnings(contrast.result.warnings),
                    fontsize=8,
                    color=WARNING_COLOR,
                )
        if estimates:
            y = np.arange(len(estimates))
            asymmetric = np.asarray(errors).T
            axis.errorbar(estimates, y, xerr=asymmetric, fmt="o", color="#3977B8", capsize=3)
            axis.set_yticks(y, labels)
            axis.set_ylim(-0.6, len(estimates) - 0.4)
        axis.axvline(0.0, color="#59636E", linewidth=0.8)
        axis.set_xlabel(f"估計值與信賴區間（多重比較校正：{result.correction}）", fontsize=10)
        self._style_axis(axis)
        axis.tick_params(labelsize=9)
        return figure


def render_overview(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_overview(model, **kwargs)


def render_laterality(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_laterality(model, **kwargs)


def render_prepost(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_prepost(model, **kwargs)


def render_regional(model: ReportViewModel, **kwargs: float | None) -> Figure:
    return ReportDashboardRenderer().render_regional(model, **kwargs)
