from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class ChannelState(str, Enum):
    VALID = "valid"
    PARTIAL = "partial"
    MISSING = "missing"
    INVALID = "invalid"
    EXCLUDED_BY_USER = "excluded_by_user"


class QualityStatus(str, Enum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class RoiDefinition:
    id: str
    name: str
    channels: tuple[int, ...]
    hemisphere: str = "unspecified"


@dataclass(frozen=True, slots=True)
class ChannelAssessment:
    channel: int
    state: ChannelState
    valid_fraction: float


@dataclass(frozen=True, slots=True)
class RoiSignal:
    definition: RoiDefinition
    values: np.ndarray
    status: QualityStatus
    valid_channels: tuple[int, ...]
    partial_channels: tuple[int, ...]
    missing_channels: tuple[int, ...]
    invalid_channels: tuple[int, ...]
    excluded_channels: tuple[int, ...]
    warnings: tuple[str, ...]

    @property
    def expected_channel_count(self) -> int:
        return len(self.definition.channels)

    @property
    def valid_channel_count(self) -> int:
        return len(self.valid_channels)


BUILTIN_ROIS = {
    "right_pfc": RoiDefinition("right_pfc", "Right Prefrontal Lobe", (1, 2, 3, 4), "right"),
    "anterior_frontal": RoiDefinition(
        "anterior_frontal", "Anterior Frontal Lobe", (5, 6, 7, 8, 9, 10, 11), "midline"
    ),
    "left_pfc": RoiDefinition("left_pfc", "Left Prefrontal Lobe", (12, 13, 14, 15), "left"),
    "lateral_frontal": RoiDefinition(
        "lateral_frontal", "Lateral Frontal Lobe", (1, 2, 3, 4, 12, 13, 14, 15), "bilateral"
    ),
}
