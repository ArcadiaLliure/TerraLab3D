from __future__ import annotations

import json
import math
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from terralab3d.application.apparent_trajectory import ApparentTrajectorySampler
from terralab3d.application.astronomical_events import (
    AstronomicalEventSearcher,
    AstronomicalEventService,
    EventSearchCancelled,
    EventSearchCoordinator,
    SolarEclipseFootprintSolver,
)
from terralab3d.domain.eclipses.calculations import (
    angular_separation_deg,
    disc_overlap,
    horizontal_direction_enu,
    occultation_state,
    solar_eclipse_state,
)
from terralab3d.domain.eclipses.models import (
    ApparentEventBody,
    AstronomicalEventSearchResult,
    EclipseKind,
    GeometryQuality,
    OccultationClassification,
    SolarEclipseClassification,
)
from terralab3d.domain.lighting.environment import LightingEnvironmentComposer
from terralab3d.domain.sky_background.sky_environment import SkyEnvironmentComposer
from terralab3d.domain.solar_system.models import ScientificObserver
from terralab3d.infrastructure.adapters.ephemeris.spice_adapter import SpiceEphemerisAdapter
from terralab3d.infrastructure.adapters.file_assets.lunar_limb import LroLolaLimbProfileProvider
from terralab3d.infrastructure.adapters.file_assets.solar_system import ManagedSolarSystemAssets


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "eclipses_2026_reference.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture(scope="module")
def spice_adapter() -> SpiceEphemerisAdapter:
    assets = ManagedSolarSystemAssets()
    if assets.kernel_manifest_path is None or assets.satellite_catalog is None:
        pytest.skip("Managed Step 8.6 SPICE resources are not installed")
    adapter = SpiceEphemerisAdapter(
        assets.kernel_manifest_path,
        assets.satellite_catalog,
    )
    yield adapter
    adapter.close()


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _body(
    body_id: str,
    *,
    direction_angle_deg: float,
    radius_deg: float,
    distance_km: float,
) -> ApparentEventBody:
    angle = math.radians(direction_angle_deg)
    direction = (math.sin(angle), 0.0, math.cos(angle))
    return ApparentEventBody(
        body_id=body_id,
        naif_id=10 if body_id == "sun" else 301,
        direction_icrf=direction,
        direction_enu=direction,
        distance_km=distance_km,
        angular_radius_deg=radius_deg,
        altitude_deg=20.0,
        physical_radius_km=radius_deg * distance_km * math.pi / 180.0,
    )


def test_stable_angular_separation_covers_wrap_zenith_antipodes_and_sub_arcminute() -> None:
    assert angular_separation_deg((1, 0, 0), (1, 0, 0)) == pytest.approx(0.0)
    assert angular_separation_deg((1, 0, 0), (-1, 0, 0)) == pytest.approx(180.0)
    assert angular_separation_deg(
        horizontal_direction_enu(359.0, 0.0),
        horizontal_direction_enu(1.0, 0.0),
    ) == pytest.approx(2.0)
    assert angular_separation_deg(
        horizontal_direction_enu(0.0, 90.0),
        horizontal_direction_enu(230.0, 90.0),
    ) == pytest.approx(0.0, abs=1.0e-12)
    tiny = 1.0 / 3_600.0
    assert angular_separation_deg(
        horizontal_direction_enu(10.0, 30.0),
        horizontal_direction_enu(10.0, 30.0 + tiny),
    ) == pytest.approx(tiny, rel=1.0e-9)


