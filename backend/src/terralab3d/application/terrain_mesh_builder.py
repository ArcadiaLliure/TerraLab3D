"""Build the persistent, observer-relative DEM terrain mesh off the UI loop.

The mesh is deliberately independent from the scientific horizon reduction:
the latter answers *what occludes the sky*, while this module transfers valid
DEM triangles plus their semantic presentation attributes to Three.js.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Callable

import numpy as np

from terralab3d.application.ports.terrain import ElevationPort, RadialCoordinateProjector
from terralab3d.domain.elevation.models import ElevationBatchRequest
from terralab3d.domain.horizon.models import EARTH_RADIUS_M, HorizonProfile, HorizonRequest
from terralab3d.infrastructure.adapters.dem.adapter import DemSamplingCancelled


TERRAIN_MESH_VERSION = 4
TERRAIN_MESH_RESOURCE_ID = "earth.terrain.mesh"
_NEAR_PATCH_HALF_EXTENT_M = 80.0
_MIN_VISUAL_AZIMUTH_STEP_DEG = 0.05
_DAY_PALETTE_STOPS = np.asarray(
    (
        (178, 194, 210),  # far atmospheric haze
        (152, 172, 186),
        (116, 138, 132),
        (82, 108, 86),
        (62, 86, 64),     # immediate foreground
    ),
    dtype=np.float32,
)


@dataclass(frozen=True, slots=True)
class TerrainMeshBuffers:
    """Typed GPU-ready arrays; positions use Three.js X=E, Y=Up, Z=-N."""

    positions: np.ndarray
    normals: np.ndarray
    colors_linear: np.ndarray
    class_ids: np.ndarray
    source_ids: np.ndarray
    indices: np.ndarray
    near_vertex_count: int
    polar_vertex_count: int
    near_axis_m: np.ndarray
    polar_distances_m: np.ndarray
    polar_azimuth_step_deg: float
    center_east_m: float
    center_north_m: float
    source_label: str

    @property
    def vertex_count(self) -> int:
        return int(self.positions.shape[0])

    @property
    def byte_length(self) -> int:
        return int(
            self.positions.nbytes
            + self.normals.nbytes
            + self.colors_linear.nbytes
            + self.class_ids.nbytes
            + self.source_ids.nbytes
            + self.indices.nbytes
        )


class TerrainMeshBuilder:
    """Port TerraLab's v3 near patch / polar mesh topology to Three.js buffers."""

    def __init__(self, elevation_port: ElevationPort, projector: RadialCoordinateProjector) -> None:
        self._elevation_port = elevation_port
        self._projector = projector

    def build(
        self,
        request: HorizonRequest,
        profile: HorizonProfile,
        cancel_event: threading.Event,
        progress_callback: Callable[[int, int], None] | None = None,
        *,
        center_east_m: float = 0.0,
        center_north_m: float = 0.0,
        visual_radius_m: float | None = None,
    ) -> TerrainMeshBuffers:
        if request.terrain_elevation_m is None:
            raise DemSamplingCancelled("Cannot build a DEM mesh without observer elevation")
        metadata = self._elevation_port.metadata()
        if not metadata.source_ids:
            raise DemSamplingCancelled("Cannot build a DEM mesh without a source")

        # A streamed mesh may be prepared while the newly centred scientific
        # profile is still finishing. Its topology must nevertheless obey the
        # current user settings captured by this request, never the previous
        # profile's range or angular precision.
        azimuth_step = _mesh_azimuth_step(request.settings.angular_step_deg)
        azimuths = np.arange(0.0, 360.0, azimuth_step, dtype=np.float64)
        mesh_radius_m = max(250.0, float(
            profile.visible_radius_m if visual_radius_m is None else visual_radius_m
        ))
        distances = _mesh_distance_rings(mesh_radius_m, metadata.resolution_m)
        effective_radius = EARTH_RADIUS_M * (
            request.settings.effective_earth_radius_factor
            if request.settings.atmospheric_refraction_enabled
            else 1.0
        )
        eye_ground = float(request.terrain_elevation_m)

        near_eastings = _near_patch_axis().astype(np.float64)
        near_northings = near_eastings.copy()
        near_east, near_north = np.meshgrid(near_eastings, near_northings)
        near_positions, near_valid = self._sample_positions(
            request,
            near_east + center_east_m,
            near_north + center_north_m,
            eye_ground,
            effective_radius,
            cancel_event,
        )
        near_normals = _cartesian_normals(
            near_positions.reshape(near_east.shape + (3,)),
            near_valid.reshape(near_east.shape),
            near_northings,
            near_eastings,
        ).reshape((-1, 3))
        near_indices = _grid_indices(near_valid.reshape(near_east.shape), wrap_columns=False)
        if progress_callback is not None:
            progress_callback(1, len(azimuths) + 1)

        n_rings = int(distances.size)
        n_azimuths = int(azimuths.size)
        polar_positions = np.zeros((n_rings, n_azimuths, 3), dtype=np.float32)
        polar_valid = np.zeros((n_rings, n_azimuths), dtype=bool)
        batch_columns = 32
        for start in range(0, n_azimuths, batch_columns):
            if cancel_event.is_set():
                raise DemSamplingCancelled()
            stop = min(n_azimuths, start + batch_columns)
            radians = np.deg2rad(azimuths[start:stop])[None, :]
            local_distances = distances[:, None]
            east = center_east_m + np.sin(radians) * local_distances
            north = center_north_m + np.cos(radians) * local_distances
            sampled_positions, sampled_valid = self._sample_positions(
                request,
                east,
                north,
                eye_ground,
                effective_radius,
                cancel_event,
            )
            polar_positions[:, start:stop] = sampled_positions.reshape(
                n_rings, stop - start, 3,
            )
            polar_valid[:, start:stop] = sampled_valid.reshape(n_rings, stop - start)
            if progress_callback is not None:
                progress_callback(stop + 1, n_azimuths + 1)

        polar_normals = _polar_normals(polar_positions, polar_valid)
        polar_indices = _grid_indices(polar_valid, wrap_columns=True)

        near_count = int(near_positions.shape[0])
        polar_count = int(polar_positions.size // 3)
        positions = np.concatenate((near_positions, polar_positions.reshape((-1, 3))), axis=0)
        normals = np.concatenate((near_normals, polar_normals.reshape((-1, 3))), axis=0)
        valid = np.concatenate((near_valid.reshape(-1), polar_valid.reshape(-1)))
        # DEM-only colour remains continuous through a streamed chunk.  Its
        # palette is measured from the persistent world origin, never from a
        # chunk-local centre, so the overlap cannot form a colour ring.
        near_world_distance = np.hypot(
            near_east + center_east_m,
            near_north + center_north_m,
        ).reshape(-1)
        polar_world_distance = np.hypot(
            center_east_m + np.sin(np.deg2rad(azimuths))[None, :] * distances[:, None],
            center_north_m + np.cos(np.deg2rad(azimuths))[None, :] * distances[:, None],
        ).reshape(-1)
        distances_per_vertex = np.concatenate((near_world_distance, polar_world_distance))
        colors = _fallback_palette_linear(distances_per_vertex, mesh_radius_m)
        colors[~valid, 3] = 0
        # The visible terrain path is deliberately DEM-only. It must not open
        # or mix any configured orthoimage or land-cover source.
        class_ids = np.zeros(valid.shape, dtype=np.uint16)
        source_ids = np.zeros(valid.shape, dtype=np.int16)
        indices = np.concatenate((near_indices, polar_indices + near_count)).astype(np.uint32, copy=False)
        return TerrainMeshBuffers(
            positions=positions,
            normals=normals,
            colors_linear=colors,
            class_ids=class_ids,
            source_ids=source_ids,
            indices=indices,
            near_vertex_count=near_count,
            polar_vertex_count=polar_count,
            near_axis_m=near_eastings.astype(np.float32, copy=False),
            polar_distances_m=distances.astype(np.float32, copy=False),
            polar_azimuth_step_deg=float(azimuth_step),
            center_east_m=float(center_east_m),
            center_north_m=float(center_north_m),
            source_label="Material DEM: paleta de relleu (sense cobertura superficial)",
        )

    def _sample_positions(
        self,
        request: HorizonRequest,
        east: np.ndarray,
        north: np.ndarray,
        observer_ground_m: float,
        effective_radius_m: float,
        cancel_event: threading.Event,
    ) -> tuple[np.ndarray, np.ndarray]:
        if cancel_event.is_set():
            raise DemSamplingCancelled()
        distance = np.hypot(east, north)
        azimuth = np.degrees(np.arctan2(east, north)) % 360.0
        latitude, longitude = self._projector.project(
            request.latitude_deg,
            request.longitude_deg,
            azimuth,
            distance,
        )
        batch = self._elevation_port.sample_points(ElevationBatchRequest(
            latitude_deg=np.asarray(latitude, dtype=np.float64),
            longitude_deg=np.asarray(longitude, dtype=np.float64),
            cancellation_check=cancel_event.is_set,
        ))
        height = np.asarray(batch.values_m, dtype=np.float64)
        # A provider's valid mask is authoritative, but enforce the known
        # persisted DEM sentinels again at the geometry boundary. A nodata
        # value must omit triangles; it can never become a deep cliff merely
        # because a converted tile marked it as valid.
        valid = (
            np.asarray(batch.valid_mask, dtype=bool)
            & np.isfinite(height)
            & (height != -9999.0)
            & (height != -8888.0)
        )
        # Build the vertical coordinate on the same effective sphere used by
        # the scientific horizon.  X/Z deliberately remain in the project
        # ENU tangent coordinates so camera navigation and DEM collision use
        # one continuous local frame through the full user-selected range.
        theta = np.minimum(distance / effective_radius_m, math.pi * 0.5)
        terrain_radius = effective_radius_m + height
        curved_up = terrain_radius * np.cos(theta) - (effective_radius_m + observer_ground_m)
        # The one project-wide scientific ENU conversion is X=east,Y=up,Z=-north.
        positions = np.column_stack((
            east.reshape(-1),
            curved_up.reshape(-1),
            -north.reshape(-1),
        )).astype(np.float32)
        positions[~valid.reshape(-1)] = 0.0
        return positions, valid.reshape(-1)


def _mesh_azimuth_step(requested_step_deg: float) -> float:
    requested = max(0.005, float(requested_step_deg))
    if requested >= _MIN_VISUAL_AZIMUTH_STEP_DEG:
        return requested
    return requested * math.ceil(_MIN_VISUAL_AZIMUTH_STEP_DEG / requested)


def _mesh_distance_rings(radius_m: float, resolution_m: float | None) -> np.ndarray:
    visual_max = max(250.0, float(radius_m))
    resolution = max(1.0, float(resolution_m or 30.0))
    zones = (
        (40.0, 5_000.0, 150),
        (5_000.0, 25_000.0, 100),
        (25_000.0, 100_000.0, 75),
        (100_000.0, 250_000.0, 45),
        (250_000.0, visual_max, 25),
    )
    segments: list[np.ndarray] = []
    for start, stop, budget in zones:
        stop = min(stop, visual_max)
        if stop <= start:
            continue
        count = max(2, min(budget, math.ceil((stop - start) / max(resolution * 2.0, 1.0)) + 1))
        segments.append(np.geomspace(start, stop, count))
    rings = np.unique(np.round(np.concatenate(segments)).astype(np.float32))
    return rings[(rings > 0.0) & (rings <= visual_max)]


def _near_patch_axis(half_extent_m: float = _NEAR_PATCH_HALF_EXTENT_M) -> np.ndarray:
    extent = max(40.0, float(half_extent_m))
    positive = np.unique(np.concatenate((
        np.arange(0.0, min(4.0, extent) + 0.25, 0.5),
        np.arange(5.0, min(12.0, extent) + 0.5, 1.0),
        np.arange(14.0, min(24.0, extent) + 1.0, 2.0),
        np.arange(28.0, min(40.0, extent) + 2.0, 4.0),
        np.arange(48.0, extent + 4.0, 8.0),
        np.asarray((extent,)),
    )))
    positive = positive[(positive >= 0.0) & (positive <= extent)]
    return np.concatenate((-positive[:0:-1], positive)).astype(np.float32)


def _grid_indices(valid: np.ndarray, *, wrap_columns: bool) -> np.ndarray:
    rows, columns = valid.shape
    triangles: list[int] = []
    maximum_column = columns if wrap_columns else columns - 1
    for row in range(rows - 1):
        for column in range(maximum_column):
            following = (column + 1) % columns
            if not (valid[row, column] and valid[row, following] and valid[row + 1, column] and valid[row + 1, following]):
                continue
            inner = row * columns + column
            inner_next = row * columns + following
            outer = (row + 1) * columns + column
            outer_next = (row + 1) * columns + following
            triangles.extend((inner, inner_next, outer, inner_next, outer_next, outer))
    return np.asarray(triangles, dtype=np.uint32)


def _polar_normals(positions: np.ndarray, valid: np.ndarray) -> np.ndarray:
    previous_rows = np.maximum(np.arange(positions.shape[0]) - 1, 0)
    next_rows = np.minimum(np.arange(positions.shape[0]) + 1, positions.shape[0] - 1)
    radial = positions[next_rows] - positions[previous_rows]
    angular = np.roll(positions, -1, axis=1) - np.roll(positions, 1, axis=1)
    normals = np.cross(angular, radial)
    normals = np.where((normals[..., 1] < 0.0)[..., None], -normals, normals)
    return _normalise(normals, valid)


def _cartesian_normals(
    positions: np.ndarray,
    valid: np.ndarray,
    northings: np.ndarray,
    eastings: np.ndarray,
) -> np.ndarray:
    heights = positions[..., 1]
    north_gradient, east_gradient = np.gradient(heights, northings, eastings, edge_order=1)
    normals = np.stack((-east_gradient, np.ones_like(heights), north_gradient), axis=-1)
    return _normalise(normals, valid)


def _normalise(normals: np.ndarray, valid: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(normals, axis=-1, keepdims=True)
    result = np.divide(normals, np.maximum(length, 1e-9), out=np.zeros_like(normals), where=length > 1e-9)
    result[~np.asarray(valid, dtype=bool)] = np.asarray((0.0, 1.0, 0.0), dtype=np.float32)
    return result.astype(np.float32)


def _fallback_palette_linear(distance_m: np.ndarray, radius_m: float) -> np.ndarray:
    """Port the day half of TerraLab's default no-surface distance palette."""

    normalized = np.sqrt(np.clip(1.0 - np.asarray(distance_m, dtype=np.float32) / max(1.0, float(radius_m)), 0.0, 1.0))
    segment = np.minimum((normalized * 4.0).astype(np.int32), 3)
    fraction = normalized * 4.0 - segment
    srgb = _DAY_PALETTE_STOPS[segment] * (1.0 - fraction[:, None]) + _DAY_PALETTE_STOPS[segment + 1] * fraction[:, None]
    srgb = np.clip(srgb / 255.0, 0.0, 1.0)
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    rgba = np.empty((srgb.shape[0], 4), dtype=np.uint8)
    rgba[:, :3] = np.rint(linear * 255.0).astype(np.uint8)
    rgba[:, 3] = 255
    return rgba
