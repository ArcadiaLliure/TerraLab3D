from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
import math
import threading
import time
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from terralab3d.application.horizon_coordinator import (
    HorizonCoordinator,
    pack_horizon_profile,
    pack_terrain_mesh,
)
from terralab3d.application.elevation_coordinator import ElevationCoordinator
from terralab3d.application.flight_terrain_refresh import (
    decide_flight_profile_refresh,
    decide_flight_stream_continuation,
    decide_visibility_window_refresh,
)
from terralab3d.application.terrain_mesh_builder import TerrainMeshBuilder
from terralab3d.domain.elevation.models import (
    ElevationBatch,
    ElevationBatchRequest,
    ElevationSample,
    ElevationSourceMetadata,
    ElevationStatus,
)
from terralab3d.domain.horizon.calculations import (
    apparent_elevation_degrees,
    curvature_parity_error_m,
    mask_after_consecutive_misses,
    reduce_horizon_samples,
    resolve_visible_radius_m,
)
from terralab3d.domain.horizon.models import (
    EARTH_RADIUS_M,
    HorizonProfileSettings,
    HorizonQuality,
    HorizonRangeMode,
    HorizonRequest,
)
from terralab3d.domain.horizon.services import HorizonVisibilityEnricher
from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId, TerrainTileId
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.terrain.models import TerrainTileRequest
from terralab3d.domain.solar_system.models import (
    ApparentBodyState,
    BodyKind,
    EphemerisQuality,
    SolarSystemSnapshot,
)
from terralab3d.infrastructure.adapters.dem.adapter import (
    DemSamplingCancelled,
    RasterioElevationAdapter,
)
from terralab3d.infrastructure.app_paths import resolve_elevation_data_dir


def test_flat_and_mountain_kernel_are_vectorized_and_nodata_aware() -> None:
    distances = np.asarray([100.0, 1_000.0, 2_000.0])
    terrain = np.asarray([
        [100.0, 100.0, 100.0],
        [100.0, 500.0, 100.0],
        [100.0, np.nan, 100.0],
        [0.0, 0.0, 0.0],
    ])
    valid = np.asarray([
        [True, True, True],
        [True, True, True],
        [True, False, True],
        [False, False, False],
    ])
    result = reduce_horizon_samples(
        distances,
        terrain,
        valid,
        102.0,
        effective_earth_radius_m=EARTH_RADIUS_M,
    )
    expected_flat = float(apparent_elevation_degrees(100.0, 2_000.0, 102.0, EARTH_RADIUS_M))
    expected_ridge = float(apparent_elevation_degrees(500.0, 1_000.0, 102.0, EARTH_RADIUS_M))
    assert result.horizon_elevation_deg[0] == pytest.approx(expected_flat, abs=1e-6)
    assert result.horizon_elevation_deg[1] == pytest.approx(expected_ridge, abs=1e-6)
    assert result.occluder_distance_m[1] == pytest.approx(1_000.0)
    assert result.occluder_height_m[1] == pytest.approx(500.0)
    assert result.valid_mask.tolist() == [True, True, True, False]
    assert result.horizon_elevation_deg[3] == 0.0


@pytest.mark.parametrize("distance_km", [1, 25, 150, 530])
def test_curvature_and_refraction_match_terralab_parity(distance_km: int) -> None:
    distance_m = distance_km * 1_000.0
    terrain = 1_000.0
    eye = 250.0
    without_refraction = float(apparent_elevation_degrees(
        terrain, distance_m, eye, EARTH_RADIUS_M,
    ))
    with_refraction = float(apparent_elevation_degrees(
        terrain, distance_m, eye, EARTH_RADIUS_M * 7.0 / 6.0,
    ))
    expected = math.degrees(math.atan2(
        terrain - distance_m * distance_m / (2 * EARTH_RADIUS_M) - eye,
        distance_m,
    ))
    assert without_refraction == pytest.approx(expected, abs=1e-12)
    assert with_refraction >= without_refraction
    assert math.isfinite(curvature_parity_error_m(distance_m))