def test_disc_overlap_and_strict_classification_never_use_obscuration_threshold() -> None:
    assert disc_overlap(3.0, 1.0, 1.0).background_area_fraction == 0.0
    assert disc_overlap(2.0, 1.0, 1.0).background_area_fraction == 0.0
    assert 0.0 < disc_overlap(1.0, 1.0, 1.0).background_area_fraction < 1.0
    assert disc_overlap(0.0, 2.0, 1.0).background_area_fraction == 1.0
    assert disc_overlap(0.0, 0.5, 1.0).background_area_fraction == pytest.approx(0.25)

    sun = _body("sun", direction_angle_deg=0.0, radius_deg=1.0, distance_km=100.0)
    almost_concentric = _body(
        "moon", direction_angle_deg=0.00001, radius_deg=1.0, distance_km=1.0
    )
    partial = solar_eclipse_state(sun, almost_concentric)
    assert partial.obscuration > 0.999
    assert partial.classification is SolarEclipseClassification.PARTIAL
    total = solar_eclipse_state(
        sun,
        _body("moon", direction_angle_deg=0.0, radius_deg=1.0, distance_km=1.0),
    )
    assert total.classification is SolarEclipseClassification.TOTAL
    annular = solar_eclipse_state(
        sun,
        _body("moon", direction_angle_deg=0.0, radius_deg=0.9, distance_km=1.0),
    )
    assert annular.classification is SolarEclipseClassification.ANNULAR


def test_generic_occultation_respects_distance_order_not_disc_size() -> None:
    near_small = _body("moon", direction_angle_deg=0.0, radius_deg=0.5, distance_km=1.0)
    far_large = _body("sun", direction_angle_deg=0.0, radius_deg=1.0, distance_km=100.0)
    assert occultation_state(near_small, far_large).classification is OccultationClassification.TRANSIT
    assert occultation_state(far_large, near_small).classification is OccultationClassification.NONE


