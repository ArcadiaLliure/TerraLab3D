from __future__ import annotations

import hashlib
import asyncio
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest
import rasterio
import aiohttp
from affine import Affine

from terralab3d.application.raster_imports import RasterImportError, RasterImportService
from terralab3d.domain.raster.models import RasterDatasetSelection
from terralab3d.domain.surface.categorical import CategoricalEncoding
from terralab3d.domain.surface.land_cover import LandCoverTileRequest
from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    ObservationState,
    SampleValidity,
    SingleSurface,
    TlstValidationError,
)
from terralab3d.infrastructure.adapters.raster import (
    RasterioCategoricalRasterAdapter,
    RasterioRasterReader,
    TextRasterMaterializer,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    LandCoverSchemeRegistry,
    load_builtin_land_cover_registry,
)
from terralab3d.infrastructure.adapters.surface.adapter import ConfiguredSurfaceSampler
from terralab3d.infrastructure.adapters.surface.land_cover_port import RasterioLandCoverPort
from terralab3d.infrastructure.resources.classification_schemes import (
    UserClassificationSchemeRepository,
)
from terralab3d.infrastructure.resources.data_sources import DataSourceRepository
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)
from terralab3d.infrastructure.resources.layer_database import LayerDatabase
from terralab3d.infrastructure.server import TerraLabServer
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def _registry() -> LandCoverSchemeRegistry:
    builtins = load_builtin_land_cover_registry()
    return LandCoverSchemeRegistry(
        builtins.taxonomy,
        MappingProxyType(dict(builtins.schemes)),
        builtins.category_presentations_ca,
    )


def _write_raster(path: Path, values: np.ndarray, *, palette: bool = False) -> None:
    arrays = values[np.newaxis, ...] if values.ndim == 2 else values
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=arrays.shape[2],
        height=arrays.shape[1],
        count=arrays.shape[0],
        dtype=arrays.dtype,
        crs="EPSG:4326",
        transform=Affine(1, 0, 0, 0, -1, arrays.shape[1]),
    ) as dataset:
        dataset.write(arrays)
        if palette:
            dataset.write_colormap(1, {1: (10, 20, 30, 255), 2: (40, 50, 60, 255)})


def _upload(service: RasterImportService, import_id: str, source: Path) -> None:
    destination = service.upload_destination(import_id, 0, source.name)
    payload = source.read_bytes()
    destination.write_bytes(payload)
    service.finish_upload(
        import_id,
        0,
        source.name,
        len(payload),
        hashlib.sha256(payload).hexdigest(),
    )


def _service(tmp_path: Path):
    root = tmp_path / "library"
    registry = _registry()
    user_schemes = UserClassificationSchemeRepository(
        registry,
        root / "config" / "classification_schemes.json",
    )
    reader = RasterioRasterReader()
    data_sources = DataSourceRepository(root / "config" / "data_sources.json")
    catalog = LayerDatabase(tmp_path / "state" / "layers.json")
    installations = ResourceInstallationRepository(
        tmp_path / "state" / "local_installation_state.json"
    )
    activated: list[bool] = []
    service = RasterImportService(
        reader,
        TextRasterMaterializer(),
        data_sources,
        catalog,
        installations,
        data_root=root,
        categorical_raster=RasterioCategoricalRasterAdapter(reader),
        scheme_registry=registry,
        user_schemes=user_schemes,
        categorical_activation_callback=lambda: activated.append(True),
    )
    return service, data_sources, registry, user_schemes, activated


def test_builtin_registry_has_complete_lcm10_and_corine_contracts() -> None:
    registry = _registry()
    lcm = registry.get("copernicus_lcm10", "2020-v100")
    assert {item.source_code for item in lcm.classes} == {
        10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 254, 255,
    }
    assert isinstance(lcm.resolve_observation(40).translation, SingleSurface)
    assert lcm.resolve_observation(40).translation.category_key == (
        "agriculture.cropland.arable.annual_crop"
    )
    assert lcm.resolve_observation(254).classification_status is ClassificationStatus.UNCLASSIFIED
    assert lcm.resolve_observation(255).validity is SampleValidity.NODATA

    corine = registry.get("corine_land_cover", "2018-v2020_20u1")
    assert len(corine.classes) == 45
    assert corine.resolve_observation(221).translation.category_key == (
        "agriculture.cropland.permanent_crop.vineyard"
    )
    assert corine.resolve_observation(412).translation.category_key == "wetland.inland.peat_bog"
    assert corine.resolve_observation(523).translation.category_key == "water.marine.sea_ocean"


