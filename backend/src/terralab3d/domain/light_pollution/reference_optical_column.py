"""Oracle de columnes SG-REF: GK21 i interpolació/partició independents.

Comparteix només dades i el model d'interpolació declarat, no sample(),
traverse(), roots geomètrics ni GK7/15 del runtime. No calcula radiància.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from typing import Callable

import numpy as np
from scipy.integrate import quad_vec

from .geometric_transport import RayGeometry
from .optical_field import OpticalCoverageError, OpticalField


@dataclass(frozen=True, slots=True)
class ReferenceOpticalColumn:
    number_column_m2: float
    estimated_error_m2: float
    evaluations: int
    revision: str = "sg-ref-optical-column-gk21-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            **asdict(self),
            "unit": "m^-2",
            "meaning": "integral_of_tabulated_dry_air_number_density;not_radiance_or_empirical_validation",
        }


class ReferenceColumnCancelledError(Exception):
    """Columna offline cancel·lada, sense resultat parcial."""


def reference_optical_column(
    field: OpticalField,
    ray: RayGeometry,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> ReferenceOpticalColumn:
    def checkpoint() -> None:
        if cancelled is not None and cancelled():
            raise ReferenceColumnCancelledError(
                "Columna atmosfèrica de referència cancel·lada"
            )

    checkpoint()
    if field.radius_m != ray.radius_m:
        raise ValueError("Referencials de columna incompatibles")
    phi, lam = np.radians([field.origin.latitude_deg, field.origin.longitude_deg])
    rotation = np.array(
        [
            [-np.sin(lam), np.cos(lam), 0],
            [-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)],
            [np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)],
        ]
    )
    field_origin = (field.radius_m + field.origin.altitude_m) * rotation[2]
    start = rotation @ (np.array(ray.origin_ecef_m) - field_origin)
    direction = rotation @ np.array(ray.direction_ecef)
    direction[np.abs(direction) < 8 * np.finfo(float).eps] = 0.0
    points = {0.0, ray.length_m}
    for tile in field.tiles:
        checkpoint()
        b = tile.bounds
        for axis, lower, upper in (
            (0, b.east_min_m, b.east_max_m),
            (1, b.north_min_m, b.north_max_m),
        ):
            if direction[axis] != 0:
                for boundary in (lower, upper):
                    s = float((boundary - start[axis]) / direction[axis])
                    if 0 < s < ray.length_m:
                        points.add(s)
        # Arrels en Decimal 50 xifres; independent de distance_to_height().
        with localcontext() as context:
            context.prec = 50
            o = [Decimal(float(x)) for x in ray.origin_ecef_m]
            d = [Decimal(float(x)) for x in ray.direction_ecef]
            a = sum(x * x for x in d)
            bq = 2 * sum(x * y for x, y in zip(o, d))
            for height in tile.profile.heights_m:
                radius = Decimal(field.radius_m) + Decimal(height)
                c = sum(x * x for x in o) - radius * radius
                disc = bq * bq - 4 * a * c
                if disc >= 0:
                    s = float((-bq + disc.sqrt()) / (2 * a))
                    if 0 < s < ray.length_m:
                        points.add(s)

    def density(s: float) -> float:
        checkpoint()
        local = start + s * direction
        candidates = [
            t
            for t in field.tiles
            if t.bounds.east_min_m <= local[0] < t.bounds.east_max_m
            and t.bounds.north_min_m <= local[1] < t.bounds.north_max_m
        ]
        if len(candidates) != 1:
            raise OpticalCoverageError("Oracle sense cobertura lateral única")
        profile = candidates[0].profile
        height = float(
            np.linalg.norm(
                np.array(ray.origin_ecef_m) + s * np.array(ray.direction_ecef)
            )
            - field.radius_m
        )
        if not profile.heights_m[0] - 1e-7 <= height <= profile.heights_m[-1] + 1e-7:
            raise OpticalCoverageError("Oracle fora del suport vertical")
        pressure = float(
            np.exp(np.interp(height, profile.heights_m, np.log(profile.pressure_pa)))
        )
        temperature = float(np.interp(height, profile.heights_m, profile.temperature_k))
        return pressure / (1.380649e-23 * temperature)

    value, error, info = quad_vec(
        density,
        0.0,
        ray.length_m,
        points=sorted(points)[1:-1],
        epsrel=1e-10,
        epsabs=0.0,
        quadrature="gk21",
        norm="max",
        workers=1,
        full_output=True,
        limit=10000,
    )
    if (
        not info.success
        or not math.isfinite(float(value))
        or float(value) <= 0
        or not math.isfinite(float(error))
    ):
        raise ValueError("Columna SG-REF no convergent")
    return ReferenceOpticalColumn(float(value), float(error), int(info.neval))