def test_visual_dem_mesh_uses_spherical_coordinates_at_long_range() -> None:
    request = replace(
        _request(1),
        settings=HorizonProfileSettings(
            range_mode=HorizonRangeMode.MANUAL,
            visible_radius_km=530.0,
            angular_step_deg=5.0,
            atmospheric_refraction_enabled=False,
        ),
    )
    builder = TerrainMeshBuilder(_SyntheticElevationPort(), _IdentityProjector())
    distance_m = 530_000.0

    positions, valid = builder._sample_positions(  # noqa: SLF001
        request,
        np.asarray([distance_m]),
        np.asarray([0.0]),
        100.0,
        EARTH_RADIUS_M,
        threading.Event(),
    )

    theta = distance_m / EARTH_RADIUS_M
    assert valid.tolist() == [True]
    assert positions[0, 0] == pytest.approx(distance_m, abs=0.1)
    assert positions[0, 1] == pytest.approx(
        (EARTH_RADIUS_M + 100.0) * math.cos(theta) - (EARTH_RADIUS_M + 100.0),
        abs=0.1,
    )


def test_horizon_request_adds_the_fixed_observer_eye_height() -> None:
    request = _request(1)
    assert request.observer_eye_elevation_m == pytest.approx(103.7)


def test_flight_profile_request_can_retain_the_resident_world_mesh() -> None:
    coordinator = _coordinator(_SyntheticElevationPort())
    request = replace(_request(1), build_terrain_mesh=False)

    async def exercise() -> None:
        coordinator.request(request)
        await coordinator.wait_idle()

    asyncio.run(exercise())
    assert coordinator.active_profile is not None
    assert coordinator._active_terrain is None  # noqa: SLF001 - lifecycle contract


def test_full_terrain_request_marks_the_resident_world_mesh_ready() -> None:
    coordinator = _coordinator(_SyntheticElevationPort())

    async def exercise() -> None:
        coordinator.request(_request(1))
        await coordinator.wait_idle()

    asyncio.run(exercise())
    assert coordinator.has_active_terrain


def test_predictive_flight_refresh_never_starts_when_stationary() -> None:
    stopped = decide_flight_profile_refresh(
        distance_since_profile_m=50_000.0,
        eye_delta_m=500.0,
        speed_mps=0.0,
        measured_prepare_ms=30_000.0,
    )
    moving = decide_flight_profile_refresh(
        distance_since_profile_m=5_000.0,
        eye_delta_m=0.0,
        speed_mps=250.0,
        measured_prepare_ms=2_000.0,
    )

    assert stopped.should_refresh is False
    assert stopped.reason == "stationary"
    assert moving.should_refresh is True
    assert moving.reason == "predicted-boundary"
    assert moving.lead_distance_m == pytest.approx(3_000.0)


def test_stream_visibility_window_obeys_the_live_user_radius() -> None:
    unchanged = decide_visibility_window_refresh(
        distance_from_loaded_center_m=20.0,
        loaded_radius_m=150_000.0,
        requested_radius_m=150_000.0,
        lead_distance_m=10_000.0,
    )
    detail_moved = decide_visibility_window_refresh(
        distance_from_loaded_center_m=6_000.0,
        loaded_radius_m=150_000.0,
        requested_radius_m=150_000.0,
        lead_distance_m=10_000.0,
    )
    enlarged = decide_visibility_window_refresh(
        distance_from_loaded_center_m=20.0,
        loaded_radius_m=150_000.0,
        requested_radius_m=300_000.0,
        lead_distance_m=10_000.0,
    )
    consumed = decide_visibility_window_refresh(
        distance_from_loaded_center_m=142_000.0,
        loaded_radius_m=150_000.0,
        requested_radius_m=150_000.0,
        lead_distance_m=10_000.0,
    )
    forced = decide_visibility_window_refresh(
        distance_from_loaded_center_m=0.0,
        loaded_radius_m=150_000.0,
        requested_radius_m=80_000.0,
        lead_distance_m=0.0,
        force=True,
    )

    assert unchanged.should_refresh is False
    assert detail_moved.should_refresh is True
    assert detail_moved.reason == "detail-boundary"
    assert enlarged.should_refresh is True
    assert enlarged.requested_radius_m == pytest.approx(300_000.0)
    assert enlarged.reason == "range-changed"
    assert consumed.should_refresh is True
    assert forced.should_refresh is True
    assert forced.requested_radius_m == pytest.approx(80_000.0)


