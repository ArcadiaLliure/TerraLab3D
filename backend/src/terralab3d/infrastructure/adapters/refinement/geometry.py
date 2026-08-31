"""Shapely/PyProj implementation of the metric coverage geometry port."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import GeometryCollection, LineString, Polygon, MultiPolygon, mapping, shape
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
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
        shape_left = self._shape(left)
        shape_right = self._shape(right)
        try:
            result = shape_left.intersection(shape_right)
        except Exception:
            result = shape_left.buffer(0).intersection(shape_right.buffer(0))
        return MetricGeometry(self._extract_polygons(result), left.crs)

    def difference(self, left: MetricGeometry, right: MetricGeometry) -> MetricGeometry:
        self._require_same_crs((left, right))
        shape_left = self._shape(left)
        shape_right = self._shape(right)
        try:
            result = shape_left.difference(shape_right)
        except Exception:
            result = shape_left.buffer(0).difference(shape_right.buffer(0))
        return MetricGeometry(self._extract_polygons(result), left.crs)

    def _extract_polygons(self, geometry: BaseGeometry) -> BaseGeometry:
        if geometry.is_empty:
            return geometry
        if isinstance(geometry, (Polygon, MultiPolygon)):
            return geometry
        if isinstance(geometry, GeometryCollection):
            polygons = [geom for geom in geometry.geoms if isinstance(geom, (Polygon, MultiPolygon))]
            if not polygons:
                return Polygon()
            return unary_union(polygons)
        return Polygon()

    def intersects(self, left: MetricGeometry, right: MetricGeometry) -> bool:
        self._require_same_crs((left, right))
        return bool(self._shape(left).intersects(self._shape(right)))

    def __init__(self) -> None:
        self._land_mask: BaseGeometry | None = None

    def _get_land_mask(self) -> BaseGeometry:
        if self._land_mask is None:
            import json
            from pathlib import Path
            path = Path(__file__).parent.parent.parent / "domain" / "refinement" / "land_mask.geojson"
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Natural Earth 110m json has features
                    if "features" in data:
                        geoms = [shape(feature["geometry"]) for feature in data["features"]]
                        from shapely.ops import unary_union
                        self._land_mask = unary_union(geoms)
                    else:
                        self._land_mask = shape(data)
            else:
                self._land_mask = Polygon()
        return self._land_mask

    def land_area(self, geometry: MetricGeometry) -> float:
        self._require_metric_crs(geometry.crs)
        mask_4326 = self._get_land_mask()
        if mask_4326.is_empty:
            return float(self._shape(geometry).area)
        
        source = _get_crs(geometry.crs)
        target = _get_crs("EPSG:4326")
        transformer_to = _get_transformer(geometry.crs, "EPSG:4326")
        geom_4326 = transform(transformer_to.transform, self._shape(geometry))
        
        intersection = geom_4326.intersection(mask_4326)
        if intersection.is_empty:
            return 0.0
            
        transformer_back = _get_transformer("EPSG:4326", geometry.crs)
        metric_intersection = transform(transformer_back.transform, intersection)
        return float(metric_intersection.area)

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
        source = _get_crs(source_crs)
        self._require_metric_crs(target_crs)
        concrete = shape(dict(geometry))
        if concrete.is_empty or not concrete.is_valid:
            raise RefinementValidationError("Coverage GeoJSON must be valid and non-empty")
        if source.is_geographic:
            concrete = _normalize_antimeridian(concrete)
        transformer = _get_transformer(source_crs, target_crs)
        projected = transform(transformer.transform, concrete)
        if projected.is_empty or not projected.is_valid:
            raise RefinementValidationError("Projected coverage geometry is invalid")
        return MetricGeometry(projected, target_crs)

    def to_geojson(
        self,
        geometry: MetricGeometry,
        *,
        target_crs: str | None = None,
    ) -> dict[str, object]:
        concrete = self._shape(geometry)
        if target_crs is not None:
            transformer = _get_transformer(geometry.crs, target_crs)
            concrete = transform(transformer.transform, concrete)
        return dict(mapping(concrete))

    def simplify_for_visualization(self, geometry: MetricGeometry) -> MetricGeometry:
        """Reduce vertex count and fill slivers for fast browser rendering."""
        self._require_metric_crs(geometry.crs)
        concrete = self._shape(geometry)
        if concrete.is_empty:
            return geometry
        # Fill tiny sliver gaps (100m) between grid tiles and simplify (500m)
        try:
            simplified = concrete.buffer(100).buffer(-100).simplify(500, preserve_topology=False)
        except Exception:
            simplified = concrete.simplify(1000, preserve_topology=False)
        return MetricGeometry(self._extract_polygons(simplified), geometry.crs)

    def reproject(self, geometry: MetricGeometry, target_crs: str) -> MetricGeometry:
        self._require_metric_crs(geometry.crs)
        self._require_metric_crs(target_crs)
        transformer = _get_transformer(geometry.crs, target_crs)
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
        first = _get_crs(geometries[0].crs)
        if any(not first.equals(_get_crs(item.crs)) for item in geometries[1:]):
            raise RefinementValidationError("Geometry operands use different CRS values")

    @staticmethod
    def _require_metric_crs(crs_value: str) -> None:
        crs = _get_crs(crs_value)
        if not crs.is_projected:
            raise RefinementValidationError("Coverage area requires a projected CRS")
        units = {axis.unit_name.lower() for axis in crs.axis_info if axis.unit_name}
        if not units or not all("metre" in unit or "meter" in unit for unit in units):
            raise RefinementValidationError("Coverage CRS axes must use metres")


@lru_cache(maxsize=128)
def _get_crs(crs_value: str) -> CRS:
    return CRS.from_user_input(crs_value)


@lru_cache(maxsize=128)
def _get_transformer(source_crs: str, target_crs: str) -> Transformer:
    source = _get_crs(source_crs)
    target = _get_crs(target_crs)
    return Transformer.from_crs(source, target, always_xy=True)


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

    if isinstance(geometry, Polygon):
        return ring_jumps(list(geometry.exterior.coords)) or any(
            ring_jumps(list(ring.coords)) for ring in geometry.interiors
        )
    if isinstance(geometry, BaseMultipartGeometry):
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
