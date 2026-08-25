"""Pure coverage calculations over opaque metric geometries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .errors import RefinementValidationError


class CoverageGeometry(Protocol):
    """Minimal geometry algebra required by the pure coverage rules."""

    def union(self, geometries: Sequence[MetricGeometry]) -> MetricGeometry: ...

    def intersection(self, left: MetricGeometry, right: MetricGeometry) -> MetricGeometry: ...

    def difference(self, left: MetricGeometry, right: MetricGeometry) -> MetricGeometry: ...

    def area(self, geometry: MetricGeometry) -> float: ...

    def is_empty(self, geometry: MetricGeometry) -> bool: ...


@dataclass(frozen=True, slots=True)
class MetricGeometry:
    """Opaque geometry known to be expressed in a projected metric CRS."""

    value: object
    crs: str

    def __post_init__(self) -> None:
        normalized = self.crs.strip().upper()
        if not normalized:
            raise RefinementValidationError("Coverage geometry CRS is required")
        if normalized in {"EPSG:4326", "OGC:CRS84", "CRS:84"}:
            raise RefinementValidationError(
                "Coverage calculations require a projected metric CRS, not longitude/latitude"
            )


@dataclass(frozen=True, slots=True)
class CoverageResult:
    existing: MetricGeometry
    new_effective: MetricGeometry
    planned: MetricGeometry
    remaining_gap: MetricGeometry
    existing_ratio: float
    new_effective_ratio: float
    planned_ratio: float
    remaining_ratio: float


@dataclass(frozen=True, slots=True)
class ProductFootprint:
    product_id: str
    geometry: MetricGeometry
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise RefinementValidationError("Product footprint id is required")


@dataclass(frozen=True, slots=True)
class ProductContribution:
    product_id: str
    available_ratio: float
    already_local_ratio: float
    new_effective_ratio: float
    previous_selection_overlap_ratio: float


@dataclass(frozen=True, slots=True)
class CoveragePlan:
    selected_product_ids: tuple[str, ...]
    planned_ratio: float
    remaining_ratio: float


def calculate_coverage(
    aoi: MetricGeometry,
    local_verified: Sequence[MetricGeometry],
    selected_products: Sequence[MetricGeometry],
    geometry: CoverageGeometry,
) -> CoverageResult:
    """Calculate A∩L, (A∩P)-L, A∩(L∪P), and A-(L∪P)."""

    _require_same_crs((aoi, *local_verified, *selected_products))
    local_union = _union_or_empty(aoi, local_verified, geometry)
    product_union = _union_or_empty(aoi, selected_products, geometry)
    local_and_products = geometry.union((local_union, product_union))
    existing = geometry.intersection(aoi, local_union)
    new_effective = geometry.difference(
        geometry.intersection(aoi, product_union),
        local_union,
    )
    planned = geometry.intersection(aoi, local_and_products)
    remaining = geometry.difference(aoi, local_and_products)
    aoi_area = geometry.area(aoi)
    if aoi_area <= 0:
        raise RefinementValidationError("AOI must have positive metric area")
    return CoverageResult(
        existing=existing,
        new_effective=new_effective,
        planned=planned,
        remaining_gap=remaining,
        existing_ratio=_ratio(geometry.area(existing), aoi_area),
        new_effective_ratio=_ratio(geometry.area(new_effective), aoi_area),
        planned_ratio=_ratio(geometry.area(planned), aoi_area),
        remaining_ratio=_ratio(geometry.area(remaining), aoi_area),
    )


def evaluate_product_contributions(
    aoi: MetricGeometry,
    local_verified: Sequence[MetricGeometry],
    products: Sequence[ProductFootprint],
    geometry: CoverageGeometry,
) -> tuple[ProductContribution, ...]:
    """Evaluate products in caller priority order without double counting gains."""

    _require_same_crs((aoi, *local_verified, *(product.geometry for product in products)))
    aoi_area = geometry.area(aoi)
    if aoi_area <= 0:
        raise RefinementValidationError("AOI must have positive metric area")
    local_union = _union_or_empty(aoi, local_verified, geometry)
    previous = geometry.difference(aoi, aoi)
    occupied = local_union
    contributions: list[ProductContribution] = []
    for product in products:
        available = geometry.intersection(aoi, product.geometry)
        local_overlap = geometry.intersection(available, local_union)
        previous_overlap = geometry.intersection(available, previous)
        new_effective = geometry.difference(available, occupied)
        contributions.append(
            ProductContribution(
                product_id=product.product_id,
                available_ratio=_ratio(geometry.area(available), aoi_area),
                already_local_ratio=_ratio(geometry.area(local_overlap), aoi_area),
                new_effective_ratio=_ratio(geometry.area(new_effective), aoi_area),
                previous_selection_overlap_ratio=_ratio(
                    geometry.area(previous_overlap),
                    aoi_area,
                ),
            )
        )
        previous = geometry.union((previous, available))
        occupied = geometry.union((occupied, available))
    return tuple(contributions)


def greedy_coverage_plan(
    aoi: MetricGeometry,
    local_verified: Sequence[MetricGeometry],
    products: Sequence[ProductFootprint],
    geometry: CoverageGeometry,
    *,
    target_ratio: float = 0.995,
) -> CoveragePlan:
    """Greedy set-cover extension point with deterministic tie breaking."""

    if target_ratio <= 0 or target_ratio > 1:
        raise RefinementValidationError("Coverage target ratio must satisfy 0 < target <= 1")
    _require_same_crs((aoi, *local_verified, *(product.geometry for product in products)))
    aoi_area = geometry.area(aoi)
    if aoi_area <= 0:
        raise RefinementValidationError("AOI must have positive metric area")
    occupied = geometry.intersection(
        aoi,
        _union_or_empty(aoi, local_verified, geometry),
    )
    remaining = list(products)
    selected: list[str] = []
    while _ratio(geometry.area(occupied), aoi_area) < target_ratio and remaining:
        ranked: list[tuple[float, int, str, ProductFootprint, MetricGeometry]] = []
        for product in remaining:
            available = geometry.intersection(aoi, product.geometry)
            gain = geometry.difference(available, occupied)
            ranked.append(
                (
                    geometry.area(gain),
                    product.priority,
                    product.product_id,
                    product,
                    available,
                )
            )
        ranked.sort(key=lambda value: (-value[0], value[1], value[2]))
        gain_area, _, _, winner, available = ranked[0]
        if gain_area <= 0:
            break
        selected.append(winner.product_id)
        occupied = geometry.union((occupied, available))
        remaining = [item for item in remaining if item.product_id != winner.product_id]
    planned_ratio = _ratio(geometry.area(occupied), aoi_area)
    return CoveragePlan(
        selected_product_ids=tuple(selected),
        planned_ratio=planned_ratio,
        remaining_ratio=max(0.0, 1.0 - planned_ratio),
    )


def _require_same_crs(geometries: Sequence[MetricGeometry]) -> None:
    crs_values = {item.crs for item in geometries}
    if len(crs_values) > 1:
        raise RefinementValidationError(
            "Coverage operands must already use the same projected metric CRS"
        )


def _union_or_empty(
    aoi: MetricGeometry,
    geometries: Sequence[MetricGeometry],
    operations: CoverageGeometry,
) -> MetricGeometry:
    if geometries:
        return operations.union(tuple(geometries))
    return operations.difference(aoi, aoi)


def _ratio(area: float, total: float) -> float:
    return min(1.0, max(0.0, area / total))
