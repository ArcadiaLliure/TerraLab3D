from __future__ import annotations

import asyncio
from datetime import datetime
import math
from pathlib import Path

import aiohttp
import numpy as np
import pytest
from astropy.io import fits
from PIL import Image

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.galactic.calculations import (
    EQUATORIAL_TO_GALACTIC_J2000,
    equatorial_to_galactic_direction,
    galactic_visibility_factor,
)
from terralab3d.domain.resources.models import ResourceInstallState
from terralab3d.domain.stars.calculations import compute_celestial_transform_matrix
from terralab3d.domain.time.engine import AstronomicalEngine
from terralab3d.application.star_coordinator import StarCoordinator
from terralab3d.infrastructure.adapters.file_assets.galactic import ManagedGalacticAssets
from terralab3d.infrastructure.adapters.planck.converter import convert_planck_fits_to_texture
from terralab3d.infrastructure.resources.catalog import ResourceCatalog
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)
from terralab3d.infrastructure.server import TerraLabServer
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def _write_planck_fixture(path: Path, *, coordinate_system: str = "G") -> None:
    values = np.linspace(0.0, 11.0, 12, dtype=np.float32)
    column = fits.Column(name="TAU353", format="E", array=values)
    table = fits.BinTableHDU.from_columns([column])
    table.header["PIXTYPE"] = "HEALPIX"
    table.header["ORDERING"] = "RING"
    table.header["NSIDE"] = 1
    table.header["COORDSYS"] = coordinate_system
    fits.HDUList([fits.PrimaryHDU(), table]).writeto(path)


def _apply(matrix: tuple[float, ...], direction: tuple[float, float, float]) -> np.ndarray:
    return np.asarray(matrix, dtype=np.float64).reshape(3, 3) @ np.asarray(direction)


def _equatorial_direction(ra_deg: float, dec_deg: float) -> tuple[float, float, float]:
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)
    cos_dec = math.cos(dec_rad)
    return (
        cos_dec * math.cos(ra_rad),
        cos_dec * math.sin(ra_rad),
        math.sin(dec_rad),
    )


def _galactic_plane_inclination_deg(matrix: tuple[float, ...]) -> float:
    """Angle de la tangent l=0°→90° respecte de l'horitzó local."""

    center = _apply(matrix, _equatorial_direction(266.4051, -28.936175))
    center /= np.linalg.norm(center)
    # La segona fila de la matriu ICRS→galàctic és l'eix l=90° en ICRS.
    plane_tangent = _apply(matrix, EQUATORIAL_TO_GALACTIC_J2000[1])
    plane_tangent /= np.linalg.norm(plane_tangent)
    local_up = np.asarray((0.0, 1.0, 0.0)) - center * center[1]
    local_up /= np.linalg.norm(local_up)
    local_right = np.cross(center, local_up)
    return math.degrees(
        math.atan2(
            float(np.dot(plane_tangent, local_up)),
            float(np.dot(plane_tangent, local_right)),
        )
    ) % 180.0


def test_catalog_uses_only_nasa_celestial_milky_way_variants() -> None:
    descriptor = ResourceCatalog().get_descriptor(ResourceId("sky.milky_way"))
    assert descriptor is not None
    assert dict(descriptor.metadata)["coordinateFrame"] == "ICRF/J2000"
    assert dict(descriptor.metadata)["raIncreases"] == "left"
    assert tuple(variant.id for variant in descriptor.variants) == (
        "4k", "8k", "16k", "32k", "64k",
    )
    for variant in descriptor.variants:
        assert variant.source_url is not None
        assert variant.source_url.endswith(f"milkyway_2020_{variant.id}.exr")
        assert "_gal.exr" not in variant.source_url
        assert variant.format == "exr"


def test_catalog_keeps_planck_fits_as_the_official_source() -> None:
    descriptor = ResourceCatalog().get_descriptor(ResourceId("sky.planck_dust"))
    assert descriptor is not None
    assert dict(descriptor.metadata)["coordinateFrame"] == "GALACTIC"
    variant = descriptor.variants[0]
    assert variant.format == "fits"
    assert variant.source_url is not None
    assert variant.source_url.endswith("COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01.fits")


