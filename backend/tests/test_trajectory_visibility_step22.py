from __future__ import annotations

import asyncio
import math
import time
from datetime import datetime, timedelta, timezone

import numpy as np

from terralab3d.application.apparent_trajectory import (
    ApparentTrajectoryCoordinator,
    ApparentTrajectorySampler,
)
from terralab3d.application.observable_positions import ObservablePositionService
from terralab3d.domain.geometry import CartesianDirection
from terralab3d.domain.horizon.models import HorizonProfile, HorizonQuality
from terralab3d.domain.identifiers import ResourceId
from terralab3d.domain.solar_system.models import ScientificObserver
from terralab3d.domain.time.engine import AstronomicalEngine
from terralab3d.domain.visibility.models import (
    ApparentPosition,
    HorizonProvenance,
    ObservableFamily,
    ObservableObject,
    TrajectoryEventKind,
    TrajectoryResolution,
    TrajectoryVisibilityState,
    VisibilityIntervalClassification,
)

UTC = timezone.utc


class SyntheticPositionPort:
    generation = "synthetic-v1"

    def __init__(self, start: datetime, duration_seconds: float, altitude) -> None:
        self.start = start
        self.duration_seconds = duration_seconds
        self.altitude = altitude

    def position_at(self, observable, instant_utc, observer):
        fraction = (instant_utc - self.start).total_seconds() / self.duration_seconds
        altitude_deg = float(self.altitude(fraction))
        azimuth_deg = (350.0 + 40.0 * fraction) % 360.0
        azimuth = math.radians(azimuth_deg)
        altitude = math.radians(altitude_deg)
        horizontal = math.cos(altitude)
        return ApparentPosition(
            instant_utc=instant_utc,
            direction_enu=CartesianDirection(
                math.sin(azimuth) * horizontal,
                math.sin(altitude),
                math.cos(azimuth) * horizontal,
            ),
            azimuth_deg=azimuth_deg,
            altitude_deg=altitude_deg,
            valid=True,
            quality="scientific",
        )


def _observable(family: ObservableFamily = ObservableFamily.COORDINATE) -> ObservableObject:
    return ObservableObject(
        object_id="fixture",
        family=family,
        display_name="Fixture",
        right_ascension_deg=12.0,
        declination_deg=34.0,
    )


def _profile(valid_mask: np.ndarray | None = None, elevation_deg: float = 2.0) -> HorizonProfile:
    count = 360
    valid = np.ones(count, dtype=np.uint8) if valid_mask is None else valid_mask
    return HorizonProfile(
        resource_id=ResourceId("earth.horizon.profile"),
        version=7,
        content_key="fixture",
        source_ids=("fixture-dem",),
        source_fingerprint="fixture",
        observer_generation=3,
        latitude_deg=41.0,
        longitude_deg=2.0,
        terrain_elevation_m=100.0,
        eye_elevation_m=101.7,
        visible_radius_m=100_000.0,
        azimuth_start_deg=0.0,
        angular_step_deg=1.0,
        horizon_elevation_deg=np.full(count, elevation_deg, dtype=np.float32),
        occluder_distance_m=np.ones(count, dtype=np.float32),
        occluder_height_m=np.ones(count, dtype=np.float32),
        valid_mask=valid,
        quality=HorizonQuality.REAL,
        resolved_fraction=float(np.mean(valid)),
    )


