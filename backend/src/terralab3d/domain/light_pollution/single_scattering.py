"""Integrand B1 directe; quadratura d'àrea, intensitat i dos trajectes òptics."""

from __future__ import annotations

import math
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Callable, cast

import numpy as np

from .geometric_transport import RayGeometry, SphericalFrame, Vector3, dot
from .optical_field import OpticalDependency, OpticalField, OpticalState
from .optical_paths import PathWork, optical_depth
from .scattering import ScatteringConfiguration
from .source_model import PointSourceGeometry, SourceModel
from .transport_profiling import TransportProfiler
from .terrain_visibility import (
    TerrainVisibility,
    VisibilityPlan,
    visible_area_nodes,
    cross,
    sub,
)


@dataclass(frozen=True, slots=True)
class TransportDiagnostics:
    phase_evaluations: int
    transmission_segments: int
    transmission_nodes: int
    max_one_leg_optical_depth_error: float
    source_nodes: int


class SingleScatteringTransport:
    def __init__(
        self,
        source: SourceModel,
        field: OpticalField,
        config: ScatteringConfiguration,
        ray: RayGeometry,
        max_segments: int,
        checkpoint: Callable[[], None],
        dependencies: set[OpticalDependency],
        profiler: TransportProfiler | None = None,
    ) -> None:
        self.source, self.field, self.config, self.ray = source, field, config, ray
        self.profiler = profiler
        self.max_segments, self.checkpoint, self.dependencies = (
            max_segments,
            checkpoint,
            dependencies,
        )
        geometry = source.geometry
        position = (
            geometry.position
            if isinstance(geometry, PointSourceGeometry)
            else geometry.center
        )
        frame = SphericalFrame(position, field.radius_m)
        center = frame.position_ecef(position)
        self.basis = frame.basis
        self.nodes: list[tuple[Vector3, float]] = []
        angle = 0.0
        if isinstance(geometry, PointSourceGeometry):
            self.nodes.append((center, 1.0))
        else:
            x, w = np.polynomial.legendre.leggauss(config.area_order)
            angle = math.radians(geometry.orientation_deg)
            for i, u in enumerate(x * geometry.east_width_m / 2):
                for j, v in enumerate(x * geometry.north_height_m / 2):
                    offset = frame.enu_to_ecef(
                        (
                            float(u * math.cos(angle) + v * math.sin(angle)),
                            float(-u * math.sin(angle) + v * math.cos(angle)),
                            0.0,
                        )
                    )
                    self.nodes.append(
                        (
                            cast(Vector3, tuple(a + b for a, b in zip(center, offset))),
                            float(w[i] * w[j] / 4),
                        )
                    )  # type: ignore[arg-type]
        self.terrain: TerrainVisibility | None = None
        self.visibility_plans: list[VisibilityPlan] = []
        self.corners: tuple[Vector3, ...] = ()
        if not isinstance(geometry, PointSourceGeometry):
            corners = []
            for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                u, v = u * geometry.east_width_m / 2, v * geometry.north_height_m / 2
                offset = frame.enu_to_ecef(
                    (
                        u * math.cos(angle) + v * math.sin(angle),
                        -u * math.sin(angle) + v * math.cos(angle),
                        0.0,
                    )
                )
                corners.append(
                    cast(Vector3, tuple(a + b for a, b in zip(center, offset)))
                )
            self.corners = tuple(corners)
        self.work = PathWork()
        self.phase_evaluations = 0
        features = []
        offset = tuple(a - b for a, b in zip(center, ray.origin_ecef_m))
        nearest = dot(offset, ray.direction_ecef)  # type: ignore[arg-type]
        perpendicular = math.dist(ray.point(nearest), center)
        features.extend((nearest - perpendicular, nearest, nearest + perpendicular))
        denominator = dot(ray.direction_ecef, self.basis[2])
        if denominator != 0:
            features.append(dot(offset, self.basis[2]) / denominator)  # type: ignore[arg-type]
        self.break_distances = tuple(s for s in features if 0 < s < ray.length_m)
        # Rebutjar la singularitat geomètrica abans de qualsevol quadratura.
        if isinstance(geometry, PointSourceGeometry):
            offset = tuple(a - b for a, b in zip(center, ray.origin_ecef_m))
            at = dot(offset, ray.direction_ecef)  # type: ignore[arg-type]
            if 0 <= at <= ray.length_m and math.dist(ray.point(at), center) < 1e-7:
                raise ValueError("La LOS interseca una font puntual singular")
        else:
            normal = self.basis[2]
            denominator = dot(ray.direction_ecef, normal)
            if denominator != 0:
                at = (
                    dot(
                        cast(
                            Vector3,
                            tuple(a - b for a, b in zip(center, ray.origin_ecef_m)),
                        ),
                        normal,
                    )
                    / denominator
                )  # type: ignore[arg-type]
                if 0 <= at <= ray.length_m:
                    local = frame.ecef_to_enu(
                        cast(
                            Vector3, tuple(a - b for a, b in zip(ray.point(at), center))
                        )
                    )  # type: ignore[arg-type]
                    u = local[0] * math.cos(angle) - local[1] * math.sin(angle)
                    v = local[0] * math.sin(angle) + local[1] * math.cos(angle)
                    if (
                        abs(u) <= geometry.east_width_m / 2
                        and abs(v) <= geometry.north_height_m / 2
                    ):
                        raise ValueError("La LOS interseca el rectangle emissor")

    def attach_terrain(self, terrain: TerrainVisibility) -> None:
        self.terrain = terrain
        features = set(self.break_distances)
        for node in self.corners or tuple(node for node, _ in self.nodes):
            terrain.assert_above(node)
            features.update(terrain.shadow_cuts(node, self.ray)[1:-1])
        # També canvia la topologia quan un vèrtex de relleu projectat
        # travessa una aresta de l'emissor (sense tocar-ne cap cantonada).
        for vertex in terrain.surface.vertices if self.corners else ():
            for a, b in zip(self.corners, self.corners[1:] + self.corners[:1]):
                self.checkpoint()
                terrain.work.shadow_planes += 1
                normal = cross(sub(a, vertex), sub(b, vertex))
                denominator = dot(normal, self.ray.direction_ecef)
                if denominator:
                    at = dot(normal, sub(vertex, self.ray.origin_ecef_m)) / denominator
                    if 0 < at < self.ray.length_m:
                        features.add(at)
        if not self.corners:
            self.visibility_plans = [
                terrain.plan(node, self.ray) for node, _ in self.nodes
            ]
        self.break_distances = tuple(sorted(features))

    def emission_nodes(
        self, distance: float, point: Vector3
    ) -> list[tuple[Vector3, float]]:
        if self.terrain is None:
            return self.nodes
        with self.profiler.measure("occlusion") if self.profiler else nullcontext():
            if self.corners:
                geometry = self.source.geometry
                assert not isinstance(geometry, PointSourceGeometry)
                return visible_area_nodes(
                    self.terrain,
                    point,
                    self.corners,
                    geometry.east_width_m * geometry.north_height_m,
                    self.config.area_order,
                )
            nodes = [
                (node, weight)
                for (node, weight), plan in zip(self.nodes, self.visibility_plans)
                if plan.at(distance)
            ]
            self.terrain.work.emission_nodes += len(nodes)
            return nodes

    def value(self, distance: float, point: Vector3, state: OpticalState) -> float:
        with self.profiler.measure("transmissions") if self.profiler else nullcontext():
            return self._value(distance, point, state)

    def _value(self, distance: float, point: Vector3, state: OpticalState) -> float:
        self.checkpoint()
        band = self.config.band
        rayleigh, _, aerosol_sca = band.coefficients(state)
        aerosol = band.aerosol(state.dependency.tile_id)
        tau_observer = optical_depth(
            self.field,
            band,
            self.ray.origin_ecef_m,
            point,
            self.config.path_quadrature,
            self.max_segments,
            self.checkpoint,
            self.dependencies,
            self.work,
            self.profiler,
        )
        contributions = []
        for node, weight in self.emission_nodes(distance, point):
            incoming = tuple(a - b for a, b in zip(point, node))
            radius = math.hypot(*incoming)
            if radius < 1e-7:
                raise ValueError("Node de dispersió singular a la font")
            unit: Vector3 = tuple(x / radius for x in incoming)  # type: ignore[assignment]
            vertical = dot(unit, self.basis[2])
            if vertical < 0:
                continue  # Hemisferi descendent exclòs pel SourceModel.
            theta = math.degrees(math.acos(min(1.0, vertical)))
            azimuth = math.degrees(
                math.atan2(dot(unit, self.basis[0]), dot(unit, self.basis[1]))
            )
            intensity = self.source.spectral_radiant_intensity(
                band.wavelength_nm, theta, azimuth
            ).value
            cosine = -dot(unit, self.ray.direction_ecef)
            gamma = rayleigh * band.rayleigh_phase.density(
                cosine
            ) + aerosol_sca * aerosol.phase.density(cosine)
            self.phase_evaluations += 2
            tau_source = optical_depth(
                self.field,
                band,
                node,
                point,
                self.config.path_quadrature,
                self.max_segments,
                self.checkpoint,
                self.dependencies,
                self.work,
                self.profiler,
            )
            contributions.append(
                weight
                * intensity
                / (radius * radius)
                * gamma
                * math.exp(-tau_source - tau_observer)
            )
        return math.fsum(contributions)

    def diagnostics(self) -> TransportDiagnostics:
        return TransportDiagnostics(
            self.phase_evaluations,
            self.work.segments,
            self.work.nodes,
            self.work.max_optical_depth_error,
            len(self.nodes),
        )
