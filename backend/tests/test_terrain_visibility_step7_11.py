"""Topologia física del DEM, discontinuïtats i compatibilitat del transport."""

from dataclasses import replace
import math
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from terrain_fixtures_step7_11 import grid_surface, request
from terralab3d.application.terrain_visibility_builder import build_terrain_surface
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    make_ray,
)
from terralab3d.domain.light_pollution.propagation_kernel import (
    PropagationKernel,
    PropagationCancelledError,
    StalePropagationError,
)
from terralab3d.domain.light_pollution.reference_single_scattering import (
    solve_reference_b1,
)
from terralab3d.domain.light_pollution.reference_terrain import ReferenceTerrain
from terralab3d.domain.light_pollution.single_scattering import (
    SingleScatteringTransport,
)
from terralab3d.domain.light_pollution.source_model import GeodeticPosition
from terralab3d.domain.light_pollution.terrain_visibility import (
    TerrainCoverageError,
    TerrainVisibility,
    visible_area_nodes,
)
from terralab3d.infrastructure.adapters.dem.adapter import RasterioElevationAdapter


def test_dem_adapter_pipeline_and_nodata(tmp_path):
    path = tmp_path / "prescribed.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=3,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-0.015, 0.015, 0.01, 0.01),
        nodata=-9999.0,
    ) as f:
        f.write(
            np.array([[10, 20, 30], [10, 20, 30], [10, 20, 30]], dtype="float32"), 1
        )
    frame = SphericalFrame(GeodeticPosition(0, 0, 0))
    dem = RasterioElevationAdapter(path)
    try:
        args = (dem, (-0.01, 0.0, 0.01), (-0.01, 0.0, 0.01), frame)
        surface = build_terrain_surface(
            *args,
            upper_envelope_m=40,
            height_interpretation="identitat prescrita radial",
            height_to_radial=lambda h: h,
        )
        assert len(surface.faces) == 8
        assert "dem:prescribed" in surface.provenance
        assert math.hypot(*surface.vertices[4]) - frame.radius_m == pytest.approx(20)
        with pytest.raises(TerrainCoverageError):
            build_terrain_surface(
                dem,
                (-1.0, 0.0),
                (0.0, 1.0),
                frame,
                upper_envelope_m=40,
                height_interpretation="prescrit",
                height_to_radial=lambda h: h,
            )
    finally:
        dem.close()


def test_mountain_observer_first_hit_matches_independent():
    req = request(elevation=5)
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000)
    vis = TerrainVisibility(req.terrain, lambda: None)
    length = vis.clip_observer(ray)
    assert 2000 < length < 2500
    ref = ReferenceTerrain(req.terrain)
    assert length == pytest.approx(
        ref.clip(
            np.array(ray.origin_ecef_m), np.array(ray.direction_ecef), ray.length_m
        ),
        abs=1e-7,
    )
    result = PropagationKernel().evaluate(req)
    assert result.rays[0].path_length_m == length


def test_point_shadow_break_is_binary_and_explicit():
    req = request()
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000)
    source = SphericalFrame(req.observer).position_ecef(
        req.sources[0].geometry.position
    )
    vis = TerrainVisibility(req.terrain, lambda: None)
    plan = vis.plan(source, ray)
    flips = [
        s for i, s in enumerate(plan.cuts[1:-1]) if plan.mask[i] != plan.mask[i + 1]
    ]
    assert len(flips) == 1
    flip = flips[0]
    assert plan.at(flip) == vis.visible(source, ray.point(flip))
    assert not plan.at(flip - 1e-4)
    assert plan.at(flip + 1e-4)
    assert vis.visible(source, ray.point(flip - 1e-4)) is False
    assert vis.visible(source, ray.point(flip + 1e-4)) is True


def test_earth_curvature_blocks_far_chord_but_not_elevated_path():
    easts = tuple(float(x) for x in range(-10000, 211000, 10000))
    surface = grid_surface(easts, (-10000.0, 0.0, 10000.0), [[0.0] * len(easts)] * 3)
    frame = SphericalFrame(GeodeticPosition(0, 0, 0))
    a = frame.position_ecef(GeodeticPosition(0, 0, 100))
    b = frame.position_ecef(
        GeodeticPosition(0, math.degrees(200000 / frame.radius_m), 100)
    )
    high = frame.position_ecef(
        GeodeticPosition(0, math.degrees(200000 / frame.radius_m), 10000)
    )
    vis = TerrainVisibility(surface, lambda: None)
    assert not vis.visible(a, b)
    assert vis.visible(a, high)
    assert not ReferenceTerrain(surface).visible(np.array(a), np.array(b))
    assert ReferenceTerrain(surface).visible(np.array(a), np.array(high))