def test_visual_stream_keeps_a_useful_sweep_and_cancels_only_after_route_divergence() -> None:
    straight = decide_flight_stream_continuation(
        active_velocity_east_mps=250.0,
        active_velocity_north_mps=0.0,
        current_velocity_east_mps=250.0,
        current_velocity_north_mps=0.0,
    )
    gentle_turn = decide_flight_stream_continuation(
        active_velocity_east_mps=250.0,
        active_velocity_north_mps=0.0,
        current_velocity_east_mps=200.0,
        current_velocity_north_mps=100.0,
    )
    reverse_course = decide_flight_stream_continuation(
        active_velocity_east_mps=250.0,
        active_velocity_north_mps=0.0,
        current_velocity_east_mps=-250.0,
        current_velocity_north_mps=0.0,
    )
    stopped = decide_flight_stream_continuation(
        active_velocity_east_mps=250.0,
        active_velocity_north_mps=0.0,
        current_velocity_east_mps=0.0,
        current_velocity_north_mps=0.0,
    )
    assert straight.keep_active_build
    assert gentle_turn.keep_active_build
    assert not reverse_course.keep_active_build
    assert stopped.keep_active_build


@pytest.mark.parametrize(
    ("step", "expected_count"),
    [(5.0, 72), (0.5, 720), (0.05, 7_200), (0.005, 72_000)],
)
def test_angular_precision_preserves_ray_count_and_binary_size(
    step: float,
    expected_count: int,
) -> None:
    request = _request(1, step=step)
    coordinator = _coordinator(_SyntheticElevationPort())
    profile = coordinator._flat_profile(request)  # noqa: SLF001 - contract fixture
    metadata, payload = pack_horizon_profile(profile)
    assert profile.sample_count == expected_count
    assert metadata["sampleCount"] == expected_count
    assert len(payload) == expected_count * 13
    assert metadata["byteLength"] == expected_count * 13


def test_ephemeris_horizon_fields_remain_json_native_with_numpy_inputs() -> None:
    body = ApparentBodyState(
        body_id=CelestialBodyId("sun"),
        kind=BodyKind.SUN,
        equatorial=EquatorialCoordinate(0.0, 4.0),
        horizontal=HorizontalCoordinate(np.float64(4.0), np.float64(0.0)),
        direction_enu=(0.0, 0.0, 1.0),
        distance_km=149_597_870.7,
        angular_radius_deg=np.float64(0.25),
        illumination_fraction=1.0,
        phase_angle_deg=0.0,
        apparent_magnitude=-26.74,
        source="fixture",
        quality=EphemerisQuality.PRECISE,
        naif_id=10,
    )
    snapshot = SolarSystemSnapshot(
        generation=1,
        timestamp_utc=datetime(2026, 8, 14, tzinfo=timezone.utc),
        observer_generation=3,
        source="fixture",
        quality=EphemerisQuality.PRECISE,
        sun=body,
        moon=None,
        planets=(),
        compute_ms=1.0,
    )
    profile = _coordinator(_SyntheticElevationPort())._flat_profile(  # noqa: SLF001
        _request(1, observer_generation=3),
    )
    enriched = HorizonVisibilityEnricher().enrich(snapshot, profile)
    assert type(enriched.sun.horizon_visible) is bool
    assert type(enriched.sun.horizon_elevation_deg) is float
    json.dumps(enriched.to_dict())


def test_settings_validate_without_silent_degradation() -> None:
    assert HorizonProfileSettings(visible_radius_km=1, angular_step_deg=0.005).validated()
    assert HorizonProfileSettings(visible_radius_km=530, angular_step_deg=5).validated()
    with pytest.raises(ValueError):
        HorizonProfileSettings(visible_radius_km=531).validated()
    with pytest.raises(ValueError):
        HorizonProfileSettings(angular_step_deg=0.004).validated()
    user_selected = HorizonProfileSettings(
        range_mode=HorizonRangeMode.MANUAL,
        visible_radius_km=530.0,
    ).validated()
    assert resolve_visible_radius_m(user_selected, observer_eye_elevation_m=100.0) == 530_000.0


