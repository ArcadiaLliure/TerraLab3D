"""Oracle F5 independent: Monte Carlo invers amb dispersions múltiples.

Trajectòries iid des del detector fins a la frontera negra/emissora; cap
integral LOS, node GK/GL ni aproximació puntual del solver determinista.
Domini: rectangle al terra, radiància limitada, atmosfera plana homogènia,
0 < albedo < 1. L'error mostral és calculat, no incertesa urbana inferida.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Callable, Literal

import numpy as np
from numpy.typing import NDArray

from .source_model import (
    AngularEmissionProfile,
    GeodeticPosition,
    RectangularAreaGeometry,
    SourceModel,
)


@dataclass(frozen=True, slots=True)
class MultipleScatteringEstimate:
    single_scattering: float
    all_orders: float
    single_standard_error: float
    all_orders_standard_error: float
    higher_orders: float
    higher_orders_standard_error: float
    truncation_upper_bound: float
    emitted_paths: int
    first_order_paths: int
    photons: int
    seed: int
    max_scatterings: int
    unit: str
    phase: str
    source_mode: str
    revision: str = "sg-ref-backward-monte-carlo-v1"

    def to_dict(self) -> dict[str, object]:
        # Delta de H/(S+H), conservant la covariància dels estimadors aparellats.
        s, h, total = self.single_scattering, self.higher_orders, self.all_orders
        vs, vh = self.single_standard_error**2, self.higher_orders_standard_error**2
        covariance = (self.all_orders_standard_error**2 - vs - vh) / 2
        bias_se = (
            math.sqrt(max(0.0, s * s * vh + h * h * vs - 2 * s * h * covariance))
            / total**2
            if total > 0
            else None
        )
        return {
            **asdict(self),
            "singleScatteringBiasFraction": 1 - self.single_scattering / self.all_orders
            if self.all_orders > 0
            else None,
            "biasFractionStandardError": bias_se,
            "biasErrorMeaning": "paired_delta_method_empirical_standard_error;not_confidence_bound",
            "errorMeaning": "empirical_iid_standard_error; finite_order_tail_bounded_separately",
            "scope": "same_flat_homogeneous_slab;not_universal_urban_F5_bound",
        }


def estimate_multiple_scattering(
    source: SourceModel,
    observer: GeodeticPosition,
    azimuth_deg: float,
    elevation_deg: float,
    wavelength_nm: float,
    extinction_per_m: float,
    single_scattering_albedo: float,
    top_m: float,
    *,
    phase: Literal["isotropic", "rayleigh", "hg"] = "isotropic",
    asymmetry: float = 0.0,
    photons: int = 262144,
    seed: int = 7601,
    max_scatterings: int = 128,
    earth_radius_m: float = 6371008.8,
    cancelled: Callable[[], bool] | None = None,
) -> MultipleScatteringEstimate:
    """Pesos ωⁿ i radiància de frontera, sense ruleta ni sigma inventada."""
    if (
        not isinstance(source.geometry, RectangularAreaGeometry)
        or source.geometry.center.altitude_m != 0
    ):
        raise ValueError("F5 requereix un rectangle emissor al terra")
    if (
        not isinstance(source.angular, AngularEmissionProfile)
        or source.angular.relative_intensity[-1] != 0
    ):
        raise ValueError(
            "F5 requereix radiància superficial limitada i perfil axial nul a l'horitzó"
        )
    scalars = (
        observer.altitude_m,
        azimuth_deg,
        elevation_deg,
        wavelength_nm,
        extinction_per_m,
        single_scattering_albedo,
        top_m,
        asymmetry,
        earth_radius_m,
    )
    if (
        any(not math.isfinite(x) for x in scalars)
        or extinction_per_m <= 0
        or not 0 < single_scattering_albedo < 1
        or not 0 <= observer.altitude_m < top_m
        or not 0.5 <= elevation_deg <= 90
        or abs(observer.latitude_deg) == 90
        or earth_radius_m <= 0
        or wavelength_nm <= 0
    ):
        raise ValueError("Paràmetres F5 fora del domini finit homogeni")
    if (
        type(photons) is not int
        or photons < 2
        or type(seed) is not int
        or seed < 0
        or type(max_scatterings) is not int
        or max_scatterings < 1
    ):
        raise ValueError("Nombre de trajectòries, llavor o truncament invàlids")
    if phase not in {"isotropic", "rayleigh", "hg"} or abs(asymmetry) >= 1:
        raise ValueError("Fase Monte Carlo no admesa")
    geometry = source.geometry
    dlon = (geometry.center.longitude_deg - observer.longitude_deg + 180) % 360 - 180
    cx = (
        earth_radius_m
        * math.radians(dlon)
        * math.cos(math.radians(observer.latitude_deg))
    )
    cy = earth_radius_m * math.radians(
        geometry.center.latitude_deg - observer.latitude_deg
    )
    rotation = math.radians(geometry.orientation_deg)
    ct, st = math.cos(rotation), math.sin(rotation)
    angular = source.angular
    angular_integral = angular.solid_angle_integral
    flux_density = source.spectral_flux(wavelength_nm).value / geometry.area_m2
    # cosθ >= 2(π/2-θ)/π. Perfil lineal: p/(π/2-θ) màxim als nusos.
    ratios = [
        v / (math.pi / 2 - math.radians(t))
        for t, v in zip(angular.zenith_deg[:-1], angular.relative_intensity[:-1])
    ]
    max_radiance = flux_density * max(ratios) * (math.pi / 2) / angular_integral
    rng = np.random.Generator(np.random.PCG64(seed))
    initial = np.array(
        [
            math.cos(math.radians(elevation_deg))
            * math.sin(math.radians(azimuth_deg % 360)),
            math.cos(math.radians(elevation_deg))
            * math.cos(math.radians(azimuth_deg % 360)),
            math.sin(math.radians(elevation_deg)),
        ]
    )
    points = np.zeros((photons, 3))
    points[:, 2] = observer.altitude_m
    directions = np.tile(initial, (photons, 1))
    indices = np.arange(photons)
    values = np.zeros(photons)
    first = np.zeros(photons)
    emitted_paths = first_paths = 0
    for order in range(max_scatterings + 1):
        if cancelled is not None and cancelled():
            raise InterruptedError("Monte Carlo F5 cancel·lat")
        if len(indices) == 0:
            break
        dz = directions[:, 2]
        boundary = np.divide(
            np.where(dz > 0, top_m - points[:, 2], -points[:, 2]),
            dz,
            out=np.full_like(dz, np.inf),
            where=dz != 0,
        )
        free = rng.exponential(1 / extinction_per_m, len(indices))
        exit_mask = boundary <= free
        ground = exit_mask & (dz < 0)
        if np.any(ground):
            ids = indices[ground]
            hit = points[ground] + boundary[ground, None] * directions[ground]
            dx, dy = hit[:, 0] - cx, hit[:, 1] - cy
            inside = (np.abs(dx * ct - dy * st) <= geometry.east_width_m / 2) & (
                np.abs(dx * st + dy * ct) <= geometry.north_height_m / 2
            )
            if np.any(inside):
                ids = ids[inside]
                cos_theta = -dz[ground][inside]
                theta = np.degrees(np.arccos(np.clip(cos_theta, 0.0, 1.0)))
                density = (
                    np.interp(theta, angular.zenith_deg, angular.relative_intensity)
                    / angular_integral
                )
                contribution = (
                    flux_density * density / cos_theta * single_scattering_albedo**order
                )
                values[ids] = contribution
                emitted_paths += len(ids)
                if order == 1:
                    first[ids] = contribution
                    first_paths += len(ids)
        scatter = ~exit_mask
        indices = indices[scatter]
        points = points[scatter] + free[scatter, None] * directions[scatter]
        directions = directions[scatter]
        if order == max_scatterings or len(indices) == 0:
            break
        n = len(indices)
        if phase == "rayleigh":
            mu = np.empty(n)
            pending = np.arange(n)
            while len(pending):
                candidates = rng.uniform(-1, 1, len(pending))
                accept = rng.random(len(pending)) <= (1 + candidates * candidates) / 2
                mu[pending[accept]] = candidates[accept]
                pending = pending[~accept]
        elif phase == "hg" and asymmetry != 0:
            g = asymmetry
            mu = (1 + g * g - ((1 - g * g) / (1 - g + 2 * g * rng.random(n))) ** 2) / (
                2 * g
            )
        else:
            mu = rng.uniform(-1, 1, n)
        phi = rng.uniform(0, 2 * math.pi, n)
        helper = np.zeros_like(directions)
        helper[:, 2] = 1
        vertical = np.abs(directions[:, 2]) > 0.9
        helper[vertical] = np.array([1.0, 0.0, 0.0])
        basis = np.cross(directions, helper)
        basis /= np.linalg.norm(basis, axis=1)[:, None]
        other = np.cross(directions, basis)
        directions = mu[:, None] * directions + np.sqrt(np.maximum(0.0, 1 - mu * mu))[
            :, None
        ] * (np.cos(phi)[:, None] * basis + np.sin(phi)[:, None] * other)
        directions /= np.linalg.norm(directions, axis=1)[:, None]

    def se(samples: NDArray[np.float64]) -> float:
        return float(np.std(samples, ddof=1) / math.sqrt(photons))

    higher = values - first
    return MultipleScatteringEstimate(
        float(np.mean(first)),
        float(np.mean(values)),
        se(first),
        se(values),
        float(np.mean(higher)),
        se(higher),
        max_radiance * single_scattering_albedo ** (max_scatterings + 1),
        emitted_paths,
        first_paths,
        photons,
        seed,
        max_scatterings,
        f"{source.amplitude.unit} m^-2 sr^-1 nm^-1",
        phase,
        source.source_mode,
    )
