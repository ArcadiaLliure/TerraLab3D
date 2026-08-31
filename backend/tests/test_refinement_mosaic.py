from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import shape

from terralab3d.domain.refinement.grid import (
    ResamplingPolicy,
    TargetGridSpec,
    TemporalPolicy,
)
from terralab3d.domain.refinement.licensing import LicenseMetadata
from terralab3d.domain.refinement.mosaic import RasterRefinementSource, SourcePriority
from terralab3d.infrastructure.adapters.refinement.mosaic import (
    RasterRefinementMosaicProcessor,
    sha256_file,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


def _license(product: str) -> LicenseMetadata:
    return LicenseMetadata(
        license_id="copernicus-clms",
        official_url="https://land.copernicus.eu/en/faq/data-use-terms-and-conditions",
        attribution_text="Contains modified Copernicus Service information (2026)",
        citation="Copernicus Land Monitoring Service",
        provider="Copernicus CLMS",
        product=product,
        version="fixture-1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://land.copernicus.eu/",
        asset_fingerprints=("fixture",),
        commercial_use=True,
    )


def _grid() -> TargetGridSpec:
    return TargetGridSpec(
        crs="EPSG:25831",
        resolution_x=10,
        resolution_y=10,
        origin_x=0,
        origin_y=0,
        min_x=0,
        min_y=0,
        max_x=320,
        max_y=160,
        width=32,
        height=16,
        dtype="uint16",
        nodata=0,
        resampling=ResamplingPolicy.NEAREST,
        tlst_version="1.0",
        temporal_policy=TemporalPolicy("latest_in_window", 365),
    )


def _write_raster(
    path: Path,
    values: np.ndarray,
    *,
    west: float,
    north: float = 160,
    resolution: float = 10,
    nodata: int = 0,
) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[1],
        height=values.shape[0],
        count=1,
        dtype=values.dtype,
        crs="EPSG:25831",
        transform=from_origin(west, north, resolution, resolution),
        nodata=nodata,
    ) as dataset:
        dataset.write(values, 1)


def _source(
    source_id: str,
    path: Path,
    translation: dict[int, str],
    priority: SourcePriority,
) -> RasterRefinementSource:
    return RasterRefinementSource(
        source_id=source_id,
        product=source_id,
        version="fixture-1",
        path=path,
        band=1,
        translations=translation,
        priority=priority,
        license=_license(source_id),
        asset_checksum=sha256_file(path),
    )


def test_mosaic_generates_four_outputs_translated_to_tlst_on_canonical_grid(tmp_path) -> None:
    fallback_path = tmp_path / "fallback.tif"
    thematic_path = tmp_path / "thematic-misaligned.tif"
    _write_raster(fallback_path, np.ones((16, 32), dtype=np.uint8), west=0)
    _write_raster(thematic_path, np.full((16, 16), 2, dtype=np.uint8), west=5)
    original_hashes = (sha256_file(fallback_path), sha256_file(thematic_path))
    processor = RasterRefinementMosaicProcessor(load_builtin_land_cover_registry().taxonomy)

    result = processor.update(
        tmp_path / "derived",
        _grid(),
        (
            _source(
                "general",
                fallback_path,
                {1: "agriculture"},
                SourcePriority.GENERAL_LAND_COVER,
            ),
            _source(
                "crop-types",
                thematic_path,
                {2: "agriculture.cropland.vineyard"},
                SourcePriority.THEMATIC_REFINEMENT,
            ),
        ),
    )

    assert all(
        path.exists()
        for path in (
            result.mosaic_path,
            result.source_path,
            result.quality_path,
            result.conflict_path,
            result.manifest_path,
        )
    )
    assert (sha256_file(fallback_path), sha256_file(thematic_path)) == original_hashes
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    agriculture = manifest["taxonomy"]["categoryCodes"]["agriculture"]
    vineyard = manifest["taxonomy"]["categoryCodes"][
        "agriculture.cropland.vineyard"
    ]
    with rasterio.open(result.mosaic_path) as dataset:
        values = dataset.read(1)
        assert dataset.transform == from_origin(0, 160, 10, 10)
        assert dataset.profile["tiled"]
        assert dataset.profile["compress"] == "deflate"
    assert np.all(values[:, :16] == vineyard)
    assert np.all(values[:, 17:] == agriculture)
    assert result.conflict_pixels > 0
    assert manifest["sources"][0]["resampling"] == "nearest"
    assert manifest["targetGrid"]["tlstVersion"] == "1.0"


def test_verified_coverage_uses_real_valid_pixels_instead_of_raster_bbox(tmp_path) -> None:
    source_path = tmp_path / "nodata.tif"
    values = np.ones((16, 32), dtype=np.uint8)
    values[:, 8:24] = 0
    _write_raster(source_path, values, west=0, nodata=0)
    processor = RasterRefinementMosaicProcessor(load_builtin_land_cover_registry().taxonomy)

    result = processor.update(
        tmp_path / "derived",
        _grid(),
        (
            _source(
                "partial",
                source_path,
                {1: "tree_cover.unspecified"},
                SourcePriority.EUROPEAN_HIGH_RESOLUTION,
            ),
        ),
    )

    verified_area = shape(dict(result.verified_geometry.geojson)).area
    assert verified_area == pytest.approx(256 * 100)
    assert verified_area < 320 * 160


