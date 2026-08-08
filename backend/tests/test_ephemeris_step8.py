from __future__ import annotations

import asyncio
import json
import math
import threading
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from terralab3d.application.ephemeris_coordinator import EphemerisCoordinator
from terralab3d.domain.sky_background.sky_environment import SkyEnvironmentComposer
from terralab3d.domain.solar_system.calculations import AU_KM, angular_radius_deg
from terralab3d.domain.solar_system.models import ScientificObserver, SolarSystemSnapshot
from terralab3d.infrastructure.adapters.ephemeris.adapter import SkyfieldEphemerisAdapter
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge

FIXTURE = Path(__file__).parent / "fixtures" / "horizons_2024_01_01.json"


@pytest.fixture(scope="module")
def authoritative_snapshot() -> SolarSystemSnapshot:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    adapter = SkyfieldEphemerisAdapter()
    snapshot = adapter.snapshot(
        datetime.fromisoformat(fixture["utc"].replace("Z", "+00:00")),
        ScientificObserver(**fixture["observer"]),
    )
    adapter.close()
    assert snapshot.source == "DE421"
    return snapshot


def test_de421_metadata_is_explicit_and_reproducible() -> None:
    adapter = SkyfieldEphemerisAdapter()
    metadata = adapter.metadata
    assert metadata.kernel_name == "de421.bsp"
    assert metadata.skyfield_version == "1.55"
    assert metadata.kernel_sha256 == "a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc"
    assert metadata.range_start_utc == "1899-07-28"
    assert metadata.range_end_utc == "2053-10-08"
    adapter.close()


def test_all_required_bodies_match_independent_horizons_fixture(
    authoritative_snapshot: SolarSystemSnapshot,
) -> None:
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))["bodies"]
    actual = {
        str(body.body_id): body
        for body in (
            authoritative_snapshot.sun,
            authoritative_snapshot.moon,
            *authoritative_snapshot.planets,
        )
        if body is not None
    }
    assert tuple(actual) == (
        "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"
    )
    for body_id, fixture in expected.items():
        body = actual[body_id]
        assert _equatorial_separation_deg(body, fixture) < 0.01
        assert _horizontal_separation_deg(body, fixture) < 0.01
        assert body.distance_km / AU_KM == pytest.approx(fixture["distance_au"], rel=5e-5)
        assert body.phase_angle_deg == pytest.approx(fixture["phase_angle_deg"], abs=0.02)
        assert body.apparent_magnitude == pytest.approx(fixture["apparent_magnitude"], abs=0.08)
        assert body.angular_radius_deg > 0.0
        assert 0.0 <= body.illumination_fraction <= 1.0


def test_moon_is_topocentric_for_distant_observers() -> None:
    adapter = SkyfieldEphemerisAdapter()
    instant = datetime(2024, 1, 18, 12, tzinfo=timezone.utc)
    north = adapter.snapshot(instant, ScientificObserver(52.0, 0.0, 50.0)).moon
    south = adapter.snapshot(instant, ScientificObserver(-35.0, 149.0, 600.0)).moon
    adapter.close()
    assert north is not None and south is not None
    assert _separation_from_directions(north.direction_enu, south.direction_enu) > 20.0
    assert abs(north.equatorial.right_ascension_deg - south.equatorial.right_ascension_deg) > 0.1


def test_representative_lunar_quarters_have_distinct_terminator_orientation() -> None:
    adapter = SkyfieldEphemerisAdapter()
    observer = ScientificObserver(41.189795, 1.210058, 0.0)
    waning = adapter.snapshot(datetime(2024, 1, 4, 12, tzinfo=timezone.utc), observer).moon
    waxing = adapter.snapshot(datetime(2024, 1, 18, 12, tzinfo=timezone.utc), observer).moon
    adapter.close()
    assert waning is not None and waxing is not None
    assert waning.illumination_fraction == pytest.approx(0.5, abs=0.05)
    assert waxing.illumination_fraction == pytest.approx(0.5, abs=0.05)
    assert waning.bright_limb_position_angle_deg is not None
    assert waxing.bright_limb_position_angle_deg is not None
    difference = abs(waning.bright_limb_position_angle_deg - waxing.bright_limb_position_angle_deg)
    assert 90.0 < difference < 270.0


def test_moon_angular_size_varies_with_topocentric_distance() -> None:
    adapter = SkyfieldEphemerisAdapter()
    observer = ScientificObserver(0.0, 0.0, 0.0)
    first = adapter.snapshot(datetime(2024, 1, 1, tzinfo=timezone.utc), observer).moon
    second = adapter.snapshot(datetime(2024, 1, 13, tzinfo=timezone.utc), observer).moon
    adapter.close()
    assert first is not None and second is not None
    assert abs(first.angular_radius_deg - second.angular_radius_deg) > 0.005
    assert first.angular_radius_deg == pytest.approx(
        angular_radius_deg(1_737.4, first.distance_km), rel=1e-12
    )


