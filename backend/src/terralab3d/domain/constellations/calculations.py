"""Geometria esfèrica pura per a constel·lacions."""

from __future__ import annotations

import math

import numpy as np

from terralab3d.domain.constellations.models import ConstellationNode
from terralab3d.domain.geometry import EquatorialCoordinate


class ConstellationValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


class SphericalConstellationCalculator:
    def validate_coordinate(self, coordinate: EquatorialCoordinate) -> EquatorialCoordinate:
        ra = float(coordinate.right_ascension_deg)
        dec = float(coordinate.declination_deg)
        if not math.isfinite(ra) or not math.isfinite(dec):
            raise ConstellationValidationError("coordinate", "la coordenada ha de ser finita")
        if dec < -90.0 or dec > 90.0:
            raise ConstellationValidationError("declinationDeg", "la declinació ha d'estar entre -90° i 90°")
        return EquatorialCoordinate(ra % 360.0, dec)

    def arc_points(
        self,
        a: ConstellationNode,
        b: ConstellationNode,
        sample_count: int,
    ) -> tuple[EquatorialCoordinate, ...]:
        if sample_count < 2:
            raise ConstellationValidationError("sampleCount", "calen almenys dues mostres")
        start = self._direction(self.validate_coordinate(a.coordinate))
        end = self._direction(self.validate_coordinate(b.coordinate))
        dot = float(np.clip(np.dot(start, end), -1.0, 1.0))
        angle = math.acos(dot)
        if angle < 1e-12:
            return tuple(a.coordinate for _ in range(sample_count))
        scale = math.sin(angle)
        result = []
        for index in range(sample_count):
            fraction = index / (sample_count - 1)
            direction = (
                math.sin((1.0 - fraction) * angle) / scale * start
                + math.sin(fraction * angle) / scale * end
            )
            result.append(self._coordinate(direction))
        return tuple(result)

    @staticmethod
    def _direction(coordinate: EquatorialCoordinate) -> np.ndarray:
        ra = math.radians(coordinate.right_ascension_deg)
        dec = math.radians(coordinate.declination_deg)
        return np.asarray((math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)))

    @staticmethod
    def _coordinate(direction: np.ndarray) -> EquatorialCoordinate:
        unit = direction / np.linalg.norm(direction)
        return EquatorialCoordinate(
            math.degrees(math.atan2(float(unit[1]), float(unit[0]))) % 360.0,
            math.degrees(math.asin(float(np.clip(unit[2], -1.0, 1.0)))),
        )
