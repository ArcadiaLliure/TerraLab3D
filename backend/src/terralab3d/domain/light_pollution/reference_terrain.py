"""SG-REF terreny: àlgebra NumPy i franges d'àrea, sense motor runtime.

Només comparteix el DTO immutable de superfície. No importa interseccions,
plans de visibilitat, retalls poligonals ni quadratura GK15 del runtime.
"""

from __future__ import annotations

import numpy as np
from scipy.special import roots_legendre

from .terrain_visibility import TerrainSurface


class ReferenceTerrain:
    def __init__(self, surface: TerrainSurface):
        self.triangles = np.asarray(surface.vertices)[np.asarray(surface.faces)]
        self.epsilon = 64 * np.spacing(surface.radius_m)
        self.envelope = surface.radius_m + surface.upper_envelope_m
        boundary = np.asarray(surface.vertices)[np.asarray(surface.boundary)]
        self.border_planes = np.cross(boundary, np.roll(boundary, -1, axis=0))
        self.cones = np.cross(self.triangles, np.roll(self.triangles, -1, axis=1))
        self.cones /= np.linalg.norm(self.cones, axis=2)[:, :, None]

    def coverage(self, a, b):
        direction = b - a
        squared = float(direction @ direction)
        if squared == 0:
            parameters = [0.0]
        else:
            nearest = np.clip(-(a @ direction) / squared, 0, 1)
            if np.linalg.norm(a + nearest * direction) > self.envelope + self.epsilon:
                return
            roots = np.polynomial.polynomial.polyroots(
                [a @ a - self.envelope**2, 2 * (a @ direction), squared]
            )
            real = sorted(float(t.real) for t in roots if abs(t.imag) < 1e-10)
            lo, hi = (max(0.0, real[0]), min(1.0, real[-1])) if real else (0.0, 1.0)
            parameters = [lo, hi]
            for plane in self.border_planes:
                den = plane @ direction
                if den:
                    t = -float(plane @ a) / float(den)
                    if lo < t < hi:
                        parameters.append(t)
            parameters.sort()
            parameters += [(u + v) / 2 for u, v in zip(parameters, parameters[1:])]
        for t in parameters:
            projected = np.einsum("ijk,k->ij", self.cones, a + t * direction)
            if not np.any(np.all(projected >= -self.epsilon, axis=1)):
                raise ValueError("SG-REF: trajecte fora de cobertura DEM")

    def hits(self, start, end, *, require_coverage=True):
        a, b = np.asarray(start), np.asarray(end)
        if require_coverage:
            self.coverage(a, b)
        direction = b - a
        length = np.linalg.norm(direction)
        hits = []
        for p, q, r in self.triangles:
            matrix = np.column_stack((direction, p - q, p - r))
            try:
                t, u, v = np.linalg.solve(matrix, p - a)
            except np.linalg.LinAlgError:
                normal = np.cross(q - p, r - p)
                if (
                    abs(float(normal @ (a - p))) / np.linalg.norm(normal)
                    <= self.epsilon
                ):
                    coordinates = np.linalg.lstsq(
                        np.column_stack((q - p, r - p)),
                        np.column_stack((a - p, b - p)),
                        rcond=None,
                    )[0]
                    weights = np.vstack((coordinates, 1 - coordinates.sum(axis=0)))
                    lo, hi = 0.0, 1.0
                    for start, finish in weights:
                        slope = finish - start
                        if slope > 0:
                            lo = max(lo, float(-start / slope))
                        elif slope < 0:
                            hi = min(hi, float(-start / slope))
                        elif start < -1e-13:
                            hi = -1.0
                    if lo <= hi:
                        hits.extend((float(lo*length),float((lo+hi)*length/2),float(hi*length)))
                continue
            if 0 <= t <= 1 and u >= -1e-13 and v >= -1e-13 and u + v <= 1 + 1e-13:
                hits.append(float(t * length))
        return sorted(hits)

    def visible(self, start, end):
        length = np.linalg.norm(np.asarray(end) - start)
        blocked = any(
            self.epsilon < s < length - self.epsilon
            for s in self.hits(start, end, require_coverage=False)
        )
        if not blocked:
            self.coverage(np.asarray(start), np.asarray(end))
        return not blocked

    def clip(self, origin, direction, length):
        hits = self.hits(origin, origin + length * direction, require_coverage=False)
        if hits and hits[0] <= self.epsilon:
            step = min(length, 1024 * self.epsilon)
            probe = origin + step * direction
            far = probe * (self.envelope + 1) / np.linalg.norm(probe)
            if any(h > self.epsilon for h in self.hits(probe, far)) or any(
                self.epsilon < h < step - self.epsilon
                for h in self.hits(origin, probe, require_coverage=False)
            ):
                return 0.0
        first = next(
            (h for h in hits if h > self.epsilon),
            length,
        )
        self.coverage(origin, origin + first * direction)
        return first

    def cuts(self, source, origin, direction, length):
        result = set()
        for a, b, c in self.triangles:
            # Plans de cara i arestes amb la font, calculats independentment.
            triples = ((a, b, c), (source, a, b), (source, b, c), (source, c, a))
            for p, q, r in triples:
                n = np.cross(q - p, r - p)
                denominator = float(n @ direction)
                if denominator:
                    s = float(n @ (p - origin)) / denominator
                    if 0 < s < length:
                        result.add(s)
        return result

    def area_nodes(self, point, center, axis_u, axis_v, width, height, order):
        """Arranjament de rectes 2D; GL per franges, sense restar polígons.

        Totes les fronteres projectades i les seves interseccions divideixen
        el rectangle. Cada cel·la oberta té visibilitat binària constant.
        """
        lines = []
        rectangle = [
            center + u * axis_u + v * axis_v
            for u in (-width / 2, width / 2)
            for v in (-height / 2, height / 2)
        ]
        for a, b, c in self.triangles:
            face_normal = np.cross(b - a, c - a)
            face_side = float(face_normal @ (a - point))
            if abs(face_side) / np.linalg.norm(face_normal) <= self.epsilon:
                continue
            shadow_planes = [(np.sign(face_side) * face_normal, a)]
            for v, w, inside in ((a, b, c), (b, c, a), (c, a, b)):
                normal = np.cross(v - point, w - point)
                normal *= np.sign(normal @ (inside - point))
                shadow_planes.append((normal, point))
            if any(
                max(float(n @ (vertex - base)) for vertex in rectangle) < 0
                for n, base in shadow_planes
            ):
                continue
            for p, q, r in ((a, b, c), (point, a, b), (point, b, c), (point, c, a)):
                n = np.cross(q - p, r - p)
                coefficients = np.array(
                    [n @ axis_u, n @ axis_v, n @ (center - p)], dtype=float
                )
                scale = np.linalg.norm(coefficients[:2])
                if scale == 0:
                    continue
                coefficients /= scale
                aa, bb, cc = coefficients
                corners = [
                    aa * u + bb * v + cc
                    for u in (-width / 2, width / 2)
                    for v in (-height / 2, height / 2)
                ]
                if min(corners) < 0 < max(corners):
                    if not any(
                        np.allclose(coefficients, other, rtol=1e-12, atol=1e-10)
                        or np.allclose(coefficients, -other, rtol=1e-12, atol=1e-10)
                        for other in lines
                    ):
                        lines.append(coefficients)
        lines += [np.array([0.0, 1.0, height / 2]), np.array([0.0, 1.0, -height / 2])]
        xs = {-width / 2, width / 2}
        for i, (a, b, c) in enumerate(lines):
            if abs(b) < 1e-14 and a:
                u = -c / a
                if -width / 2 < u < width / 2:
                    xs.add(float(u))
            for d, e, f in lines[i + 1 :]:
                det = a * e - b * d
                if abs(det) < 1e-14:
                    continue
                u, v = (b * f - c * e) / det, (c * d - a * f) / det
                if (
                    -width / 2 < u < width / 2
                    and -height / 2 - 1e-9 <= v <= height / 2 + 1e-9
                ):
                    xs.add(float(u))
        x, w = roots_legendre(order)
        nodes, weights = [], []
        ordered = sorted(xs)
        for lo, hi in zip(ordered, ordered[1:]):
            mid = (lo + hi) / 2
            boundaries = sorted(
                [
                    (float(-(a * mid + c) / b), a, b, c)
                    for a, b, c in lines
                    if abs(b) >= 1e-14
                ]
            )
            for lower, upper in zip(boundaries, boundaries[1:]):
                vmid = (lower[0] + upper[0]) / 2
                if not -height / 2 < vmid < height / 2:
                    continue
                if not self.visible(center + mid * axis_u + vmid * axis_v, point):
                    continue
                for xx, wx in zip(x, w):
                    u = mid + (hi - lo) * xx / 2
                    vlo = -(lower[1] * u + lower[3]) / lower[2]
                    vhi = -(upper[1] * u + upper[3]) / upper[2]
                    for yy, wy in zip(x, w):
                        v = (vlo + vhi) / 2 + (vhi - vlo) * yy / 2
                        nodes.append(center + u * axis_u + v * axis_v)
                        weights.append(
                            float(
                                wx * wy * (hi - lo) * (vhi - vlo) / 4 / (width * height)
                            )
                        )
        return np.asarray(nodes).reshape((-1, 3)), np.asarray(weights)

    def area_cuts(self, corners, origin, direction, length):
        cuts = set()
        for corner in corners:
            cuts.update(self.cuts(corner, origin, direction, length))
        for vertex in self.triangles.reshape((-1, 3)):
            for a, b in zip(corners, np.roll(corners, -1, axis=0)):
                normal = np.cross(a - vertex, b - vertex)
                den = float(normal @ direction)
                if den:
                    s = float(normal @ (vertex - origin)) / den
                    if 0 < s < length:
                        cuts.add(s)
        return cuts