def test_adaptive_visibility_finds_multiple_crossings_and_keeps_north_continuous() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    duration = 3_600.0
    positions = SyntheticPositionPort(
        start,
        duration,
        lambda fraction: 4.0 + 3.0 * math.cos(4.0 * math.pi * fraction),
    )
    sampler = ApparentTrajectorySampler(
        None,
        position_port=positions,
        horizon_profile=lambda: _profile(),
    )
    trajectory = sampler.sample_visibility(
        _observable(),
        ScientificObserver(41.0, 2.0, 100.0),
        3,
        start,
        start + timedelta(seconds=duration),
        9,
        resolution=TrajectoryResolution.DETAILED,
    )

    crossings = [event for event in trajectory.events if event.kind is not TrajectoryEventKind.TANGENT]
    assert [event.kind for event in crossings] == [
        TrajectoryEventKind.SET,
        TrajectoryEventKind.RISE,
        TrajectoryEventKind.SET,
        TrajectoryEventKind.RISE,
    ]
    assert any(sample.apparent.azimuth_deg < 5.0 for sample in trajectory.samples)
    assert any(sample.apparent.azimuth_deg > 355.0 for sample in trajectory.samples)
    assert {segment.visibility for segment in trajectory.segments} == {
        TrajectoryVisibilityState.VISIBLE,
        TrajectoryVisibilityState.TERRAIN_OCCLUDED,
    }
    assert all(event.horizon_provenance is HorizonProvenance.REAL for event in crossings)
    assert trajectory.temporal_tolerance_seconds == 0.25


def test_dem_gap_is_explicit_and_does_not_create_fictitious_events() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    valid = np.ones(360, dtype=np.uint8)
    valid[:15] = 0
    valid[345:] = 0
    positions = SyntheticPositionPort(start, 3_600.0, lambda _fraction: 5.0)
    sampler = ApparentTrajectorySampler(
        None,
        position_port=positions,
        horizon_profile=lambda: _profile(valid, elevation_deg=1.0),
    )
    trajectory = sampler.sample_visibility(
        _observable(),
        ScientificObserver(41.0, 2.0, 100.0),
        3,
        start,
        start + timedelta(hours=1),
        5,
    )

    assert not trajectory.events
    assert trajectory.interval_classification is VisibilityIntervalClassification.INSUFFICIENT_DATA
    assert any(
        sample.visibility is TrajectoryVisibilityState.INSUFFICIENT_DATA
        for sample in trajectory.samples
    )
    assert any(
        sample.horizon_provenance is HorizonProvenance.INSUFFICIENT
        for sample in trajectory.samples
    )
    assert any(
        sample.horizon_provenance is HorizonProvenance.REAL
        for sample in trajectory.samples
    )


def test_real_and_astronomical_horizons_preserve_the_same_apparent_path() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    positions = SyntheticPositionPort(start, 600.0, lambda _fraction: 1.0)
    sampler = ApparentTrajectorySampler(
        None,
        position_port=positions,
        horizon_profile=lambda: _profile(elevation_deg=2.0),
    )
    arguments = (
        _observable(),
        ScientificObserver(41.0, 2.0, 100.0),
        3,
        start,
        start + timedelta(minutes=10),
        5,
    )

    real = sampler.sample_visibility(*arguments, use_terrain_horizon=True)
    astronomical = sampler.sample_visibility(*arguments, use_terrain_horizon=False)

    assert [sample.apparent.direction_enu for sample in real.samples] == [
        sample.apparent.direction_enu for sample in astronomical.samples
    ]
    assert real.interval_classification is VisibilityIntervalClassification.NEVER_VISIBLE
    assert astronomical.interval_classification is VisibilityIntervalClassification.VISIBLE_THROUGHOUT
    assert {sample.horizon_provenance for sample in real.samples} == {HorizonProvenance.REAL}
    assert {sample.horizon_provenance for sample in astronomical.samples} == {
        HorizonProvenance.FALLBACK_ASTRONOMICAL,
    }


