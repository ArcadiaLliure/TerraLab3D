"""Cota exterior condicionada: hidrostàtica, dilució i dispersió simple.

No extrapola P/T, no pressuposa P(infinit)=0 i no modela la termosfera real.
La cota requereix les hipòtesis explícites de l'evidència 7.12. Ignorar
absorció i oclusió aquí només augmenta la cota d'una integrand positiva.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.special import roots_legendre

from .geometric_transport import SphericalFrame, ViewDirection, make_ray
from .scattering import PhaseFunction, ScatteringConfiguration, dry_air_rayleigh
from .source_model import (
    AzimuthalAngularEmissionProfile,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)
from .spectral_transport import SpectralTransportConfiguration


def phase_maximum(phase: PhaseFunction) -> float:
    if phase.kind == "isotropic":
        return 1 / (4 * math.pi)
    if phase.kind == "rayleigh":
        return 3 / (8 * math.pi)  # envolupant per tot delta admissible
    if phase.kind == "hg_fallback":
        g = abs(phase.asymmetry)
        return (1 + g) / (4 * math.pi * (1 - g) ** 2)
    return max(phase.relative_values) / phase.normalization


@dataclass(frozen=True, slots=True)
class ConditionalTailBound:
    upper_radiance: float
    molecular_weighted_column: float
    aerosol_weighted_length_m: float
    geometry_envelope: float
    radial_jacobian: float
    pressure_at_top_pa: float
    top_m: float
    hypothesis: str = "aire sec hidrostàtic exterior, aerosol exponencial prescrit, dispersió simple; no validació observacional"


def conditional_tail_bound(
    source: SourceModel,
    observer: GeodeticPosition,
    direction: ViewDirection,
    top_m: float,
    pressure_at_top_pa: float,
    config: ScatteringConfiguration | SpectralTransportConfiguration,
    *,
    radius_m: float = 6371008.8,
) -> ConditionalTailBound:
    """Integra una envolupant a l'infinit sense imposar una T exterior.

    n dh = -(Re+h)^2 dP/(m g0 Re^2). La caiguda total de pressió
    és <= P(H) per P>=0; el màxim geomètric inclou el límit a l'infinit.
    m és una cota inferior de la massa efectiva de l'aire sec COESA.
    """
    if not math.isfinite(pressure_at_top_pa) or pressure_at_top_pa < 0:
        raise ValueError("Pressió exterior no finita o negativa")
    frame = SphericalFrame(observer, radius_m)
    ray = make_ray(frame, direction, top_m)
    geometry = source.geometry
    position = (
        geometry.position
        if isinstance(geometry, PointSourceGeometry)
        else geometry.center
    )
    center = frame.position_ecef(position)
    offset = tuple(center[i] - ray.origin_ecef_m[i] for i in range(3))
    a = math.fsum(x * y for x, y in zip(offset, ray.direction_ecef))
    b2 = max(0.0, math.fsum(x * x for x in offset) - a * a)
    q = ray.length_m - a
    big_a = radius_m + observer.altitude_m + a
    if q <= 0 or big_a <= 0:
        raise ValueError("La font no queda per sota del domini exterior de la cota")

    def ratio(x):
        return (x + big_a) ** 2 / (x * x + b2)

    envelope = max(1.0, ratio(q), ratio(b2 / big_a) if b2 / big_a >= q else 1.0)
    r_top = math.sqrt(q * q + b2)
    area_radius = (
        0.0
        if isinstance(geometry, PointSourceGeometry)
        else math.hypot(geometry.east_width_m, geometry.north_height_m) / 2
    )
    if area_radius >= r_top:
        raise ValueError("Àrea font singular respecte de la cota exterior")
    envelope /= (1 - area_radius / r_top) ** 2
    impact2 = (radius_m + observer.altitude_m) ** 2 * (1 - ray.direction_enu[2] ** 2)
    jacobian = (radius_m + top_m) / math.sqrt((radius_m + top_m) ** 2 - impact2)
    mass = 0.0289644 / 6.02214076e23
    molecular = (
        pressure_at_top_pa * jacobian * envelope / (mass * 9.80665 * radius_m**2)
    )
    angular = source.angular
    axial = (
        angular.axial
        if isinstance(angular, AzimuthalAngularEmissionProfile)
        else angular
    )
    angular_max = max(axial.relative_intensity) / axial.solid_angle_integral
    if isinstance(angular, AzimuthalAngularEmissionProfile):
        angular_max *= max(angular.relative_azimuth) / angular.azimuth_mean
    if isinstance(config, ScatteringConfiguration):
        if len(config.band.aerosols) != 1:
            raise ValueError("La cota requereix un únic aerosol exterior prescrit")
        aerosol = config.band.aerosols[0]
        ray_factor = (
            source.spectrum.density_per_nm(config.band.wavelength_nm)
            * config.band.rayleigh_cross_section_m2
            * phase_maximum(config.band.rayleigh_phase)
        )
        aer_factor = (
            source.spectrum.density_per_nm(config.band.wavelength_nm)
            * aerosol.extinction_per_m
            * aerosol.single_scattering_albedo
            * phase_maximum(aerosol.phase)
        )
    else:
        if len(config.aerosols) != 1:
            raise ValueError("La cota requereix un únic aerosol exterior prescrit")
        spectral_aerosol = config.aerosols[0]
        aerosol = spectral_aerosol.reference
        lo, hi = config.wavelength_start_nm, config.wavelength_end_nm
        knots = sorted(
            {lo, hi}
            | {x for x in source.spectrum.wavelengths_nm if lo < x < hi}
            | {x for r in config.responses for x in r.wavelengths_nm if lo < x < hi}
        )
        left, right = np.asarray(knots[:-1]), np.asarray(knots[1:])
        x, w = roots_legendre(2)  # produit de <=3 funcions lineals: integral exacta
        if len(config.responses) > 2:
            raise ValueError("Cota espectral només homologada fins a dues respostes")
        waves = (left[:, None] + right[:, None]) / 2 + (right - left)[:, None] / 2 * x
        weights = (
            (right - left)[:, None]
            / 2
            * w
            * np.interp(
                waves,
                source.spectrum.wavelengths_nm,
                source.spectrum.relative_power,
                left=0,
                right=0,
            )
            / source.spectrum.raw_integral_nm
        )
        for response in config.responses:
            weights *= np.interp(
                waves, response.wavelengths_nm, response.values, left=0, right=0
            )
        energy = weights.sum(axis=1)
        # sigma decreix al visible; màxim al cap esquerre de cada interval.
        sigma = np.array(
            [dry_air_rayleigh(float(wavelength))[0] for wavelength in left]
        )
        ray_factor = float(energy @ sigma) * 3 / (8 * math.pi)
        spectral_ext = np.maximum(
            (left / spectral_aerosol.reference_wavelength_nm)
            ** (-spectral_aerosol.angstrom_exponent),
            (right / spectral_aerosol.reference_wavelength_nm)
            ** (-spectral_aerosol.angstrom_exponent),
        )
        aer_factor = (
            float(energy @ spectral_ext)
            * aerosol.extinction_per_m
            * aerosol.single_scattering_albedo
            * phase_maximum(aerosol.phase)
        )
    if aerosol.scale_height_m is None:
        raise ValueError("Cota exterior requereix un aerosol exponencial prescrit")
    aerosol_length = (
        jacobian
        * aerosol.scale_height_m
        * math.exp(-top_m / aerosol.scale_height_m)
        / (r_top - area_radius) ** 2
    )
    upper = (
        source.amplitude.value
        * angular_max
        * (molecular * ray_factor + aerosol_length * aer_factor)
    )
    # Marge aritmètic conservador, sense pretensió d'aritmètica d'intervals.
    upper = math.nextafter(upper * (1 + 128 * math.ulp(1.0)), math.inf)
    return ConditionalTailBound(
        upper, molecular, aerosol_length, envelope, jacobian, pressure_at_top_pa, top_m
    )
