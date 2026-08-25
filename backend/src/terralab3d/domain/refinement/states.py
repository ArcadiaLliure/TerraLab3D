"""Spatial TLST state derivation and hierarchy aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .errors import RefinementValidationError


class SpatialCoverageState(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class LeafCoverageFacts:
    verified_ratio: float
    planned_ratio: float
    applicable: bool = True
    active_job: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.verified_ratio <= 1 or not 0 <= self.planned_ratio <= 1:
            raise RefinementValidationError("Coverage ratios must be between zero and one")


def leaf_coverage_state(
    facts: LeafCoverageFacts,
    *,
    complete_tolerance: float = 0.995,
) -> SpatialCoverageState:
    if not 0 < complete_tolerance <= 1:
        raise RefinementValidationError("Complete tolerance must satisfy 0 < value <= 1")
    if not facts.applicable:
        return SpatialCoverageState.NOT_APPLICABLE
    if facts.verified_ratio >= complete_tolerance:
        return SpatialCoverageState.COMPLETE
    if facts.verified_ratio > 0 or facts.planned_ratio > 0 or facts.active_job:
        return SpatialCoverageState.PARTIAL
    return SpatialCoverageState.ABSENT


def aggregate_coverage_states(
    descendant_states: Sequence[SpatialCoverageState],
) -> SpatialCoverageState:
    applicable = [
        state
        for state in descendant_states
        if state is not SpatialCoverageState.NOT_APPLICABLE
    ]
    if not applicable:
        return SpatialCoverageState.NOT_APPLICABLE
    if all(state is SpatialCoverageState.COMPLETE for state in applicable):
        return SpatialCoverageState.COMPLETE
    if all(state is SpatialCoverageState.ABSENT for state in applicable):
        return SpatialCoverageState.ABSENT
    return SpatialCoverageState.PARTIAL