def test_missing_or_out_of_range_kernel_has_honest_solar_only_fallback(tmp_path: Path) -> None:
    adapter = SkyfieldEphemerisAdapter(tmp_path / "missing-de421.bsp")
    fallback = adapter.snapshot(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        ScientificObserver(41.0, 1.0, 0.0),
    )
    adapter.close()
    assert fallback.source == "fallback"
    assert fallback.sun.source == "analytical-solar-fallback"
    assert fallback.moon is None
    assert fallback.planets == ()

    adapter = SkyfieldEphemerisAdapter()
    out_of_range = adapter.snapshot(
        datetime(2200, 1, 1, tzinfo=timezone.utc),
        ScientificObserver(41.0, 1.0, 0.0),
    )
    adapter.close()
    assert out_of_range.source == "fallback"
    assert out_of_range.moon is None
    assert "outside DE421 range" in (out_of_range.detail or "")


def test_atmosphere_and_solar_renderer_payload_share_exactly_one_sun(
    authoritative_snapshot: SolarSystemSnapshot,
) -> None:
    sky = SkyEnvironmentComposer().compose(authoritative_snapshot.sun, generation := 17)
    assert sky.solar_system_generation == generation
    assert sky.sun_direction_enu == authoritative_snapshot.sun.direction_enu
    assert sky.sun_altitude_deg == authoritative_snapshot.sun.horizontal.altitude_deg
    assert sky.sun_azimuth_deg == authoritative_snapshot.sun.horizontal.azimuth_deg


def test_latest_wins_discards_stale_result_and_keeps_one_pending(
    authoritative_snapshot: SolarSystemSnapshot,
) -> None:
    class BlockingPort:
        metadata = None

        def __init__(self) -> None:
            self.release = threading.Event()
            self.calls: list[datetime] = []

        def snapshot(self, utc: datetime, _observer: ScientificObserver) -> SolarSystemSnapshot:
            self.calls.append(utc)
            if len(self.calls) == 1:
                self.release.wait(timeout=2)
            return replace(authoritative_snapshot, timestamp_utc=utc, compute_ms=1.0)

        def close(self) -> None:
            self.release.set()

    async def scenario() -> None:
        port = BlockingPort()
        published: list[SolarSystemSnapshot] = []

        async def publish(snapshot: SolarSystemSnapshot) -> int:
            published.append(snapshot)
            return 123

        coordinator = EphemerisCoordinator(port, publish)
        observer = ScientificObserver(41.0, 1.0, 0.0)
        coordinator.request(datetime(2024, 1, 1, tzinfo=timezone.utc), observer, 1)
        await asyncio.sleep(0.02)
        coordinator.request(datetime(2024, 1, 2, tzinfo=timezone.utc), observer, 1)
        coordinator.request(datetime(2024, 1, 3, tzinfo=timezone.utc), observer, 1)
        port.release.set()
        await coordinator.wait_idle()
        metrics = coordinator.metrics()
        assert len(port.calls) == 2
        assert [item.generation for item in published] == [1, 3]
        assert metrics["ephemeris_stale_count"] == 0
        assert metrics["ephemeris_coalesced_count"] == 1
        assert metrics["solar_system_bridge_bytes"] == 123
        await coordinator.close()

    asyncio.run(scenario())


def test_solar_system_bridge_is_compact_and_never_uses_binary_gaia_transport(
    authoritative_snapshot: SolarSystemSnapshot,
) -> None:
    class FakeWebSocket:
        closed = False

        def __init__(self) -> None:
            self.json_messages: list[dict] = []
            self.binary_messages: list[bytes] = []

        async def send_json(self, payload: dict) -> None:
            self.json_messages.append(payload)

        async def send_bytes(self, payload: bytes) -> None:
            self.binary_messages.append(payload)

    async def scenario() -> None:
        bridge = WebSocketBridge()
        socket = FakeWebSocket()
        bridge._ws = socket  # focused transport double
        binary_before = bridge.binary_bytes_sent
        byte_count = await bridge.send_solar_system_snapshot(authoritative_snapshot)
        assert 1_000 < byte_count < 8_000
        assert len(socket.json_messages) == 1
        assert socket.binary_messages == []
        assert bridge.binary_bytes_sent == binary_before
        assert "gaia" not in json.dumps(socket.json_messages[0]).lower()

    asyncio.run(scenario())


def _equatorial_separation_deg(body, fixture: dict) -> float:
    return _spherical_separation_deg(
        body.equatorial.right_ascension_deg,
        body.equatorial.declination_deg,
        fixture["ra_deg"],
        fixture["dec_deg"],
    )


def _horizontal_separation_deg(body, fixture: dict) -> float:
    return _spherical_separation_deg(
        body.horizontal.azimuth_deg,
        body.horizontal.altitude_deg,
        fixture["azimuth_deg"],
        fixture["altitude_deg"],
    )


def _spherical_separation_deg(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (lon_a, lat_a, lon_b, lat_b))
    cosine = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon1 - lon2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _separation_from_directions(first, second) -> float:
    dot = sum(a * b for a, b in zip(first, second, strict=True))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))

