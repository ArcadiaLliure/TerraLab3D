from __future__ import annotations

import hashlib
import asyncio
import threading
import json
import os
from pathlib import Path

import numpy as np
import pytest
import rasterio
import aiohttp
from affine import Affine

from terralab3d.application.raster_imports import (
    RasterImportError,
    RasterImportService,
    elevation_sources_from_repository,
)
from terralab3d.application.reloadable_elevation import ReloadableElevationPort
from terralab3d.domain.elevation.models import (
    ElevationSample,
    ElevationSourceMetadata,
    ElevationStatus,
)
from terralab3d.domain.elevation.models import ElevationRasterSource, VerticalUnit
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.identifiers import TerrainTileId
from terralab3d.domain.raster.models import RasterDatasetSelection
from terralab3d.domain.terrain.models import TerrainTileRequest
from terralab3d.infrastructure.adapters.dem.adapter import RasterioElevationAdapter
from terralab3d.infrastructure.adapters.raster import RasterioRasterReader, TextRasterMaterializer
from terralab3d.infrastructure.resources.data_sources import DataSourceRepository
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)
from terralab3d.infrastructure.resources.layer_database import LayerDatabase
from terralab3d.infrastructure.server import TerraLabServer
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def _write_tiff(
    path: Path,
    values: np.ndarray,
    *,
    nodata: float | None = -9999,
    scale: float = 1.0,
    offset: float = 0.0,
) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[1],
        height=values.shape[0],
        count=1,
        dtype=values.dtype,
        crs="EPSG:4326",
        transform=Affine(1, 0, 0, 0, -1, 2),
        nodata=nodata,
    ) as dataset:
        dataset.write(values, 1)
        dataset.scales = (scale,)
        dataset.offsets = (offset,)


def _service(tmp_path: Path, *, callback=None):
    root = tmp_path / "library"
    repository = DataSourceRepository(root / "config" / "data_sources.json")
    catalog = LayerDatabase(tmp_path / "state" / "layers.json")
    installations = ResourceInstallationRepository(
        tmp_path / "state" / "local_installation_state.json"
    )
    service = RasterImportService(
        RasterioRasterReader(),
        TextRasterMaterializer(),
        repository,
        catalog,
        installations,
        data_root=root,
        activation_callback=callback,
    )
    return service, repository, catalog, installations


def _upload(service: RasterImportService, import_id: str, source: Path, relative: str) -> None:
    destination = service.upload_destination(import_id, 0, relative)
    payload = source.read_bytes()
    destination.write_bytes(payload)
    service.finish_upload(
        import_id,
        0,
        relative,
        len(payload),
        hashlib.sha256(payload).hexdigest(),
    )


def _upload_at(
    service: RasterImportService,
    import_id: str,
    ordinal: int,
    source: Path,
    relative: str,
) -> None:
    destination = service.upload_destination(import_id, ordinal, relative)
    payload = source.read_bytes()
    destination.write_bytes(payload)
    service.finish_upload(
        import_id,
        ordinal,
        relative,
        len(payload),
        hashlib.sha256(payload).hexdigest(),
    )


def test_data_sources_migrates_order_and_preserves_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "data_sources.json"
    path.write_text(
        '{"schemaVersion":3,"futureRoot":7,"sources":['
        '{"id":"old","layer_type":"elevation","futureField":"kept"}],'
        '"selections":{"elevation":{"source_id":"old","futureSelection":true}}}',
        encoding="utf-8",
    )
    repository = DataSourceRepository(path)
    snapshot = repository.snapshot()
    assert snapshot["schemaVersion"] == 6
    assert snapshot["futureRoot"] == 7
    assert snapshot["sources"][0]["futureField"] == "kept"
    assert snapshot["selections"]["elevation"]["source_ids"] == ["old"]
    assert "source_id" not in snapshot["selections"]["elevation"]