def test_partial_rectangle_integrates_visible_geometry():
    req = request(area=True)
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000)
    transport = SingleScatteringTransport(
        req.sources[0],
        req.optical_field,
        req.scattering,
        ray,
        4096,
        lambda: None,
        set(),
    )
    visibility = TerrainVisibility(req.terrain, lambda: None)
    transport.attach_terrain(visibility)
    # Prop del límit de l'ombra: la superfície emissora queda parcialment visible.
    point = ray.point(2300.0)
    nodes = visible_area_nodes(visibility, point, transport.corners, 160000.0, 4)
    fraction = sum(w for _, w in nodes)
    ref = ReferenceTerrain(req.terrain)
    center = np.mean(transport.corners, axis=0)
    u = (np.array(transport.corners[1]) - transport.corners[0]) / 400
    v = (np.array(transport.corners[3]) - transport.corners[0]) / 400
    _, weights = ref.area_nodes(np.array(point), center, u, v, 400, 400, 4)
    assert 0 < fraction < 1
    assert fraction == pytest.approx(sum(weights), abs=2e-9)
    assert all(visibility.visible(node, point) for node, _ in nodes)


@pytest.mark.parametrize("mode", ["B0", "B1", "B2", "B4"])
def test_modes_remain_compatible_and_metadata_explicit(mode):
    req = request(mode)
    result = PropagationKernel().evaluate(req)
    assert result.to_dict()["schemaVersion"] == 5
    assert result.terrain_metadata["surfaceSignature"] == req.terrain.signature
    assert result.integral_unit
    old = PropagationKernel().evaluate(replace(req, terrain=None))
    assert "terrain_metadata" not in old.to_dict()
    if mode != "B0":
        assert 0 < result.rays[0].integral < old.rays[0].integral


def test_b1_diagnostic_reference_and_topology():
    req = request()
    result = PropagationKernel().evaluate(req)
    ref = solve_reference_b1(
        req.sources[0],
        req.observer,
        90,
        90,
        req.optical_field,
        req.scattering.band,
        10000,
        terrain=req.terrain,
    )
    # Contrast diagnòstic; el llindar radiomètric runtime es preregistra a 7.12.
    assert ref.value > 0 and result.rays[0].integral > 0


def test_missing_coverage_under_ground_and_invalid_mesh():
    req = request()
    vis = TerrainVisibility(req.terrain, lambda: None)
    frame = SphericalFrame(req.observer)
    with pytest.raises(TerrainCoverageError):
        vis.visible(
            frame.position_ecef(GeodeticPosition(0, 1, 1)),
            frame.position_ecef(GeodeticPosition(0, 2, 100)),
        )
    with pytest.raises(ValueError, match="sota"):
        vis.assert_above(
            frame.position_ecef(
                GeodeticPosition(0, math.degrees(2500 / frame.radius_m), 500)
            )
        )
    with pytest.raises(ValueError):
        replace(req.terrain, faces=req.terrain.faces[:-1])
    with pytest.raises(ValueError):
        replace(req.terrain, upper_envelope_m=1)


def test_cancel_stale_and_budget_abort():
    req = request()
    with pytest.raises(PropagationCancelledError):
        PropagationKernel().evaluate(req, cancelled=lambda: True)
    with pytest.raises(StalePropagationError):
        PropagationKernel().evaluate(req, is_current=lambda: False)
    with pytest.raises(ValueError, match="Pressupost"):
        PropagationKernel().evaluate(
            replace(req, options=replace(req.options, max_segments_per_ray=2))
        )


def test_contact_at_ground_looking_into_slope_is_zero():
    req = request(elevation=5)
    req = replace(
        req,
        observer=GeodeticPosition(
            0, math.degrees(2000 / req.options.earth_radius_m), 0
        ),
    )
    result = PropagationKernel().evaluate(req)
    assert result.rays[0].path_length_m == 0
    assert result.rays[0].integral == 0
    assert result.counters.quadrature_node_count == 0


def test_coplanar_contact_is_opaque_and_reciprocal():
    from terralab3d.domain.light_pollution.terrain_visibility import TerrainSurface

    radius = 6371008.8
    surface = TerrainSurface(
        ((radius, 0.0, 0.0), (radius, 100.0, 0.0), (radius, 0.0, 100.0)),
        ((0, 1, 2),),
        (0, 1, 2),
        radius,
        1.0,
        "triangle pla prescrit",
        "radial prescrit",
    )
    vis = TerrainVisibility(surface, lambda: None)
    a, b = (radius, 10.0, 10.0), (radius, 50.0, 10.0)
    assert not vis.visible(a, b)
    assert not vis.visible(b, a)
    assert not ReferenceTerrain(surface).visible(np.array(a), np.array(b))