def test_planck_converter_creates_local_equirectangular_texture(tmp_path: Path) -> None:
    source = tmp_path / "planck.fits"
    output = tmp_path / "derived" / "planck-opacity.png"
    _write_planck_fixture(source)

    result = convert_planck_fits_to_texture(
        source,
        output,
        width=64,
        height=32,
        workers=1,
        chunk_rows=8,
    )

    assert source.exists(), "el FITS oficial no s'ha de substituir"
    assert result.output_path == output.resolve()
    assert result.coordinate_system == "G"
    assert result.source_column == "TAU353"
    assert result.nside == 1
    with Image.open(output) as image:
        assert image.mode == "L"
        assert image.size == (64, 32)
        values = np.asarray(image)
    assert values.dtype == np.uint8
    assert int(values.max()) > int(values.min())


def test_planck_converter_rejects_a_non_galactic_source(tmp_path: Path) -> None:
    source = tmp_path / "not-galactic.fits"
    _write_planck_fixture(source, coordinate_system="C")
    with pytest.raises(ValueError, match="coordenades galàctiques"):
        convert_planck_fits_to_texture(source, tmp_path / "out.png", width=32, height=16)


def test_galactic_layers_share_gaia_observer_and_time_transform() -> None:
    vernal_direction = (1.0, 0.0, 0.0)  # RA=0, Dec=0 in ICRF/J2000
    barcelona = _apply(
        compute_celestial_transform_matrix(latitude_deg=41.3874, lst_deg=0.0),
        vernal_direction,
    )
    sydney = _apply(
        compute_celestial_transform_matrix(latitude_deg=-33.8688, lst_deg=0.0),
        vernal_direction,
    )
    six_sidereal_hours_later = _apply(
        compute_celestial_transform_matrix(latitude_deg=41.3874, lst_deg=90.0),
        vernal_direction,
    )

    assert barcelona[2] > 0.0
    assert sydney[2] < 0.0
    assert not np.allclose(barcelona, sydney)
    assert not np.allclose(barcelona, six_sidereal_hours_later)
    assert np.allclose(six_sidereal_hours_later, (-1.0, 0.0, 0.0), atol=1e-12)


def test_galactic_plane_inclination_changes_with_observer_latitude() -> None:
    lst_deg = 280.9752748692408
    barcelona_matrix = compute_celestial_transform_matrix(41.3874, lst_deg)
    sydney_matrix = compute_celestial_transform_matrix(-33.8688, lst_deg)

    barcelona_inclination = _galactic_plane_inclination_deg(barcelona_matrix)
    sydney_inclination = _galactic_plane_inclination_deg(sydney_matrix)
    line_angle_difference = abs(barcelona_inclination - sydney_inclination)
    line_angle_difference = min(line_angle_difference, 180.0 - line_angle_difference)

    assert line_angle_difference > 60.0


def test_galactic_center_is_below_barcelona_horizon_on_a_winter_night() -> None:
    engine = AstronomicalEngine()
    center = _equatorial_direction(266.4051, -28.936175)

    def center_altitude_deg(instant_iso: str) -> float:
        instant = datetime.fromisoformat(instant_iso)
        lst_deg = engine.local_sidereal_angle_deg(instant, 2.1686)
        local = _apply(
            compute_celestial_transform_matrix(41.3874, lst_deg),
            center,
        )
        return math.degrees(math.asin(float(np.clip(local[1], -1.0, 1.0))))

    winter_altitude = center_altitude_deg("2026-01-15T00:00:00+00:00")
    summer_altitude = center_altitude_deg("2026-07-15T00:00:00+00:00")

    assert winter_altitude < -60.0
    assert summer_altitude > 14.0


