"""Pure, vectorized horizon science with explicit units and tolerances."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike, NDArray

from terralab3d.domain.horizon.models import (
    EARTH_RADIUS_M,
    HorizonProfileSettings,
    HorizonReduction,
    HorizonRangeMode,
)


def apparent_elevation_degrees(
    terrain_elevation_m: ArrayLike,
    horizontal_distance_m: ArrayLike,
    observer_eye_elevation_m: float,
    effective_earth_radius_m: float,
) -> NDArray[np.float64]:
    """TerraLab parity model: drop=d^2/(2R), then atan2(delta height, d)."""

    distance = np.asarray(horizontal_distance_m, dtype=np.float64)
    terrain = np.asarray(terrain_elevation_m, dtype=np.float64)
    safe_distance = np.maximum(distance, 1e-9)
    drop = safe_distance * safe_distance / (2.0 * float(effective_earth_radius_m))
    return np.degrees(
        np.arctan2(terrain - drop - float(observer_eye_elevation_m), safe_distance)
    )


def reduce_horizon_samples(
    distances_m: ArrayLike,
    terrain_elevations_m: ArrayLike,
    valid_mask: ArrayLike,
    observer_eye_elevation_m: float,
    *,
    effective_earth_radius_m: float,
) -> HorizonReduction:
    """Reduce one matrix [azimuth, distance] without raster or CRS dependencies."""

    distances = np.asarray(distances_m, dtype=np.float64)
    terrain = np.asarray(terrain_elevations_m, dtype=np.float64)
    valid = np.asarray(valid_mask, dtype=np.bool_)
    if terrain.ndim != 2 or valid.shape != terrain.shape:
        raise ValueError("Terrain elevations and valid mask must be aligned 2D matrices")
    if distances.ndim == 1:
        if distances.size != terrain.shape[1]:
            raise ValueError("Distance vector must match the terrain matrix columns")
        distance_matrix = np.broadcast_to(distances[None, :], terrain.shape)
    elif distances.ndim == 2 and distances.shape == terrain.shape:
        distance_matrix = distances
    else:
        raise ValueError("Distances must be one shared vector or an aligned 2D matrix")

    angles = apparent_elevation_degrees(
        terrain,
        distance_matrix,
        observer_eye_elevation_m,
        effective_earth_radius_m,
    )
    usable = valid & np.isfinite(terrain) & np.isfinite(angles)
    masked = np.where(usable, angles, -np.inf)
    winning = np.argmax(masked, axis=1)
    rows = np.arange(terrain.shape[0])
    resolved = np.any(usable, axis=1)
    horizon = np.where(resolved, masked[rows, winning], 0.0).astype(np.float32)
    occluder_distance = np.where(resolved, distance_matrix[rows, winning], 0.0).astype(np.float32)
    occluder_height = np.where(resolved, terrain[rows, winning], 0.0).astype(np.float32)
    return HorizonReduction(horizon, occluder_distance, occluder_height, resolved)


def mask_after_consecutive_misses(
    valid_mask: ArrayLike,
    *,
    threshold: int = 8,
) -> NDArray[np.bool_]:
    """Stop each radial coverage sequence after the configured miss run."""

    valid = np.asarray(valid_mask, dtype=np.bool_)
    if valid.ndim != 2:
        raise ValueError("Coverage mask must be a 2D azimuth-by-distance matrix")
    if threshold < 1:
        raise ValueError("Miss threshold must be positive")
    result = valid.copy()
    if valid.shape[1] < threshold:
        return result
    missing_windows = np.lib.stride_tricks.sliding_window_view(
        ~valid,
        threshold,
        axis=1,
    )
    runs = np.all(missing_windows, axis=-1)
    has_exit = np.any(runs, axis=1)
    first_start = np.argmax(runs, axis=1)
    columns = np.arange(valid.shape[1])[None, :]
    stop_columns = (first_start + threshold)[:, None]
    result &= ~(has_exit[:, None] & (columns >= stop_columns))
    return result


def horizon_distance_m(height_m: float, earth_radius_m: float) -> float:
    height = max(0.0, float(height_m))
    return math.sqrt(2.0 * earth_radius_m * height + height * height)


def resolve_visible_radius_m(
    settings: HorizonProfileSettings,
    observer_eye_elevation_m: float,
    *,
    target_max_elevation_m: float = 8_849.0,
) -> float:
    checked = settings.validated()
    if checked.range_mode is HorizonRangeMode.MANUAL:
        return checked.visible_radius_km * 1000.0
    factor = checked.effective_earth_radius_factor if checked.atmospheric_refraction_enabled else 1.0
    radius = EARTH_RADIUS_M * factor
    calculated = horizon_distance_m(observer_eye_elevation_m, radius) + horizon_distance_m(
        target_max_elevation_m, radius
    )
    return min(530_000.0, max(1_000.0, calculated))


def adaptive_distances_m(
    visible_radius_m: float,
    nominal_resolution_m: float | None,
    max_samples_per_ray: int,
) -> NDArray[np.float64]:
    """Near-to-far 1x/2x/4x/8x schedule, bounded without changing radius."""

    radius = float(visible_radius_m)
    base = max(5.0, float(nominal_resolution_m or 50.0))
    limits = (10_000.0, 50_000.0, 150_000.0, radius)
    multipliers = (1.0, 2.0, 4.0, 8.0)
    chunks: list[NDArray[np.float64]] = []
    start = base
    for limit, multiplier in zip(limits, multipliers):
        end = min(radius, limit)
        if end >= start:
            step = base * multiplier
            chunks.append(np.arange(start, end + step * 0.25, step, dtype=np.float64))
        start = end + base * multiplier
        if end >= radius:
            break
    distances = np.unique(np.clip(np.concatenate(chunks) if chunks else np.array([radius]), base, radius))
    if distances[-1] < radius:
        distances = np.append(distances, radius)
    maximum = int(max_samples_per_ray)
    if distances.size > maximum:
        positions = np.linspace(0, distances.size - 1, maximum, dtype=np.int64)
        distances = distances[positions]
        distances[-1] = radius
    return distances


def curvature_parity_error_m(distance_m: float, earth_radius_m: float = EARTH_RADIUS_M) -> float:
    """Difference between TerraLab's parabolic drop and exact spherical drop."""

    distance = float(distance_m)
    approximate = distance * distance / (2.0 * earth_radius_m)
    exact = earth_radius_m - math.sqrt(max(0.0, earth_radius_m * earth_radius_m - distance * distance))
    return approximate - exact