def test_eight_consecutive_misses_end_coverage_but_short_holes_do_not() -> None:
    short_hole = np.ones((1, 20), dtype=np.bool_)
    short_hole[:, 3:10] = False
    assert mask_after_consecutive_misses(short_hole).tolist() == short_hole.tolist()
    long_hole = np.ones((1, 20), dtype=np.bool_)
    long_hole[:, 3:11] = False
    masked = mask_after_consecutive_misses(long_hole)
    assert masked[0, :3].all()
    assert not masked[0, 11:].any()


def test_configured_elevation_directory_comes_from_data_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    assert resolve_elevation_data_dir() == (
        tmp_path / "library" / "data" / "earth" / "elevation"
    ).resolve()


def test_geographic_geotiff_sampling_and_nodata(tmp_path: Path) -> None:
    path = tmp_path / "geographic.tif"
    values = np.full((10, 10), 42.5, dtype=np.float32)
    values[2, 2] = -9999.0
    _write_tiff(path, values, "EPSG:4326", from_origin(-1, 1, 0.1, 0.1), -9999.0)
    adapter = RasterioElevationAdapter(path, virtual_window_size=32)
    batch = adapter.sample_points(ElevationBatchRequest(
        latitude_deg=np.asarray([0.55, 0.75, 5.0]),
        longitude_deg=np.asarray([-0.55, -0.75, 5.0]),
    ))
    assert batch.valid_mask.tolist() == [True, False, False]
    assert batch.values_m[0] == pytest.approx(42.5)
    assert batch.values_m[1] == 0.0
    assert batch.source_indices[0] == 0
    assert adapter.metrics()["rasterBytesRead"] > 0
    adapter.close()
    adapter.close()


def test_projected_geotiff_sampling_uses_explicit_crs(tmp_path: Path) -> None:
    path = tmp_path / "projected.tif"
    values = np.full((10, 10), 123.25, dtype=np.float32)
    _write_tiff(path, values, "EPSG:3857", from_origin(-5_000, 5_000, 1_000, 1_000), None)
    adapter = RasterioElevationAdapter(path, virtual_window_size=32)
    sample = adapter.elevation(GeoLocation(0.0, 0.0))
    assert sample.status is ElevationStatus.REAL
    assert sample.elevation_m == pytest.approx(123.25)
    assert adapter.metadata().native_crs == "EPSG:3857"
    adapter.close()


def test_dem_elevation_uses_bilinear_interpolation_without_inventing_nodata(tmp_path: Path) -> None:
    path = tmp_path / "bilinear.tif"
    values = np.asarray([[0.0, 10.0], [20.0, 30.0]], dtype=np.float32)
    _write_tiff(path, values, "EPSG:4326", from_origin(0, 2, 1, 1), -9999.0)
    adapter = RasterioElevationAdapter(path, virtual_window_size=32)
    batch = adapter.sample_points(ElevationBatchRequest(
        latitude_deg=np.asarray([1.0]),
        longitude_deg=np.asarray([1.0]),
    ))
    assert batch.valid_mask.tolist() == [True]
    assert batch.values_m[0] == pytest.approx(15.0)
    adapter.close()


def test_terrain_grid_uses_the_real_dem_sampling_chain(tmp_path: Path) -> None:
    path = tmp_path / "grid.tif"
    _write_tiff(
        path,
        np.full((10, 10), 73.25, dtype=np.float32),
        "EPSG:4326",
        from_origin(-4, 6, 1, 1),
        -9999.0,
    )
    adapter = RasterioElevationAdapter(path, virtual_window_size=32)
    grid = adapter.terrain_grid(TerrainTileRequest(
        tile_id=TerrainTileId("fixture"),
        center_latitude_deg=1.0,
        center_longitude_deg=1.0,
        radius_m=1.0,
        target_resolution_m=1.0,
    ))
    assert (grid.width, grid.height, grid.spacing_m) == (3, 3, 1.0)
    assert grid.valid_mask.all()
    assert np.allclose(grid.values_m, 73.25)
    assert np.all(grid.source_indices == 0)
    adapter.close()


