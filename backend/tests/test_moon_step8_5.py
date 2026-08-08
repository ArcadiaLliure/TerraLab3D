from __future__ import annotations

import asyncio
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from terralab3d.domain.resources.moon_surface import MoonSurfaceStatus
from terralab3d.domain.solar_system.calculations import matrix3_apply
from terralab3d.domain.solar_system.models import (
    LunarOrientationQuality,
    ScientificObserver,
)
from terralab3d.infrastructure.adapters.ephemeris.adapter import SkyfieldEphemerisAdapter
from terralab3d.infrastructure.adapters.file_assets.moon_surface import ManagedMoonSurfaceAssets
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


@pytest.fixture()
def orientation_adapter() -> SkyfieldEphemerisAdapter:
    adapter = SkyfieldEphemerisAdapter()
    if adapter.metadata.lunar_orientation_frame is None:
        adapter.close()
        pytest.skip("Managed DE421 lunar orientation kernels are not installed")
    yield adapter
    adapter.close()


def test_official_skyfield_libration_example_matches_de421(
    orientation_adapter: SkyfieldEphemerisAdapter,
) -> None:
    moon = orientation_adapter.snapshot(
        datetime(2019, 12, 20, 11, 5, tzinfo=timezone.utc),
        ScientificObserver(0.0, 0.0, 0.0),
    ).moon
    assert moon is not None and moon.orientation is not None
    orientation = moon.orientation
    assert orientation.quality is LunarOrientationQuality.PRECISE
    assert orientation.frame == "MOON_ME_DE421"
    # Independent values published by the Skyfield planetary-frame example.
    assert orientation.libration_longitude_deg == pytest.approx(1.520, abs=0.001)
    assert orientation.libration_latitude_deg == pytest.approx(-6.749, abs=0.001)
    assert orientation.north_pole_position_angle_deg == pytest.approx(22.559, abs=0.001)
    assert orientation.bright_limb_position_angle_deg == pytest.approx(114.087, abs=0.001)


def test_body_quaternion_places_subobserver_point_toward_real_observer(
    orientation_adapter: SkyfieldEphemerisAdapter,
) -> None:
    moon = orientation_adapter.snapshot(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        ScientificObserver(41.189795, 1.210058, 0.0),
    ).moon
    assert moon is not None and moon.orientation is not None
    orientation = moon.orientation
    assert orientation.body_to_enu_quaternion is not None
    assert orientation.sub_observer_longitude_deg is not None
    assert orientation.sub_observer_latitude_deg is not None

    longitude = math.radians(orientation.sub_observer_longitude_deg)
    latitude = math.radians(orientation.sub_observer_latitude_deg)
    subobserver_body = (
        math.cos(latitude) * math.cos(longitude),
        math.cos(latitude) * math.sin(longitude),
        math.sin(latitude),
    )
    transformed = matrix3_apply(
        _quaternion_matrix(orientation.body_to_enu_quaternion),
        subobserver_body,
    )
    east, up, north = moon.direction_enu
    moon_to_observer_enu = (-east, -north, -up)
    error = math.sqrt(
        sum((actual - expected) ** 2 for actual, expected in zip(transformed, moon_to_observer_enu))
    )
    assert error < 3.0e-6


def test_subobserver_point_is_topocentric_and_local_orientation_changes_by_hemisphere(
    orientation_adapter: SkyfieldEphemerisAdapter,
) -> None:
    instant = datetime(2024, 1, 1, tzinfo=timezone.utc)
    north = orientation_adapter.snapshot(
        instant, ScientificObserver(41.189795, 1.210058, 0.0)
    ).moon
    south = orientation_adapter.snapshot(
        instant, ScientificObserver(-35.0, 149.0, 600.0)
    ).moon
    assert north is not None and south is not None
    assert north.orientation is not None and south.orientation is not None
    assert north.orientation.sub_earth_longitude_deg == pytest.approx(
        south.orientation.sub_earth_longitude_deg, abs=1e-12
    )
    assert abs(
        north.orientation.sub_observer_longitude_deg
        - south.orientation.sub_observer_longitude_deg
    ) > 1.0
    assert north.orientation.body_to_enu_quaternion != south.orientation.body_to_enu_quaternion


def test_lunar_orientation_and_kernel_lifecycle_are_explicit(
    orientation_adapter: SkyfieldEphemerisAdapter,
) -> None:
    metadata = orientation_adapter.metadata
    assert metadata.lunar_orientation_frame == "MOON_ME_DE421"
    assert metadata.lunar_frame_kernel_sha256 == (
        "78732477b96f9863e7b0d65bcee3c22b8707ca5ed0db56d1173319cb2e8c7993"
    )
    assert metadata.lunar_orientation_kernel_sha256 == (
        "656f90616403d75a75f0cd6c8830fc5b44f8cb4facb5ccb8915e752b397520cf"
    )
    observer = ScientificObserver(41.0, 1.0, 0.0)
    for second in range(5):
        moon = orientation_adapter.snapshot(
            datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc), observer
        ).moon
        assert moon is not None and moon.orientation is not None
        assert math.isclose(
            sum(value * value for value in moon.orientation.body_to_enu_quaternion),
            1.0,
            abs_tol=1e-12,
        )
        assert math.isclose(
            sum(value * value for value in moon.orientation.moon_to_sun_direction_enu),
            1.0,
            abs_tol=1e-12,
        )
    assert orientation_adapter.lunar_orientation_kernel_load_count == 1