def test_semantically_specific_lower_resolution_source_beats_general_high_resolution(tmp_path) -> None:
    general_path = tmp_path / "general-10m.tif"
    thematic_path = tmp_path / "thematic-20m.tif"
    _write_raster(general_path, np.ones((16, 32), dtype=np.uint8), west=0, resolution=10)
    _write_raster(thematic_path, np.full((8, 16), 2, dtype=np.uint8), west=0, resolution=20)
    processor = RasterRefinementMosaicProcessor(load_builtin_land_cover_registry().taxonomy)

    result = processor.update(
        tmp_path / "derived",
        _grid(),
        (
            _source(
                "general-10m",
                general_path,
                {1: "tree_cover.unspecified"},
                SourcePriority.GENERAL_LAND_COVER,
            ),
            _source(
                "thematic-20m",
                thematic_path,
                {2: "tree_cover.broadleaf"},
                SourcePriority.THEMATIC_REFINEMENT,
            ),
        ),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    broadleaf = manifest["taxonomy"]["categoryCodes"]["tree_cover.broadleaf"]
    with rasterio.open(result.mosaic_path) as dataset:
        assert np.all(dataset.read(1) == broadleaf)


def test_icgc_local_official_pixel_wins_over_clms_global_fallback(tmp_path) -> None:
    clms_path = tmp_path / "clms-global.tif"
    icgc_path = tmp_path / "icgc-local.tif"
    _write_raster(clms_path, np.full((16, 32), 10, dtype=np.uint8), west=0)
    _write_raster(icgc_path, np.full((16, 32), 8, dtype=np.uint8), west=0)

    result = RasterRefinementMosaicProcessor(
        load_builtin_land_cover_registry().taxonomy
    ).update(
        tmp_path / "derived-cross-provider",
        _grid(),
        (
            _source(
                "clms-global-dynamic",
                clms_path,
                {10: "tree_cover.unspecified"},
                SourcePriority.GENERAL_LAND_COVER,
            ),
            _source(
                "icgc-mcsc-2024",
                icgc_path,
                {8: "tree_cover.broadleaf"},
                SourcePriority.LOCAL_OFFICIAL,
            ),
        ),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    broadleaf = manifest["taxonomy"]["categoryCodes"]["tree_cover.broadleaf"]
    with rasterio.open(result.mosaic_path) as dataset:
        assert np.all(dataset.read(1) == broadleaf)
    assert result.conflict_pixels == _grid().width * _grid().height
    priorities = {item["sourceId"]: item["priority"] for item in manifest["sources"]}
    assert priorities["icgc-mcsc-2024"] == "LOCAL_OFFICIAL"
    assert priorities["clms-global-dynamic"] == "GENERAL_LAND_COVER"


def test_incremental_update_reprocesses_only_intersecting_block(tmp_path) -> None:
    base_path = tmp_path / "base.tif"
    right_path = tmp_path / "right.tif"
    _write_raster(base_path, np.ones((16, 32), dtype=np.uint8), west=0)
    _write_raster(right_path, np.full((16, 16), 3, dtype=np.uint8), west=160)
    processor = RasterRefinementMosaicProcessor(load_builtin_land_cover_registry().taxonomy)
    derived = tmp_path / "derived"
    processor.update(
        derived,
        _grid(),
        (
            _source(
                "base",
                base_path,
                {1: "agriculture"},
                SourcePriority.GENERAL_LAND_COVER,
            ),
        ),
    )
    with rasterio.open(derived / "refinement_mosaic.tif") as dataset:
        left_before = dataset.read(1, window=rasterio.windows.Window(0, 0, 16, 16))

    result = processor.update(
        derived,
        _grid(),
        (
            _source(
                "right-specific",
                right_path,
                {3: "tree_cover.broadleaf"},
                SourcePriority.LOCAL_OFFICIAL,
            ),
        ),
    )

    assert result.updated_windows == ((16, 0, 16, 16),)
    with rasterio.open(result.mosaic_path) as dataset:
        left_after = dataset.read(1, window=rasterio.windows.Window(0, 0, 16, 16))
    assert np.array_equal(left_after, left_before)


def test_continuous_qualifier_is_written_outside_categorical_tlst_band(tmp_path) -> None:
    density_path = tmp_path / "tree-density.tif"
    density = np.full((16, 32), 64, dtype=np.uint8)
    density[:, 0] = 254
    _write_raster(density_path, density, west=0, nodata=255)
    source = _source(
        "tree-cover-density",
        density_path,
        {value: "tree_cover.unspecified" for value in range(1, 101)},
        SourcePriority.EUROPEAN_HIGH_RESOLUTION,
    )
    source = RasterRefinementSource(
        source_id=source.source_id,
        product=source.product,
        version=source.version,
        path=source.path,
        band=source.band,
        translations=source.translations,
        priority=source.priority,
        license=source.license,
        asset_checksum=source.asset_checksum,
        qualifier_key="canopy_cover",
        invalid_values=(0, 254, 255),
    )

    result = RasterRefinementMosaicProcessor(
        load_builtin_land_cover_registry().taxonomy
    ).update(tmp_path / "derived", _grid(), (source,))

    qualifier_path = result.qualifier_paths["canopy_cover"]
    with rasterio.open(qualifier_path) as dataset:
        values = dataset.read(1)
        assert values[0, 1] == pytest.approx(64)
        assert values[0, 0] == dataset.nodata
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["outputs"]["qualifiers"]["canopy_cover"] == qualifier_path.name
