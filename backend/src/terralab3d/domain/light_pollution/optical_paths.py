"""Travessa i transmissió directa d'un segment ECEF, també amb altura no monòtona."""

from __future__ import annotations

from contextlib import nullcontext

import math
import sys
from dataclasses import dataclass
from typing import Callable

from .gauss_kronrod import QuadratureSettings, integrate_gk15
from .geometric_transport import SphericalFrame, Vector3, dot
from .optical_field import (
    OpticalCoverageError,
    OpticalDependency,
    OpticalField,
    OpticalPathSegment,
)
from .scattering import ScatteringBand
from .transport_profiling import TransportProfiler


@dataclass(slots=True)
class PathWork:
    segments: int = 0
    nodes: int = 0
    max_optical_depth_error: float = 0.0


def segment_path(
    field: OpticalField,
    start: Vector3,
    end: Vector3,
    max_segments: int,
    checkpoint: Callable[[], None],
    extra_heights_m: dict[str, tuple[float, ...]] | None = None,
) -> tuple[float, Vector3, tuple[OpticalPathSegment, ...]]:
    if any(not math.isfinite(x) for x in (*start, *end)):
        raise ValueError("Extrems del trajecte no finits")
    length = math.dist(start, end)
    if length <= 0 or not math.isfinite(length):
        raise ValueError("Segment òptic buit o no finit")
    direction: Vector3 = tuple((b - a) / length for a, b in zip(start, end))  # type: ignore[assignment]
    local = field.local(start)
    local_direction = SphericalFrame(field.origin, field.radius_m).ecef_to_enu(
        direction
    )
    intervals = []
    for tile in field.tiles:
        checkpoint()
        lo, hi = 0.0, length
        bounds = tile.bounds
        for x, d, lower, upper in (
            (local[0], local_direction[0], bounds.east_min_m, bounds.east_max_m),
            (local[1], local_direction[1], bounds.north_min_m, bounds.north_max_m),
        ):
            if abs(d) < 8 * sys.float_info.epsilon:
                d = 0.0
            if d == 0:
                if not lower <= x < upper:
                    hi = lo
            else:
                a, b = (lower - x) / d, (upper - x) / d
                lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        if hi > lo:
            intervals.append((lo, hi, tile))
    intervals.sort(key=lambda row: row[0])
    cursor = 0.0
    result = []
    q = dot(start, direction)
    # Forma racionalitzada de |start|²-(R+h)²; sense restar dos quadrats grans.
    start_radius = math.hypot(*start)
    for lo, hi, tile in intervals:
        if lo != cursor:
            raise OpticalCoverageError("Buit/ambigüitat en un trajecte de transmissió")
        cuts = {lo, hi}
        heights = tile.profile.heights_m
        if extra_heights_m is not None:
            heights += extra_heights_m.get(tile.tile_id, ())
        for h in heights:
            c = (start_radius - (field.radius_m + h)) * (
                start_radius + field.radius_m + h
            )
            disc = q * q - c
            if disc >= 0:
                root = math.sqrt(disc)
                first = -q - math.copysign(root, q)
                roots = (first, c / first) if first else (0.0,)
                for s in roots:
                    if lo < s < hi:
                        cuts.add(s)
        ordered = sorted(cuts)
        if len(result) + len(ordered) - 1 > max_segments:
            raise ValueError("Pressupost de segments de transmissió excedit")
        for a, b in zip(ordered, ordered[1:]):
            checkpoint()
            point = tuple(x + (a + b) / 2 * d for x, d in zip(start, direction))
            h = math.hypot(*point) - field.radius_m
            tolerance = 64 * sys.float_info.epsilon * field.radius_m
            if tile.profile.heights_m[0] - tolerance <= h < tile.profile.heights_m[0]:
                h = tile.profile.heights_m[0]
            if tile.profile.heights_m[-1] < h <= tile.profile.heights_m[-1] + tolerance:
                h = tile.profile.heights_m[-1]
            index = tile.profile.layer_index(h)
            result.append(
                OpticalPathSegment(
                    a,
                    b,
                    OpticalDependency(
                        tile.tile_id,
                        tile.version,
                        index,
                        tile.profile.layer_signature(index),
                    ),
                )
            )
        cursor = hi
    if cursor != length or not result:
        raise OpticalCoverageError("Trajecte de transmissió fora del camp")
    return length, direction, tuple(result)


def optical_depth(
    field: OpticalField,
    band: ScatteringBand,
    start: Vector3,
    end: Vector3,
    settings: QuadratureSettings,
    max_segments: int,
    checkpoint: Callable[[], None],
    dependencies: set[OpticalDependency],
    work: PathWork,
    profiler: TransportProfiler | None = None,
) -> float:
    with profiler.measure("geometry") if profiler else nullcontext():
        length, direction, segments = segment_path(
            field, start, end, max_segments, checkpoint
        )
    values = []
    errors = []
    for segment in segments:
        checkpoint()
        dependencies.add(segment.dependency)
        tile = field.tile(segment.dependency.tile_id)
        i = segment.dependency.layer_index
        profile = tile.profile
        aerosol = band.aerosol(tile.tile_id)
        work.segments += 1
        # Cas homogeni exacte, sense LUT ni reutilització entre peticions.
        if (
            profile.pressure_pa[i] == profile.pressure_pa[i + 1]
            and profile.temperature_k[i] == profile.temperature_k[i + 1]
            and aerosol.scale_height_m is None
        ):
            beta = (
                profile.pressure_pa[i]
                / (1.380649e-23 * profile.temperature_k[i])
                * band.rayleigh_cross_section_m2
                + aerosol.extinction_per_m
            )
            values.append(beta * (segment.end_m - segment.start_m))
            continue

        def extinction(s: float) -> float:
            point: Vector3 = tuple(x + s * d for x, d in zip(start, direction))  # type: ignore[assignment]
            with (
                profiler.measure("atmospheric_sampling") if profiler else nullcontext()
            ):
                state = field.sample(point, segment)
            dependencies.add(state.dependency)
            rayleigh, aer_ext, _ = band.coefficients(state)
            return rayleigh + aer_ext

        with profiler.measure("quadrature") if profiler else nullcontext():
            q = integrate_gk15(
                extinction,
                ((segment.start_m, segment.end_m),),
                settings,
                checkpoint=checkpoint,
            )
        work.nodes += q.evaluations
        values.append(q.value)
        errors.append(q.estimated_error)
    work.max_optical_depth_error = max(work.max_optical_depth_error, math.fsum(errors))
    tau = math.fsum(values)
    if not math.isfinite(tau) or tau < 0:
        raise ValueError("Profunditat òptica negativa o no finita")
    return tau
