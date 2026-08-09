from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
import math

import pytest

from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId
from terralab3d.domain.lighting.environment import LightingEnvironmentComposer
from terralab3d.domain.sky_background.sky_environment import SkyEnvironmentComposer
from terralab3d.domain.solar_system.models import (
    ApparentBodyState,
    BodyKind,
    EphemerisQuality,
    SolarSystemSnapshot,
)
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def _body(
    body_id: str,
    kind: BodyKind,
    *,
    altitude_deg: float,
    magnitude: float | None,
    illumination: float = 1.0,
    distance_km: float = 384_400.0,
) -> ApparentBodyState:
    altitude_rad = math.radians(altitude_deg)
    direction = (0.0, math.sin(altitude_rad), math.cos(altitude_rad))
    return ApparentBodyState(
        body_id=CelestialBodyId(body_id),
        kind=kind,
        equatorial=EquatorialCoordinate(0.0, altitude_deg),
        horizontal=HorizontalCoordinate(altitude_deg, 0.0),
        direction_enu=direction,
        distance_km=distance_km,
        angular_radius_deg=0.25,
        illumination_fraction=illumination,
        phase_angle_deg=math.degrees(math.acos(max(-1.0, min(1.0, illumination * 2 - 1)))),
        apparent_magnitude=magnitude,
        source="DE421",
        quality=EphemerisQuality.PRECISE,
    )


def _solar_snapshot(
    *,
    sun_altitude_deg: float = 45.0,
    moon_altitude_deg: float = 50.0,
    moon_magnitude: float | None = -12.74,
    moon_illumination: float = 1.0,
    generation: int = 7,
) -> SolarSystemSnapshot:
    return SolarSystemSnapshot(
        generation=generation,
        timestamp_utc=datetime(2026, 8, 9, 22, 0, tzinfo=timezone.utc),
        observer_generation=3,
        source="DE421",
        quality=EphemerisQuality.PRECISE,
        sun=_body(
            "sun",
            BodyKind.SUN,
            altitude_deg=sun_altitude_deg,
            magnitude=-26.74,
            distance_km=149_597_870.7,
        ),
        moon=_body(
            "moon",
            BodyKind.MOON,
            altitude_deg=moon_altitude_deg,
            magnitude=moon_magnitude,
            illumination=moon_illumination,
        ),
        planets=(),
        compute_ms=1.0,
    )


def _compose(snapshot: SolarSystemSnapshot) -> tuple[LightingEnvironmentComposer, object, object]:
    sky = SkyEnvironmentComposer().compose(snapshot.sun, snapshot.generation)
    composer = LightingEnvironmentComposer()
    return composer, sky, composer.compose(sky, snapshot)


def test_compact_snapshot_preserves_sources_and_existing_science() -> None:
    solar = _solar_snapshot()
    composer, sky, lighting = _compose(solar)
    assert lighting.source_sky_generation == sky.generation
    assert lighting.source_solar_system_generation == solar.generation
    assert lighting.timestamp_utc == solar.timestamp_utc
    assert lighting.sun.direction_to_source_enu == pytest.approx(solar.sun.direction_enu)
    assert lighting.moon.direction_to_source_enu == pytest.approx(solar.moon.direction_enu)
    assert lighting.sun.intensity_kind == "visual"
    assert lighting.moon.intensity_kind == "relative"
    assert lighting.direct_solar_visibility_factor == 1.0
    assert composer.metrics()["lighting_snapshot_count"] == 1


def test_apparent_magnitude_is_not_multiplied_by_phase_or_distance_again() -> None:
    full = _solar_snapshot(moon_magnitude=-12.74, moon_illumination=1.0)
    # Same apparent magnitude but deliberately incompatible phase/distance. The
    # lighting result must be identical because magnitude already includes both.
    altered_moon = replace(
        full.moon,
        illumination_fraction=0.01,
        distance_km=800_000.0,
    )
    altered = replace(full, moon=altered_moon)
    _, _, full_lighting = _compose(full)
    _, _, altered_lighting = _compose(altered)
    assert altered_lighting.moon.intensity == pytest.approx(full_lighting.moon.intensity)