def test_torroja_solar_contacts_and_real_distance_radii(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    fixture = FIXTURE["solarTorroja"]
    observer = ScientificObserver(
        fixture["observer"]["latitudeDeg"],
        fixture["observer"]["longitudeDeg"],
        fixture["observer"]["elevationM"],
    )
    loads_before = spice_adapter.kernel_load_count
    result = AstronomicalEventSearcher(spice_adapter).search_solar(
        "solar-2026",
        observer,
        7,
        _utc(fixture["intervalStartUtc"]),
        _utc(fixture["intervalEndUtc"]),
    )
    assert result.classification == fixture["expectedClassification"]
    assert result.event_exists and result.locally_visible
    assert result.maximum_magnitude == pytest.approx(fixture["maximumMagnitude"], abs=2.0e-5)
    assert result.maximum_obscuration == pytest.approx(1.0)
    assert result.greatest_utc is not None
    assert abs((result.greatest_utc - _utc(fixture["greatestUtc"])).total_seconds()) < 1.0
    actual_contacts = {contact.name: contact.instant_utc for contact in result.contacts}
    assert set(actual_contacts) == {"C1", "C2", "C3", "C4"}
    for name, expected in fixture["contactsUtc"].items():
        assert abs((actual_contacts[name] - _utc(expected)).total_seconds()) < fixture[
            "contactValidationToleranceSeconds"
        ]
    assert spice_adapter.kernel_load_count == loads_before

    ephemeris = spice_adapter.event_ephemeris(
        result.greatest_utc, observer, ("sun", "moon")
    )
    for body_id in ("sun", "moon"):
        body = ephemeris.body(body_id)
        assert body is not None
        assert body.angular_radius_deg == pytest.approx(
            math.degrees(math.atan2(body.physical_radius_km, body.distance_km)),
            rel=1.0e-14,
        )


def test_precise_observer_corona_and_sky_follow_internal_contact_not_two_minutes_early(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    fixture = FIXTURE["solarTorroja"]
    observer = ScientificObserver(
        fixture["observer"]["latitudeDeg"],
        fixture["observer"]["longitudeDeg"],
        fixture["observer"]["elevationM"],
    )
    service = AstronomicalEventService(spice_adapter)
    c2 = _utc(fixture["contactsUtc"]["C2"])

    def event_at(instant: datetime):
        solar_system = spice_adapter.snapshot(instant, observer)
        return service.snapshot(
            instant,
            observer,
            observer_generation=solar_system.observer_generation,
            source_solar_system_generation=solar_system.generation,
        )

    two_minutes_before = event_at(c2 - timedelta(seconds=120))
    five_seconds_before = event_at(c2 - timedelta(seconds=5))
    inside_totality = event_at(c2 + timedelta(seconds=0.5))

    assert two_minutes_before.solar.obscuration > 0.96
    assert two_minutes_before.totality_appearance.corona.visibility == 0.0
    assert 0.0 < five_seconds_before.totality_appearance.corona.visibility < 1.0
    assert inside_totality.solar.classification is SolarEclipseClassification.TOTAL
    assert inside_totality.totality_appearance.corona.visibility == 1.0

    eclipse_sky = SkyEnvironmentComposer().compose(
        spice_adapter.snapshot(_utc(fixture["greatestUtc"]), observer).sun,
        1,
        solar_disc_transmission=inside_totality.solar.solar_disc_transmission,
        sky_eclipse_dimming_factor=inside_totality.sky_eclipse_dimming_factor,
    )
    effective_zenith_limit = (
        eclipse_sky.visibility.zenith_magnitude_limit
        - eclipse_sky.visibility.twilight_suppression
    )
    assert inside_totality.sky_eclipse_dimming_factor == pytest.approx(0.06, abs=1.0e-5)
    assert 1.0 < effective_zenith_limit < 2.0


def test_same_utc_observers_a_few_km_across_totality_boundary_are_independent(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    fixture = FIXTURE["solarTorroja"]
    boundary = fixture["northBoundaryAtGreatest"]
    instant = _utc(fixture["greatestUtc"])
    solver = SolarEclipseFootprintSolver(spice_adapter)
    query_before = spice_adapter.event_query_count
    inside = solver.classify_observer(
        boundary["insideLatitudeDeg"], fixture["observer"]["longitudeDeg"], 0.0, instant
    )
    outside = solver.classify_observer(
        boundary["outsideLatitudeDeg"], fixture["observer"]["longitudeDeg"], 0.0, instant
    )
    assert spice_adapter.event_query_count - query_before == 2
    assert solver.classification_count == 2
    assert inside.classification is SolarEclipseClassification.TOTAL
    assert outside.classification is SolarEclipseClassification.PARTIAL
    assert inside.center_separation_deg != outside.center_separation_deg
    assert boundary["observerSeparationKmApprox"] < 5.0


def test_requested_pair_publishes_separation_limb_gap_and_distance_order(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    fixture = FIXTURE["solarTorroja"]
    result = AstronomicalEventService(spice_adapter).measure_pair(
        "sun-moon",
        _utc(fixture["greatestUtc"]),
        ScientificObserver(
            fixture["observer"]["latitudeDeg"],
            fixture["observer"]["longitudeDeg"],
            fixture["observer"]["elevationM"],
        ),
        "sun",
        "moon",
    )
    assert result.measurement.separation_deg > 0.0
    assert result.measurement.limb_separation_deg < 0.0
    assert result.occultation.foreground == "moon"
    assert result.occultation.background == "sun"
    assert result.occultation.classification is OccultationClassification.TOTAL
    payload = result.to_dict()
    assert payload["requestId"] == "sun-moon"
    assert payload["quality"] == "scientific"


def test_footprint_refines_both_limits_with_solver_tolerances(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    fixture = FIXTURE["solarTorroja"]
    solver = SolarEclipseFootprintSolver(
        spice_adapter,
        angular_tolerance_deg=1.0e-8,
        latitude_tolerance_deg=1.0e-6,
    )
    limits = solver.central_band_limits(
        fixture["observer"]["longitudeDeg"],
        0.0,
        _utc(fixture["greatestUtc"]),
        scan_step_deg=0.05,
    )
    assert limits is not None
    assert limits.north_latitude_deg == pytest.approx(
        fixture["northBoundaryAtGreatest"]["latitudeDeg"], abs=2.0e-5
    )
    assert limits.south_latitude_deg == pytest.approx(
        fixture["southBoundaryAtGreatest"]["latitudeDeg"], abs=2.0e-5
    )
    assert limits.angular_tolerance_deg == 1.0e-8
    assert limits.latitude_tolerance_deg == 1.0e-6


def test_lunar_earth_shadow_contacts_and_local_visibility(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    fixture = FIXTURE["lunar"]
    observer = ScientificObserver(**{
        "latitude_deg": fixture["observer"]["latitudeDeg"],
        "longitude_deg": fixture["observer"]["longitudeDeg"],
        "elevation_m": fixture["observer"]["elevationM"],
    })
    result = AstronomicalEventSearcher(spice_adapter).search_lunar(
        "lunar-2026",
        observer,
        9,
        _utc(fixture["intervalStartUtc"]),
        _utc(fixture["intervalEndUtc"]),
    )
    assert result.classification == fixture["expectedClassification"]
    assert result.event_exists
    assert result.maximum_magnitude == pytest.approx(
        fixture["maximumUmbralMagnitude"], abs=2.0e-5
    )
    assert result.greatest_utc is not None
    assert abs((result.greatest_utc - _utc(fixture["greatestUtc"])).total_seconds()) < 1.0
    actual_contacts = {contact.name: contact.instant_utc for contact in result.contacts}
    assert set(actual_contacts) == {"P1", "U1", "U2", "U3", "U4", "P4"}
    for name, expected in fixture["contactsUtc"].items():
        assert abs((actual_contacts[name] - _utc(expected)).total_seconds()) < fixture[
            "contactValidationToleranceSeconds"
        ]


def test_lola_limb_and_baily_beads_change_with_observer_location(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    provider = LroLolaLimbProfileProvider()
    try:
        fixture = FIXTURE["solarTorroja"]
        precise_observer = ScientificObserver(
            fixture["observer"]["latitudeDeg"],
            fixture["observer"]["longitudeDeg"],
            fixture["observer"]["elevationM"],
        )
        service = AstronomicalEventService(spice_adapter, provider)
        instant = _utc("2026-08-12T18:29:20Z")
        first = service.snapshot(
            instant,
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=1,
        )
        second = service.snapshot(
            instant,
            ScientificObserver(41.250000, fixture["observer"]["longitudeDeg"], 0.0),
            observer_generation=2,
            source_solar_system_generation=2,
        )
        assert provider.load_count == 1
        assert (
            first.totality_appearance.limb_quality
            == second.totality_appearance.limb_quality
            == "lro_lola"
        )
        first_angles = [bead.lunar_position_angle_deg for bead in first.totality_appearance.beads]
        second_angles = [bead.lunar_position_angle_deg for bead in second.totality_appearance.beads]
        assert first_angles and second_angles and first_angles != second_angles
        assert first.totality_appearance.phase.value == "baily_ingress"
        assert first.totality_appearance.corona.visibility > 0.0
        assert first.totality_appearance.terrain_corrected_limb is not None
        assert len(
            first.totality_appearance.terrain_corrected_limb.radius_scale_samples
        ) == 720
        assert (
            first.totality_appearance.terrain_corrected_limb.maximum_radius_scale
            > 1.0
        )

        # The isolated bead visible in the reported 20:29:18 CEST sequence is
        # not decorative: its weighted position lands on a local LOLA valley.
        valley_instant = _utc("2026-08-12T18:29:18Z")
        valley_event = service.snapshot(
            valley_instant,
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=8,
        )
        moon = spice_adapter.event_ephemeris(
            valley_instant,
            precise_observer,
            ("sun", "moon"),
        ).body("moon")
        assert moon is not None
        valley_profile = provider.profile(moon)
        assert valley_profile is not None
        isolated_bead = min(
            valley_event.totality_appearance.beads,
            key=lambda bead: bead.angular_width_deg,
        )
        assert isolated_bead.angular_width_deg <= 6.0
        sample_count = len(valley_profile.samples)
        sample_step = 360.0 / sample_count
        center_index = round(
            isolated_bead.lunar_position_angle_deg / sample_step
        ) % sample_count
        local_elevations = [
            valley_profile.samples[(center_index + offset) % sample_count].elevation_km
            for offset in range(-12, 13)
        ]
        assert valley_profile.samples[center_index].elevation_km == pytest.approx(
            min(local_elevations),
            abs=1.0e-9,
        )

        ordinary_crescent = service.snapshot(
            _utc(fixture["contactsUtc"]["C2"]) - timedelta(seconds=60),
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=6,
        )
        assert ordinary_crescent.totality_appearance.phase.value == "partial"
        assert ordinary_crescent.totality_appearance.beads == ()
        assert ordinary_crescent.totality_appearance.corona.visibility == 0.0

        diamond = service.snapshot(
            _utc(fixture["contactsUtc"]["C2"]) - timedelta(seconds=1),
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=7,
        )
        assert diamond.totality_appearance.phase.value == "diamond_ingress"
        assert len(diamond.totality_appearance.beads) == 1
        assert 0.0 < diamond.totality_appearance.corona.visibility < 1.0
        assert diamond.totality_appearance.chromosphere_visibility > 0.0

        egress = service.snapshot(
            _utc("2026-08-12T18:30:35Z"),
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=3,
        )
        egress_angles = [bead.lunar_position_angle_deg for bead in egress.totality_appearance.beads]
        assert egress.totality_appearance.phase.value.endswith("egress")
        assert egress_angles and max(first_angles) < min(egress_angles)
        c2 = service.snapshot(
            _utc(fixture["contactsUtc"]["C2"]) + timedelta(seconds=0.5),
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=4,
        )
        assert c2.solar.classification is SolarEclipseClassification.TOTAL
        assert c2.totality_appearance.exposed_photosphere_area_square_deg == 0.0
        after_c3 = service.snapshot(
            _utc(fixture["contactsUtc"]["C3"]) + timedelta(seconds=0.5),
            precise_observer,
            observer_generation=1,
            source_solar_system_generation=5,
        )
        assert after_c3.solar.classification is SolarEclipseClassification.PARTIAL
        assert after_c3.totality_appearance.exposed_photosphere_area_square_deg > 0.0
        assert first.totality_appearance.corona.quality == "approximate"
        kinds = {item.kind for item in first.totality_appearance.corona.structures}
        assert {"polar_plume", "helmet_streamer"} <= kinds
    finally:
        provider.close()


def test_solar_and_lunar_visibility_factors_feed_sky_and_step87_lighting(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    solar_fixture = FIXTURE["solarTorroja"]
    solar_instant = _utc(solar_fixture["greatestUtc"])
    solar_observer = ScientificObserver(
        solar_fixture["observer"]["latitudeDeg"],
        solar_fixture["observer"]["longitudeDeg"],
        solar_fixture["observer"]["elevationM"],
    )
    solar_system = spice_adapter.snapshot(solar_instant, solar_observer)
    event = AstronomicalEventService(spice_adapter).snapshot(
        solar_instant,
        solar_observer,
        observer_generation=solar_system.observer_generation,
        source_solar_system_generation=solar_system.generation,
    )
    sky_composer = SkyEnvironmentComposer()
    normal_sky = sky_composer.compose(solar_system.sun, solar_system.generation)
    eclipse_sky = sky_composer.compose(
        solar_system.sun,
        solar_system.generation,
        solar_disc_transmission=event.solar.solar_disc_transmission,
        sky_eclipse_dimming_factor=event.sky_eclipse_dimming_factor,
    )
    assert eclipse_sky.bortle_class == normal_sky.bortle_class
    assert eclipse_sky.sky_diffuse_intensity < normal_sky.sky_diffuse_intensity
    assert eclipse_sky.visibility.twilight_suppression < normal_sky.visibility.twilight_suppression
    assert eclipse_sky.visibility.sky_brightness_normalized < normal_sky.visibility.sky_brightness_normalized
    lighting = LightingEnvironmentComposer()
    normal_lighting = lighting.compose(normal_sky, solar_system)
    eclipse_lighting = lighting.compose(
        eclipse_sky,
        solar_system,
        direct_solar_visibility_factor=event.solar.solar_disc_transmission,
    )
    assert eclipse_lighting.direct_solar_visibility_factor == event.solar.solar_disc_transmission
    assert eclipse_lighting.sun.intensity < normal_lighting.sun.intensity

    lunar_instant = _utc(FIXTURE["lunar"]["greatestUtc"])
    lunar_observer = ScientificObserver(0.0, 180.0, 0.0)
    lunar_system = spice_adapter.snapshot(lunar_instant, lunar_observer)
    lunar_event = AstronomicalEventService(spice_adapter).snapshot(
        lunar_instant,
        lunar_observer,
        observer_generation=lunar_system.observer_generation,
        source_solar_system_generation=lunar_system.generation,
    )
    lunar_sky = SkyEnvironmentComposer().compose(lunar_system.sun, lunar_system.generation)
    baseline = LightingEnvironmentComposer().compose(lunar_sky, lunar_system)
    eclipsed = LightingEnvironmentComposer().compose(
        lunar_sky,
        lunar_system,
        lunar_direct_visibility_factor=lunar_event.lunar.mean_lunar_light_transmission,
    )
    assert baseline.moon.intensity > 0.0
    assert eclipsed.moon.intensity < baseline.moon.intensity
    assert eclipsed.lunar_direct_visibility_factor == lunar_event.lunar.mean_lunar_light_transmission


@pytest.mark.parametrize("body_id", ["sun", "moon", "mars", "naif-501"])
def test_apparent_trajectories_are_topocentric_versioned_and_cached(
    spice_adapter: SpiceEphemerisAdapter,
    body_id: str,
) -> None:
    sampler = ApparentTrajectorySampler(spice_adapter)
    observer = ScientificObserver(41.3874, 2.1686, 25.0)
    start = _utc("2026-08-12T17:00:00Z")
    end = _utc("2026-08-12T19:00:00Z")
    first = sampler.sample(body_id, observer, 3, start, end, 9)
    second = sampler.sample(body_id, observer, 3, start, end, 9)
    assert first is second
    assert sampler.compute_count == 1 and sampler.cache_hit_count == 1
    assert len(first.directions_enu) == len(first.time_offsets_seconds) == 9
    assert all(first.validity)
    resource = sampler.encode(first)
    assert resource.metadata["frame"] == "topocentric ENU East/Up/North"
    assert len(resource.payload) == 9 * (12 + 4 + 1)


def test_event_search_coordinator_cancels_old_work_and_publishes_latest_only() -> None:
    published: list[str] = []
    instant = _utc("2026-08-12T18:00:00Z")

    class FakeSearcher:
        def search_solar(self, request_id, observer, observer_generation, start, end, *, cancel):
            for _ in range(80 if request_id == "old" else 2):
                if cancel.is_set():
                    raise EventSearchCancelled()
                time.sleep(0.001)
            return AstronomicalEventSearchResult(
                request_id=request_id,
                event_type=EclipseKind.SOLAR,
                classification="partial",
                interval_start_utc=start,
                interval_end_utc=end,
                greatest_utc=instant,
                contacts=(),
                event_exists=True,
                locally_visible=True,
                maximum_magnitude=0.5,
                maximum_obscuration=0.4,
                observer_generation=observer_generation,
                kernel_generation="fixture",
                quality=GeometryQuality.SCIENTIFIC,
                ephemeris_query_count=10,
                duration_ms=1.0,
                temporal_tolerance_seconds=0.25,
                angular_tolerance_deg=1.0e-8,
            )

        search_lunar = search_solar

    async def publish(result: AstronomicalEventSearchResult) -> int:
        published.append(result.request_id)
        return 1

    async def scenario() -> None:
        coordinator = EventSearchCoordinator(FakeSearcher(), publish)  # type: ignore[arg-type]
        kwargs = {
            "event_type": EclipseKind.SOLAR,
            "observer": ScientificObserver(0.0, 0.0, 0.0),
            "observer_generation": 1,
            "start_utc": instant,
            "end_utc": instant.replace(hour=19),
        }
        coordinator.request(request_id="old", **kwargs)
        await asyncio.sleep(0.005)
        coordinator.request(request_id="latest", **kwargs)
        await asyncio.sleep(0.02)
        await coordinator.close()
        assert coordinator.cancel_count == 1

    asyncio.run(scenario())
    assert published == ["latest"]
