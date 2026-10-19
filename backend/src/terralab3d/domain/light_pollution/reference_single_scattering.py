"""SG-REF B1: geometria NumPy, GK21 LOS i GL de trajectes/àrea independents.

Comparteix dades i SourceModel; no importa el kernel, mostreig/travessa,
fases ni integrador de transmissió del runtime. Sense gate de producció.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import quad_vec
from scipy.special import roots_legendre

from .optical_field import OpticalField, OpticalCoverageError
from .gas_absorption import GasAbsorptionModel
from .scattering import PhaseFunction, ScatteringBand
from .reference_terrain import ReferenceTerrain
from .terrain_visibility import TerrainSurface
from .source_model import (
    AzimuthalAngularEmissionProfile,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)

Array = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class ReferenceB1Result:
    value: float
    los_error_estimate: float
    evaluations: int
    path_order: int
    area_order: int
    revision: str = "sg-ref-spherical-monochromatic-v1"


class ReferenceB1CancelledError(Exception):
    """Cancel·lació offline sense resultat publicable."""


def _basis(pos: GeodeticPosition) -> Array:
    p, longitude = np.radians([pos.latitude_deg, pos.longitude_deg])
    return np.array(
        [
            [-np.sin(longitude), np.cos(longitude), 0],
            [-np.sin(p) * np.cos(longitude), -np.sin(p) * np.sin(longitude), np.cos(p)],
            [np.cos(p) * np.cos(longitude), np.cos(p) * np.sin(longitude), np.sin(p)],
        ]
    )


def _position(pos: GeodeticPosition, radius: float) -> Array:
    return (radius + pos.altitude_m) * _basis(pos)[2]


def _phase(phase: PhaseFunction, mu: float) -> float:
    # Expressions independents, amb ρ de la convenció Chance–Spurr eq. 2.
    mu = float(np.clip(mu, -1, 1))
    if phase.kind == "isotropic":
        return 0.25 / np.pi
    if phase.kind == "rayleigh":
        rho = 2 * phase.depolarization_delta / (1 + phase.depolarization_delta)
        return float(3 / (8 * np.pi) * ((1 + rho) + (1 - rho) * mu**2) / (2 + rho))
    if phase.kind == "hg_fallback":
        g = phase.asymmetry
        return float((1 - g**2) / (4 * np.pi * (1 + g**2 - 2 * g * mu) ** 1.5))
    return float(
        np.interp(mu, phase.cosines, phase.relative_values)
        / (2 * np.pi * np.trapezoid(phase.relative_values, phase.cosines))
    )


class _ReferenceMedium:
    def __init__(
        self,
        field: OpticalField,
        band: ScatteringBand,
        order: int,
        checkpoint: Callable[[], None],
        gas: GasAbsorptionModel | None = None,
    ):
        self.field, self.band, self.checkpoint = field, band, checkpoint
        self.frame = _basis(field.origin)
        self.origin = _position(field.origin, field.radius_m)
        self.x, self.w = roots_legendre(order)
        self.gas = gas
        self.gas_sigma = tuple(
            np.array(
                [
                    np.interp(band.wavelength_nm, lut.wavelengths_nm, row)
                    for row in lut.cross_sections_m2
                ]
            )
            for lut in (gas.luts if gas else ())
        )

    def gas_extinction(self, point: Array, tile) -> float:
        if self.gas is None:
            return 0.0
        h = float(np.linalg.norm(point) - self.field.radius_m)
        profile = tile.profile
        temperature = float(np.interp(h, profile.heights_m, profile.temperature_k))
        density = float(
            np.exp(np.interp(h, profile.heights_m, np.log(profile.pressure_pa)))
            / (1.380649e-23 * temperature)
        )
        result = 0.0
        for lut, sigma in zip(self.gas.luts, self.gas_sigma):
            p = next(
                p
                for p in self.gas.profiles
                if (p.tile_id, p.species) == (tile.tile_id, lut.species)
            )
            if (
                not lut.temperatures_k[0] <= temperature <= lut.temperatures_k[-1]
                or not p.heights_m[0] - 1e-7 <= h <= p.heights_m[-1] + 1e-7
            ):
                raise ValueError("Gas fora del domini SG-REF")
            result += (
                density
                * float(np.interp(h, p.heights_m, p.mole_fractions))
                * float(np.interp(temperature, lut.temperatures_k, sigma))
            )
        return result

    def state(self, point: Array):
        local = self.frame @ (point - self.origin)
        matches = [
            t
            for t in self.field.tiles
            if t.bounds.east_min_m <= local[0] < t.bounds.east_max_m
            and t.bounds.north_min_m <= local[1] < t.bounds.north_max_m
        ]
        if len(matches) != 1:
            raise OpticalCoverageError("SG-REF B1 sense cobertura lateral única")
        tile = matches[0]
        height = float(np.linalg.norm(point) - self.field.radius_m)
        profile = tile.profile
        if not profile.heights_m[0] - 1e-7 <= height <= profile.heights_m[-1] + 1e-7:
            raise OpticalCoverageError("SG-REF B1 fora del perfil vertical")
        n = float(
            np.exp(np.interp(height, profile.heights_m, np.log(profile.pressure_pa)))
            / (
                1.380649e-23
                * np.interp(height, profile.heights_m, profile.temperature_k)
            )
        )
        aerosol = next(a for a in self.band.aerosols if a.tile_id == tile.tile_id)
        ext = aerosol.extinction_per_m * (
            np.exp(-height / aerosol.scale_height_m)
            if aerosol.scale_height_m is not None
            else 1
        )
        return tile, n * self.band.rayleigh_cross_section_m2, float(ext), aerosol

    def cuts(self, start: Array, direction: Array, length: float) -> list[float]:
        local = self.frame @ (start - self.origin)
        d = self.frame @ direction
        d[np.abs(d) < 8 * np.finfo(float).eps] = 0
        points = {0.0, length}
        for tile in self.field.tiles:
            self.checkpoint()
            b = tile.bounds
            for axis, low, high in (
                (0, b.east_min_m, b.east_max_m),
                (1, b.north_min_m, b.north_max_m),
            ):
                if d[axis] != 0:
                    for bound in (low, high):
                        s = float((bound - local[axis]) / d[axis])
                        if 0 < s < length:
                            points.add(s)
            closest = -float(start @ direction)
            perpendicular2 = float(np.sum((start + closest * direction) ** 2))
            heights = list(tile.profile.heights_m)
            if self.gas is not None:
                temperatures = np.unique([t for lut in self.gas.luts for t in lut.temperatures_k])
                p = tile.profile
                for i in range(len(p.heights_m) - 1):
                    ta, tb = p.temperature_k[i:i + 2]
                    chosen = temperatures[(temperatures > min(ta, tb)) & (temperatures < max(ta, tb))]
                    if len(chosen):
                        x, y = ((ta, tb), p.heights_m[i:i + 2]) if ta < tb else ((tb, ta), p.heights_m[i:i + 2][::-1])
                        heights.extend(float(z) for z in np.interp(chosen, x, y))
            for h in heights:
                disc = (self.field.radius_m + h) ** 2 - perpendicular2
                if disc >= 0:
                    for s in (closest - np.sqrt(disc), closest + np.sqrt(disc)):
                        if 0 < s < length:
                            points.add(float(s))
        if len(points) > 10000:
            raise ValueError("Pressupost SG-REF B1 excedit")
        return sorted(points)

    def tau(self, start: Array, end: Array) -> float:
        self.checkpoint()
        length = float(np.linalg.norm(end - start))
        if length <= 0:
            raise ValueError("Trajecte de referència buit")
        direction = (end - start) / length
        cuts = self.cuts(start, direction, length)
        terms = []
        for a, b in zip(cuts, cuts[1:]):
            tile, molecular, ext, aer = self.state(start + (a + b) / 2 * direction)
            p = tile.profile
            if (
                len(set(p.pressure_pa)) == 1
                and len(set(p.temperature_k)) == 1
                and aer.scale_height_m is None
                and (
                    self.gas is None
                    or all(len(set(p.mole_fractions)) == 1 for p in self.gas.profiles)
                )
            ):
                terms.append(
                    (b - a)
                    * (
                        molecular
                        + ext
                        + self.gas_extinction(start + (a + b) / 2 * direction, tile)
                    )
                )
            else:
                values = []
                for s in (a + b) / 2 + (b - a) / 2 * self.x:
                    self.checkpoint()
                    t, m, e, _ = self.state(start + s * direction)
                    values.append(m + e + self.gas_extinction(start + s * direction, t))
                terms.append((b - a) / 2 * float(self.w @ np.array(values)))
        return math.fsum(terms)


def solve_reference_b1(
    source: SourceModel,
    observer: GeodeticPosition,
    azimuth_deg: float,
    elevation_deg: float,
    field: OpticalField,
    band: ScatteringBand,
    top_m: float,
    *,
    relative_tolerance: float = 1e-9,
    path_order: int = 32,
    area_order: int = 8,
    cancelled: Callable[[], bool] | None = None,
    aerosol_phase_evaluator: Callable[[float], float] | None = None,
    gas: GasAbsorptionModel | None = None,
    terrain: TerrainSurface | None = None,
) -> ReferenceB1Result:
    def checkpoint():
        if cancelled is not None and cancelled():
            raise ReferenceB1CancelledError("SG-REF B1 cancel·lat")

    checkpoint()
    if not 0.5 <= elevation_deg <= 90 or not 0 <= observer.altitude_m < top_m:
        raise ValueError("Direcció/observador de referència no admès")
    origin = _position(observer, field.radius_m)
    az, el = np.radians([azimuth_deg, elevation_deg])
    direction = np.array(
        [np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)]
    ) @ _basis(observer)
    q = float(origin @ direction)
    delta = (top_m - observer.altitude_m) * (
        2 * field.radius_m + top_m + observer.altitude_m
    )
    length = delta / (np.sqrt(q * q + delta) + q)
    terrain_ref = ReferenceTerrain(terrain) if terrain else None
    if terrain_ref:
        length = terrain_ref.clip(origin, direction, float(length))
        if length == 0:
            return ReferenceB1Result(
                0.0,
                0.0,
                0,
                path_order,
                area_order,
                "sg-ref-opaque-terrain-zero-domain-v1",
            )
    medium = _ReferenceMedium(field, band, path_order, checkpoint, gas)
    geometry = source.geometry
    pos = (
        geometry.position
        if isinstance(geometry, PointSourceGeometry)
        else geometry.center
    )
    basis = _basis(pos)
    center = _position(pos, field.radius_m)
    if isinstance(geometry, PointSourceGeometry):
        nodes, weights = center[None, :], np.ones(1)
    else:
        x, w = roots_legendre(area_order)
        a, b = np.meshgrid(
            x * geometry.east_width_m / 2,
            x * geometry.north_height_m / 2,
            indexing="ij",
        )
        angle = np.radians(geometry.orientation_deg)
        local = np.column_stack(
            (
                (a * np.cos(angle) + b * np.sin(angle)).ravel(),
                (-a * np.sin(angle) + b * np.cos(angle)).ravel(),
                np.zeros(a.size),
            )
        )
        nodes, weights = center + local @ basis, np.outer(w, w).ravel() / 4
    breaks = set(medium.cuts(origin, direction, float(length)))
    offset = center - origin
    closest = float(offset @ direction)
    perpendicular = float(np.linalg.norm(offset - closest * direction))
    breaks.update(
        s
        for s in (closest - perpendicular, closest, closest + perpendicular)
        if 0 < s < length
    )
    normal = float(direction @ basis[2])
    if normal != 0:
        s = float(offset @ basis[2]) / normal
        if 0 < s < length:
            breaks.add(s)
    if terrain_ref:
        if isinstance(geometry, PointSourceGeometry):
            breaks.update(terrain_ref.cuts(center, origin, direction, float(length)))
        else:
            angle = np.radians(geometry.orientation_deg)
            uaxis = np.cos(angle) * basis[0] - np.sin(angle) * basis[1]
            vaxis = np.sin(angle) * basis[0] + np.cos(angle) * basis[1]
            corners = np.array(
                [
                    center
                    + u * geometry.east_width_m / 2 * uaxis
                    + v * geometry.north_height_m / 2 * vaxis
                    for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))
                ]
            )
            breaks.update(
                terrain_ref.area_cuts(corners, origin, direction, float(length))
            )
    flux = source.spectral_flux(band.wavelength_nm).value
    angular = source.angular
    axial = (
        angular.axial
        if isinstance(angular, AzimuthalAngularEmissionProfile)
        else angular
    )

    def integrand(s: float):
        checkpoint()
        point = origin + s * direction
        _, rayleigh, _, aerosol = medium.state(point)
        total = []
        tau_o = medium.tau(origin, point)
        active_nodes, active_weights = nodes, weights
        if terrain_ref and not isinstance(geometry, PointSourceGeometry):
            angle = np.radians(geometry.orientation_deg)
            uaxis = np.cos(angle) * basis[0] - np.sin(angle) * basis[1]
            vaxis = np.sin(angle) * basis[0] + np.cos(angle) * basis[1]
            active_nodes, active_weights = terrain_ref.area_nodes(
                point,
                center,
                uaxis,
                vaxis,
                geometry.east_width_m,
                geometry.north_height_m,
                area_order,
            )
        for node, weight in zip(active_nodes, active_weights):
            if (
                terrain_ref
                and isinstance(geometry, PointSourceGeometry)
                and not terrain_ref.visible(node, point)
            ):
                continue
            vector = point - node
            r = float(np.linalg.norm(vector))
            if r < 1e-7:
                raise ValueError("Singularitat SG-REF B1")
            incoming = vector / r
            vertical = float(incoming @ basis[2])
            if vertical < 0:
                continue
            theta = float(np.degrees(np.arccos(np.clip(vertical, -1, 1))))
            density = float(
                np.interp(theta, axial.zenith_deg, axial.relative_intensity)
                / axial.solid_angle_integral
            )
            if isinstance(angular, AzimuthalAngularEmissionProfile):
                azimuth = float(
                    np.degrees(np.arctan2(incoming @ basis[0], incoming @ basis[1]))
                    % 360
                )
                density *= float(
                    np.interp(azimuth, angular.azimuth_deg, angular.relative_azimuth)
                    / angular.azimuth_mean
                )
            mu = -float(incoming @ direction)
            height = float(np.linalg.norm(point) - field.radius_m)
            aer_ext = aerosol.extinction_per_m * (
                np.exp(-height / aerosol.scale_height_m)
                if aerosol.scale_height_m
                else 1
            )
            gamma = rayleigh * _phase(
                band.rayleigh_phase, mu
            ) + aer_ext * aerosol.single_scattering_albedo * (
                aerosol_phase_evaluator(mu)
                if aerosol_phase_evaluator is not None
                else _phase(aerosol.phase, mu)
            )
            total.append(
                weight
                * flux
                * density
                * gamma
                / r**2
                * np.exp(-tau_o - medium.tau(node, point))
            )
        return float(sum(total))

    value, error, info = quad_vec(
        integrand,
        0,
        float(length),
        points=sorted(breaks)[1:-1],
        epsrel=relative_tolerance,
        epsabs=1e-26,
        quadrature="gk21",
        norm="max",
        workers=1,
        limit=10000,
        full_output=True,
    )
    if (
        not info.success
        or not math.isfinite(float(value))
        or float(value) < 0
        or not math.isfinite(float(error))
    ):
        raise ValueError("SG-REF B1 sense convergència")
    return ReferenceB1Result(
        float(value), float(error), int(info.neval), path_order, area_order
    )
