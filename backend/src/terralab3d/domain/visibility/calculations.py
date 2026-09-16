"""Pure classification and segmentation for local-horizon trajectories."""

from __future__ import annotations

from collections.abc import Sequence

from terralab3d.domain.visibility.models import (
    HorizonProvenance,
    ObservableFamily,
    TrajectorySample,
    TrajectorySegment,
    TrajectoryVisibilityState,
    VisibilityIntervalClassification,
)

SIDEREAL_DAY_SECONDS = 86_164.0905


def classify_visibility(
    altitude_deg: float,
    horizon_elevation_deg: float,
    provenance: HorizonProvenance,
    *,
    valid: bool,
) -> TrajectoryVisibilityState:
    if not valid or provenance is HorizonProvenance.INSUFFICIENT:
        return TrajectoryVisibilityState.INSUFFICIENT_DATA
    if (
        provenance is HorizonProvenance.REAL
        and horizon_elevation_deg > 0.0
        and altitude_deg < horizon_elevation_deg
    ):
        return TrajectoryVisibilityState.TERRAIN_OCCLUDED
    if altitude_deg < 0.0:
        return TrajectoryVisibilityState.BELOW_ASTRONOMICAL_HORIZON
    return TrajectoryVisibilityState.VISIBLE


def build_segments(samples: Sequence[TrajectorySample]) -> tuple[TrajectorySegment, ...]:
    if not samples:
        return ()
    segments: list[TrajectorySegment] = []
    start = 0
    state = samples[0].visibility
    provenance = samples[0].horizon_provenance
    for index in range(1, len(samples)):
        sample = samples[index]
        if sample.visibility is state and sample.horizon_provenance is provenance:
            continue
        # The transition sample belongs to both adjacent segments. It is the
        # shared refined vertex and prevents cracks in the rendered path.
        segments.append(TrajectorySegment(start, index, state, provenance))
        start = index
        state = sample.visibility
        provenance = sample.horizon_provenance
    segments.append(TrajectorySegment(start, len(samples) - 1, state, provenance))
    return tuple(segments)


def interval_classification(
    samples: Sequence[TrajectorySample],
) -> VisibilityIntervalClassification:
    if not samples or any(
        sample.visibility is TrajectoryVisibilityState.INSUFFICIENT_DATA
        for sample in samples
    ):
        return VisibilityIntervalClassification.INSUFFICIENT_DATA
    visible = sum(
        sample.visibility is TrajectoryVisibilityState.VISIBLE
        for sample in samples
    )
    if visible == len(samples):
        return VisibilityIntervalClassification.VISIBLE_THROUGHOUT
    if visible == 0:
        return VisibilityIntervalClassification.NEVER_VISIBLE
    return VisibilityIntervalClassification.MIXED


def is_astronomically_circumpolar(
    family: ObservableFamily,
    samples: Sequence[TrajectorySample],
    interval_seconds: float,
    *,
    angular_tolerance_deg: float,
) -> bool:
    if family not in (
        ObservableFamily.STAR,
        ObservableFamily.DEEP_SKY,
        ObservableFamily.COORDINATE,
    ):
        return False
    if interval_seconds + 1.0 < SIDEREAL_DAY_SECONDS or not samples:
        return False
    return all(
        sample.apparent.valid
        and sample.apparent.altitude_deg > angular_tolerance_deg
        for sample in samples
    )
