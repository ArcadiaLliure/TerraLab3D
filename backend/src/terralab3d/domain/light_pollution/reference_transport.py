"""SG-REF offline: integral LOS GK21 i àrea GL, independents del futur runtime.

Domini declarat: pla tangent cartesià, atmosfera espectral homogènia entre
z=0 i z=H, terra negre i cel clar escalar. No inclou curvatura, DEM, BRDF,
polarització ni múltiples dispersions (contrast separat Monte Carlo).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Callable, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import quad_vec

from .source_model import (
    AzimuthalAngularEmissionProfile,
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
    SourceModel,
)

REVISION = "sg-ref-flat-homogeneous-v1"
FloatArray = NDArray[np.float64]


class ReferenceConvergenceError(ValueError):
    """No es pot declarar convergència amb els límits sol·licitats."""


class ReferenceCancelledError(Exception):
    """Càlcul offline cancel·lat; no es publica cap resultat parcial."""


@dataclass(frozen=True, slots=True)
class ReferencePhase:
    kind: Literal["isotropic", "rayleigh", "hg", "tabulated"]
    asymmetry: float = 0.0
    cosines: tuple[float, ...] = ()
    relative_values: tuple[float, ...] = ()
    evidence_reference: str = "definició analítica escalar de referència"

    def __post_init__(self) -> None:
        if (
            self.kind not in {"isotropic", "rayleigh", "hg", "tabulated"}
            or not self.evidence_reference
        ):
            raise ValueError("Cal una fase de referència identificada")
        if not math.isfinite(self.asymmetry) or abs(self.asymmetry) >= 1:
            raise ValueError("Asimetria HG fora de (-1,1)")
        if self.kind == "tabulated":
            if len(self.cosines) < 3 or len(self.cosines) != len(self.relative_values):
                raise ValueError("Taula de fase incompleta")
            if (
                self.cosines[0] != -1
                or self.cosines[-1] != 1
                or any(b <= a for a, b in zip(self.cosines, self.cosines[1:]))
            ):
                raise ValueError("La taula de fase ha de cobrir -1..1")
            if (
                any(
                    not math.isfinite(x) for x in (*self.cosines, *self.relative_values)
                )
                or min(self.relative_values) < 0
                or max(self.relative_values) <= 0
            ):
                raise ValueError("Taula de fase no finita, negativa o nul·la")

    def density(self, cosine: FloatArray) -> FloatArray:
        mu = np.clip(cosine, -1.0, 1.0)
        if self.kind == "isotropic":
            return np.full_like(mu, 1 / (4 * math.pi))
        if self.kind == "rayleigh":
            return 3 * (1 + mu * mu) / (16 * math.pi)
        if self.kind == "hg":
            g = self.asymmetry
            return (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * mu) ** 1.5)
        normalizer = (
            2 * math.pi * float(np.trapezoid(self.relative_values, self.cosines))
        )
        return np.interp(mu, self.cosines, self.relative_values) / normalizer


@dataclass(frozen=True, slots=True)
class ReferenceOptics:
    wavelengths_nm: tuple[float, ...]
    extinction_per_m: tuple[float, ...]
    scattering_per_m: tuple[float, ...]
    top_m: float
    phase: ReferencePhase
    evidence_reference: str

    def __post_init__(self) -> None:
        n = len(self.wavelengths_nm)
        if n == 0 or n != len(self.extinction_per_m) or n != len(self.scattering_per_m):
            raise ValueError("Longituds d'ona i coeficients òptics no aparellats")
        if any(
            not math.isfinite(x)
            for x in (
                *self.wavelengths_nm,
                *self.extinction_per_m,
                *self.scattering_per_m,
                self.top_m,
            )
        ):
            raise ValueError("Òptica no finita")
        if min(self.wavelengths_nm) <= 0 or any(
            b <= a for a, b in zip(self.wavelengths_nm, self.wavelengths_nm[1:])
        ):
            raise ValueError("Longituds d'ona no positives o no creixents")
        if (
            self.top_m <= 0
            or not self.evidence_reference
            or any(
                not 0 <= sca <= ext
                for sca, ext in zip(self.scattering_per_m, self.extinction_per_m)
            )
        ):
            raise ValueError("Cal 0 ≤ dispersió ≤ extinció i altura positiva")


@dataclass(frozen=True, slots=True)
class ReferenceSettings:
    los_relative_tolerance: float = 1e-8
    absolute_tolerance: float = 1e-20
    area_relative_tolerance: float = 1e-6
    area_orders: tuple[int, ...] = (8, 16, 32, 64, 128)
    los_limit: int = 10000
    earth_radius_m: float = 6371008.8

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(x) or x <= 0
            for x in (
                self.los_relative_tolerance,
                self.absolute_tolerance,
                self.area_relative_tolerance,
                self.earth_radius_m,
            )
        ):
            raise ValueError("Toleràncies i radi de referència han de ser positius")
        if (
            len(self.area_orders) < 3
            or any(type(x) is not int or x < 2 or x > 512 for x in self.area_orders)
            or any(b <= a for a, b in zip(self.area_orders, self.area_orders[1:]))
        ):
            raise ValueError(
                "Calen almenys tres ordres espacials creixents entre 2 i 512"
            )
        if type(self.los_limit) is not int or self.los_limit < 2:
            raise ValueError("Límit d'integració invàlid")


@dataclass(frozen=True, slots=True)
class ReferenceRadiance:
    wavelengths_nm: tuple[float, ...]
    values: tuple[float, ...]
    numerical_error_estimate: tuple[float, ...]
    unit: str
    source_ids: tuple[str, ...]
    source_modes: tuple[str, ...]
    input_signature: str
    refinement_history: tuple[dict[str, object], ...]
    los_evaluations: int
    revision: str = REVISION

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            **asdict(self),
            "errorMeaning": "estimated_LOS_plus_spatial_refinement_difference;not_rigorous_interval",
            "structuralUncertainty": "not_quantified",
            "physicalDomain": "flat_tangent_homogeneous_slab_single_scattering",
            "empiricalValidation": "not_evaluated",
            "runtimeGate": "not_evaluated_step_7.12",
        }


def _angular_density(
    source: SourceModel, theta: FloatArray, azimuth: FloatArray
) -> FloatArray:
    angular = source.angular
    axial = (
        angular.axial
        if isinstance(angular, AzimuthalAngularEmissionProfile)
        else angular
    )
    density = (
        np.interp(theta, axial.zenith_deg, axial.relative_intensity)
        / axial.solid_angle_integral
    )
    if isinstance(angular, AzimuthalAngularEmissionProfile):
        density *= (
            np.interp(azimuth % 360, angular.azimuth_deg, angular.relative_azimuth)
            / angular.azimuth_mean
        )
    return density


def _source_nodes(
    source: SourceModel, observer: GeodeticPosition, order: int, radius: float
) -> tuple[FloatArray, FloatArray]:
    geometry = source.geometry
    pos = (
        geometry.position
        if isinstance(geometry, PointSourceGeometry)
        else geometry.center
    )
    # Projecció de referència local explícita; no és geodèsia global.
    dlon = (pos.longitude_deg - observer.longitude_deg + 180) % 360 - 180
    center = np.array(
        [
            radius * math.radians(dlon) * math.cos(math.radians(observer.latitude_deg)),
            radius * math.radians(pos.latitude_deg - observer.latitude_deg),
            pos.altitude_m,
        ]
    )
    if isinstance(geometry, PointSourceGeometry):
        return center[None, :], np.ones(1)
    x, w = np.polynomial.legendre.leggauss(order)
    u, v = np.meshgrid(
        x * geometry.east_width_m / 2, x * geometry.north_height_m / 2, indexing="ij"
    )
    angle = math.radians(geometry.orientation_deg)
    points = np.column_stack(
        (
            center[0] + (u * math.cos(angle) + v * math.sin(angle)).ravel(),
            center[1] + (-u * math.sin(angle) + v * math.cos(angle)).ravel(),
            np.full(order * order, center[2]),
        )
    )
    return points, np.outer(w, w).ravel() / 4


def solve_reference(
    sources: tuple[SourceModel, ...],
    observer: GeodeticPosition,
    azimuth_deg: float,
    elevation_deg: float,
    optics: ReferenceOptics,
    settings: ReferenceSettings = ReferenceSettings(),
    *,
    cancelled: Callable[[], bool] | None = None,
) -> ReferenceRadiance:
    """Suma explícita de fonts físiques, mai d'alternatives d'un ensemble.

    ∫ ds Σ_j [Pλ a(θ) / r²] βsca Pphase Tsource Tobserver.
    Rectangle: integral directa dA/A, sense aproximació puntual ni quadtree.
    L'error de LOS és en norma màxima; la cota estimada es reporta per canal.
    """
    if (
        not sources
        or not math.isfinite(azimuth_deg)
        or not math.isfinite(elevation_deg)
        or not 0.5 <= elevation_deg <= 90
    ):
        raise ValueError("Calen fonts i direcció dins del domini 0,5–90°")
    if not 0 <= observer.altitude_m < optics.top_m or abs(observer.latitude_deg) == 90:
        raise ValueError("Observador fora del domini del pla tangent")
    units = {source.amplitude.unit for source in sources}
    if (
        len(units) != 1
        or len(
            {
                s.amplitude.parameter_name
                for s in sources
                if s.amplitude.unit == "relative"
            }
        )
        > 1
    ):
        raise ValueError(
            "No se sumen watts i escales relatives ni paràmetres incompatibles"
        )
    if len({s.source_model_id for s in sources}) != len(sources):
        raise ValueError("Font duplicada en la suma")
    origin = np.array([0.0, 0.0, observer.altitude_m])
    az, el = math.radians(azimuth_deg % 360), math.radians(elevation_deg)
    direction = np.array(
        [math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)]
    )
    length = (optics.top_m - observer.altitude_m) / direction[2]
    extinction, scattering = (
        np.array(optics.extinction_per_m),
        np.array(optics.scattering_per_m),
    )
    spectral_flux = [
        np.array([s.spectral_flux(w).value for w in optics.wavelengths_nm])
        for s in sources
    ]
    break_distances: set[float] = set()
    for source in sources:
        center, _ = _source_nodes(
            source,
            observer,
            1 if isinstance(source.geometry, PointSourceGeometry) else 2,
            settings.earth_radius_m,
        )
        z = float(center[0, 2])
        if not 0 <= z < optics.top_m:
            raise ValueError("Font fora de l'atmosfera de referència")
        at = (z - origin[2]) / direction[2]
        # L'emissió només existeix per damunt de la font. Segmentar evita
        # perdre una capa emissora molt prima prop del límit superior.
        if 0 < at < length:
            break_distances.add(at)
        if isinstance(source.geometry, PointSourceGeometry):
            offset = center[0] - origin
            nearest = float(offset @ direction)
            perpendicular = float(np.linalg.norm(offset - nearest * direction))
            for feature in (nearest - perpendicular, nearest, nearest + perpendicular):
                if 0 < feature < length:
                    break_distances.add(feature)
        if 0 <= at <= length:
            crossing = origin + at * direction
            if isinstance(source.geometry, PointSourceGeometry):
                collision = np.linalg.norm(center[0] - crossing) < 1e-8
            else:
                # Intersecció exacta del rectangle, independent dels nodes GL.
                g = source.geometry
                p = g.center
                ce = (
                    settings.earth_radius_m
                    * math.radians(
                        (p.longitude_deg - observer.longitude_deg + 180) % 360 - 180
                    )
                    * math.cos(math.radians(observer.latitude_deg))
                )
                cn = settings.earth_radius_m * math.radians(
                    p.latitude_deg - observer.latitude_deg
                )
                de, dn = crossing[0] - ce, crossing[1] - cn
                a = math.radians(g.orientation_deg)
                collision = (
                    abs(de * math.cos(a) - dn * math.sin(a)) <= g.east_width_m / 2
                    and abs(de * math.sin(a) + dn * math.cos(a)) <= g.north_height_m / 2
                )
            if collision:
                raise ValueError(
                    "LOS interseca la font: geometria singular fora del domini"
                )
    distances = [
        float(
            np.min(
                np.linalg.norm(
                    _source_nodes(s, observer, 2, settings.earth_radius_m)[0] - origin,
                    axis=1,
                )
            )
        )
        for s in sources
    ]
    scale = min(distances)  # Canvi de variable exacte; no és cap tall físic.
    upper = math.asinh(length / scale)
    history: list[dict[str, object]] = []
    previous: FloatArray | None = None
    previous_los = 0.0
    consecutive = 0
    evaluations = 0
    has_area = any(isinstance(s.geometry, RectangularAreaGeometry) for s in sources)
    final_error = np.zeros(len(extinction))
    for order in settings.area_orders if has_area else (2,):
        nodes = [
            _source_nodes(s, observer, order, settings.earth_radius_m) for s in sources
        ]

        def integrand(t: float) -> FloatArray:
            if cancelled is not None and cancelled():
                raise ReferenceCancelledError("SG-REF cancel·lat")
            distance_los = scale * math.sinh(t)
            scatter_point = origin + distance_los * direction
            total = np.zeros(len(extinction))
            for source, (points, weights), flux in zip(sources, nodes, spectral_flux):
                displacement = scatter_point - points
                r = np.linalg.norm(displacement, axis=1)
                upward = displacement[:, 2] >= 0
                mu_source = displacement[:, 2] / r
                theta = np.degrees(np.arccos(np.clip(mu_source, -1.0, 1.0)))
                emission = _angular_density(
                    source,
                    theta,
                    np.degrees(np.arctan2(displacement[:, 0], displacement[:, 1])),
                )
                phase = optics.phase.density(-(displacement @ direction) / r)
                geometric = np.where(upward, weights * emission * phase / (r * r), 0.0)
                transmission = np.exp(-np.outer(r + distance_los, extinction))
                total += flux * scattering * (geometric @ transmission)
            return total * scale * math.cosh(t)

        value, error, info = quad_vec(
            integrand,
            0.0,
            upper,
            epsabs=settings.absolute_tolerance,
            epsrel=settings.los_relative_tolerance,
            norm="max",
            quadrature="gk21",
            workers=1,
            limit=settings.los_limit,
            full_output=True,
            points=sorted(math.asinh(s / scale) for s in break_distances),
        )
        evaluations += info.neval
        value = np.asarray(value, dtype=float)
        if (
            not info.success
            or not math.isfinite(float(error))
            or np.any(~np.isfinite(value))
            or np.any(value < 0)
        ):
            raise ReferenceConvergenceError(f"LOS no convergent: {info.message}")
        delta = (
            np.abs(value - previous)
            if previous is not None
            else np.full_like(value, np.inf)
        )
        if previous is not None:
            budget = (
                settings.absolute_tolerance
                + settings.area_relative_tolerance * np.abs(value)
            )
            consecutive = (
                consecutive + 1 if np.all(delta + error + previous_los <= budget) else 0
            )
        history.append(
            {
                "areaOrder": order if has_area else None,
                "values": tuple(float(x) for x in value),
                "losErrorMax": float(error),
                "spatialDifference": tuple(float(x) for x in delta)
                if previous is not None
                else None,
            }
        )
        final_error = (
            delta + error + previous_los
            if previous is not None
            else np.full_like(value, error)
        )
        if not has_area or consecutive >= 2:
            break
        previous, previous_los = value, float(error)
    else:
        raise ReferenceConvergenceError(
            "Àrea sense dues refinacions convergents consecutives"
        )
    signature = hashlib.sha256(
        json.dumps(
            {
                "revision": REVISION,
                "sources": [s.to_dict() for s in sources],
                "observer": asdict(observer),
                "azimuth": azimuth_deg % 360,
                "elevation": elevation_deg,
                "optics": asdict(optics),
                "settings": asdict(settings),
            },
            sort_keys=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return ReferenceRadiance(
        optics.wavelengths_nm,
        tuple(float(x) for x in value),
        tuple(float(x) for x in final_error),
        f"{sources[0].amplitude.unit} m^-2 sr^-1 nm^-1",
        tuple(s.source_model_id for s in sources),
        tuple(s.source_mode for s in sources),
        signature,
        tuple(history),
        evaluations,
    )