def test_hierarchical_coverage_distinguishes_direct_and_generic_mappings() -> None:
    taxonomy = _registry().taxonomy
    direct = taxonomy.hierarchy_coverage("tree_cover.broadleaf")
    generic = taxonomy.hierarchy_coverage("tree_cover.unspecified")
    assert direct.resolved_path == ("tree_cover", "tree_cover.broadleaf")
    assert direct.unresolved_children == ()
    assert generic.semantic_depth == 1
    assert set(generic.unresolved_children) == {
        "tree_cover.broadleaf", "tree_cover.needleleaf", "tree_cover.mixed",
    }


def test_exact_integer_palette_rgb_and_rgba_analysis_and_index_materialization(
    tmp_path: Path,
) -> None:
    reader = RasterioRasterReader()
    adapter = RasterioCategoricalRasterAdapter(reader)

    integer = tmp_path / "integer.tif"
    _write_raster(integer, np.asarray([[40, 70], [40, 80]], dtype=np.uint8))
    integer_analysis = adapter.analyse(
        RasterDatasetSelection(str(integer)),
        encoding=CategoricalEncoding.INTEGER,
        band_indices=(1,),
    )
    assert [(item.source_value, item.pixel_count) for item in integer_analysis.values] == [
        (40, 2), (70, 1), (80, 1),
    ]

    palette = tmp_path / "palette.tif"
    _write_raster(palette, np.asarray([[1, 2]], dtype=np.uint8), palette=True)
    palette_analysis = adapter.analyse(
        RasterDatasetSelection(str(palette)),
        encoding=CategoricalEncoding.PALETTE,
        band_indices=(1,),
    )
    assert palette_analysis.values[0].color_rgba == (10, 20, 30, 255)

    rgb = tmp_path / "rgb.tif"
    rgb_values = np.asarray([
        [[10, 40], [10, 40]],
        [[20, 50], [20, 50]],
        [[30, 60], [30, 60]],
        [[255, 128], [255, 128]],
    ], dtype=np.uint8)
    _write_raster(rgb, rgb_values)
    rgb_analysis = adapter.analyse(
        RasterDatasetSelection(str(rgb)),
        encoding=CategoricalEncoding.RGB,
        band_indices=(1, 2, 3),
    )
    assert [item.source_value for item in rgb_analysis.values] == ["#0A141E", "#28323C"]
    rgba_analysis = adapter.analyse(
        RasterDatasetSelection(str(rgb)),
        encoding=CategoricalEncoding.RGBA,
        band_indices=(1, 2, 3, 4),
    )
    assert [item.source_value for item in rgba_analysis.values] == ["#0A141EFF", "#28323C80"]

    indexed = adapter.materialize_indexed(
        RasterDatasetSelection(str(rgb)),
        tmp_path / "indexed.tif",
        encoding=CategoricalEncoding.RGBA,
        band_indices=(1, 2, 3, 4),
        code_by_source_value={"#0A141EFF": 7, "#28323C80": 9},
    )
    with rasterio.open(indexed) as dataset:
        assert dataset.read(1).tolist() == [[7, 9], [7, 9]]
        assert dataset.dtypes == ("uint16",)
        assert dataset.tags()["TERRALAB_ENCODING"] == "rgba"


