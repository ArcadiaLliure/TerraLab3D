"""Superfície DEM triangular opaca en el mateix ECEF esfèric del kernel.

Interseccions directes, sense índex espacial ni reutilització entre peticions.
La malla és el model físic discret: no s'hi aplica alfa ni perfil 2D d'horitzó.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import asdict, dataclass
from typing import Callable, cast

import numpy as np

from .geometric_transport import RayGeometry, Vector3, dot
from .optical_field import fingerprint


def sub(a: Vector3, b: Vector3) -> Vector3:
    return cast(Vector3, tuple(x - y for x, y in zip(a, b)))


def cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def unit(a: Vector3) -> Vector3:
    return cast(Vector3, tuple(x / math.hypot(*a) for x in a))


class TerrainCoverageError(ValueError):
    """Cobertura desconeguda: mai equival a cel transparent."""


@dataclass(frozen=True, slots=True)
class TerrainSurface:
    vertices: tuple[Vector3, ...]
    faces: tuple[tuple[int, int, int], ...]
    boundary: tuple[int, ...]
    radius_m: float
    upper_envelope_m: float
    provenance: str
    height_interpretation: str
    revision: str = "opaque-triangular-dem-v1"

    def __post_init__(self) -> None:
        if (
            not self.faces
            or len(self.boundary) < 3
            or not self.provenance
            or not self.height_interpretation
            or not math.isfinite(self.radius_m)
            or self.radius_m <= 0
            or not math.isfinite(self.upper_envelope_m)
        ):
            raise ValueError("Superfície DEM incompleta")
        if any(
            not all(math.isfinite(x) for x in v) or math.hypot(*v) <= 0
            for v in self.vertices
        ):
            raise ValueError("Vèrtex DEM invàlid")
        ids = [i for face in self.faces for i in face] + list(self.boundary)
        if min(ids) < 0 or max(ids) >= len(self.vertices):
            raise ValueError("Índex DEM invàlid")
        if (
            max(math.hypot(*v) for v in self.vertices)
            > self.radius_m + self.upper_envelope_m + self.epsilon_m
        ):
            raise ValueError("L'envolupant no conté el DEM")
        edges: dict[tuple[int, int], int] = {}
        for face in self.faces:
            a, b, c = (self.vertices[i] for i in face)
            if dot(cross(sub(b, a), sub(c, a)), a) <= 0:
                raise ValueError("Triangle degenerat o orientació DEM invertida")
            for i, j in zip(face, (face[1], face[2], face[0])):
                key = (min(i, j), max(i, j))
                edges[key] = edges.get(key, 0) + 1
        border = {
            tuple(sorted((i, j)))
            for i, j in zip(self.boundary, self.boundary[1:] + self.boundary[:1])
        }
        if {e for e, n in edges.items() if n == 1} != border or any(
            n > 2 for n in edges.values()
        ):
            raise ValueError("Malla DEM amb forats o topologia no manifold")
        center = cast(
            Vector3, tuple(math.fsum(v[i] for v in self.vertices) for i in range(3))
        )
        if any(dot(center, v) <= 0 for v in self.vertices):
            raise ValueError("La cobertura DEM ha de ser menor que un hemisferi")

    @property
    def epsilon_m(self) -> float:
        # Exclusivament incertesa aritmètica ECEF, no gruix/transparència física.
        return 64 * math.ulp(self.radius_m)

    @property
    def triangles(self) -> tuple[tuple[Vector3, Vector3, Vector3], ...]:
        return tuple(
            cast(tuple[Vector3, Vector3, Vector3], tuple(self.vertices[i] for i in f))
            for f in self.faces
        )

    @property
    def coverage_normals(self) -> tuple[Vector3, ...]:
        return tuple(
            unit(cross(self.vertices[i], self.vertices[j]))
            for i, j in zip(self.boundary, self.boundary[1:] + self.boundary[:1])
        )

    @property
    def signature(self) -> str:
        return fingerprint(asdict(self))


@dataclass(slots=True)
class VisibilityWork:
    segment_checks: int = 0
    triangle_tests: int = 0
    shadow_planes: int = 0
    visibility_intervals: int = 0
    area_polygons: int = 0
    emission_nodes: int = 0
    max_area_nodes: int = 0
    max_area_roundoff_fraction: float = 0.0


class TerrainVisibility:
    def __init__(
        self,
        surface: TerrainSurface,
        checkpoint: Callable[[], None],
        max_parts: int = 4096,
    ):
        self.surface, self.checkpoint, self.max_parts = surface, checkpoint, max_parts
        self.triangles, self.normals = surface.triangles, surface.coverage_normals
        self.cones = tuple(
            tuple(unit(cross(v, w)) for v, w in ((a, b), (b, c), (c, a)))
            for a, b, c in self.triangles
        )
        self.work = VisibilityWork()

    def coverage(self, a: Vector3, b: Vector3) -> None:
        """Només la part dins l'envolupant radial pot tocar el terreny.

        La unió dels cons radials dels triangles defineix la cobertura.
        Es parteix a totes les arestes de frontera: també admet paral·lels
        geogràfics que no són arcs de cercle màxim convexos.
        """
        d = sub(b, a)
        aa, ab = dot(d, d), dot(a, d)
        if aa == 0:
            points = (a,)
        else:
            r = self.surface.radius_m + self.surface.upper_envelope_m
            closest = min(1.0, max(0.0, -ab / aa))
            if (
                math.hypot(*(a[i] + closest * d[i] for i in range(3)))
                > r + self.surface.epsilon_m
            ):
                return
            disc = ab * ab - aa * (dot(a, a) - r * r)
            if disc < 0:
                points = (a, b)  # només possible a la banda d'arrodoniment
            else:
                root = math.sqrt(disc)
                lo, hi = max(0.0, (-ab - root) / aa), min(1.0, (-ab + root) / aa)
                cuts = {lo, hi}
                for normal in self.normals:
                    den = dot(normal, d)
                    if den:
                        t = -dot(normal, a) / den
                        if lo < t < hi:
                            cuts.add(t)
                ordered = sorted(cuts)
                tests = ordered + [(x + y) / 2 for x, y in zip(ordered, ordered[1:])]
                points = tuple(
                    cast(Vector3, tuple(a[i] + t * d[i] for i in range(3)))
                    for t in tests
                )
        if any(
            not any(
                all(dot(n, p) >= -self.surface.epsilon_m for n in cone)
                for cone in self.cones
            )
            for p in points
        ):
            raise TerrainCoverageError(
                "Trajecte potencialment terrestre fora de cobertura DEM"
            )

    def intersections(
        self, a: Vector3, b: Vector3, *, require_coverage: bool = True
    ) -> tuple[float, ...]:
        self.checkpoint()
        self.work.segment_checks += 1
        if require_coverage:
            self.coverage(a, b)
        d = sub(b, a)
        length = math.hypot(*d)
        if length == 0:
            return ()
        hits = []
        for v0, v1, v2 in self.triangles:
            self.checkpoint()
            self.work.triangle_tests += 1
            e1, e2 = sub(v1, v0), sub(v2, v0)
            h = cross(d, e2)
            det = dot(e1, h)
            if abs(det) <= 32 * math.ulp(1.0) * math.hypot(*e1) * math.hypot(*h):
                normal = unit(cross(e1, e2))
                if abs(dot(normal, sub(a, v0))) <= self.surface.epsilon_m:
                    lo, hi = 0.0, 1.0
                    for v, w in ((v0, v1), (v1, v2), (v2, v0)):
                        inside = unit(cross(normal, sub(w, v)))
                        start, change = dot(inside, sub(a, v)), dot(inside, d)
                        if change == 0:
                            if start < -self.surface.epsilon_m:
                                hi = -1.0
                        elif change > 0:
                            lo = max(lo, -start / change)
                        else:
                            hi = min(hi, -start / change)
                    if hi >= lo:
                        hits.extend((lo * length, (lo + hi) * length / 2, hi * length))
                continue
            s = sub(a, v0)
            u = dot(s, h) / det
            q = cross(s, e1)
            v, t = dot(d, q) / det, dot(e2, q) / det
            eps = 64 * math.ulp(1.0)
            if u >= -eps and v >= -eps and u + v <= 1 + eps and -eps <= t <= 1 + eps:
                hits.append(min(length, max(0.0, t * length)))
        return tuple(sorted(hits))

    def below(self, point: Vector3) -> bool:
        r = math.hypot(*point)
        far = cast(
            Vector3,
            tuple(
                x * (self.surface.radius_m + self.surface.upper_envelope_m + 1) / r
                for x in point
            ),
        )
        self.coverage(point, far)
        return any(s > self.surface.epsilon_m for s in self.intersections(point, far))

    def assert_above(self, point: Vector3) -> None:
        if self.below(point):
            raise ValueError("Observador/font sota la superfície DEM")

    def visible(self, a: Vector3, b: Vector3) -> bool:
        # El contacte inicial d'una font al sòl no és una oclusió.
        # La tangència interior és opaca; no hi ha cap fracció alfa.
        blocked = any(
            self.surface.epsilon_m < s < math.dist(a, b) - self.surface.epsilon_m
            for s in self.intersections(a, b, require_coverage=False)
        )
        if not blocked:
            self.coverage(a, b)
        return not blocked

    def clip_observer(self, ray: RayGeometry) -> float:
        self.assert_above(ray.origin_ecef_m)
        hits = self.intersections(
            ray.origin_ecef_m, ray.point(ray.length_m), require_coverage=False
        )
        if hits and hits[0] <= self.surface.epsilon_m:
            probe_length = min(ray.length_m, 1024 * self.surface.epsilon_m)
            probe = ray.point(probe_length)
            if self.below(probe) or any(
                self.surface.epsilon_m < s < probe_length - self.surface.epsilon_m
                for s in self.intersections(
                    ray.origin_ecef_m, probe, require_coverage=False
                )
            ):
                return 0.0
        first = next((s for s in hits if s > self.surface.epsilon_m), ray.length_m)
        self.coverage(ray.origin_ecef_m, ray.point(first))
        return first

    def shadow_cuts(self, source: Vector3, ray: RayGeometry) -> tuple[float, ...]:
        cuts = {0.0, ray.length_m}
        for a, b, c in self.triangles:
            self.checkpoint()
            planes = [(cross(sub(b, a), sub(c, a)), a)]
            planes += [
                (cross(sub(v, source), sub(w, source)), source)
                for v, w in ((a, b), (b, c), (c, a))
            ]
            for normal, base in planes:
                self.work.shadow_planes += 1
                den = dot(normal, ray.direction_ecef)
                if den:
                    at = dot(normal, sub(base, ray.origin_ecef_m)) / den
                    if 0 < at < ray.length_m:
                        cuts.add(at)
            if len(cuts) > self.max_parts:
                raise ValueError("Pressupost de discontinuïtats DEM excedit")
        return tuple(sorted(cuts))

    def plan(self, source: Vector3, ray: RayGeometry) -> VisibilityPlan:
        self.assert_above(source)
        cuts = self.shadow_cuts(source, ray)
        mask = tuple(
            self.visible(source, ray.point((a + b) / 2)) for a, b in zip(cuts, cuts[1:])
        )
        self.work.visibility_intervals += len(mask)
        boundaries = tuple(self.visible(source, ray.point(s)) for s in cuts)
        return VisibilityPlan(cuts, mask, boundaries)


@dataclass(frozen=True, slots=True)
class VisibilityPlan:
    cuts: tuple[float, ...]
    mask: tuple[bool, ...]
    boundary_mask: tuple[bool, ...]

    def at(self, distance: float) -> bool:
        index = max(0, bisect_right(self.cuts, distance) - 1)
        if distance == self.cuts[index]:
            return self.boundary_mask[index]
        return self.mask[min(len(self.mask) - 1, index)]


def _clip(poly: list[Vector3], normal: Vector3, base: Vector3) -> list[Vector3]:
    result = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        fa, fb = dot(normal, sub(a, base)), dot(normal, sub(b, base))
        if fa >= 0:
            result.append(a)
        if (fa < 0) != (fb < 0):
            t = fa / (fa - fb)
            result.append(
                cast(Vector3, tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
            )
    return result


def visible_area_nodes(
    visibility: TerrainVisibility,
    point: Vector3,
    corners: tuple[Vector3, ...],
    area: float,
    order: int,
) -> list[tuple[Vector3, float]]:
    """Soustrau les ombres triangulars del rectangle abans d'integrar l'àrea.

    Polígons convexos disjunts + GL/Duffy; pesos dA/A, mai percentatge
    de transparència assignat a una font parcialment oculta.
    """
    polys = [list(corners)]
    discarded = 0.0
    for a, b, c in visibility.triangles:
        visibility.checkpoint()
        normal = unit(cross(sub(b, a), sub(c, a)))
        side = dot(normal, sub(a, point))
        if abs(side) <= visibility.surface.epsilon_m:
            continue
        planes = [
            (
                cast(Vector3, tuple(math.copysign(1, side) * v for v in normal)),
                a,
            )
        ]
        for v, w, inside in ((a, b, c), (b, c, a), (c, a, b)):
            n = unit(cross(sub(v, point), sub(w, point)))
            if dot(n, sub(inside, point)) < 0:
                n = cast(Vector3, tuple(-v for v in n))
            planes.append((n, point))
        remaining = []
        for poly in polys:
            inside_poly = poly
            for n, base in planes:
                outside = _clip(inside_poly, cast(Vector3, tuple(-v for v in n)), base)
                if len(outside) >= 3:
                    remaining.append(outside)
                inside_poly = _clip(inside_poly, n, base)
                if len(inside_poly) < 3:
                    break
        polys = []
        for poly in remaining:
            polygon_area = math.fsum(
                math.hypot(*cross(sub(b, poly[0]), sub(c, poly[0]))) / 2
                for b, c in zip(poly[1:-1], poly[2:])
            )
            perimeter = math.fsum(
                math.dist(a, b) for a, b in zip(poly, poly[1:] + poly[:1])
            )
            # Escletxes de l'ordre de la resolució ECEF, amb àrea descartada
            # quantificada. No és un suavitzat ni una tolerància radiomètrica.
            if polygon_area <= visibility.surface.epsilon_m * perimeter:
                discarded += polygon_area
            else:
                polys.append(poly)
        if len(polys) > visibility.max_parts:
            raise ValueError("Pressupost de polígons visibles excedit")
    x, w = np.polynomial.legendre.leggauss(order)
    x, w = (x + 1) / 2, w / 2
    nodes = []
    for poly in polys:
        for b, c in zip(poly[1:-1], poly[2:]):
            a = poly[0]
            jac = math.hypot(*cross(sub(b, a), sub(c, a)))
            if jac <= visibility.surface.epsilon_m**2:
                continue
            for i, u in enumerate(x):
                for j, v in enumerate(x):
                    node = cast(
                        Vector3,
                        tuple(
                            a[k] + u * (b[k] - a[k]) + (1 - u) * v * (c[k] - a[k])
                            for k in range(3)
                        ),
                    )
                    # Verificació binària també als nodes de les escletxes
                    # numèriques creades per plans gairebé coincidents.
                    if visibility.visible(node, point):
                        nodes.append((node, float(jac * (1 - u) * w[i] * w[j] / area)))
    visibility.work.area_polygons += len(polys)
    visibility.work.emission_nodes += len(nodes)
    visibility.work.max_area_nodes = max(visibility.work.max_area_nodes, len(nodes))
    visibility.work.max_area_roundoff_fraction = max(
        visibility.work.max_area_roundoff_fraction, discarded / area
    )
    return nodes