def test_managed_import_survives_restart_and_drives_real_elevation(tmp_path: Path) -> None:
    source = tmp_path / "mi_dem.tif"
    _write_tiff(source, np.full((2, 2), 10, dtype=np.int16))
    activated: list[bool] = []
    service, repository, catalog, installations = _service(
        tmp_path, callback=lambda: activated.append(True)
    )
    session = service.create(ownership="managed", name="El meu DEM", file_count=1)
    _upload(service, session.import_id, source, "bundle/mi_dem.tif")
    inspection = service.inspect(session.import_id, {"fileOrdinal": 0})
    assert inspection["sourceDtype"] == "int16"
    assert inspection["metadataSuggestions"]["requiresUnitConfirmation"] is True
    committed = service.commit(session.import_id, {
        "name": "El meu DEM",
        "bandIndex": 1,
        "verticalUnit": "international_foot",
        "unitConfirmed": True,
    })
    assert committed["active"] is True and activated == [True]
    assert catalog.get_descriptor(committed["resourceId"]) is not None
    assert installations.snapshot()[f'{committed["resourceId"]}::local']["status"] == "READY"

    restarted = DataSourceRepository(repository.path)
    assert restarted.active_elevation_source_id() == committed["sourceId"]
    sources = elevation_sources_from_repository(restarted)
    adapter = RasterioElevationAdapter(sources=sources)
    sample = adapter.elevation(GeoLocation(latitude_deg=1.5, longitude_deg=0.5))
    assert sample.available
    assert sample.elevation_m == pytest.approx(3.048, abs=1e-5)
    assert sample.source_id == committed["sourceId"]


def test_managed_mi_dem_asc_bundle_publishes_real_mesh_source_after_restart(tmp_path: Path) -> None:
    source_dir = tmp_path / "asc-source"
    source_dir.mkdir()
    asc = source_dir / "mi_dem.asc"
    values = np.asarray([[30, 30], [30, 30]], dtype=np.float32)
    with rasterio.open(
        asc,
        "w",
        driver="AAIGrid",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=Affine(1, 0, 0, 0, -1, 2),
        nodata=-9999,
    ) as dataset:
        dataset.write(values, 1)
    bundle_files = sorted(path for path in source_dir.iterdir() if path.is_file())
    asc_ordinal = bundle_files.index(asc)
    service, repository, _, _ = _service(tmp_path)
    session = service.create(
        ownership="managed",
        name="mi_dem.asc",
        file_count=len(bundle_files),
    )
    for ordinal, path in enumerate(bundle_files):
        _upload_at(service, session.import_id, ordinal, path, f"mi_dem/{path.name}")
    service.inspect(session.import_id, {"fileOrdinal": asc_ordinal})
    committed = service.commit(session.import_id, {
        "name": "mi_dem.asc",
        "bandIndex": 1,
        "verticalUnit": "metre",
        "unitConfirmed": True,
    })
    restarted = DataSourceRepository(repository.path)
    adapter = RasterioElevationAdapter(sources=elevation_sources_from_repository(restarted))
    sample = adapter.elevation(GeoLocation(latitude_deg=1.5, longitude_deg=0.5))
    grid = adapter.terrain_grid(TerrainTileRequest(
        tile_id=TerrainTileId("mi-dem-e2e"),
        center_latitude_deg=1.5,
        center_longitude_deg=0.5,
        radius_m=1,
        target_resolution_m=1,
    ))
    assert sample.elevation_m == pytest.approx(30)
    assert sample.source_id == committed["sourceId"]
    assert grid.valid_mask.any()
    assert np.allclose(grid.values_m[grid.valid_mask], 30)


def test_primary_wins_and_nodata_falls_back_after_scale_and_units(tmp_path: Path) -> None:
    primary = tmp_path / "primary.tif"
    fallback = tmp_path / "fallback.tif"
    _write_tiff(primary, np.asarray([[10, -9999], [10, 10]], dtype=np.int16), scale=2, offset=1)
    _write_tiff(fallback, np.full((2, 2), 100, dtype=np.int16))
    adapter = RasterioElevationAdapter(sources=(
        ElevationRasterSource(
            "primary",
            RasterDatasetSelection(str(primary), band_index=1),
            VerticalUnit.INTERNATIONAL_FOOT,
            True,
        ),
        ElevationRasterSource(
            "fallback",
            RasterDatasetSelection(str(fallback), band_index=1),
            VerticalUnit.METRE,
            True,
        ),
    ))
    primary_sample = adapter.elevation(GeoLocation(latitude_deg=1.5, longitude_deg=0.5))
    fallback_sample = adapter.elevation(GeoLocation(latitude_deg=1.5, longitude_deg=1.5))
    assert primary_sample.elevation_m == pytest.approx(21 * 0.3048, abs=1e-5)
    assert primary_sample.source_id == "primary"
    assert fallback_sample.elevation_m == pytest.approx(100, abs=1e-5)
    assert fallback_sample.source_id == "fallback"