def test_out_of_range_and_missing_orientation_keep_step8_moon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = SkyfieldEphemerisAdapter()
    out_of_range = adapter.snapshot(
        datetime(2051, 1, 1, tzinfo=timezone.utc),
        ScientificObserver(41.0, 1.0, 0.0),
    )
    adapter.close()
    assert out_of_range.source == "DE421"
    assert out_of_range.moon is not None and out_of_range.moon.orientation is not None
    assert out_of_range.moon.orientation.quality is LunarOrientationQuality.OUT_OF_RANGE
    assert out_of_range.moon.orientation.body_to_enu_quaternion is None

    monkeypatch.setenv("TERRALAB3D_LUNAR_ORIENTATION_DIR", str(tmp_path / "missing"))
    adapter = SkyfieldEphemerisAdapter()
    partial = adapter.snapshot(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        ScientificObserver(41.0, 1.0, 0.0),
    )
    adapter.close()
    assert partial.moon is not None and partial.moon.orientation is not None
    assert partial.moon.orientation.quality is LunarOrientationQuality.UNAVAILABLE
    assert partial.moon.orientation.body_to_enu_quaternion is None


def test_managed_surface_manifest_is_validated_and_never_resolves_unknown_names(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    assets = []
    for role, name, dimensions in (
        ("albedo_8k", "moon-8k.jpg", (8192, 4096)),
        ("albedo_4k", "moon-4k.jpg", (4096, 2048)),
        ("normal_4k", "moon-normal.png", (4096, 2048)),
    ):
        path = runtime / name
        path.write_bytes(role.encode("ascii"))
        assets.append(
            {
                "role": role,
                "name": name,
                "widthPx": dimensions[0],
                "heightPx": dimensions[1],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "byteSize": path.stat().st_size,
            }
        )
    manifest = _manifest(assets)
    (tmp_path / "moon-surface-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    catalog = ManagedMoonSurfaceAssets(tmp_path)
    assert catalog.descriptor.status is MoonSurfaceStatus.READY
    assert catalog.descriptor.label == "LRO 2025 8K"
    assert catalog.resolve_asset("moon-8k.jpg") == (runtime / "moon-8k.jpg").resolve()
    assert catalog.resolve_asset("../moon-8k.jpg") is None


def test_invalid_or_missing_surface_manifest_has_honest_fallback(tmp_path: Path) -> None:
    missing = ManagedMoonSurfaceAssets(tmp_path)
    assert missing.descriptor.status is MoonSurfaceStatus.UNAVAILABLE

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    asset = runtime / "moon-4k.jpg"
    asset.write_bytes(b"not-the-declared-content")
    manifest = _manifest(
        [
            {
                "role": "albedo_4k",
                "name": asset.name,
                "widthPx": 4096,
                "heightPx": 2048,
                "sha256": "0" * 64,
                "byteSize": asset.stat().st_size,
            }
        ]
    )
    (tmp_path / "moon-surface-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    invalid = ManagedMoonSurfaceAssets(tmp_path)
    assert invalid.descriptor.status is MoonSurfaceStatus.INVALID
    assert invalid.resolve_asset(asset.name) is None


def test_moon_resource_bridge_contains_descriptors_but_no_texture_bytes(tmp_path: Path) -> None:
    catalog = ManagedMoonSurfaceAssets(tmp_path)

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
        bridge._ws = socket
        binary_before = bridge.binary_bytes_sent
        await bridge.send_moon_surface_resource(catalog.descriptor)
        assert len(socket.json_messages) == 1
        assert socket.json_messages[0]["type"] == "moon_surface_resource"
        assert socket.binary_messages == []
        assert bridge.binary_bytes_sent == binary_before
        assert "base64" not in json.dumps(socket.json_messages[0]).lower()

    asyncio.run(scenario())


def _quaternion_matrix(quaternion: tuple[float, float, float, float]):
    x, y, z, w = quaternion
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def _manifest(assets: list[dict]) -> dict:
    return {
        "source": "NASA Scientific Visualization Studio — CGI Moon Kit",
        "sourcePage": "https://svs.gsfc.nasa.gov/4720/",
        "sourceUrl": "https://svs.gsfc.nasa.gov/example/lroc.tif",
        "sourceFile": "lroc_color_16bit_srgb_8k.tif",
        "sourceVersion": "LROC color map 2025",
        "acquisitionDate": "2026-08-08",
        "sha256": "source-hash",
        "projection": "global equirectangular/cylindrical",
        "centralLongitudeDeg": 0,
        "colorSpace": "sRGB",
        "generatedAsset": assets[0]["name"],
        "generatedAssetSha256": assets[0]["sha256"],
        "generatorVersion": "test",
        "credits": ["NASA's Scientific Visualization Studio"],
        "assets": assets,
    }
