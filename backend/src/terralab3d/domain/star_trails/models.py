"""Models de domini tipats per a la capacitat traces circumpolars."""

import math
from dataclasses import dataclass
from datetime import datetime

from terralab3d.domain.identifiers import ResourceId


@dataclass(frozen=True, slots=True)
class StarTrailPlaybackConfig:
    """Validated controls for one GPU-resident trail session."""

    duration_seconds: float
    sample_interval_seconds: float
    magnitude_limit: float
    playback_rate: float

    @classmethod
    def normalized(
        cls,
        *,
        duration_seconds: float,
        sample_interval_seconds: float,
        magnitude_limit: float,
        playback_rate: float,
    ) -> "StarTrailPlaybackConfig":
        return cls(
            duration_seconds=max(1.0, _finite_or(duration_seconds, 86_400.0)),
            sample_interval_seconds=max(
                1.0, _finite_or(sample_interval_seconds, 60.0)
            ),
            magnitude_limit=_finite_or(magnitude_limit, 6.0),
            playback_rate=max(0.01, _finite_or(playback_rate, 1.0)),
        )


def clamped_exposure_seconds(
    start_utc: datetime,
    current_utc: datetime,
    duration_seconds: float,
) -> float:
    """Return deterministic session exposure inside [0, duration]."""

    return min(
        max(0.0, (current_utc - start_utc).total_seconds()),
        max(0.0, duration_seconds),
    )


@dataclass(frozen=True, slots=True)
class StarTrailRequest:
    start_utc: datetime
    end_utc: datetime
    sample_count: int
    magnitude_limit: float

@dataclass(frozen=True, slots=True)
class StarTrailGeometry:
    resource_id: ResourceId
    version: int
    segment_count: int


def _finite_or(value: float, fallback: float) -> float:
    return float(value) if math.isfinite(float(value)) else fallback