def test_lazy_npy_geometry_uses_actual_array_shape(tmp_path: Path) -> None:
    path = tmp_path / "Y_(0_10000)X_(0_10000).npy"
    np.save(path, np.full((9, 9), 77.0, dtype=np.float32))
    adapter = RasterioElevationAdapter(tmp_path, local_resolution_m=1_000, virtual_window_size=32)
    batch = adapter.sample_points(ElevationBatchRequest(
        latitude_deg=np.asarray([500.0]),
        longitude_deg=np.asarray([9_500.0]),
        input_crs="EPSG:25831",
    ))
    assert batch.valid_mask.tolist() == [True]
    assert batch.values_m[0] == pytest.approx(77.0)
    adapter.close()


def test_npy_nodata_sentinels_never_become_elevation_samples(tmp_path: Path) -> None:
    path = tmp_path / "Y_(0_10000)X_(0_10000).npy"
    np.save(path, np.asarray([
        [77.0, -8888.0],
        [-9999.0, 42.0],
    ], dtype=np.float32))
    adapter = RasterioElevationAdapter(tmp_path, local_resolution_m=1_000, virtual_window_size=32)
    batch = adapter.sample_points(ElevationBatchRequest(
        latitude_deg=np.asarray([7_500.0, 7_500.0, 2_500.0, 2_500.0]),
        longitude_deg=np.asarray([2_500.0, 7_500.0, 2_500.0, 7_500.0]),
        input_crs="EPSG:25831",
    ))
    assert batch.valid_mask.tolist() == [True, False, False, True]
    assert batch.values_m.tolist() == pytest.approx([77.0, 0.0, 0.0, 42.0])
    adapter.close()


def test_dem_chain_prefers_precision_and_falls_back_after_npy_nodata(tmp_path: Path) -> None:
    np.save(
        tmp_path / "Y_(0_10000)X_(0_10000).npy",
        np.asarray([[77.0, -9999.0], [77.0, 77.0]], dtype=np.float32),
    )
    _write_tiff(
        tmp_path / "continental.tif",
        np.full((2, 2), 12.0, dtype=np.float32),
        "EPSG:25831",
        from_origin(0, 10_000, 5_000, 5_000),
        -9999.0,
    )
    adapter = RasterioElevationAdapter(
        tmp_path,
        local_resolution_m=5.0,
        virtual_window_size=32,
    )
    batch = adapter.sample_points(ElevationBatchRequest(
        latitude_deg=np.asarray([7_500.0, 7_500.0]),
        longitude_deg=np.asarray([2_500.0, 7_500.0]),
        input_crs="EPSG:25831",
    ))
    assert batch.valid_mask.tolist() == [True, True]
    assert batch.values_m.tolist() == pytest.approx([77.0, 12.0])
    assert batch.source_indices.tolist() == [0, 1]
    adapter.close()


def test_dem_chain_does_not_give_npy_priority_over_a_finer_raster(tmp_path: Path) -> None:
    np.save(
        tmp_path / "Y_(0_10000)X_(0_10000).npy",
        np.full((2, 2), 40.0, dtype=np.float32),
    )
    _write_tiff(
        tmp_path / "finer.tif",
        np.full((4, 4), 99.0, dtype=np.float32),
        "EPSG:25831",
        from_origin(0, 10_000, 2_500, 2_500),
        -9999.0,
    )
    adapter = RasterioElevationAdapter(
        tmp_path,
        local_resolution_m=5_000.0,
        virtual_window_size=32,
    )
    batch = adapter.sample_points(ElevationBatchRequest(
        latitude_deg=np.asarray([8_750.0]),
        longitude_deg=np.asarray([1_250.0]),
        input_crs="EPSG:25831",
    ))
    assert batch.valid_mask.tolist() == [True]
    assert batch.values_m.tolist() == pytest.approx([99.0])
    assert batch.source_indices.tolist() == [0]
    adapter.close()


def test_partial_profile_and_bounded_refinement() -> None:
    coordinator = _coordinator(_SyntheticElevationPort(partial=True))
    profile = coordinator._bake(_request(1, step=5.0), threading.Event(), "partial")  # noqa: SLF001
    assert profile.quality is HorizonQuality.PARTIAL_DEM
    assert profile.resolved_fraction == pytest.approx(0.5)
    assert profile.valid_mask[:36].tolist() == [1] * 36
    assert profile.valid_mask[36:].tolist() == [0] * 36


