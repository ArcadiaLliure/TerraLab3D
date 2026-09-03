from datetime import datetime, timezone

import pytest

from terralab3d.application.solar_system_preview import (
    PREVIEW_BODY_IDS,
    SolarSystemPreviewService,
)
from terralab3d.domain.eclipses.models import (
    ApparentEventBody,
    AstronomicalEventEphemeris,
    GeometryQuality,
)
from terralab3d.domain.solar_system.models import ScientificObserver


def test_preview_uses_lightweight_topocentric_positions() -> None:
    instant = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)

    class FakeEphemeris:
        requested_body_ids: tuple[str, ...] = ()

        def event_ephemeris(
            self,
            utc: datetime,
            observer: ScientificObserver,
            body_ids: tuple[str, ...] = ("sun", "moon"),
            *,
            include_lunar_shadow_geometry: bool = False,
            include_body_orientation: bool = True,
            allow_unknown_radius: bool = False,
        ) -> AstronomicalEventEphemeris:
            assert utc == instant
            assert observer.latitude_deg == 41.2
            assert include_lunar_shadow_geometry
            assert not include_body_orientation
            assert allow_unknown_radius
            self.requested_body_ids = body_ids
            return AstronomicalEventEphemeris(
                timestamp_utc=utc,
                observer_latitude_deg=observer.latitude_deg,
                observer_longitude_deg=observer.longitude_deg,
                observer_elevation_m=observer.elevation_m,
                kernel_generation="test",
                source="SPICE lightweight test",
                quality=GeometryQuality.SCIENTIFIC,
                bodies=(
                    ApparentEventBody(
                        body_id="sun",
                        naif_id=10,
                        direction_icrf=(1.0, 0.0, 0.0),
                        direction_enu=(1.0, 0.0, 0.0),
                        distance_km=149_597_870.0,
                        angular_radius_deg=0.266,
                        altitude_deg=0.0,
                        physical_radius_km=695_700.0,
                    ),
                    ApparentEventBody(
                        body_id="moon",
                        naif_id=301,
                        direction_icrf=(-1.0, 0.0, 0.0),
                        direction_enu=(0.0, 1.0, 0.0),
                        distance_km=384_400.0,
                        angular_radius_deg=0.259,
                        altitude_deg=90.0,
                        physical_radius_km=1_737.4,
                    ),
                    ApparentEventBody(
                        body_id="naif-501",
                        naif_id=501,
                        direction_icrf=(0.0, 1.0, 0.0),
                        direction_enu=(-1.0, 0.0, 0.0),
                        distance_km=628_000_000.0,
                        angular_radius_deg=0.0,
                        altitude_deg=0.0,
                        physical_radius_km=0.0,
                    ),
                ),
                earth_to_sun_icrf_km=(149_597_870.0, 0.0, 0.0),
                earth_to_moon_icrf_km=(-384_400.0, 0.0, 0.0),
                observer_position_icrf_km=(0.0, 0.0, 0.0),
            )

    ephemeris = FakeEphemeris()
    preview = SolarSystemPreviewService(ephemeris).calculate(
        instant,
        ScientificObserver(41.2, 0.8, 377.0),
        generation=7,
        observer_generation=3,
        additional_body_ids=("naif-501",),
    )

    assert ephemeris.requested_body_ids == PREVIEW_BODY_IDS + ("naif-501",)
    assert preview.generation == 7
    assert preview.observer_generation == 3
    assert preview.bodies[0].azimuth_deg == pytest.approx(90.0)
    assert preview.bodies[1].illumination_fraction == pytest.approx(1.0, abs=1e-4)
    assert preview.bodies[1].apparent_magnitude is not None
    assert preview.bodies[1].apparent_magnitude < -12.0
    assert preview.event.lunar.mean_lunar_light_transmission < 1.0
    assert preview.bodies[2].body_id == "naif-501"
    assert preview.bodies[2].direction_enu == (-1.0, 0.0, 0.0)
    assert preview.to_dict()["bodies"][0]["directionENU"] == [1.0, 0.0, 0.0]
