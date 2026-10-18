"""Geometria B0 explícita sobre una esfera; cap visibilitat DEM ni emissió.

ECEF en metres, ENU=(est,nord,amunt), azimut des del nord cap a l'est.
Les fórmules de rotació segueixen ESA Navipedia; no s'importa SG-REF.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

from .source_model import GeodeticPosition

Vector3 = tuple[float, float, float]
EARTH_RADIUS_M = 6371008.8


def dot(a: Vector3, b: Vector3) -> float:
    return math.fsum(x * y for x, y in zip(a, b))


@dataclass(frozen=True, slots=True)
class SphericalFrame:
    observer: GeodeticPosition
    radius_m: float = EARTH_RADIUS_M

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.radius_m)
            or self.radius_m <= 0
            or self.observer.altitude_m < 0
        ):
            raise ValueError(
                "B0 requereix radi positiu i observador damunt de l'esfera"
            )

    def position_ecef(self, position: GeodeticPosition) -> Vector3:
        if position.altitude_m < 0:
            raise ValueError("Altura negativa fora del domini geomètric B0")
        phi, lam = (
            math.radians(position.latitude_deg),
            math.radians(position.longitude_deg),
        )
        r = self.radius_m + position.altitude_m
        return (
            r * math.cos(phi) * math.cos(lam),
            r * math.cos(phi) * math.sin(lam),
            r * math.sin(phi),
        )

    @property
    def basis(self) -> tuple[Vector3, Vector3, Vector3]:
        phi, lam = (
            math.radians(self.observer.latitude_deg),
            math.radians(self.observer.longitude_deg),
        )
        return (
            (-math.sin(lam), math.cos(lam), 0.0),
            (
                -math.sin(phi) * math.cos(lam),
                -math.sin(phi) * math.sin(lam),
                math.cos(phi),
            ),
            (
                math.cos(phi) * math.cos(lam),
                math.cos(phi) * math.sin(lam),
                math.sin(phi),
            ),
        )

    def enu_to_ecef(self, vector: Vector3) -> Vector3:
        e, n, u = self.basis
        return tuple(
            math.fsum((vector[0] * e[i], vector[1] * n[i], vector[2] * u[i]))
            for i in range(3)
        )  # type: ignore[return-value]

    def ecef_to_enu(self, vector: Vector3) -> Vector3:
        e, n, u = self.basis
        return dot(vector, e), dot(vector, n), dot(vector, u)


@dataclass(frozen=True, slots=True)
class ViewDirection:
    direction_id: str
    azimuth_deg: float
    elevation_deg: float

    def __post_init__(self) -> None:
        if (
            not self.direction_id
            or not math.isfinite(self.azimuth_deg)
            or not math.isfinite(self.elevation_deg)
            or not 0.5 <= self.elevation_deg <= 90
        ):
            raise ValueError("Cal direcció identificada, finita i elevació 0,5–90°")

    @property
    def enu(self) -> Vector3:
        a, e = math.radians(self.azimuth_deg % 360), math.radians(self.elevation_deg)
        return math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)


@dataclass(frozen=True, slots=True)
class RayGeometry:
    origin_ecef_m: Vector3
    direction_ecef: Vector3
    direction_enu: Vector3
    length_m: float
    radius_m: float
    observer_height_m: float

    def point(self, s: float) -> Vector3:
        return tuple(
            self.origin_ecef_m[i] + s * self.direction_ecef[i] for i in range(3)
        )  # type: ignore[return-value]

    def distance_to_height(self, altitude_m: float) -> float:
        # Racó positiu de la quadràtica, racionalitzat per evitar cancel·lació.
        h = self.observer_height_m
        delta = (altitude_m - h) * (2 * self.radius_m + altitude_m + h)
        q = (self.radius_m + h) * self.direction_enu[2]
        return delta / (math.sqrt(q * q + delta) + q)


def make_ray(
    frame: SphericalFrame, direction: ViewDirection, top_m: float
) -> RayGeometry:
    if not math.isfinite(top_m) or top_m <= frame.observer.altitude_m:
        raise ValueError("El sostre geomètric ha de superar l'observador")
    provisional = RayGeometry(
        frame.position_ecef(frame.observer),
        frame.enu_to_ecef(direction.enu),
        direction.enu,
        0.0,
        frame.radius_m,
        frame.observer.altitude_m,
    )
    length = provisional.distance_to_height(top_m)
    if not math.isfinite(length) or length <= 0:
        raise ValueError("LOS no finita")
    return RayGeometry(
        provisional.origin_ecef_m,
        provisional.direction_ecef,
        provisional.direction_enu,
        length,
        frame.radius_m,
        frame.observer.altitude_m,
    )


@dataclass(frozen=True, slots=True)
class GeometricPartition:
    cell_size_m: float = 20000.0
    layer_heights_m: tuple[float, ...] = (1000.0, 5000.0)

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.cell_size_m)
            or self.cell_size_m <= 0
            or any(not math.isfinite(x) or x <= 0 for x in self.layer_heights_m)
            or any(
                b <= a for a, b in zip(self.layer_heights_m, self.layer_heights_m[1:])
            )
        ):
            raise ValueError("Partició geomètrica no finita, negativa o desordenada")

    def segments(
        self, ray: RayGeometry, top_m: float, max_segments: int
    ) -> tuple[GeometricSegment, ...]:
        points = {0.0, ray.length_m}
        for component in ray.direction_enu[:2]:
            count = math.floor(abs(component) * ray.length_m / self.cell_size_m)
            if count + 1 > max_segments:
                raise ValueError("Partició excedeix el pressupost de segments")
            for k in range(1, count + 1):
                s = k * self.cell_size_m / abs(component)
                if 0 < s < ray.length_m:
                    points.add(s)
        for height in self.layer_heights_m:
            if ray.observer_height_m < height < top_m:
                points.add(ray.distance_to_height(height))
        cuts = sorted(points)
        if len(cuts) - 1 > max_segments:
            raise ValueError("Partició excedeix el pressupost de segments")
        segments = []
        for start, end in zip(cuts, cuts[1:]):
            middle = (start + end) / 2
            # Altura al punt mitjà; identificador de cel·la geomètric, no OpticalTile.
            altitude = math.hypot(*ray.point(middle)) - ray.radius_m
            cell = (
                math.floor(middle * ray.direction_enu[0] / self.cell_size_m),
                math.floor(middle * ray.direction_enu[1] / self.cell_size_m),
                bisect_right(self.layer_heights_m, altitude),
            )
            segments.append(GeometricSegment(start, end, cell))
        return tuple(segments)


@dataclass(frozen=True, slots=True)
class GeometricSegment:
    start_m: float
    end_m: float
    cell_id: tuple[int, int, int]
