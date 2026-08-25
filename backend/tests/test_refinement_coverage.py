from __future__ import annotations

import math

import pytest
from shapely.geometry import MultiPolygon, Polygon, box

from terralab3d.domain.refinement.coverage import (
    MetricGeometry,
    ProductFootprint,
    calculate_coverage,
    evaluate_product_contributions,
    greedy_coverage_plan,
)
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.states import (
    LeafCoverageFacts,
    SpatialCoverageState,
    aggregate_coverage_states,
    leaf_coverage_state,
)
from terralab3d.infrastructure.adapters.refinement.geometry import ShapelyGeometryAdapter


CRS = "EPSG:25831"


def _metric(value: object) -> MetricGeometry:
    return MetricGeometry(value, CRS)


def test_coverage_intersection_union_difference_and_partial_aoi() -> None:
    geometry = ShapelyGeometryAdapter()
    result = calculate_coverage(
        _metric(box(0, 0, 100, 100)),
        (_metric(box(0, 0, 40, 100)),),
        (_metric(box(30, 0, 80, 100)),),
        geometry,
    )

    assert result.existing_ratio == pytest.approx(0.4)
    assert result.new_effective_ratio == pytest.approx(0.4)
    assert result.planned_ratio == pytest.approx(0.8)
    assert result.remaining_ratio == pytest.approx(0.2)


def test_coverage_preserves_holes_and_multipolygons() -> None:
    geometry = ShapelyGeometryAdapter()
    aoi_with_hole = Polygon(
        ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)),
        holes=(((40, 40), (60, 40), (60, 60), (40, 60), (40, 40)),),
    )
    product = MultiPolygon((box(0, 0, 30, 100), box(70, 0, 100, 100)))

    result = calculate_coverage(_metric(aoi_with_hole), (), (_metric(product),), geometry)

    assert result.planned_ratio == pytest.approx(6000 / 9600)
    assert result.remaining_ratio == pytest.approx(3600 / 9600)


def test_product_contributions_do_not_double_count_previous_products() -> None:
    geometry = ShapelyGeometryAdapter()
    products = (
        ProductFootprint("first", _metric(box(20, 0, 70, 100))),
        ProductFootprint("second", _metric(box(60, 0, 100, 100))),
    )

    contributions = evaluate_product_contributions(
        _metric(box(0, 0, 100, 100)),
        (_metric(box(0, 0, 30, 100)),),
        products,
        geometry,
    )

    assert contributions[0].available_ratio == pytest.approx(0.5)
    assert contributions[0].already_local_ratio == pytest.approx(0.1)
    assert contributions[0].new_effective_ratio == pytest.approx(0.4)
    assert contributions[1].previous_selection_overlap_ratio == pytest.approx(0.1)
    assert contributions[1].new_effective_ratio == pytest.approx(0.3)


def test_greedy_set_cover_selects_largest_effective_gain_deterministically() -> None:
    geometry = ShapelyGeometryAdapter()
    plan = greedy_coverage_plan(
        _metric(box(0, 0, 100, 100)),
        (_metric(box(0, 0, 20, 100)),),
        (
            ProductFootprint("small", _metric(box(20, 0, 50, 100))),
            ProductFootprint("large", _metric(box(20, 0, 90, 100))),
            ProductFootprint("tail", _metric(box(90, 0, 100, 100))),
        ),
        geometry,
    )

    assert plan.selected_product_ids == ("large", "tail")
    assert plan.planned_ratio == pytest.approx(1.0)
    assert plan.remaining_ratio == pytest.approx(0.0)


def test_geographic_crs_is_rejected_for_area_calculation() -> None:
    with pytest.raises(RefinementValidationError, match="projected metric CRS"):
        MetricGeometry(box(0, 0, 1, 1), "EPSG:4326")


def test_reprojection_to_local_metric_crs() -> None:
    geometry = ShapelyGeometryAdapter()
    projected = geometry.from_geojson(
        {
            "type": "Polygon",
            "coordinates": (((2.0, 41.0), (2.1, 41.0), (2.1, 41.1), (2.0, 41.1), (2.0, 41.0)),),
        },
        source_crs="EPSG:4326",
        target_crs="EPSG:25831",
    )

    assert 80_000_000 < geometry.area(projected) < 100_000_000


def test_antimeridian_polygon_is_split_before_global_equal_area_projection() -> None:
    geometry = ShapelyGeometryAdapter()
    projected = geometry.from_geojson(
        {
            "type": "Polygon",
            "coordinates": (((170, -10), (-170, -10), (-170, 10), (170, 10), (170, -10)),),
        },
        source_crs="EPSG:4326",
        target_crs="EPSG:6933",
    )

    area = geometry.area(projected)
    assert math.isfinite(area)
    assert 4e12 < area < 6e12


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (LeafCoverageFacts(0.995, 0), SpatialCoverageState.COMPLETE),
        (LeafCoverageFacts(0.994, 0), SpatialCoverageState.PARTIAL),
        (LeafCoverageFacts(0, 0.4), SpatialCoverageState.PARTIAL),
        (LeafCoverageFacts(0, 0, active_job=True), SpatialCoverageState.PARTIAL),
        (LeafCoverageFacts(0, 0), SpatialCoverageState.ABSENT),
        (LeafCoverageFacts(0, 0, applicable=False), SpatialCoverageState.NOT_APPLICABLE),
    ],
)
def test_leaf_state_uses_configurable_995_threshold(
    facts: LeafCoverageFacts,
    expected: SpatialCoverageState,
) -> None:
    assert leaf_coverage_state(facts) is expected


@pytest.mark.parametrize(
    ("children", "expected"),
    [
        ((SpatialCoverageState.COMPLETE, SpatialCoverageState.COMPLETE), SpatialCoverageState.COMPLETE),
        ((SpatialCoverageState.ABSENT, SpatialCoverageState.ABSENT), SpatialCoverageState.ABSENT),
        ((SpatialCoverageState.COMPLETE, SpatialCoverageState.ABSENT), SpatialCoverageState.PARTIAL),
        ((SpatialCoverageState.PARTIAL, SpatialCoverageState.ABSENT), SpatialCoverageState.PARTIAL),
        ((SpatialCoverageState.NOT_APPLICABLE,), SpatialCoverageState.NOT_APPLICABLE),
        (
            (SpatialCoverageState.COMPLETE, SpatialCoverageState.NOT_APPLICABLE),
            SpatialCoverageState.COMPLETE,
        ),
    ],
)
def test_parent_state_aggregates_only_applicable_descendants(
    children: tuple[SpatialCoverageState, ...],
    expected: SpatialCoverageState,
) -> None:
    assert aggregate_coverage_states(children) is expected