def test_celestial_frame_is_republished_without_a_fake_generation() -> None:
    published: list[dict[str, object]] = []

    async def ignore(*_args: object, **_kwargs: object) -> None:
        return None

    async def capture(payload: dict[str, object]) -> None:
        published.append(payload)

    async def scenario() -> None:
        coordinator = StarCoordinator()
        coordinator.set_publishers(ignore, ignore, capture)
        assert await coordinator.update_celestial_transform(41.3874, 280.0)
        assert not await coordinator.update_celestial_transform(41.3874, 280.0)
        assert await coordinator.update_celestial_transform(
            41.3874,
            280.0,
            force_publish=True,
        )
        await coordinator.shutdown()

    asyncio.run(scenario())

    assert len(published) == 2
    assert published[0]["generation"] == published[1]["generation"] == 1
    assert published[0]["matrix3x3"] == published[1]["matrix3x3"]


def test_planck_only_uses_the_fixed_icrs_to_galactic_transform() -> None:
    ra = np.deg2rad(266.4051)
    dec = np.deg2rad(-28.936175)
    equatorial = (
        float(np.cos(dec) * np.cos(ra)),
        float(np.cos(dec) * np.sin(ra)),
        float(np.sin(dec)),
    )
    galactic = equatorial_to_galactic_direction(equatorial)
    longitude = np.rad2deg(np.arctan2(galactic[1], galactic[0])) % 360.0
    latitude = np.rad2deg(np.arcsin(galactic[2]))
    assert min(abs(longitude), abs(longitude - 360.0)) < 0.001
    assert abs(latitude) < 0.001


def test_galactic_visibility_is_continuous_for_daylight_and_bortle() -> None:
    dark = galactic_visibility_factor(
        sky_brightness_normalized=0.0,
        light_pollution_enabled=True,
        bortle_class=1.0,
    )
    polluted = galactic_visibility_factor(
        sky_brightness_normalized=0.7,
        light_pollution_enabled=True,
        bortle_class=8.0,
    )
    daylight = galactic_visibility_factor(
        sky_brightness_normalized=1.0,
        light_pollution_enabled=True,
        bortle_class=1.0,
    )
    assert dark > polluted > daylight
    assert daylight == 0.0


def test_managed_asset_only_exposes_ready_files_inside_data_library(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path))
    repository = ResourceInstallationRepository()
    assets = ManagedGalacticAssets(repository)
    managed = tmp_path / "data" / "sky" / "managed"
    managed.mkdir(parents=True)
    texture = managed / "milkyway.exr"
    texture.write_bytes(b"EXR fixture")

    repository.set_resource_state(
        ResourceId("sky.milky_way"),
        ResourceInstallState.READY,
        VariantId("4k"),
        resolved_path=str(texture),
        manifest_data={"sourcePath": str(texture), "renderPath": str(texture)},
    )
    assert assets.resolve_asset("sky.milky_way") == texture.resolve()
    assert assets.resolve_asset("sky.not_registered") is None

    outside = tmp_path.parent / "outside.exr"
    outside.write_bytes(b"outside")
    repository.set_resource_state(
        ResourceId("sky.milky_way"),
        ResourceInstallState.READY,
        VariantId("4k"),
        resolved_path=str(outside),
        manifest_data={"renderPath": str(outside)},
    )
    assert assets.resolve_asset("sky.milky_way") is None
    outside.unlink()


def test_local_server_streams_only_the_registered_galactic_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    repository = ResourceInstallationRepository()
    managed_dir = tmp_path / "library" / "data" / "sky" / "managed"
    managed_dir.mkdir(parents=True)
    texture = managed_dir / "milkyway.exr"
    texture.write_bytes(b"0123456789")
    repository.set_resource_state(
        ResourceId("sky.milky_way"),
        ResourceInstallState.READY,
        VariantId("4k"),
        resolved_path=str(texture),
        manifest_data={"renderPath": str(texture)},
    )
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("ok", encoding="utf-8")

    async def scenario() -> None:
        server = TerraLabServer(
            dist,
            WebSocketBridge(),
            galactic_assets=ManagedGalacticAssets(repository),
            port=0,
        )
        await server.start()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{server.url}/managed-galactic-assets/sky.milky_way",
                    headers={"Range": "bytes=2-5"},
                ) as response:
                    assert response.status == 206
                    assert await response.read() == b"2345"
                async with session.get(
                    f"{server.url}/managed-galactic-assets/sky.unknown"
                ) as response:
                    assert response.status == 404
        finally:
            await server.stop()

    asyncio.run(scenario())