def test_full_new_and_quarter_moon_have_distinct_local_contributions() -> None:
    _, _, full = _compose(_solar_snapshot(moon_magnitude=-12.74))
    _, _, quarter = _compose(_solar_snapshot(moon_magnitude=-10.0))
    _, _, new = _compose(_solar_snapshot(moon_magnitude=-3.8))
    # Visual PBR calibration: a high full Moon must remain observable after
    # atmospheric extinction, while staying vastly dimmer than direct Sun.
    assert 0.08 < full.moon.intensity < 0.2
    assert full.moon.intensity > quarter.moon.intensity > new.moon.intensity
    assert full.moon.intensity > new.moon.intensity * 1_000


def test_moon_fallback_uses_phase_distance_only_when_magnitude_is_missing() -> None:
    _, _, full = _compose(
        _solar_snapshot(moon_magnitude=None, moon_illumination=1.0)
    )
    _, _, crescent = _compose(
        _solar_snapshot(moon_magnitude=None, moon_illumination=0.1)
    )
    assert full.moon.quality == "approximate"
    assert full.moon.intensity_kind == "visual"
    assert full.moon.intensity > crescent.moon.intensity * 9


def test_direct_lights_are_zero_below_the_authoritative_horizon() -> None:
    _, _, lighting = _compose(
        _solar_snapshot(sun_altitude_deg=-0.1, moon_altitude_deg=-0.1)
    )
    assert not lighting.sun.enabled and lighting.sun.intensity == 0
    assert not lighting.moon.enabled and lighting.moon.intensity == 0


def test_pas9_visibility_hook_is_single_bounded_factor() -> None:
    solar = _solar_snapshot()
    sky = SkyEnvironmentComposer().compose(solar.sun, solar.generation)
    composer = LightingEnvironmentComposer()
    normal = composer.compose(sky, solar)
    hidden = composer.compose(sky, solar, direct_solar_visibility_factor=0.0)
    assert hidden.sun.intensity == 0
    assert hidden.moon.intensity == pytest.approx(normal.moon.intensity)
    assert hidden.sky_diffuse == normal.sky_diffuse


def test_invalid_or_degenerate_scientific_vectors_are_rejected() -> None:
    solar = _solar_snapshot()
    assert solar.moon is not None
    broken = replace(solar, moon=replace(solar.moon, direction_enu=(math.nan, 0.0, 0.0)))
    sky = SkyEnvironmentComposer().compose(solar.sun, solar.generation)
    with pytest.raises(ValueError, match="moon.directionENU"):
        LightingEnvironmentComposer().compose(sky, broken)


def test_sky_and_diffuse_light_share_exact_linear_palette() -> None:
    solar = _solar_snapshot(sun_altitude_deg=3.0)
    _, sky, lighting = _compose(solar)
    assert lighting.sky_diffuse.zenith_color_linear == sky.zenith_color_linear
    assert lighting.sky_diffuse.horizon_color_linear == sky.horizon_color_linear
    assert lighting.sky_diffuse.ground_color_linear == sky.ground_color_linear
    assert lighting.sky_diffuse.intensity == sky.sky_diffuse_intensity


def test_lighting_bridge_is_json_only_and_reports_exact_bytes() -> None:
    class FakeWebSocket:
        closed = False

        def __init__(self) -> None:
            self.json_messages: list[dict] = []

        async def send_json(self, payload: dict) -> None:
            self.json_messages.append(payload)

    async def scenario() -> None:
        _, _, lighting = _compose(_solar_snapshot())
        bridge = WebSocketBridge()
        socket = FakeWebSocket()
        bridge._ws = socket  # focused transport double
        binary_before = bridge.binary_bytes_sent
        byte_count = await bridge.send_lighting_environment_snapshot(lighting)
        assert byte_count == bridge.lighting_bridge_bytes
        assert byte_count < 2_000
        assert bridge.binary_bytes_sent == binary_before
        assert len(socket.json_messages) == 1
        encoded = json.dumps(socket.json_messages[0]).lower()
        assert "texture" not in encoded and "geometry" not in encoded and "gaia" not in encoded

    asyncio.run(scenario())
