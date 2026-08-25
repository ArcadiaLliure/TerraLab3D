"""Shapely/PyProj implementation of the metric coverage geometry port."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import GeometryCollection, LineString, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import split, transform, unary_union

from terralab3d.domain.refinement.coverage import MetricGeometry
from terralab3d.domain.refinement.errors import RefinementValidationError


class ShapelyGeometryAdapter:
    """Execute concrete geometry operations without leaking Shapely to domain."""

    def union(self, geometries: Sequence[MetricGeometry]) -> MetricGeometry:
        if not geometries:
            return MetricGeometry(GeometryCollection(), "EPSG:3035")
        self._require_same_crs(geometries)
        return MetricGeometry(
            unary_union([self._shape(item) for item in geometries]),
            geometries[0].crs,
        )

    def intersection(self, left: MetricGeometry, right: MetricGeometry) -> MetricGeometry:
        self._require_same_crs((left, right))
        return MetricGeometry(self._shape(left).intersection(self._shape(right)), left.crs)

    def difference(self, left: MetricGeometry, right: MetricGeometry) -> MetricGeometry:
        self._require_same_crs((left, right))
        return MetricGeometry(self._shape(left).difference(self._shape(right)), left.crs)

    def area(self, geometry: MetricGeometry) -> float:
        self._require_metric_crs(geometry.crs)
        return float(self._shape(geometry).area)

    def is_empty(self, geometry: MetricGeometry) -> bool:
        return bool(self._shape(geometry).is_empty)

    def from_geojson(
        self,
        geometry: Mapping[str, object],
        *,
        source_crs: str,
        target_crs: str,
    ) -> MetricGeometry:
        source = CRS.from_user_input(source_crs)
        self._require_metric_crs(target_crs)
        concrete = shape(dict(geometry))
        if concrete.is_empty or not concrete.is_valid:
            raise RefinementValidationError("Coverage GeoJSON must be valid and non-empty")
        if source.is_geographic:
            concrete = _normalize_antimeridian(concrete)
        transformer = Transformer.from_crs(source, target_crs, always_xy=True)
        projected = transform(transformer.transform, concrete)
        if projected.is_empty or not projected.is_valid:
            raise RefinementValidationError("Projected coverage geometry is invalid")
        return MetricGeometry(projected, target_crs)

    def to_geojson(self, geometry: MetricGeometry) -> dict[str, object]:
        return dict(mapping(self._shape(geometry)))

    def reproject(self, geometry: MetricGeometry, target_crs: str) -> MetricGeometry:
        self._require_metric_crs(geometry.crs)
        self._require_metric_crs(target_crs)
        transformer = Transformer.from_crs(geometry.crs, target_crs, always_xy=True)
        projected = transform(transformer.transform, self._shape(geometry))
        return MetricGeometry(projected, target_crs)

    @staticmethod
    def _shape(geometry: MetricGeometry) -> BaseGeometry:
        if not isinstance(geometry.value, BaseGeometry):
            raise RefinementValidationError("Geometry value is not a Shapely geometry")
        return geometry.value

    @staticmethod
    def _require_same_crs(geometries: Sequence[MetricGeometry]) -> None:
        if not geometries:
            return
        first = CRS.from_user_input(geometries[0].crs)
        if any(not first.equals(CRS.from_user_input(item.crs)) for item in geometries[1:]):
            raise RefinementValidationError("Geometry operands use different CRS values")

    @staticmethod
    def _require_metric_crs(crs_value: str) -> None:
        crs = CRS.from_user_input(crs_value)
        if not crs.is_projected:
            raise RefinementValidationError("Coverage area requires a projected CRS")
        units = {axis.unit_name.lower() for axis in crs.axis_info if axis.unit_name}
        if not units or not all("metre" in unit or "meter" in unit for unit in units):
            raise RefinementValidationError("Coverage CRS axes must use metres")


def _normalize_antimeridian(geometry: BaseGeometry) -> BaseGeometry:
    """Split dateline-crossing polygons before projection.

    GeoJSON represents the short 170E→170W edge with a numeric jump of 340°.
    Shapely is planar, so that ring must be unwrapped, cut at 180°, and wrapped
    back into two pieces before PyProj sees it.
    """

    if not _has_dateline_jump(geometry):
        return geometry
    shifted = transform(_coordinate_transform(lambda x: x + 360.0 if x < 0 else x), geometry)
    pieces = split(shifted, LineString(((180.0, -90.0), (180.0, 90.0))))
    wrapped: list[BaseGeometry] = []
    for part in pieces.geoms:
        if part.bounds[0] >= 180.0:
            part = transform(_coordinate_transform(lambda x: x - 360.0), part)
        wrapped.append(part)
    return unary_union(wrapped)


def _has_dateline_jump(geometry: BaseGeometry) -> bool:
    def ring_jumps(coordinates: Sequence[tuple[float, ...]]) -> bool:
        return any(abs(current[0] - previous[0]) > 180 for previous, current in zip(coordinates, coordinates[1:]))

    if geometry.geom_type == "Polygon":
        polygon = geometry
        return ring_jumps(list(polygon.exterior.coords)) or any(
            ring_jumps(list(ring.coords)) for ring in polygon.interiors
        )
    if hasattr(geometry, "geoms"):
        return any(_has_dateline_jump(item) for item in geometry.geoms)
    return False


def _coordinate_transform(change_x: Callable[[float], float]) -> Callable[..., Any]:
    def apply(x: Any, y: Any, z: Any = None) -> tuple[Any, ...]:
        try:
            changed = tuple(change_x(float(value)) for value in x)
        except TypeError:
            changed = change_x(float(x))
        return (changed, y) if z is None else (changed, y, z)

    return apply
