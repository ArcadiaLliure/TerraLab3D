"""Geometria esfèrica estable, pura i independent del renderer."""

from __future__ import annotations

import math
from typing import Protocol
from terralab3d.domain.geometry import HorizontalCoordinate
from terralab3d.domain.measurements.models import Measurement, MeasurementGeometry, MeasurementKind

class MeasurementCalculator(Protocol):
    """Defineix els càlculs purs de mesures angulars i formes sense I/O ni renderitzat."""
    def angular_distance_deg(self, a: HorizontalCoordinate, b: HorizontalCoordinate) -> float: ...
    def geometry(self, measurement: Measurement) -> MeasurementGeometry: ...


class MeasurementValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


class SphericalMeasurementCalculator:
    """Calcula geodèsiques i formes en el marc horitzontal (graus)."""

    def __init__(self, path_segments: int = 48) -> None:
        if path_segments < 8:
            raise ValueError("path_segments ha de ser com a mínim 8")
        self._segments = path_segments

    def angular_distance_deg(self, a: HorizontalCoordinate, b: HorizontalCoordinate) -> float:
        first = _unit(a)
        second = _unit(b)
        cross = _cross(first, second)
        return math.degrees(math.atan2(_norm(cross), _dot(first, second)))

    def geometry(self, measurement: Measurement) -> MeasurementGeometry:
        _validate_measurement(measurement)
        distance = self.angular_distance_deg(measurement.start, measurement.end)
        if distance <= 1e-9:
            raise MeasurementValidationError("end", "la mesura necessita una extensió angular no nul·la")
        if measurement.kind is MeasurementKind.RULER:
            path = tuple(_slerp_coordinate(measurement.start, measurement.end, index / self._segments)
                         for index in range(self._segments + 1))
            return MeasurementGeometry((path,), _format_angle(distance), _slerp_coordinate(measurement.start, measurement.end, 0.5))
        if measurement.kind is MeasurementKind.CIRCLE:
            center = _slerp_coordinate(measurement.start, measurement.end, 0.5)
            radius = distance / 2.0
            path = tuple(_destination(center, radius, 360.0 * index / self._segments)
                         for index in range(self._segments + 1))
            label = f"r {_format_angle(radius)} · Ø {_format_angle(distance)}"
            return MeasurementGeometry((path,), label, _destination(center, radius, 90.0))

        bearing_from_start = math.radians(_initial_bearing_deg(measurement.start, measurement.end))
        distance_rad = math.radians(distance)
        dx = distance_rad * math.sin(bearing_from_start)
        dy = distance_rad * math.cos(bearing_from_start)
        
        if measurement.kind is MeasurementKind.SQUARE:
            s = max(abs(dx), abs(dy))
            dx = (1.0 if dx >= 0 else -1.0) * s
            dy = (1.0 if dy >= 0 else -1.0) * s

        if abs(dx) <= 1e-9 or abs(dy) <= 1e-9:
            raise MeasurementValidationError("end", "el rectangle necessita amplada i alçada no nul·les")

        rotation = math.radians(measurement.rotation_deg)
        corners = [(0.0, 0.0), (dx, 0.0), (dx, dy), (0.0, dy)]
        rotated = [_rotate_xy(x, y, rotation) for x, y in corners]
        path_points: list[HorizontalCoordinate] = []
        edge_segments = max(2, self._segments // 4)
        for edge in range(4):
            x0, y0 = rotated[edge]
            x1, y1 = rotated[(edge + 1) % 4]
            for index in range(edge_segments):
                t = index / edge_segments
                path_points.append(_gnomonic_offset(measurement.start, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        path_points.append(path_points[0])
        width_deg = math.degrees(abs(dx))
        height_deg = math.degrees(abs(dy))
        label = f"{_format_angle(width_deg)} × {_format_angle(height_deg)}"
        anchor_offset = _rotate_xy(dx / 2.0, dy + (0.01 if dy >= 0 else -0.01), rotation)
        anchor = _gnomonic_offset(measurement.start, anchor_offset[0], anchor_offset[1])
        return MeasurementGeometry((tuple(path_points),), label, anchor)


def _validate_measurement(measurement: Measurement) -> None:
    if not str(measurement.measurement_id):
        raise MeasurementValidationError("measurementId", "l'identificador és obligatori")
    for name, coordinate in (("start", measurement.start), ("end", measurement.end)):
        if not math.isfinite(coordinate.altitude_deg) or not -90.0 <= coordinate.altitude_deg <= 90.0:
            raise MeasurementValidationError(name, "l'altitud ha d'estar dins [-90, 90]")
        if not math.isfinite(coordinate.azimuth_deg):
            raise MeasurementValidationError(name, "l'azimut ha de ser finit")
    if not math.isfinite(measurement.rotation_deg):
        raise MeasurementValidationError("rotationDeg", "la rotació ha de ser finita")
    if measurement.tracking and measurement.fixed_quaternion_xyzw is not None:
        raise MeasurementValidationError("fixedQuaternion", "una mesura amb seguiment no pot tenir una orientació congelada")
    if not measurement.tracking:
        quaternion = measurement.fixed_quaternion_xyzw
        if quaternion is None or len(quaternion) != 4 or not all(math.isfinite(value) for value in quaternion):
            raise MeasurementValidationError("fixedQuaternion", "una mesura fixa necessita un quaternion finit")
        norm = math.sqrt(sum(value * value for value in quaternion))
        if abs(norm - 1.0) > 1e-6:
            raise MeasurementValidationError("fixedQuaternion", "el quaternion congelat ha d'estar normalitzat")


def _unit(coordinate: HorizontalCoordinate) -> tuple[float, float, float]:
    altitude = math.radians(coordinate.altitude_deg)
    azimuth = math.radians(coordinate.azimuth_deg)
    horizontal = math.cos(altitude)
    return math.sin(azimuth) * horizontal, math.cos(azimuth) * horizontal, math.sin(altitude)


def _coordinate(vector: tuple[float, float, float]) -> HorizontalCoordinate:
    x, y, z = vector
    length = _norm(vector)
    return HorizontalCoordinate(
        altitude_deg=math.degrees(math.asin(max(-1.0, min(1.0, z / length)))),
        azimuth_deg=(math.degrees(math.atan2(x, y)) + 360.0) % 360.0,
    )


def _slerp_coordinate(a: HorizontalCoordinate, b: HorizontalCoordinate, t: float) -> HorizontalCoordinate:
    first = _unit(a)
    second = _unit(b)
    dot = max(-1.0, min(1.0, _dot(first, second)))
    angle = math.acos(dot)
    if angle < 1e-12:
        return a
    if math.pi - angle < 1e-8:
        axis = _normalize(_cross(first, (0.0, 0.0, 1.0)))
        if _norm(axis) < 1e-8:
            axis = (1.0, 0.0, 0.0)
        vector = _rodrigues(first, axis, math.pi * t)
    else:
        sine = math.sin(angle)
        vector = tuple((math.sin((1.0 - t) * angle) * first[i] + math.sin(t * angle) * second[i]) / sine for i in range(3))
    return _coordinate(vector)  # type: ignore[arg-type]


def _initial_bearing_deg(a: HorizontalCoordinate, b: HorizontalCoordinate) -> float:
    lat1, lat2 = map(math.radians, (a.altitude_deg, b.altitude_deg))
    delta_lon = math.radians(((b.azimuth_deg - a.azimuth_deg + 180.0) % 360.0) - 180.0)
    y = math.sin(delta_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _destination(center: HorizontalCoordinate, distance_deg: float, bearing_deg: float) -> HorizontalCoordinate:
    latitude = math.radians(center.altitude_deg)
    longitude = math.radians(center.azimuth_deg)
    distance = math.radians(distance_deg)
    bearing = math.radians(bearing_deg)
    latitude2 = math.asin(math.sin(latitude) * math.cos(distance) + math.cos(latitude) * math.sin(distance) * math.cos(bearing))
    longitude2 = longitude + math.atan2(math.sin(bearing) * math.sin(distance) * math.cos(latitude), math.cos(distance) - math.sin(latitude) * math.sin(latitude2))
    return HorizontalCoordinate(math.degrees(latitude2), (math.degrees(longitude2) + 360.0) % 360.0)


def _gnomonic_offset(center: HorizontalCoordinate, x_rad: float, y_rad: float) -> HorizontalCoordinate:
    c = _unit(center)
    azimuth = math.radians(center.azimuth_deg)
    altitude = math.radians(center.altitude_deg)
    east = (math.cos(azimuth), -math.sin(azimuth), 0.0)
    north = (-math.sin(azimuth) * math.sin(altitude), -math.cos(azimuth) * math.sin(altitude), math.cos(altitude))
    vector = _normalize(tuple(c[i] + math.tan(x_rad) * east[i] + math.tan(y_rad) * north[i] for i in range(3)))
    return _coordinate(vector)  # type: ignore[arg-type]


def _format_angle(value_deg: float) -> str:
    value = abs(value_deg)
    if value < 1.0 / 60.0:
        return f"{value * 3600.0:.2f}″"
    if value < 1.0:
        return f"{value * 60.0:.2f}′"
    return f"{value:.3f}°"


def _rotate_xy(x: float, y: float, angle: float) -> tuple[float, float]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return x * cosine - y * sine, x * sine + y * cosine


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def _norm(value: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _norm(value)
    if length <= 1e-15:
        return value
    return value[0] / length, value[1] / length, value[2] / length


def _rodrigues(vector: tuple[float, float, float], axis: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
    cosine, sine = math.cos(angle), math.sin(angle)
    cross = _cross(axis, vector)
    dot = _dot(axis, vector)
    return tuple(vector[i] * cosine + cross[i] * sine + axis[i] * dot * (1.0 - cosine) for i in range(3))  # type: ignore[return-value]