def test_visibility_binary_appends_arrays_without_moving_pas9_offsets() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    positions = SyntheticPositionPort(start, 600.0, lambda fraction: -1.0 + 4.0 * fraction)
    sampler = ApparentTrajectorySampler(None, position_port=positions)
    trajectory = sampler.sample_visibility(
        _observable(),
        ScientificObserver(41.0, 2.0, 100.0),
        3,
        start,
        start + timedelta(minutes=10),
        3,
        use_terrain_horizon=False,
    )
    resource = sampler.encode_visibility(trajectory, "latest-request")
    count = len(trajectory.samples)

    assert resource.metadata["directionByteOffset"] == 0
    assert resource.metadata["timeOffsetByteOffset"] == count * 12
    assert resource.metadata["validityByteOffset"] == count * 16
    assert resource.metadata["visibilityByteOffset"] == count * 17
    assert resource.metadata["horizonProvenanceByteOffset"] == count * 18
    assert len(resource.payload) == count * 19
    assert resource.metadata["requestId"] == "latest-request"
    assert resource.metadata["contractVersion"] == 2


def test_circumpolar_is_only_claimed_for_a_full_sidereal_interval() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    duration = 86_165.0
    positions = SyntheticPositionPort(start, duration, lambda _fraction: 35.0)
    sampler = ApparentTrajectorySampler(None, position_port=positions)
    observer = ScientificObserver(70.0, 2.0, 10.0)

    short = sampler.sample_visibility(
        _observable(ObservableFamily.STAR),
        observer,
        1,
        start,
        start + timedelta(hours=2),
        3,
        use_terrain_horizon=False,
    )
    full = sampler.sample_visibility(
        _observable(ObservableFamily.STAR),
        observer,
        1,
        start,
        start + timedelta(seconds=duration),
        12,
        use_terrain_horizon=False,
    )

    assert not short.astronomically_circumpolar
    assert full.astronomically_circumpolar
    assert short.interval_classification is VisibilityIntervalClassification.VISIBLE_THROUGHOUT


def test_fixed_equatorial_target_reuses_the_shared_sidereal_transform() -> None:
    instant = datetime(2026, 9, 16, 20, tzinfo=UTC)
    observer = ScientificObserver(41.0, 2.0, 100.0)
    right_ascension_deg = AstronomicalEngine().local_sidereal_angle_deg(
        instant,
        observer.longitude_deg,
    )
    observable = ObservableObject(
        object_id="zenith-fixture",
        family=ObservableFamily.STAR,
        display_name="Zenith fixture",
        right_ascension_deg=right_ascension_deg,
        declination_deg=observer.latitude_deg,
    )

    position = ObservablePositionService(None).position_at(observable, instant, observer)

    assert position.valid
    assert position.altitude_deg > 89.999
    assert position.direction_enu.y > 0.999999


def test_flat_horizon_refines_crossing_and_distinguishes_a_tangent() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    observer = ScientificObserver(41.0, 2.0, 100.0)
    crossing_sampler = ApparentTrajectorySampler(
        None,
        position_port=SyntheticPositionPort(start, 600.0, lambda fraction: -1.0 + 2.0 * fraction),
    )
    crossing = crossing_sampler.sample_visibility(
        _observable(),
        observer,
        1,
        start,
        start + timedelta(minutes=10),
        3,
        use_terrain_horizon=False,
        resolution=TrajectoryResolution.DETAILED,
    )
    assert [event.kind for event in crossing.events] == [TrajectoryEventKind.RISE]
    assert abs((crossing.events[0].instant_utc - (start + timedelta(minutes=5))).total_seconds()) <= 0.25
    assert crossing.events[0].horizon_provenance is HorizonProvenance.FALLBACK_ASTRONOMICAL

    tangent_sampler = ApparentTrajectorySampler(
        None,
        position_port=SyntheticPositionPort(
            start,
            600.0,
            lambda fraction: 100.0 * (fraction - 0.5) ** 2,
        ),
    )
    tangent = tangent_sampler.sample_visibility(
        _observable(),
        observer,
        1,
        start,
        start + timedelta(minutes=10),
        3,
        use_terrain_horizon=False,
        resolution=TrajectoryResolution.DETAILED,
    )
    assert not [event for event in tangent.events if event.kind is not TrajectoryEventKind.TANGENT]
    assert any(event.kind is TrajectoryEventKind.TANGENT for event in tangent.events)

    narrow_sampler = ApparentTrajectorySampler(
        None,
        position_port=SyntheticPositionPort(
            start,
            600.0,
            lambda fraction: 8.0 * abs(fraction - 0.5) - 1.0,
        ),
    )
    narrow = narrow_sampler.sample_visibility(
        _observable(),
        observer,
        1,
        start,
        start + timedelta(minutes=10),
        2,
        use_terrain_horizon=False,
    )
    assert [event.kind for event in narrow.events] == [
        TrajectoryEventKind.SET,
        TrajectoryEventKind.RISE,
    ]

    never_sampler = ApparentTrajectorySampler(
        None,
        position_port=SyntheticPositionPort(start, 600.0, lambda _fraction: -5.0),
    )
    never = never_sampler.sample_visibility(
        _observable(),
        observer,
        1,
        start,
        start + timedelta(minutes=10),
        3,
        use_terrain_horizon=False,
    )
    assert never.interval_classification is VisibilityIntervalClassification.NEVER_VISIBLE


