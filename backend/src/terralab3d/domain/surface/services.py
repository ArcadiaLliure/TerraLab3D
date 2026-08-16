"""Serveis de domini per a superfícies categòriques.

Policies pures que no fan I/O, no importen rasterio ni pyproj.
"""

from __future__ import annotations

import math
from typing import Protocol, Sequence

from .models import (
    LandCoverSourceDescriptor,
    LandCoverSourceType,
    SurfaceMaterialDescriptor,
    SurfaceSampleGrid,
)


# ─── Legacy protocol ─────────────────────────────────────────────────

class SurfaceMaterialModel(Protocol):
    """Converteix mostres i estil en un descriptor de material neutral."""
    def describe(self, grid: SurfaceSampleGrid, *, style_key: str, version: int) -> SurfaceMaterialDescriptor: ...


# ─── Source selection policy ──────────────────────────────────────────

def select_sources_automatic(
    sources: Sequence[LandCoverSourceDescriptor],
) -> tuple[LandCoverSourceDescriptor, ...]:
    """Select and order sources by automatic priority.

    Rules:
    1. Native categorical sources before RGB-categorical
    2. Within the same type: higher priority first
    3. Within the same priority: finer resolution first
    4. Stable tiebreak: alphabetical by id
    """
    def sort_key(s: LandCoverSourceDescriptor) -> tuple[int, int, float, str]:
        type_rank = 0 if s.source_type == LandCoverSourceType.CATEGORICAL_NATIVE else 1
        return (type_rank, -s.priority, s.resolution_m, s.id)

    enabled = [s for s in sources if s.enabled]
    return tuple(sorted(enabled, key=sort_key))


def select_sources_manual(
    sources: Sequence[LandCoverSourceDescriptor],
    selected_id: str,
) -> tuple[LandCoverSourceDescriptor, ...]:
    """Select sources with a manual primary choice.

    The manually selected source goes first.  Remaining enabled sources
    follow in automatic order to fill nodata gaps.
    """
    selected: LandCoverSourceDescriptor | None = None
    rest: list[LandCoverSourceDescriptor] = []
    for s in sources:
        if not s.enabled:
            continue
        if s.id == selected_id:
            selected = s
        else:
            rest.append(s)

    auto = select_sources_automatic(rest)
    if selected is not None:
        return (selected,) + auto
    return auto


# ─── LOD policy ───────────────────────────────────────────────────────

class LodTier:
    """Discrete LOD tier with hysteresis thresholds."""
    __slots__ = ("tier", "block_size", "max_samples")

    def __init__(self, tier: int, block_size: int, max_samples: int) -> None:
        self.tier = tier
        self.block_size = block_size
        self.max_samples = max_samples


# Standard LOD tiers — block_size doubles at each level
LOD_TIERS = (
    LodTier(0, 1, 500_000),     # full resolution
    LodTier(1, 2, 250_000),
    LodTier(2, 4, 125_000),
    LodTier(3, 8, 62_500),
    LodTier(4, 16, 31_250),
)


def select_lod_tier(
    distance_m: float,
    native_resolution_m: float,
    fov_deg: float = 60.0,
    viewport_width_px: int = 1920,
    memory_pressure: float = 0.0,
    *,
    hysteresis_factor: float = 1.3,
    current_tier: int = 0,
) -> int:
    """Select the appropriate LOD tier for categorical sampling.

    Avoids two extremes:
    1. Reading 10 m raster for a category occupying 0.05 px on screen
    2. Degrading a nearby category spanning several pixels

    The function incorporates hysteresis to prevent thrashing when the
    camera oscillates near a tier boundary.
    """
    if distance_m <= 0 or native_resolution_m <= 0:
        return 0

    fov_rad = math.radians(max(1.0, min(180.0, fov_deg)))
    pixel_size_at_distance = 2.0 * distance_m * math.tan(fov_rad / 2.0) / max(1, viewport_width_px)
    effective_resolution = max(native_resolution_m, pixel_size_at_distance)

    # Each tier doubles the effective block size
    base_tier = 0
    for tier_def in LOD_TIERS:
        block_resolution = native_resolution_m * tier_def.block_size
        if effective_resolution >= block_resolution:
            base_tier = tier_def.tier
        else:
            break

    # Apply memory pressure: higher pressure pushes towards coarser tiers
    if memory_pressure > 0.8:
        base_tier = min(base_tier + 2, len(LOD_TIERS) - 1)
    elif memory_pressure > 0.5:
        base_tier = min(base_tier + 1, len(LOD_TIERS) - 1)

    # Hysteresis: don't switch back to a finer tier unless we're clearly past
    if base_tier < current_tier:
        upgrade_threshold = native_resolution_m * LOD_TIERS[base_tier].block_size * hysteresis_factor
        if effective_resolution > upgrade_threshold:
            return current_tier
    elif base_tier > current_tier:
        downgrade_threshold = native_resolution_m * LOD_TIERS[base_tier].block_size / hysteresis_factor
        if effective_resolution < downgrade_threshold:
            return current_tier

    return base_tier


def lod_block_size(tier: int) -> int:
    """Get the block size for a LOD tier."""
    if 0 <= tier < len(LOD_TIERS):
        return LOD_TIERS[tier].block_size
    return LOD_TIERS[-1].block_size