def test_visible_terrain_uses_only_dem_material() -> None:
    port = _SyntheticElevationPort()
    request = _request(1, step=5.0)
    profile = _coordinator(port)._bake(request, threading.Event(), "dem-only")  # noqa: SLF001

    mesh = TerrainMeshBuilder(port, _IdentityProjector()).build(request, profile, threading.Event())

    assert mesh.source_label == "Material DEM: paleta de relleu (sense cobertura superficial)"
    assert not np.any(mesh.class_ids)
    assert not np.any(mesh.source_ids)


def test_mesh_builder_never_turns_nodata_sentinels_into_cliffs() -> None:
    class SentinelPort(_SyntheticElevationPort):
        def sample_points(self, request: ElevationBatchRequest) -> ElevationBatch:
            values = np.asarray([100.0, -8888.0, -9999.0, np.nan], dtype=np.float32)
            values = np.resize(values, request.latitude_deg.shape)
            return ElevationBatch(
                values,
                np.ones(request.latitude_deg.shape, dtype=np.bool_),
                np.zeros(request.latitude_deg.shape, dtype=np.int16),
            )

    positions, valid = TerrainMeshBuilder(SentinelPort(), _IdentityProjector())._sample_positions(  # noqa: SLF001
        _request(1),
        np.asarray([[0.0, 1.0], [2.0, 3.0]]),
        np.zeros((2, 2), dtype=np.float64),
        observer_ground_m=100.0,
        effective_radius_m=EARTH_RADIUS_M,
        cancel_event=threading.Event(),
    )
    assert valid.tolist() == [True, False, False, False]
    assert np.all(positions[1:] == 0.0)


def test_streamed_dem_chunk_keeps_its_global_enu_center_and_binary_contract() -> None:
    """The detail mesh overlays the resident world; it is not a new origin."""

    port = _SyntheticElevationPort()
    request = _request(1, step=5.0)
    profile = _coordinator(port)._bake(request, threading.Event(), "streaming")  # noqa: SLF001
    mesh = TerrainMeshBuilder(port, _IdentityProjector()).build(
        request,
        profile,
        threading.Event(),
        center_east_m=2_000.0,
        center_north_m=-500.0,
        visual_radius_m=25_000.0,
    )

    zero_axis = int(np.where(mesh.near_axis_m == 0.0)[0][0])
    center_index = zero_axis * mesh.near_axis_m.size + zero_axis
    assert mesh.center_east_m == 2_000.0
    assert mesh.center_north_m == -500.0
    assert mesh.polar_distances_m[-1] == pytest.approx(25_000.0)
    assert mesh.positions[center_index, 0] == pytest.approx(2_000.0)
    assert mesh.positions[center_index, 2] == pytest.approx(500.0)

    metadata, payload = pack_terrain_mesh(
        profile,
        mesh,
        role="terrain_stream_chunk",
        resource_id="earth.terrain.stream",
    )
    assert metadata["role"] == "terrain_stream_chunk"
    navigation_sampling = metadata["navigationSampling"]
    assert isinstance(navigation_sampling, dict)
    assert navigation_sampling["centerEastM"] == 2_000.0
    assert navigation_sampling["centerNorthM"] == -500.0
    assert navigation_sampling["polarAzimuthStepDeg"] == pytest.approx(mesh.polar_azimuth_step_deg)
    assert len(payload) == metadata["byteLength"]


def test_latest_wins_publishes_only_latest_request() -> None:
    async def scenario() -> list[int]:
        published: list[int] = []

        async def publish(metadata: dict[str, object], payload: bytes) -> int:
            if metadata["role"] == "horizon_profile":
                published.append(int(metadata["observerGeneration"]))
            return len(payload)

        async def status(_: dict[str, object]) -> None:
            return None

        coordinator = HorizonCoordinator(
            _SyntheticElevationPort(), _IdentityProjector(), publish, status,
        )
        coordinator.request(_request(1, observer_generation=1))
        coordinator.request(_request(2, observer_generation=2))
        coordinator.request(_request(3, observer_generation=3))
        await coordinator.wait_idle()
        await coordinator.close()
        return published

    assert asyncio.run(scenario()) == [3]


