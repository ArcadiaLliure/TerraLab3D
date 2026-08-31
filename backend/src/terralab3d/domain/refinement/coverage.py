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
    
    def intersects(self, left: MetricGeometry, right: MetricGeometry) -> bool: ...

    def area(self, geometry: MetricGeometry) -> float: ...

    def land_area(self, geometry: MetricGeometry) -> float: ...

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
    remaining_gap = geometry.difference(aoi, local_and_products)

    aoi_area = geometry.land_area(aoi)
    if aoi_area <= 0:
        return CoverageResult(existing, new_effective, planned, remaining_gap, 0, 0, 0, 0)

    return CoverageResult(
        existing=existing,
        new_effective=new_effective,
        planned=planned,
        remaining_gap=remaining_gap,
        existing_ratio=geometry.land_area(existing) / aoi_area,
        new_effective_ratio=geometry.land_area(new_effective) / aoi_area,
        planned_ratio=geometry.land_area(planned) / aoi_area,
        remaining_ratio=geometry.land_area(remaining_gap) / aoi_area,
    )


def evaluate_product_contributions(
    aoi: MetricGeometry,
    local_verified: Sequence[MetricGeometry],
    products: Sequence[ProductFootprint],
    geometry: CoverageGeometry,
    progress_callback: Callable[[float, str], None] | None = None,
) -> tuple[ProductContribution, ...]:
    """Evaluate products in caller priority order without double counting gains."""

    _require_same_crs((aoi, *local_verified, *(p.geometry for p in products)))
    local_union = _union_or_empty(aoi, local_verified, geometry)
    aoi_area = geometry.land_area(aoi)
    if aoi_area <= 0:
        return ()

    import logging
    import time
    logger = logging.getLogger(__name__)
    t_start = time.monotonic()
    
    total = len(products)
    contributions: list[ProductContribution] = []

    for idx, product in enumerate(products):
        if progress_callback is not None and idx % 20 == 0:
            progress_callback(idx / max(1, total), f"{idx}/{total}")

        available = geometry.intersection(aoi, product.geometry)
        local_overlap = geometry.intersection(available, local_union)
        new_effective = geometry.difference(available, local_union)

        contributions.append(
            ProductContribution(
                product_id=product.product_id,
                available_ratio=_ratio(geometry.land_area(available), aoi_area),
                already_local_ratio=_ratio(geometry.land_area(local_overlap), aoi_area),
                new_effective_ratio=_ratio(geometry.land_area(new_effective), aoi_area),
                previous_selection_overlap_ratio=0.0,
            )
        )
        
    logger.info("MGP: evaluate_product_contributions took %.2f seconds", time.monotonic() - t_start)
    return tuple(contributions)


def greedy_coverage_plan(
    aoi: MetricGeometry,
    local_verified: Sequence[MetricGeometry],
    products: Sequence[ProductFootprint],
    geometry: CoverageGeometry,
    *,
    target_ratio: float = 0.995,
    progress_callback: Callable[[float, str], None] | None = None,
) -> CoveragePlan:
    """Greedy set-cover extension point with deterministic tie breaking."""

    if target_ratio <= 0 or target_ratio > 1:
        raise RefinementValidationError("Coverage target ratio must satisfy 0 < target <= 1")
    _require_same_crs((aoi, *local_verified, *(product.geometry for product in products)))
    aoi_area = geometry.land_area(aoi)
    if aoi_area <= 0:
        return CoveragePlan((), 0.0, 0.0)
        
    local_occupied = geometry.intersection(
        aoi,
        _union_or_empty(aoi, local_verified, geometry),
    )
    
    occupied_union = local_occupied
    total_occupied_area = geometry.land_area(local_occupied) if not geometry.is_empty(local_occupied) else 0.0

    import logging
    import time
    import heapq
    logger = logging.getLogger(__name__)
    logger.info("MGP: Starting greedy_coverage_plan for %d products", len(products))
    
    remaining_items = []
    for product in products:
        gain = geometry.difference(
            geometry.intersection(aoi, product.geometry),
            occupied_union
        )
        area = geometry.land_area(gain)
        if area >= 1.0:
            remaining_items.append([-area, product.priority, product.product_id, gain, product, 0])

    heapq.heapify(remaining_items)
    
    selected: list[str] = []
    selected_gains: list[MetricGeometry] = []
    iteration = 0
    max_iterations = len(products)
    
    t_start = time.monotonic()
    while _ratio(total_occupied_area, aoi_area) < target_ratio and remaining_items:
        item = heapq.heappop(remaining_items)
        neg_area, priority, product_id, gain, product, last_update = item
        
        if last_update < len(selected_gains):
            for i in range(last_update, len(selected_gains)):
                gain = geometry.difference(gain, selected_gains[i])
                if geometry.is_empty(gain):
                    break
            
            true_area = geometry.land_area(gain)
            if true_area >= 1.0:
                heapq.heappush(remaining_items, [-true_area, priority, product_id, gain, product, len(selected_gains)])
            continue
            
        iteration += 1
        if progress_callback is not None:
            progress_callback(iteration / max(1, max_iterations), f"{iteration}/{max_iterations}")
            
        logger.info("MGP: greedy_coverage_plan iteration %d picked %s in %.2fs. Total pieces: %d. Gain: %.4f", iteration, product_id, time.monotonic() - t_start, len(selected), -neg_area)
        selected.append(product_id)
        selected_gains.append(gain)
        total_occupied_area += -neg_area
        t_start = time.monotonic()
        
    planned_ratio = _ratio(total_occupied_area, aoi_area)
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
