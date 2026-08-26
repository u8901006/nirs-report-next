from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import (
    ChannelAssessment,
    ChannelState,
    QualityStatus,
    RoiDefinition,
    RoiSignal,
)


def assess_channel(frame: pd.DataFrame, channel: int) -> ChannelAssessment:
    column = f"ch{channel}"
    if column not in frame.columns:
        return ChannelAssessment(channel, ChannelState.MISSING, 0.0)
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(values)
    fraction = float(valid.mean()) if values.size else 0.0
    if fraction == 0:
        state = ChannelState.INVALID
    elif fraction < 1:
        state = ChannelState.PARTIAL
    else:
        state = ChannelState.VALID
    return ChannelAssessment(channel, state, fraction)


def aggregate_roi(
    frame: pd.DataFrame,
    definition: RoiDefinition,
    *,
    excluded_channels: tuple[int, ...] = (),
    minimum_fraction: float = 0.5,
) -> RoiSignal:
    excluded = tuple(channel for channel in definition.channels if channel in excluded_channels)
    active = tuple(channel for channel in definition.channels if channel not in excluded_channels)
    assessments = tuple(assess_channel(frame, channel) for channel in active)
    missing = tuple(item.channel for item in assessments if item.state is ChannelState.MISSING)
    invalid = tuple(item.channel for item in assessments if item.state is ChannelState.INVALID)
    partial = tuple(item.channel for item in assessments if item.state is ChannelState.PARTIAL)
    usable = tuple(
        item.channel
        for item in assessments
        if item.state in (ChannelState.VALID, ChannelState.PARTIAL)
    )

    warnings: list[str] = []
    if missing:
        warnings.append("W_CHANNEL_MISSING")
    if partial:
        warnings.append("W_CHANNEL_PARTIAL")
    if invalid:
        warnings.append("W_CHANNEL_INVALID")

    if not usable:
        warnings.append("E_ROI_EMPTY")
        return RoiSignal(
            definition,
            np.full(len(frame), np.nan, dtype=float),
            QualityStatus.INVALID,
            (),
            partial,
            missing,
            invalid,
            excluded,
            tuple(warnings),
        )

    stack = np.vstack(
        [pd.to_numeric(frame[f"ch{channel}"], errors="coerce").to_numpy(float) for channel in usable]
    )
    finite = np.isfinite(stack)
    required = max(1, math.ceil(len(active) * minimum_fraction))
    counts = finite.sum(axis=0)
    sums = np.where(finite, stack, 0.0).sum(axis=0)
    values = np.divide(
        sums,
        counts,
        out=np.full(len(frame), np.nan, dtype=float),
        where=counts >= required,
    )
    degraded = bool(missing or invalid or partial or excluded or np.isnan(values).any())
    if degraded:
        warnings.append("W_ROI_DEGRADED")
    return RoiSignal(
        definition,
        values,
        QualityStatus.DEGRADED if degraded else QualityStatus.COMPLETE,
        usable,
        partial,
        missing,
        invalid,
        excluded,
        tuple(dict.fromkeys(warnings)),
    )