def test_unit_confirmation_traversal_cancel_and_external_ownership(tmp_path: Path) -> None:
    source = tmp_path / "external.tif"
    _write_tiff(source, np.ones((2, 2), dtype=np.float32))
    service, repository, _, _ = _service(tmp_path)
    managed = service.create(ownership="managed")
    with pytest.raises(RasterImportError, match="safe relative"):
        service.upload_destination(managed.import_id, 0, "../escape.tif")
    service.cancel(managed.import_id)
    assert not managed.staging_dir.exists()

    external = service.create(
        ownership="external",
        name="Extern",
        external_path=str(source.resolve()),
    )
    service.inspect(external.import_id, {})
    with pytest.raises(RasterImportError, match="unit"):
        service.commit(external.import_id, {
            "name": "Extern",
            "bandIndex": 1,
            "verticalUnit": "metre",
            "unitConfirmed": False,
        })
    committed = service.commit(external.import_id, {
        "name": "Extern",
        "bandIndex": 1,
        "verticalUnit": "metre",
        "unitConfirmed": True,
    })
    service.remove_resource(committed["sourceId"])
    assert source.exists()
    assert repository.active_elevation_source_id() is None


def test_interrupted_managed_consolidation_is_recoverable(tmp_path: Path) -> None:
    source = tmp_path / "recover.tif"
    _write_tiff(source, np.full((2, 2), 7, dtype=np.int16))
    service, repository, catalog, installations = _service(tmp_path)
    session = service.create(ownership="managed", name="Recuperable")
    _upload(service, session.import_id, source, "recover.tif")
    service.inspect(session.import_id, {"fileOrdinal": 0})
    pending_source = "elevation.imported.recoveryfixture"
    installed = tmp_path / "library" / "data" / "earth" / "elevation" / "imports" / pending_source
    installed.parent.mkdir(parents=True, exist_ok=True)
    os.replace(session.staging_dir / "files", installed)
    manifest_path = session.staging_dir / "session.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "state": "committing",
        "pendingSourceId": pending_source,
        "pendingResourceId": f"earth.{pending_source}",
        "pendingInstallDir": str(installed),
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    restarted = RasterImportService(
        RasterioRasterReader(),
        TextRasterMaterializer(),
        repository,
        catalog,
        installations,
        data_root=tmp_path / "library",
    )
    assert restarted.recoverable_sessions()[0].state == "committing"
    committed = restarted.commit(session.import_id, {
        "name": "Recuperable",
        "bandIndex": 1,
        "verticalUnit": "metre",
        "unitConfirmed": True,
    })
    assert committed["sourceId"] == pending_source
    assert repository.active_elevation_source_id() == pending_source


def test_failed_activation_rolls_back_catalog_selection_and_managed_files(tmp_path: Path) -> None:
    source = tmp_path / "activation-failure.tif"
    _write_tiff(source, np.full((2, 2), 9, dtype=np.int16))

    def fail_activation() -> None:
        raise RuntimeError("activation failed")

    service, repository, catalog, _ = _service(tmp_path, callback=fail_activation)
    session = service.create(ownership="managed", name="Fallida")
    _upload(service, session.import_id, source, "failure.tif")
    service.inspect(session.import_id, {"fileOrdinal": 0})
    with pytest.raises(RuntimeError, match="activation failed"):
        service.commit(session.import_id, {
            "name": "Fallida",
            "bandIndex": 1,
            "verticalUnit": "metre",
            "unitConfirmed": True,
        })
    assert repository.active_elevation_source_id() is None
    assert not list((tmp_path / "library" / "data" / "earth" / "elevation" / "imports").iterdir())
    assert not [item for item in catalog.get_all_descriptors() if item.id.startswith("earth.elevation.imported.")]


def test_managed_vrt_cannot_escape_bundle(tmp_path: Path) -> None:
    outside = tmp_path / "outside.tif"
    _write_tiff(outside, np.ones((2, 2), dtype=np.float32))
    service, _, _, _ = _service(tmp_path)
    session = service.create(ownership="managed", file_count=1)
    vrt = tmp_path / "escape.vrt"
    vrt.write_text(
        '<VRTDataset rasterXSize="2" rasterYSize="2"><SRS>EPSG:4326</SRS>'
        '<GeoTransform>0,1,0,2,0,-1</GeoTransform><VRTRasterBand dataType="Float32" band="1">'
        f'<SimpleSource><SourceFilename>{outside}</SourceFilename><SourceBand>1</SourceBand>'
        '<SourceProperties RasterXSize="2" RasterYSize="2" DataType="Float32" BlockXSize="2" BlockYSize="2"/>'
        '<SrcRect xOff="0" yOff="0" xSize="2" ySize="2"/><DstRect xOff="0" yOff="0" xSize="2" ySize="2"/>'
        '</SimpleSource></VRTRasterBand></VRTDataset>',
        encoding="utf-8",
    )
    _upload(service, session.import_id, vrt, "escape.vrt")
    service.inspect(session.import_id, {"fileOrdinal": 0})
    with pytest.raises(RasterImportError, match="outside"):
        service.commit(session.import_id, {
            "name": "Escape",
            "bandIndex": 1,
            "verticalUnit": "metre",
            "unitConfirmed": True,
        })