def test_standard_import_requires_confirmation_and_survives_restart(tmp_path: Path) -> None:
    source = tmp_path / "worldcover.tif"
    _write_raster(source, np.asarray([[40, 70], [80, 90]], dtype=np.uint8))
    service, data_sources, registry, _, activated = _service(tmp_path)
    session = service.create(
        ownership="managed", name="WorldCover local", file_count=1,
        semantic_kind="categorical",
    )
    _upload(service, session.import_id, source)
    inspection = service.inspect(session.import_id, {"fileOrdinal": 0})
    analysis = inspection["categoricalAnalysis"]
    candidate = next(
        item for item in analysis["schemeCandidates"]
        if item["schemeKey"] == "esa_worldcover" and item["schemeVersion"] == "2021-v200"
    )
    with pytest.raises(RasterImportError, match="reviewed and confirmed"):
        service.commit(session.import_id, {
            "schemeKey": candidate["schemeKey"],
            "schemeVersion": candidate["schemeVersion"],
            "mappingRevision": candidate["mappingRevision"],
        })
    committed = service.commit(session.import_id, {
        "name": "WorldCover local",
        "mappingConfirmed": True,
        "schemeKey": candidate["schemeKey"],
        "schemeVersion": candidate["schemeVersion"],
        "mappingRevision": candidate["mappingRevision"],
    })
    assert committed["active"] is True and activated == [True]
    restarted = DataSourceRepository(data_sources.path)
    assert restarted.active_land_cover_source_id() == committed["sourceId"]
    record = restarted.land_cover_records()[0]
    assert record["source_dtype"] == "uint8"
    assert record["payload_dtype"] == "uint16"
    assert Path(record["path"]).is_file()
    assert registry.get(
        record["scheme_key"], record["scheme_version"], record["mapping_revision"],
    ).resolve_observation(70).translation.category_key == "snow_ice.unspecified"
    sampler = ConfiguredSurfaceSampler(
        config_paths=(data_sources.path,), scheme_registry=registry,
    )
    port = RasterioLandCoverPort(sampler, scheme_registry=registry)
    tile = port.read_tile(LandCoverTileRequest(
        min_x=0, min_y=0, max_x=2, max_y=2, resolution=1,
        crs="EPSG:4326", source_mode="manual", source_id=committed["sourceId"],
    ))
    assert tile is not None and tile.valid_pixels == 4
    legend = port.legend(
        record["scheme_key"], record["scheme_version"], record["mapping_revision"],
    )
    assert legend.mapping_revision == committed["mappingRevision"]
    assert next(item for item in legend.entries if item.source_code == 40).source_value == 40
    port.close()


def test_custom_scheme_accepts_any_tlst_node_and_is_reusable(tmp_path: Path) -> None:
    source = tmp_path / "custom.tif"
    _write_raster(source, np.asarray([[1, 2]], dtype=np.uint8))
    service, _, registry, repository, _ = _service(tmp_path)
    session = service.create(
        ownership="managed", name="Esquema local", file_count=1,
        semantic_kind="categorical",
    )
    _upload(service, session.import_id, source)
    inspection = service.inspect(session.import_id, {"fileOrdinal": 0})
    assert inspection["categoricalAnalysis"]["values"]
    # The public confirmation path deliberately accepts a structural (non-leaf) node.
    committed = service.commit(session.import_id, {
        "name": "Esquema local",
        "mappingConfirmed": True,
        "customScheme": {
            "displayName": "Classes de camp",
            "schemeVersion": "2026.1",
            "classes": [
                {"sourceValue": 1, "sourceLabel": "Vegetació", "categoryKey": "low_vegetation"},
                {"sourceValue": 2, "sourceLabel": "Dubtós", "classificationStatus": "unknown"},
            ],
        },
    })
    scheme = registry.get(
        committed["schemeKey"], committed["schemeVersion"], committed["mappingRevision"],
    )
    assert scheme.resolve_observation(1).translation == SingleSurface("low_vegetation")
    assert scheme.resolve_observation(2).translation == ObservationState(ClassificationStatus.UNKNOWN)

    restarted_registry = _registry()
    UserClassificationSchemeRepository(restarted_registry, repository.path)
    assert restarted_registry.get(
        committed["schemeKey"], committed["schemeVersion"], committed["mappingRevision"],
    ) == scheme

    altered = scheme.__class__(
        scheme_key=scheme.scheme_key,
        scheme_version=scheme.scheme_version,
        display_name="Nom alterat",
        taxonomy_key=scheme.taxonomy_key,
        taxonomy_version=scheme.taxonomy_version,
        classes=scheme.classes,
        mapping_revision=scheme.mapping_revision,
        source_semantics=scheme.source_semantics,
    )
    with pytest.raises(TlstValidationError, match="cannot be changed silently"):
        repository.upsert(altered)