def test_forced_recalculation_bypasses_cached_profile() -> None:
    async def scenario() -> tuple[int, int, int]:
        port = _SyntheticElevationPort()
        coordinator = _coordinator(port)
        coordinator.request(_request(1))
        await coordinator.wait_idle()
        after_first_bake = port.batch_calls

        coordinator.request(_request(2))
        await coordinator.wait_idle()
        after_cached_request = port.batch_calls

        coordinator.request(replace(_request(3), force_recalculate=True))
        await coordinator.wait_idle()
        after_forced_request = port.batch_calls
        await coordinator.close()
        return after_first_bake, after_cached_request, after_forced_request

    first, cached, forced = asyncio.run(scenario())
    assert first > 0
    assert cached == first
    assert forced > cached


def test_sampling_progress_advances_while_the_background_bake_runs() -> None:
    async def scenario() -> list[dict[str, object]]:
        statuses: list[dict[str, object]] = []

        async def publish(_: dict[str, object], payload: bytes) -> int:
            return len(payload)

        async def status(message: dict[str, object]) -> None:
            statuses.append(message)

        coordinator = HorizonCoordinator(
            _SyntheticElevationPort(), _IdentityProjector(), publish, status,
        )
        coordinator.request(_request(1, step=5.0))
        await coordinator.wait_idle()
        await coordinator.close()
        return statuses

    sampling = [
        float(status["progress"])
        for status in asyncio.run(scenario())
        if status["phase"] == "sampling" and status["progress"] is not None
    ]
    assert sampling[0] == pytest.approx(0.05)
    assert any(0.05 < progress < 0.90 for progress in sampling)
    assert sampling == sorted(sampling)


def test_cache_invalidation_uses_only_scientific_observer_dem_and_settings() -> None:
    base = _request(1)
    coordinator = _coordinator(_SyntheticElevationPort(fingerprint="dem-v1"))
    base_key = coordinator._cache_key(base)  # noqa: SLF001 - contract assertion

    invalidating = (
        replace(base, latitude_deg=1.0),
        replace(base, height_offset_m=3.0),
        replace(base, settings=replace(base.settings, visible_radius_km=2.0)),
        replace(base, settings=replace(base.settings, angular_step_deg=1.0)),
        replace(base, settings=replace(base.settings, atmospheric_refraction_enabled=False)),
    )
    assert all(coordinator._cache_key(request) != base_key for request in invalidating)  # noqa: SLF001

    dem_v2 = _coordinator(_SyntheticElevationPort(fingerprint="dem-v2"))
    assert dem_v2._cache_key(base) != base_key  # noqa: SLF001

    request_fields = HorizonRequest.__dataclass_fields__
    for unrelated in ("camera", "fov", "time", "bortle", "selection", "tracking"):
        assert unrelated not in request_fields


def test_bare_elevation_is_latest_wins_cancellable_and_cacheable() -> None:
    class SlowBarePort(_SyntheticElevationPort):
        def elevation(self, location: GeoLocation, cancellation_check: object = None) -> ElevationSample:
            check = cancellation_check if callable(cancellation_check) else lambda: False
            for _ in range(50):
                if check():
                    return ElevationSample(location, None, None, ElevationStatus.CANCELLED)
                time.sleep(0.001)
            return ElevationSample(location, location.latitude_deg, "fixture", ElevationStatus.REAL)

    async def scenario() -> tuple[object, object, object, dict[str, float | int]]:
        coordinator = ElevationCoordinator(SlowBarePort())
        first_task = asyncio.create_task(coordinator.resolve(GeoLocation(1, 1)))
        await asyncio.sleep(0.005)
        second_task = asyncio.create_task(coordinator.resolve(GeoLocation(2, 2)))
        first, second = await asyncio.gather(first_task, second_task)
        cached = await coordinator.resolve(GeoLocation(2, 2))
        return first, second, cached, coordinator.metrics()

    first, second, cached, metrics = asyncio.run(scenario())
    assert first is None
    assert second is not None and second.sample.elevation_m == 2
    assert cached is not None and cached.cache_hit
    assert metrics["bareElevationCacheHits"] == 1


