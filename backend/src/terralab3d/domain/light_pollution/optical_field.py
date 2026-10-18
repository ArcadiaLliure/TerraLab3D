"""Camp atmosfèric immutable, perfils verticals i dependències reals de tiles.

Alçades geomètriques sobre l'esfera declarada; cap provider ni I/O al domini.
Pressió log-lineal i temperatura lineal són part del model tabulat explícit.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

from .geometric_transport import EARTH_RADIUS_M, RayGeometry, SphericalFrame, Vector3
from .source_model import GeodeticPosition

BOLTZMANN_J_K = 1.380649e-23
FIELD_REVISION = "optical-field-tabulated-v1"


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


class OpticalCoverageError(ValueError):
    """Falta cobertura; no es substitueix per una atmosfera nul·la."""


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    field_name: str
    provider_id: str
    model_revision: str
    source_reference: str
    interpretation: str

    def __post_init__(self) -> None:
        if any(not x for x in asdict(self).values()):
            raise ValueError("Procedència atmosfèrica incompleta")


@dataclass(frozen=True, slots=True)
class VerticalProfile:
    heights_m: tuple[float, ...]
    pressure_pa: tuple[float, ...]
    temperature_k: tuple[float, ...]
    revision: str
    provenance: tuple[FieldProvenance, ...]
    relative_humidity: float = 0.0

    def __post_init__(self) -> None:
        n = len(self.heights_m)
        if (
            n < 2
            or n != len(self.pressure_pa)
            or n != len(self.temperature_k)
            or any(
                not math.isfinite(x)
                for x in (
                    *self.heights_m,
                    *self.pressure_pa,
                    *self.temperature_k,
                    self.relative_humidity,
                )
            )
        ):
            raise ValueError("Perfil vertical no finit o incomplet")
        if (
            self.heights_m[0] < 0
            or any(b <= a for a, b in zip(self.heights_m, self.heights_m[1:]))
            or min(self.pressure_pa) <= 0
            or min(self.temperature_k) <= 0
            or not 0 <= self.relative_humidity <= 1
            or not self.revision
            or not self.provenance
        ):
            raise ValueError("Perfil atmosfèric fora del domini positiu/ordenat")
        names = {p.field_name for p in self.provenance}
        if not {
            "pressure",
            "temperature",
            "relative_humidity",
            "number_density",
        } <= names or len(names) != len(self.provenance):
            raise ValueError("Cal procedència única per cada magnitud atmosfèrica")

    def layer_index(self, height_m: float) -> int:
        if (
            not math.isfinite(height_m)
            or not self.heights_m[0] <= height_m <= self.heights_m[-1]
        ):
            raise OpticalCoverageError("Altura fora del perfil; extrapolació prohibida")
        return min(bisect_right(self.heights_m, height_m) - 1, len(self.heights_m) - 2)

    def values(self, height_m: float) -> tuple[float, float, int]:
        i = self.layer_index(height_m)
        fraction = (height_m - self.heights_m[i]) / (
            self.heights_m[i + 1] - self.heights_m[i]
        )
        pressure = math.exp(
            (1 - fraction) * math.log(self.pressure_pa[i])
            + fraction * math.log(self.pressure_pa[i + 1])
        )
        temperature = (1 - fraction) * self.temperature_k[
            i
        ] + fraction * self.temperature_k[i + 1]
        return pressure, temperature, i

    def layer_signature(self, index: int) -> str:
        return fingerprint(
            {
                "heights": self.heights_m[index : index + 2],
                "pressure": self.pressure_pa[index : index + 2],
                "temperature": self.temperature_k[index : index + 2],
                "humidity": self.relative_humidity,
                "revision": self.revision,
                "provenance": [asdict(p) for p in self.provenance],
                "interpolation": "log_pressure_linear_temperature",
            }
        )


@dataclass(frozen=True, slots=True)
class TileBounds:
    east_min_m: float
    east_max_m: float
    north_min_m: float
    north_max_m: float

    def __post_init__(self) -> None:
        if (
            any(not math.isfinite(x) for x in asdict(self).values())
            or self.east_min_m >= self.east_max_m
            or self.north_min_m >= self.north_max_m
        ):
            raise ValueError("Bounds de tile no finits o buits")

    def contains(self, east: float, north: float) -> bool:
        return (
            self.east_min_m <= east < self.east_max_m
            and self.north_min_m <= north < self.north_max_m
        )


@dataclass(frozen=True, slots=True)
class OpticalTile:
    tile_id: str
    version: str
    bounds: TileBounds
    profile: VerticalProfile

    def __post_init__(self) -> None:
        if not self.tile_id or not self.version:
            raise ValueError("Tile sense identitat/versió")


@dataclass(frozen=True, slots=True, order=True)
class OpticalDependency:
    tile_id: str
    tile_version: str
    layer_index: int
    layer_signature: str


@dataclass(frozen=True, slots=True)
class OpticalPathSegment:
    start_m: float
    end_m: float
    dependency: OpticalDependency


@dataclass(frozen=True, slots=True)
class OpticalState:
    position_ecef_m: Vector3
    altitude_m: float
    time_utc: datetime
    pressure_pa: float
    temperature_k: float
    number_density_m3: float
    relative_humidity: float
    dependency: OpticalDependency
    fields_provenance: tuple[FieldProvenance, ...]
    gas_absorption_state: None = None
    aerosol_state: None = None
    cloud_optics: None = None

    def __post_init__(self) -> None:
        if self.time_utc.tzinfo is None or self.time_utc.utcoffset() is None:
            raise ValueError("Estat atmosfèric sense zona temporal")
        if (
            any(
                not math.isfinite(x)
                for x in (
                    *self.position_ecef_m,
                    self.altitude_m,
                    self.pressure_pa,
                    self.temperature_k,
                    self.number_density_m3,
                    self.relative_humidity,
                )
            )
            or min(self.pressure_pa, self.temperature_k, self.number_density_m3) <= 0
            or not 0 <= self.relative_humidity <= 1
        ):
            raise ValueError("Estat atmosfèric no finit o no físic")

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            **asdict(self),
            "time_utc": self.time_utc.isoformat(),
            "quality": "prescribed_standard_or_fixture",
            "opticalCoefficientsStatus": "not_computed_steps_7.9_7.10",
            "structuralUncertainty": "not_quantified",
        }


@dataclass(frozen=True, slots=True)
class OpticalField:
    origin: GeodeticPosition
    tiles: tuple[OpticalTile, ...]
    time_utc: datetime
    radius_m: float = EARTH_RADIUS_M
    revision: str = FIELD_REVISION

    def __post_init__(self) -> None:
        if (
            not self.tiles
            or len({t.tile_id for t in self.tiles}) != len(self.tiles)
            or self.revision != FIELD_REVISION
            or not math.isfinite(self.radius_m)
            or self.radius_m <= 0
            or self.time_utc.tzinfo is None
            or self.time_utc.utcoffset() is None
        ):
            raise ValueError(
                "Camp òptic buit, amb versions incompatibles o temps sense zona"
            )
        SphericalFrame(self.origin, self.radius_m)
        for i, first in enumerate(self.tiles):
            for second in self.tiles[i + 1 :]:
                a, b = first.bounds, second.bounds
                if max(a.east_min_m, b.east_min_m) < min(
                    a.east_max_m, b.east_max_m
                ) and max(a.north_min_m, b.north_min_m) < min(
                    a.north_max_m, b.north_max_m
                ):
                    raise ValueError(
                        "Tiles solapats; no es resol l'ambigüitat per ordre"
                    )

    @property
    def signature(self) -> str:
        return fingerprint(self.to_dict())

    def dependency_signature(self, dependencies: tuple[OpticalDependency, ...]) -> str:
        return fingerprint(
            {
                "origin": asdict(self.origin),
                "radius_m": self.radius_m,
                "revision": self.revision,
                "time_utc": self.time_utc.astimezone(timezone.utc).isoformat(),
                "dependencies": [asdict(d) for d in sorted(set(dependencies))],
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            "revision": self.revision,
            "origin": asdict(self.origin),
            "radius_m": self.radius_m,
            "time_utc": self.time_utc.astimezone(timezone.utc).isoformat(),
            "tiles": [asdict(t) for t in sorted(self.tiles, key=lambda t: t.tile_id)],
            "interpolation": "log_pressure_linear_temperature;number_density_from_ideal_gas",
            "coordinateModel": "fixed_field_ENU_prisms_and_spherical_height",
            "parallelDirectionRoundoffEpsilonFactor": 8,
        }

    def local(self, point: Vector3) -> Vector3:
        frame = SphericalFrame(self.origin, self.radius_m)
        origin = frame.position_ecef(self.origin)
        return frame.ecef_to_enu(
            (point[0] - origin[0], point[1] - origin[1], point[2] - origin[2])
        )

    def tile(self, tile_id: str) -> OpticalTile:
        return next(t for t in self.tiles if t.tile_id == tile_id)

    def sample(
        self, point: Vector3, segment: OpticalPathSegment | None = None
    ) -> OpticalState:
        if any(not math.isfinite(x) for x in point):
            raise ValueError("Posició de consulta atmosfèrica no finita")
        east, north, _ = self.local(point)
        tolerance = 64 * sys.float_info.epsilon * self.radius_m
        if segment is None:
            candidates = [t for t in self.tiles if t.bounds.contains(east, north)]
            if len(candidates) != 1:
                raise OpticalCoverageError("Posició sense cobertura atmosfèrica única")
            tile = candidates[0]
        else:
            tile = self.tile(segment.dependency.tile_id)
            b = tile.bounds
            if (
                not b.east_min_m - tolerance <= east <= b.east_max_m + tolerance
                or not b.north_min_m - tolerance <= north <= b.north_max_m + tolerance
            ):
                raise OpticalCoverageError("Punt fora del tile del segment")
        height = math.hypot(*point) - self.radius_m
        profile = tile.profile
        if profile.heights_m[0] - tolerance <= height < profile.heights_m[0]:
            height = profile.heights_m[0]
        if profile.heights_m[-1] < height <= profile.heights_m[-1] + tolerance:
            height = profile.heights_m[-1]
        pressure, temperature, index = profile.values(height)
        dependency = OpticalDependency(
            tile.tile_id, tile.version, index, profile.layer_signature(index)
        )
        if segment is not None and dependency != segment.dependency:
            raise OpticalCoverageError(
                "Mostra incompatible amb la capa/versió del segment"
            )
        return OpticalState(
            point,
            height,
            self.time_utc.astimezone(timezone.utc),
            pressure,
            temperature,
            pressure / (BOLTZMANN_J_K * temperature),
            profile.relative_humidity,
            dependency,
            profile.provenance,
        )

    def traverse(
        self,
        ray: RayGeometry,
        max_segments: int,
        checkpoint: Callable[[], None] | None = None,
    ) -> tuple[OpticalPathSegment, ...]:
        if (
            ray.radius_m != self.radius_m
            or type(max_segments) is not int
            or max_segments < 1
        ):
            raise ValueError("Referencial o pressupost de travessa incompatible")
        frame = SphericalFrame(self.origin, self.radius_m)
        start = self.local(ray.origin_ecef_m)
        direction = frame.ecef_to_enu(ray.direction_ecef)
        intervals = []
        for tile in self.tiles:
            if checkpoint is not None:
                checkpoint()
            lo, hi = 0.0, ray.length_m
            b = tile.bounds
            for x, d, lower, upper in (
                (start[0], direction[0], b.east_min_m, b.east_max_m),
                (start[1], direction[1], b.north_min_m, b.north_max_m),
            ):
                # Error de rotació/dot d'un vector unitari: un eix numèricament
                # paral·lel manté la propietat semioberta de la frontera.
                if abs(d) < 8 * sys.float_info.epsilon:
                    d = 0.0
                if d == 0:
                    if not lower <= x < upper:
                        hi = lo
                else:
                    a, c = (lower - x) / d, (upper - x) / d
                    lo, hi = max(lo, min(a, c)), min(hi, max(a, c))
            if hi > lo:
                intervals.append((lo, hi, tile))
        intervals.sort(key=lambda t: t[0])
        cursor = 0.0
        segments = []
        for lo, hi, tile in intervals:
            if lo != cursor:
                raise OpticalCoverageError("Buit o ambigüitat al llarg de la LOS")
            cuts = {lo, hi}
            for height in tile.profile.heights_m:
                if height > ray.observer_height_m:
                    distance = ray.distance_to_height(height)
                    if lo < distance < hi:
                        cuts.add(distance)
            ordered = sorted(cuts)
            if len(segments) + len(ordered) - 1 > max_segments:
                raise ValueError("Travessa òptica excedeix el pressupost de segments")
            for a, c in zip(ordered, ordered[1:]):
                if checkpoint is not None:
                    checkpoint()
                height = math.hypot(*ray.point((a + c) / 2)) - self.radius_m
                index = tile.profile.layer_index(height)
                dependency = OpticalDependency(
                    tile.tile_id,
                    tile.version,
                    index,
                    tile.profile.layer_signature(index),
                )
                segments.append(OpticalPathSegment(a, c, dependency))
            cursor = hi
        if cursor != ray.length_m or not segments:
            raise OpticalCoverageError("La LOS surt de la cobertura atmosfèrica")
        return tuple(segments)