def test_rgb_import_preserves_exact_source_values_behind_compact_codes(tmp_path: Path) -> None:
    source = tmp_path / "colors.tif"
    values = np.asarray([
        [[1, 4]],
        [[2, 5]],
        [[3, 6]],
    ], dtype=np.uint8)
    _write_raster(source, values)
    service, data_sources, registry, _, _ = _service(tmp_path)
    session = service.create(
        ownership="managed", name="Colors", file_count=1,
        semantic_kind="categorical",
    )
    _upload(service, session.import_id, source)
    inspection = service.inspect(session.import_id, {"fileOrdinal": 0})
    assert inspection["categoricalAnalysis"]["encoding"] == "rgb"
    assert [
        item["sourceValue"] for item in inspection["categoricalAnalysis"]["values"]
    ] == ["#010203", "#040506"]
    committed = service.commit(session.import_id, {
        "mappingConfirmed": True,
        "customScheme": {
            "displayName": "Colors exactes",
            "schemeVersion": "1",
            "classes": [
                {"sourceValue": "#010203", "sourceLabel": "Vegetació", "categoryKey": "low_vegetation"},
                {"sourceValue": "#040506", "sourceLabel": "Aigua", "categoryKey": "water"},
            ],
        },
    })
    record = data_sources.land_cover_records()[0]
    assert record["source_dtype"] == "uint8,uint8,uint8"
    assert record["categorical_encoding"] == "rgb"
    scheme = registry.get(
        committed["schemeKey"], committed["schemeVersion"], committed["mappingRevision"],
    )
    assert {item.source_value for item in scheme.classes} == {"#010203", "#040506"}
    with rasterio.open(record["path"]) as dataset:
        assert set(dataset.read(1).ravel().tolist()) == {
            item.source_code for item in scheme.classes
        }


def test_http_catalog_and_categorical_session_contract(tmp_path: Path) -> None:
    asyncio.run(_exercise_http_catalog_and_session(tmp_path))


async def _exercise_http_catalog_and_session(tmp_path: Path) -> None:
    service, _, _, _, _ = _service(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (dist / "bundle.js").write_text("console.log('current')", encoding="utf-8")
    server = TerraLabServer(dist, WebSocketBridge(), raster_imports=service, port=0)
    await server.start()
    try:
        async with aiohttp.ClientSession() as client:
            index_response = await client.get(f"{server.url}/")
            assert index_response.status == 200
            assert index_response.headers["Cache-Control"] == "no-store, max-age=0"
            bundle_response = await client.get(f"{server.url}/bundle.js")
            assert bundle_response.status == 200
            assert bundle_response.headers["Cache-Control"] == "no-store, max-age=0"
            catalog_response = await client.get(
                f"{server.url}/api/classification-schemes"
            )
            assert catalog_response.status == 200
            catalog = await catalog_response.json()
            assert catalog["taxonomyKey"] == "TLST"
            assert {item["schemeKey"] for item in catalog["schemes"]} >= {
                "copernicus_lcm10", "corine_land_cover",
            }
            created = await client.post(
                f"{server.url}/api/raster-imports",
                json={
                    "semanticKind": "categorical",
                    "ownership": "external",
                    "externalPath": str(tmp_path / "missing.tif"),
                    "name": "Sessió categòrica",
                    "fileCount": 1,
                },
            )
            assert created.status == 201
            payload = await created.json()
            assert payload["semanticKind"] == "categorical"
            cancelled = await client.delete(
                f"{server.url}/api/raster-imports/{payload['importId']}"
            )
            assert cancelled.status == 200
    finally:
        await server.stop()