def test_expensive_bake_cancels_between_batches_and_worker_remains_reusable() -> None:
    async def scenario() -> tuple[float, list[str], int]:
        phases: list[str] = []
        published = 0

        async def publish(_: dict[str, object], payload: bytes) -> int:
            nonlocal published
            if _["role"] == "horizon_profile":
                published += 1
            return len(payload)

        async def status(message: dict[str, object]) -> None:
            phases.append(str(message["phase"]))

        port = _SyntheticElevationPort(slow=True)
        coordinator = HorizonCoordinator(port, _IdentityProjector(), publish, status)
        coordinator.request(_request(1, step=0.005, max_samples=32))
        await asyncio.sleep(0.03)
        started = time.perf_counter()
        coordinator.cancel()
        await coordinator.wait_idle()
        latency = time.perf_counter() - started
        coordinator.request(_request(2, step=5.0))
        await coordinator.wait_idle()
        await coordinator.close()
        return latency, phases, published

    latency, phases, published = asyncio.run(scenario())
    assert latency < 0.5
    assert "cancelled" in phases
    assert published == 1


class _IdentityProjector:
    working_crs = "fixture:azimuth-distance"

    def project(
        self,
        latitude_deg: float,
        longitude_deg: float,
        azimuth_deg: object,
        distance_m: object,
    ) -> tuple[np.ndarray, np.ndarray]:
        return np.asarray(azimuth_deg, dtype=np.float64), np.asarray(distance_m, dtype=np.float64)


class _SyntheticElevationPort:
    def __init__(
        self,
        *,
        partial: bool = False,
        slow: bool = False,
        fingerprint: str = "fixture-v1",
    ) -> None:
        self.partial = partial
        self.slow = slow
        self.fingerprint = fingerprint
        self.batch_calls = 0

    def metadata(self) -> ElevationSourceMetadata:
        return ElevationSourceMetadata(
            "fixture", self.fingerprint, "fixture", 25.0, None, None, "synthetic", ("fixture",),
        )

    def elevation(
        self,
        location: GeoLocation,
        cancellation_check: object = None,
    ) -> ElevationSample:
        return ElevationSample(location, 100.0, "fixture", ElevationStatus.REAL)

    def sample_points(self, request: ElevationBatchRequest) -> ElevationBatch:
        self.batch_calls += 1
        if self.slow:
            for _ in range(40):
                if request.cancellation_check is not None and request.cancellation_check():
                    raise DemSamplingCancelled()
                time.sleep(0.001)
        if request.cancellation_check is not None and request.cancellation_check():
            raise DemSamplingCancelled()
        values = np.full(request.latitude_deg.shape, 100.0, dtype=np.float32)
        valid = np.ones(request.latitude_deg.shape, dtype=np.bool_)
        if self.partial:
            valid &= request.latitude_deg < 180.0
        indices = np.where(valid, 0, -1).astype(np.int16)
        return ElevationBatch(values, valid, indices)

    def terrain_grid(self, request: object) -> object:
        raise NotImplementedError

    def close(self) -> None:
        return None


def _request(
    generation: int,
    *,
    observer_generation: int = 1,
    step: float = 5.0,
    max_samples: int = 64,
) -> HorizonRequest:
    return HorizonRequest(
        request_id=f"fixture-{generation}",
        generation=generation,
        observer_generation=observer_generation,
        settings_generation=1,
        latitude_deg=0.0,
        longitude_deg=0.0,
        terrain_elevation_m=100.0,
        height_offset_m=2.0,
        settings=HorizonProfileSettings(
            range_mode=HorizonRangeMode.MANUAL,
            visible_radius_km=1.0,
            angular_step_deg=step,
            max_samples_per_ray=max_samples,
        ),
    )


def _coordinator(port: _SyntheticElevationPort) -> HorizonCoordinator:
    async def publish(_: dict[str, object], payload: bytes) -> int:
        return len(payload)

    async def status(_: dict[str, object]) -> None:
        return None

    return HorizonCoordinator(port, _IdentityProjector(), publish, status)


def _write_tiff(
    path: Path,
    values: np.ndarray,
    crs: str,
    transform: object,
    nodata: float | None,
) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[1],
        height=values.shape[0],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dataset:
        dataset.write(values, 1)
