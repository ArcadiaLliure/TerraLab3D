"""SG-REF espectral homogeni: GL fi + GK21, geometria NumPy independent.

Domini explícit d'una sola composició/tile homogeni. Les columnes variables
es contrasten separadament amb SG-REF monocromàtic i GL de trajectes.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import roots_legendre

from .reference_terrain import ReferenceTerrain
from .terrain_visibility import TerrainSurface
from .optical_field import OpticalField
from .reference_single_scattering import ReferenceB1Result, _basis, _position, _phase
from .source_model import (
    AzimuthalAngularEmissionProfile,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)
from .spectral_transport import SpectralTransportConfiguration


def solve_reference_spectral(
    source: SourceModel,
    observer: GeodeticPosition,
    field: OpticalField,
    config: SpectralTransportConfiguration,
    azimuth_deg: float,
    elevation_deg: float,
    top_m: float,
    *,
    spectral_order: int = 8,
    area_order: int = 8,
    relative_tolerance: float = 1e-9,
    terrain: TerrainSurface | None = None,
) -> ReferenceB1Result:
    if len(field.tiles) != 1:
        raise ValueError("SG-REF espectral homogeni requereix un sol tile")
    tile = field.tiles[0]
    profile = tile.profile
    aerosol = config.aerosols[0]
    if (
        len(set(profile.pressure_pa)) != 1
        or len(set(profile.temperature_k)) != 1
        or aerosol.reference.scale_height_m is not None
    ):
        raise ValueError("SG-REF espectral homogeni no admet perfils variables")
    if (
        not 0.5 <= elevation_deg <= 90
        or not 0 <= observer.altitude_m < top_m <= profile.heights_m[-1]
    ):
        raise ValueError("LOS fora del domini SG-REF espectral")
    if config.gas and any(len(set(p.mole_fractions)) != 1 for p in config.gas.profiles):
        raise ValueError("SG-REF espectral homogeni no admet composició variable")
    lo, hi = config.wavelength_start_nm, config.wavelength_end_nm
    knots = sorted(
        {lo, hi}
        | {w for w in source.spectrum.wavelengths_nm if lo < w < hi}
        | {w for r in config.responses for w in r.wavelengths_nm if lo < w < hi}
        | {
            w
            for lut in (config.gas.luts if config.gas else ())
            for w in lut.wavelengths_nm
            if lo < w < hi
        }
    )
    a, b = np.array(knots[:-1]), np.array(knots[1:])
    x, weights = roots_legendre(spectral_order)
    waves = ((a + b)[:, None] / 2 + (b - a)[:, None] / 2 * x).ravel()
    spectral_weights = (
        (b - a)[:, None] / 2 * np.broadcast_to(weights, (len(a), spectral_order))
    ).ravel()
    spectral_weights *= (
        np.interp(
            waves,
            source.spectrum.wavelengths_nm,
            source.spectrum.relative_power,
            left=0,
            right=0,
        )
        / source.spectrum.raw_integral_nm
        * source.amplitude.value
    )
    for response in config.responses:
        spectral_weights *= np.interp(
            waves, response.wavelengths_nm, response.values, left=0, right=0
        )
    z = (1000 / waves) ** 2
    sigma = 3.9993e-32 * z**2 / (1 - 0.01069 * z - 0.00006681 * z**2)
    nr = (0.7041 + 315.90 / (157.39 - z) + 8.4127 / (50.429 - z)) * 1e-4
    king = sigma * 3 * 2.686763e25**2 * (waves * 1e-9) ** 4 / (32 * np.pi**3 * nr**2)
    rho = 6 * (king - 1) / (7 * king + 3)
    temperature = profile.temperature_k[0]
    density = profile.pressure_pa[0] / (1.380649e-23 * temperature)
    aer = aerosol.reference.extinction_per_m * (
        waves / aerosol.reference_wavelength_nm
    ) ** (-aerosol.angstrom_exponent)
    extinction = density * sigma + aer
    if config.gas:
        for lut in config.gas.luts:
            p = next(
                p
                for p in config.gas.profiles
                if (p.tile_id, p.species) == (tile.tile_id, lut.species)
            )
            if not lut.temperatures_k[0] <= temperature <= lut.temperatures_k[-1]:
                raise ValueError("Temperatura SG-REF fora de LUT")
            i = min(
                int(np.searchsorted(lut.temperatures_k, temperature, side="right")) - 1,
                len(lut.temperatures_k) - 2,
            )
            f = (temperature - lut.temperatures_k[i]) / (
                lut.temperatures_k[i + 1] - lut.temperatures_k[i]
            )
            sigma_gas = (1 - f) * np.interp(
                waves, lut.wavelengths_nm, lut.cross_sections_m2[i]
            ) + f * np.interp(waves, lut.wavelengths_nm, lut.cross_sections_m2[i + 1])
            extinction += density * p.mole_fractions[0] * sigma_gas
    origin = _position(observer, field.radius_m)
    az, el = np.radians([azimuth_deg, elevation_deg])
    direction = np.array(
        [np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)]
    ) @ _basis(observer)
    projection = float(origin @ direction)
    delta = (top_m - observer.altitude_m) * (
        2 * field.radius_m + top_m + observer.altitude_m
    )
    length = delta / (np.sqrt(projection**2 + delta) + projection)
    terrain_ref = ReferenceTerrain(terrain) if terrain else None
    if terrain_ref:
        length = terrain_ref.clip(origin, direction, float(length))
        if length == 0:
            return ReferenceB1Result(
                0.0,
                0.0,
                0,
                spectral_order,
                area_order,
                "sg-ref-opaque-terrain-zero-domain-v1",
            )
    geo = source.geometry
    position = geo.position if isinstance(geo, PointSourceGeometry) else geo.center
    basis, center = _basis(position), _position(position, field.radius_m)
    if isinstance(geo, PointSourceGeometry):
        nodes, areas = center[None, :], np.ones(1)
    else:
        u, v = roots_legendre(area_order)
        east, north = np.meshgrid(
            u * geo.east_width_m / 2, u * geo.north_height_m / 2, indexing="ij"
        )
        angle = np.radians(geo.orientation_deg)
        local = np.column_stack(
            (
                (east * np.cos(angle) + north * np.sin(angle)).ravel(),
                (-east * np.sin(angle) + north * np.cos(angle)).ravel(),
                np.zeros(east.size),
            )
        )
        nodes, areas = center + local @ basis, np.outer(v, v).ravel() / 4
    angular = source.angular
    axial = (
        angular.axial
        if isinstance(angular, AzimuthalAngularEmissionProfile)
        else angular
    )
    offset = center - origin
    closest = float(offset @ direction)
    perpendicular = float(np.linalg.norm(offset - closest * direction))
    breaks = {
        s
        for s in (closest - perpendicular, closest, closest + perpendicular)
        if 0 < s < length
    }
    denominator = float(direction @ basis[2])
    if denominator:
        s = float(offset @ basis[2]) / denominator
        if 0 < s < length:
            breaks.add(s)

    if terrain_ref:
        if isinstance(geo, PointSourceGeometry):
            breaks.update(terrain_ref.cuts(center, origin, direction, float(length)))
        else:
            angle = np.radians(geo.orientation_deg)
            uaxis = np.cos(angle) * basis[0] - np.sin(angle) * basis[1]
            vaxis = np.sin(angle) * basis[0] + np.cos(angle) * basis[1]
            corners = np.array(
                [
                    center
                    + u * geo.east_width_m / 2 * uaxis
                    + v * geo.north_height_m / 2 * vaxis
                    for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))
                ]
            )
            breaks.update(
                terrain_ref.area_cuts(corners, origin, direction, float(length))
            )

    def value(s):
        point = origin + s * direction
        terms = []
        active_nodes, active_areas = nodes, areas
        if terrain_ref and not isinstance(geo, PointSourceGeometry):
            angle = np.radians(geo.orientation_deg)
            uaxis = np.cos(angle) * basis[0] - np.sin(angle) * basis[1]
            vaxis = np.sin(angle) * basis[0] + np.cos(angle) * basis[1]
            active_nodes, active_areas = terrain_ref.area_nodes(
                point,
                center,
                uaxis,
                vaxis,
                geo.east_width_m,
                geo.north_height_m,
                area_order,
            )
        for node, area in zip(active_nodes, active_areas):
            if (
                terrain_ref
                and isinstance(geo, PointSourceGeometry)
                and not terrain_ref.visible(node, point)
            ):
                continue
            vector = point - node
            r = float(np.linalg.norm(vector))
            incoming = vector / r
            up = float(incoming @ basis[2])
            if up < 0:
                continue
            theta = float(np.degrees(np.arccos(np.clip(up, -1, 1))))
            emission = float(
                np.interp(theta, axial.zenith_deg, axial.relative_intensity)
                / axial.solid_angle_integral
            )
            if isinstance(angular, AzimuthalAngularEmissionProfile):
                azimuth = float(
                    np.degrees(np.arctan2(incoming @ basis[0], incoming @ basis[1]))
                    % 360
                )
                emission *= float(
                    np.interp(azimuth, angular.azimuth_deg, angular.relative_azimuth)
                    / angular.azimuth_mean
                )
            mu = -float(incoming @ direction)
            phase = 3 / (8 * np.pi) * ((1 + rho) + (1 - rho) * mu**2) / (2 + rho)
            scattering = (
                density * sigma * phase
                + aer
                * aerosol.reference.single_scattering_albedo
                * _phase(aerosol.reference.phase, mu)
            )
            spectral = spectral_weights * scattering * np.exp(-(s + r) * extinction)
            terms.append(float(spectral.sum()) * emission * float(area) / r**2)
        return math.fsum(terms)

    result, error, info = quad_vec(
        value,
        0.0,
        float(length),
        points=sorted(breaks),
        epsrel=relative_tolerance,
        epsabs=1e-26,
        quadrature="gk21",
        norm="max",
        full_output=True,
    )
    if not info.success:
        raise ValueError("SG-REF espectral sense convergència")
    return ReferenceB1Result(
        float(result),
        float(error),
        int(info.neval),
        spectral_order,
        area_order,
        "sg-ref-homogeneous-spectral-v1",
    )