def test_reference_terrain_does_not_use_runtime(monkeypatch):
    req = request()

    def forbidden(*args, **kwargs):
        raise AssertionError("SG-REF ha cridat visibilitat runtime")

    monkeypatch.setattr(TerrainVisibility, "visible", forbidden)
    monkeypatch.setattr(TerrainVisibility, "shadow_cuts", forbidden)
    ref = solve_reference_b1(
        req.sources[0],
        req.observer,
        90,
        90,
        req.optical_field,
        req.scattering.band,
        10000,
        terrain=req.terrain,
    )
    assert ref.value > 0


def test_cancellation_during_visibility():
    req = request()
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        return calls > 15

    with pytest.raises(PropagationCancelledError):
        PropagationKernel().evaluate(req, cancelled=cancelled)
    assert calls == 16


def test_occluded_observer_prefix_does_not_require_dem_behind_wall():
    req = request(elevation=0.5)
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000)
    vis = TerrainVisibility(req.terrain, lambda: None)
    with pytest.raises(TerrainCoverageError):
        vis.coverage(ray.origin_ecef_m, ray.point(ray.length_m))
    assert 2000 < vis.clip_observer(ray) < 2500
    assert PropagationKernel().evaluate(req).rays[0].path_length_m < 2500


def test_geometry_plan_work_is_independent_of_spectral_node_count():
    req = request("B4")
    small = replace(
        req,
        spectral=replace(
            req.spectral, wavelength_start_nm=549.0, wavelength_end_nm=551.0
        ),
    )
    wide = PropagationKernel().evaluate(req)
    narrow = PropagationKernel().evaluate(small)
    for name in (
        "shadow_planes",
        "visibility_intervals",
        "triangle_tests",
        "segment_checks",
    ):
        assert (
            wide.terrain_metadata["work"][name] == narrow.terrain_metadata["work"][name]
        )


def test_terrain_signature_and_radius_are_authoritative():
    req = request()
    first = PropagationKernel().evaluate(req)
    second = PropagationKernel().evaluate(
        replace(req, terrain=replace(req.terrain, revision="revised"))
    )
    assert first.input_signature != second.input_signature
    assert first.optical_dependency_signature != second.optical_dependency_signature
    with pytest.raises(ValueError, match="radis"):
        replace(req, terrain=replace(req.terrain, radius_m=req.terrain.radius_m + 1))


def test_observer_coplanar_contact_truncates_immediately():
    from terralab3d.domain.light_pollution.terrain_visibility import TerrainSurface
    from terralab3d.domain.light_pollution.geometric_transport import RayGeometry

    radius = 6371008.8
    surface = TerrainSurface(
        ((radius, 0.0, 0.0), (radius, 100.0, 0.0), (radius, 0.0, 100.0)),
        ((0, 1, 2),),
        (0, 1, 2),
        radius,
        1.0,
        "triangle pla prescrit",
        "radial prescrit",
    )
    a, d = (radius, 10.0, 10.0), (0.0, 1.0, 0.0)
    ray = RayGeometry(a, d, (1.0, 0.0, 0.0), 20.0, radius, 0.0)
    assert TerrainVisibility(surface, lambda: None).clip_observer(ray) == 0
    assert ReferenceTerrain(surface).clip(np.array(a), np.array(d), 20.0) == 0


def test_reference_ground_slope_contact_is_zero():
    req = request(elevation=5)
    req = replace(
        req,
        observer=GeodeticPosition(
            0, math.degrees(2000 / req.options.earth_radius_m), 0
        ),
    )
    ref = solve_reference_b1(
        req.sources[0],
        req.observer,
        90,
        5,
        req.optical_field,
        req.scattering.band,
        10000,
        terrain=req.terrain,
    )
    assert ref.value == 0


def test_dem_internal_nodata_is_never_filled(tmp_path):
    path = tmp_path / "nodata.tif"
    values = np.full((3, 3), 10.0, dtype="float32")
    values[1, 1] = -9999.0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=3,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-0.015, 0.015, 0.01, 0.01),
        nodata=-9999.0,
    ) as f:
        f.write(values, 1)
    dem = RasterioElevationAdapter(path)
    try:
        with pytest.raises(TerrainCoverageError):
            build_terrain_surface(
                dem,
                (-0.01, 0.0, 0.01),
                (-0.01, 0.0, 0.01),
                SphericalFrame(GeodeticPosition(0, 0, 0)),
                upper_envelope_m=20,
                height_interpretation="radial prescrit",
                height_to_radial=lambda h: h,
            )
        with pytest.raises(ValueError, match="Pressupost"):
            build_terrain_surface(
                dem,
                (-0.01, 0.0, 0.01),
                (-0.01, 0.0, 0.01),
                SphericalFrame(GeodeticPosition(0, 0, 0)),
                upper_envelope_m=20,
                height_interpretation="radial prescrit",
                height_to_radial=lambda h: h,
                max_vertices=4,
            )
    finally:
        dem.close()
