"""Canonical raster-grid contract used by all refinement sources."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .errors import GridAlignmentError, RefinementValidationError


class ResamplingPolicy(str, Enum):
    NEAREST = "nearest"
    MODE = "mode"
    BILINEAR = "bilinear"
    CUBIC = "cubic"


@dataclass(frozen=True, slots=True)
class TemporalPolicy:
    strategy: str
    window_days: int | None = None

    def __post_init__(self) -> None:
        if not self.strategy.strip():
            raise RefinementValidationError("Temporal policy strategy is required")
        if self.window_days is not None and self.window_days <= 0:
            raise RefinementValidationError("Temporal window must be positive")


@dataclass(frozen=True, slots=True)
class TargetGridSpec:
    """Exact target grid, including pixel origin and temporal semantics."""

    crs: str
    resolution_x: float
    resolution_y: float
    origin_x: float
    origin_y: float
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: int
    height: int
    dtype: str
    nodata: int | float | None
    resampling: ResamplingPolicy
    tlst_version: str
    temporal_policy: TemporalPolicy

    def __post_init__(self) -> None:
        if not self.crs.strip():
            raise RefinementValidationError("Grid CRS is required")
        if self.resolution_x <= 0 or self.resolution_y <= 0:
            raise RefinementValidationError("Grid resolution must be positive")
        if self.width <= 0 or self.height <= 0:
            raise RefinementValidationError("Grid dimensions must be positive")
        if self.max_x <= self.min_x or self.max_y <= self.min_y:
            raise RefinementValidationError("Grid extent must have positive area")
        if not self.dtype.strip() or not self.tlst_version.strip():
            raise RefinementValidationError("Grid dtype and TLST version are required")
        expected_width = (self.max_x - self.min_x) / self.resolution_x
        expected_height = (self.max_y - self.min_y) / self.resolution_y
        if not math.isclose(expected_width, self.width, rel_tol=0, abs_tol=1e-8):
            raise RefinementValidationError("Grid width does not match extent and resolution")
        if not math.isclose(expected_height, self.height, rel_tol=0, abs_tol=1e-8):
            raise RefinementValidationError("Grid height does not match extent and resolution")
        if not self._on_lattice(self.min_x, self.origin_x, self.resolution_x):
            raise RefinementValidationError("Grid minimum X is not aligned to its pixel origin")
        if not self._on_lattice(self.min_y, self.origin_y, self.resolution_y):
            raise RefinementValidationError("Grid minimum Y is not aligned to its pixel origin")

    def is_aligned_with(self, other: TargetGridSpec, *, tolerance: float = 1e-8) -> bool:
        if self.crs != other.crs or self.tlst_version != other.tlst_version:
            return False
        if self.resampling is not other.resampling:
            return False
        if not math.isclose(self.resolution_x, other.resolution_x, rel_tol=0, abs_tol=tolerance):
            return False
        if not math.isclose(self.resolution_y, other.resolution_y, rel_tol=0, abs_tol=tolerance):
            return False
        return self._same_lattice(
            self.origin_x,
            other.origin_x,
            self.resolution_x,
            tolerance,
        ) and self._same_lattice(
            self.origin_y,
            other.origin_y,
            self.resolution_y,
            tolerance,
        )

    def require_aligned_with(self, other: TargetGridSpec) -> None:
        if not self.is_aligned_with(other):
            raise GridAlignmentError("Raster source is not aligned to the canonical target grid")

    @staticmethod
    def _on_lattice(value: float, origin: float, resolution: float) -> bool:
        return math.isclose(
            (value - origin) / resolution,
            round((value - origin) / resolution),
            rel_tol=0,
            abs_tol=1e-8,
        )

    @staticmethod
    def _same_lattice(first: float, second: float, resolution: float, tolerance: float) -> bool:
        offset_pixels = (first - second) / resolution
        return math.isclose(offset_pixels, round(offset_pixels), rel_tol=0, abs_tol=tolerance)
