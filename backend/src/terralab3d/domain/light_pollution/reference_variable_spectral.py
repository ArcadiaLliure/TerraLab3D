"""SG-REF espectral de perfils variables: NumPy/GL i GK21 independents.

Les columnes es calculen amb GL compost sobre els talls propis de SG-REF.
No importa SpectralOperator, GK15, mostreig/travessa ni transmissions runtime.
L'àrea amb terreny usa franges de ReferenceTerrain, no retalls runtime.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import roots_legendre

from .optical_field import OpticalField
from .reference_single_scattering import (
    ReferenceB1Result,
    _ReferenceMedium,
    _basis,
    _position,
    _phase,
)
from .reference_terrain import ReferenceTerrain
from .source_model import (
    AzimuthalAngularEmissionProfile,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)
from .spectral_transport import SpectralTransportConfiguration
from .terrain_visibility import TerrainSurface


class _SpectralMedium:
    def __init__(self, source, field, config, spectral_order, path_order, checkpoint):
        self.field, self.config, self.checkpoint = field, config, checkpoint
        self.path = _ReferenceMedium(
            field, config.monochromatic().band, path_order, checkpoint, config.gas
        )
        lo, hi = config.wavelength_start_nm, config.wavelength_end_nm
        knots = sorted(
            {lo, hi}
            | {w for w in source.spectrum.wavelengths_nm if lo < w < hi}
            | {w for r in config.responses for w in r.wavelengths_nm if lo < w < hi}
            | {
                w
                for g in (config.gas.luts if config.gas else ())
                for w in g.wavelengths_nm
                if lo < w < hi
            }
        )
        left, right = np.asarray(knots[:-1]), np.asarray(knots[1:])
        x, w = roots_legendre(spectral_order)
        self.waves = (
            (left + right)[:, None] / 2 + (right - left)[:, None] / 2 * x
        ).ravel()
        self.weights = (
            (right - left)[:, None]
            / 2
            * np.broadcast_to(w, (len(left), spectral_order))
        ).ravel()
        self.weights *= (
            np.interp(
                self.waves,
                source.spectrum.wavelengths_nm,
                source.spectrum.relative_power,
                left=0,
                right=0,
            )
            / source.spectrum.raw_integral_nm
            * source.amplitude.value
        )
        for response in config.responses:
            self.weights *= np.interp(
                self.waves, response.wavelengths_nm, response.values, left=0, right=0
            )
        # Chance–Spurr: implementació espectral pròpia de la referència.
        z = (1000 / self.waves) ** 2
        self.sigma = 3.9993e-32 * z**2 / (1 - 0.01069 * z - 0.00006681 * z**2)
        nr = (0.7041 + 315.90 / (157.39 - z) + 8.4127 / (50.429 - z)) * 1e-4
        king = (
            self.sigma
            * 3
            * 2.686763e25**2
            * (self.waves * 1e-9) ** 4
            / (32 * np.pi**3 * nr**2)
        )
        self.rho = 6 * (king - 1) / (7 * king + 3)
        self.aerosols = {a.reference.tile_id: a for a in config.aerosols}
        self.aer_ext = {
            key: a.reference.extinction_per_m
            * (self.waves / a.reference_wavelength_nm) ** (-a.angstrom_exponent)
            for key, a in self.aerosols.items()
        }
        self.gas_matrices = [
            np.array(
                [
                    np.interp(self.waves, g.wavelengths_nm, row)
                    for row in g.cross_sections_m2
                ]
            )
            for g in (config.gas.luts if config.gas else ())
        ]

    def samples(self, points):
        local = (points - self.path.origin) @ self.path.frame.T
        heights = np.linalg.norm(points, axis=1) - self.field.radius_m
        coverage = np.zeros(len(points), dtype=int)
        result = []
        for tile in self.field.tiles:
            b = tile.bounds
            mask = (
                (local[:, 0] >= b.east_min_m)
                & (local[:, 0] < b.east_max_m)
                & (local[:, 1] >= b.north_min_m)
                & (local[:, 1] < b.north_max_m)
            )
            coverage += mask
            if not np.any(mask):
                continue
            p = tile.profile
            h = heights[mask]
            if np.any(h < p.heights_m[0] - 1e-7) or np.any(h > p.heights_m[-1] + 1e-7):
                raise ValueError("SG-REF espectral fora del perfil")
            h = np.clip(h, p.heights_m[0], p.heights_m[-1])
            temperature = np.interp(h, p.heights_m, p.temperature_k)
            density = np.exp(np.interp(h, p.heights_m, np.log(p.pressure_pa))) / (
                1.380649e-23 * temperature
            )
            result.append((tile, mask, h, temperature, density))
        if np.any(coverage != 1):
            raise ValueError("SG-REF espectral sense cobertura lateral única")
        return result

    def depth(self, start, end):
        self.checkpoint()
        length = float(np.linalg.norm(end - start))
        if length <= 0:
            return np.zeros(len(self.waves))
        direction = (end - start) / length
        cuts = np.asarray(self.path.cuts(start, direction, length))
        a, b = cuts[:-1], cuts[1:]
        distances = ((a + b)[:, None] / 2 + (b - a)[:, None] / 2 * self.path.x).ravel()
        weights = (
            (b - a)[:, None]
            / 2
            * np.broadcast_to(self.path.w, (len(a), len(self.path.w)))
        ).ravel()
        points = start + distances[:, None] * direction
        tau = np.zeros(len(self.waves))
        for tile, mask, h, temperature, density in self.samples(points):
            self.checkpoint()
            w = weights[mask]
            tau += float(w @ density) * self.sigma
            aerosol = self.aerosols[tile.tile_id].reference
            shape = (
                np.ones(len(h))
                if aerosol.scale_height_m is None
                else np.exp(-h / aerosol.scale_height_m)
            )
            tau += float(w @ shape) * self.aer_ext[tile.tile_id]
            for j, lut in enumerate(self.config.gas.luts if self.config.gas else ()):
                profile = next(
                    p
                    for p in self.config.gas.profiles
                    if p.tile_id == tile.tile_id and p.species == lut.species
                )
                if (
                    np.any(temperature < lut.temperatures_k[0])
                    or np.any(temperature > lut.temperatures_k[-1])
                    or h.min() < profile.heights_m[0] - 1e-7
                    or h.max() > profile.heights_m[-1] + 1e-7
                ):
                    raise ValueError("SG-REF: gas fora de cobertura")
                population = (
                    w
                    * density
                    * np.interp(h, profile.heights_m, profile.mole_fractions)
                )
                temperatures = np.asarray(lut.temperatures_k)
                index = np.clip(
                    np.searchsorted(temperatures, temperature, side="right") - 1,
                    0,
                    len(temperatures) - 2,
                )
                fraction = (temperature - temperatures[index]) / (
                    temperatures[index + 1] - temperatures[index]
                )
                columns = np.bincount(
                    index,
                    weights=population * (1 - fraction),
                    minlength=len(temperatures),
                ) + np.bincount(
                    index + 1,
                    weights=population * fraction,
                    minlength=len(temperatures),
                )
                tau += columns @ self.gas_matrices[j]
        return tau


def solve_reference_variable_spectral(
    source: SourceModel,
    observer: GeodeticPosition,
    field: OpticalField,
    config: SpectralTransportConfiguration,
    azimuth_deg: float,
    elevation_deg: float,
    top_m: float,
    *,
    spectral_order: int = 4,
    path_order: int = 8,
    area_order: int = 4,
    relative_tolerance: float = 1e-10,
    terrain: TerrainSurface | None = None,
    checkpoint: Callable[[], None] = lambda: None,
) -> ReferenceB1Result:
    if not 0.5 <= elevation_deg <= 90 or not 0 <= observer.altitude_m < top_m:
        raise ValueError("Direcció SG-REF fora del domini")
    medium = _SpectralMedium(
        source, field, config, spectral_order, path_order, checkpoint
    )
    origin = _position(observer, field.radius_m)
    az, el = np.radians([azimuth_deg, elevation_deg])
    direction = np.array(
        [np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)]
    ) @ _basis(observer)
    q = float(origin @ direction)
    delta = (top_m - observer.altitude_m) * (
        2 * field.radius_m + top_m + observer.altitude_m
    )
    length = float(delta / (np.sqrt(q * q + delta) + q))
    terrain_ref = ReferenceTerrain(terrain) if terrain else None
    if terrain_ref:
        length = terrain_ref.clip(origin, direction, length)
    if length == 0:
        return ReferenceB1Result(
            0.0, 0.0, 0, path_order, area_order, "sg-ref-variable-spectral-GL-v1"
        )
    geometry = source.geometry
    point_source = isinstance(geometry, PointSourceGeometry)
    position = geometry.position if point_source else geometry.center
    center, basis = _position(position, field.radius_m), _basis(position)
    corners = None
    axis_u, axis_v = basis[0], basis[1]
    if point_source:
        nodes, weights = center[None, :], np.ones(1)
    else:
        angle = np.radians(geometry.orientation_deg)
        axis_u = np.cos(angle) * basis[0] - np.sin(angle) * basis[1]
        axis_v = np.sin(angle) * basis[0] + np.cos(angle) * basis[1]
        corners = np.array(
            [
                center
                + u * geometry.east_width_m / 2 * axis_u
                + v * geometry.north_height_m / 2 * axis_v
                for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]
        )
        x, w = roots_legendre(area_order)
        nodes = np.array(
            [
                center
                + u * geometry.east_width_m / 2 * axis_u
                + v * geometry.north_height_m / 2 * axis_v
                for u in x
                for v in x
            ]
        )
        weights = np.outer(w, w).ravel() / 4
    breaks = set(medium.path.cuts(origin, direction, length))
    offset = center - origin
    closest = float(offset @ direction)
    perpendicular = float(np.linalg.norm(offset - closest * direction))
    breaks.update(
        s
        for s in (closest - perpendicular, closest, closest + perpendicular)
        if 0 < s < length
    )
    den = float(direction @ basis[2])
    if den:
        s = float(offset @ basis[2]) / den
        if 0 < s < length:
            breaks.add(s)
    if terrain_ref:
        breaks.update(
            terrain_ref.cuts(center, origin, direction, length)
            if point_source
            else terrain_ref.area_cuts(corners, origin, direction, length)
        )
    angular = source.angular
    axial = (
        angular.axial
        if isinstance(angular, AzimuthalAngularEmissionProfile)
        else angular
    )

    def value(s):
        checkpoint()
        point = origin + s * direction
        tile, _, height, _, density = medium.samples(point[None, :])[0]
        aer = medium.aerosols[tile.tile_id].reference
        local_aer = medium.aer_ext[tile.tile_id] * (
            1.0
            if aer.scale_height_m is None
            else np.exp(-height[0] / aer.scale_height_m)
        )
        tau_observer = medium.depth(origin, point)
        active_nodes, active_weights = nodes, weights
        if terrain_ref and not point_source:
            assert not isinstance(geometry, PointSourceGeometry)
            active_nodes, active_weights = terrain_ref.area_nodes(
                point,
                center,
                axis_u,
                axis_v,
                geometry.east_width_m,
                geometry.north_height_m,
                area_order,
            )
        terms = []
        for node, weight in zip(active_nodes, active_weights):
            checkpoint()
            if terrain_ref and point_source and not terrain_ref.visible(node, point):
                continue
            vector = point - node
            r = float(np.linalg.norm(vector))
            if r < 1e-7:
                raise ValueError("Singularitat SG-REF espectral")
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
            phase_r = (
                3
                / (8 * np.pi)
                * ((1 + medium.rho) + (1 - medium.rho) * mu * mu)
                / (2 + medium.rho)
            )
            gamma = (
                density[0] * medium.sigma * phase_r
                + local_aer * aer.single_scattering_albedo * _phase(aer.phase, mu)
            )
            spectral = (
                medium.weights
                * gamma
                * np.exp(-tau_observer - medium.depth(node, point))
            )
            terms.append(float(spectral.sum()) * emission * float(weight) / (r * r))
        return math.fsum(terms)

    result, error, info = quad_vec(
        value,
        0.0,
        length,
        points=sorted(s for s in breaks if 0 < s < length),
        epsrel=relative_tolerance,
        epsabs=1e-34,
        quadrature="gk21",
        norm="max",
        limit=20000,
        full_output=True,
    )
    if not info.success or not math.isfinite(float(result)) or float(result) < 0:
        raise ValueError("SG-REF espectral variable sense convergència")
    return ReferenceB1Result(
        float(result),
        float(error),
        int(info.neval),
        path_order,
        area_order,
        "sg-ref-variable-spectral-GL-v1",
    )