def test_negative_terrain_horizon_keeps_events_on_astronomical_horizon() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    sampler = ApparentTrajectorySampler(
        None,
        position_port=SyntheticPositionPort(start, 600.0, lambda fraction: -1.0 + 2.0 * fraction),
        horizon_profile=lambda: _profile(elevation_deg=-3.0),
    )
    trajectory = sampler.sample_visibility(
        _observable(),
        ScientificObserver(41.0, 2.0, 100.0),
        3,
        start,
        start + timedelta(minutes=10),
        3,
        resolution=TrajectoryResolution.DETAILED,
    )

    assert [event.kind for event in trajectory.events] == [TrajectoryEventKind.RISE]
    assert abs((trajectory.events[0].instant_utc - (start + timedelta(minutes=5))).total_seconds()) <= 0.25
    assert abs(trajectory.events[0].altitude_deg) <= trajectory.angular_tolerance_deg
    assert trajectory.events[0].horizon_elevation_deg == -3.0
    assert TrajectoryVisibilityState.TERRAIN_OCCLUDED not in {
        sample.visibility for sample in trajectory.samples
    }


def test_latest_visibility_request_is_the_only_one_published() -> None:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    published: list[str] = []

    class LatestWinsPositionPort(SyntheticPositionPort):
        def position_at(self, observable, instant_utc, observer):
            if observable.object_id == "old":
                time.sleep(0.002)
            return super().position_at(observable, instant_utc, observer)

    positions = LatestWinsPositionPort(start, 600.0, lambda fraction: 10.0 * fraction)
    sampler = ApparentTrajectorySampler(None, position_port=positions)

    async def publish(resource) -> int:
        published.append(str(resource.metadata["requestId"]))
        return len(resource.payload)

    async def scenario() -> None:
        coordinator = ApparentTrajectoryCoordinator(sampler, publish)
        kwargs = {
            "observer": ScientificObserver(41.0, 2.0, 100.0),
            "observer_generation": 1,
            "start_utc": start,
            "end_utc": start + timedelta(minutes=10),
            "sample_count": 16,
        }
        coordinator.request(
            request_id="old",
            observable=ObservableObject(
                "old", ObservableFamily.COORDINATE, "Old", right_ascension_deg=1, declination_deg=1,
            ),
            **kwargs,
        )
        await asyncio.sleep(0.01)
        coordinator.request(
            request_id="latest",
            observable=ObservableObject(
                "latest", ObservableFamily.COORDINATE, "Latest", right_ascension_deg=2, declination_deg=2,
            ),
            **kwargs,
        )
        await asyncio.sleep(0.08)
        await coordinator.close()
        assert coordinator.cancel_count == 1

    asyncio.run(scenario())
    assert published == ["latest"]