def test_http_import_session_streams_binary_and_commits(tmp_path: Path) -> None:
    asyncio.run(_exercise_http_import_session(tmp_path))


def test_second_server_falls_back_instead_of_sharing_an_occupied_port(tmp_path: Path) -> None:
    asyncio.run(_exercise_occupied_port_fallback(tmp_path))


async def _exercise_occupied_port_fallback(tmp_path: Path) -> None:
    dist = tmp_path / "port-dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    first = TerraLabServer(dist, WebSocketBridge(), port=0)
    await first.start()
    second = TerraLabServer(dist, WebSocketBridge(), port=first.actual_port)
    try:
        await second.start()
        assert second.actual_port != first.actual_port
    finally:
        await second.stop()
        await first.stop()


async def _exercise_http_import_session(tmp_path: Path) -> None:
    source = tmp_path / "mi_dem.tif"
    _write_tiff(source, np.full((2, 2), 12, dtype=np.int16))
    service, _, _, _ = _service(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    server = TerraLabServer(
        dist,
        WebSocketBridge(),
        raster_imports=service,
        port=0,
    )
    await server.start()
    try:
        async with aiohttp.ClientSession() as client:
            create = await client.post(
                f"{server.url}/api/raster-imports",
                json={"ownership": "managed", "name": "mi_dem.asc", "fileCount": 1},
            )
            assert create.status == 201
            import_id = (await create.json())["importId"]
            malicious = await client.put(
                f"{server.url}/api/raster-imports/{import_id}/files/0",
                headers={"X-TerraLab-Relative-Path": "../escape.tif"},
                data=b"bad",
            )
            assert malicious.status == 400
            uploaded = await client.put(
                f"{server.url}/api/raster-imports/{import_id}/files/0",
                headers={"X-TerraLab-Relative-Path": "bundle/mi_dem.tif"},
                data=source.open("rb"),
            )
            assert uploaded.status == 200
            inspected = await client.post(
                f"{server.url}/api/raster-imports/{import_id}/inspect",
                json={"fileOrdinal": 0},
            )
            assert inspected.status == 200
            assert (await inspected.json())["sourceDtype"] == "int16"
            committed = await client.post(
                f"{server.url}/api/raster-imports/{import_id}/commit",
                json={
                    "name": "mi_dem.asc",
                    "bandIndex": 1,
                    "verticalUnit": "metre",
                    "unitConfirmed": True,
                },
            )
            assert committed.status == 200, await committed.text()
            assert (await committed.json())["active"] is True
    finally:
        await server.stop()


def test_reloadable_elevation_closes_retired_adapter_after_active_read() -> None:
    started = threading.Event()
    release = threading.Event()

    class FakeElevation:
        def __init__(self, source_id: str, blocking: bool = False) -> None:
            self.source_id = source_id
            self.blocking = blocking
            self.closed = False

        def metadata(self):
            return ElevationSourceMetadata(self.source_id, self.source_id, "EPSG:4326", 1, None, None, "fake")

        def elevation(self, location, cancellation_check=None):
            if self.blocking:
                started.set()
                release.wait(timeout=5)
            return ElevationSample(location, 1.0, self.source_id, ElevationStatus.REAL)

        def sample_points(self, request):
            raise NotImplementedError

        def terrain_grid(self, request):
            raise NotImplementedError

        def close(self):
            self.closed = True

    old = FakeElevation("old", blocking=True)
    replacement = FakeElevation("new")
    port = ReloadableElevationPort(old)
    result: list[ElevationSample] = []
    worker = threading.Thread(
        target=lambda: result.append(port.elevation(GeoLocation(1, 1))),
        daemon=True,
    )
    worker.start()
    assert started.wait(timeout=2)
    port.reload(lambda: replacement)
    assert old.closed is False
    assert port.elevation(GeoLocation(1, 1)).source_id == "new"
    release.set()
    worker.join(timeout=2)
    assert result[0].source_id == "old"
    assert old.closed is True
