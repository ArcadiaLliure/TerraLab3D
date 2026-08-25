from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from terralab3d.infrastructure.adapters.surface import ConfiguredSurfaceSampler


def _write_rgb(path: Path) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
    ) as dataset:
        dataset.write(
            np.asarray(
                [
                    [[255, 10], [10, 10]],
                    [[128, 10], [10, 10]],
                    [[0, 10], [10, 10]],
                ],
                dtype=np.uint8,
            )
        )


def _write_categories(
    path: Path,
    *,
    nodata: int | None = None,
    colormap: bool = True,
) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="uint8",
        crs="EPSG:3035",
        transform=from_origin(3_548_930, 2_059_452, 10, 10),
        nodata=nodata,
    ) as dataset:
        dataset.write(
            np.asarray(
                [[[104, 255 if nodata == 255 else 0], [62, 83]]],
                dtype=np.uint8,
            )
        )
        if colormap:
            dataset.write_colormap(
                1,
                {
                    104: (141, 139, 0, 255),
                    62: (210, 0, 0, 255),
                    83: (35, 152, 0, 255),
                    0: (0, 0, 0, 0),
                    255: (0, 0, 0, 0),
                },
            )


def test_surface_rgb_is_selected_from_legacy_config_and_sampled_in_native_crs(
    tmp_path: Path,
) -> None:
    raster = tmp_path / "surface.tif"
    _write_rgb(raster)
    config = tmp_path / "data_sources.json"
    config.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "surface-fixture",
                        "display_name": "Fixture RGB",
                        "layer_type": "surface_rgb",
                        "path": str(raster),
                        "priority": 1,
                        "enabled": True,
                        "coverage": [0, 0, 2, 2],
                    }
                ],
                "selections": {
                    "surface": {
                        "mode": "automatic",
                        "source_id": None,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    samples = ConfiguredSurfaceSampler((config,)).sample(
        np.asarray([1.5, 5.0]),
        np.asarray([0.5, 5.0]),
    )

    assert samples.valid.tolist() == [True, False]
    assert samples.rgba_linear[0].tolist() == [255, 55, 0, 255]
    assert samples.class_ids.tolist() == [0, 0]
    assert samples.source_ids.tolist() == [1, 0]
    assert samples.source_label == "Fixture RGB"


def test_land_cover_selection_resolves_directory_metadata_to_real_geotiff(
    tmp_path: Path,
) -> None:
    raster_dir = tmp_path / "land_cover"
    raster_dir.mkdir()
    raster = raster_dir / "categorical.tif"
    _write_categories(raster, nodata=255, colormap=False)
    cache = tmp_path / "materialized.npy"
    np.save(cache, np.zeros((2, 2), dtype=np.uint8))

    config = tmp_path / "data_sources.json"
    config.write_text(
        json.dumps(
            {
                "version": 3,
                "sources": [
                    {
                        "id": "other-land-cover",
                        "display_name": "Other",
                        "layer_type": "land_cover_categorical",
                        "path": str(raster_dir),
                        "format": "raster_mosaic",
                        "crs": "EPSG:3035",
                        "resolution_m": 20.0,
                        "priority": 999,
                        "enabled": True,
                        "metadata": {
                            "legend_id": "other",
                            "rasters": [{"paths": [str(raster)]}],
                        },
                    },
                    {
                        "id": "selected-land-cover",
                        "display_name": "Selected categories",
                        "layer_type": "land_cover_categorical",
                        "path": str(raster_dir),
                        "format": "raster_mosaic",
                        "crs": "EPSG:3035",
                        "resolution_m": 9.9994162612822,
                        "coverage": [-33.5, 31.8, 62.1, 72.3],
                        "priority": 0,
                        "enabled": True,
                        "metadata": {
                            "legend_id": "s2glc_europe_2017",
                            "rasters": [
                                {
                                    "driver": "GTiff",
                                    "band_count": 1,
                                    "paths": [
                                        str(raster),
                                        str(cache),
                                    ],
                                }
                            ],
                        },
                    },
                ],
                "selections": {
                    "land_cover": {
                        "mode": "manual",
                        "source_id": "selected-land-cover",
                    }
                },
                "surface_mode": "land_cover",
            }
        ),
        encoding="utf-8",
    )

    source = ConfiguredSurfaceSampler((config,)).resolve_land_cover_source()

    assert source is not None
    assert source.source_id == "selected-land-cover"
    assert source.config_path == config.resolve()
    assert source.raster_paths == (raster.resolve(),)
    assert source.crs == "EPSG:3035"
    assert source.resolution_m == 9.9994162612822
    assert source.nodata == 255
    assert source.scheme_key == "s2glc_europe"
    assert source.scheme_version == "2017-v1.2"
    assert source.source_dtype == "uint8"


def test_manual_land_cover_does_not_fall_back_to_another_source(
    tmp_path: Path,
) -> None:
    raster = tmp_path / "classes.tif"
    _write_categories(raster, nodata=255, colormap=False)
    config = tmp_path / "data_sources.json"
    config.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "available",
                        "display_name": "Available",
                        "layer_type": "land_cover_categorical",
                        "path": str(raster),
                        "enabled": True,
                    }
                ],
                "selections": {
                    "land_cover": {
                        "mode": "manual",
                        "source_id": "missing",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    assert ConfiguredSurfaceSampler((config,)).resolve_land_cover_source() is None


def test_categorical_sampling_keeps_class_id_without_embedded_colormap(
    tmp_path: Path,
) -> None:
    raster = tmp_path / "classes.tif"
    with rasterio.open(
        raster,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
        nodata=255,
    ) as dataset:
        dataset.write(np.asarray([[[104, 255], [62, 83]]], dtype=np.uint8))

    config = tmp_path / "data_sources.json"
    config.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "classes-fixture",
                        "display_name": "Fixture categories",
                        "layer_type": "land_cover_categorical",
                        "path": str(raster),
                        "priority": 1,
                        "enabled": True,
                        "coverage": [0, 0, 2, 2],
                    }
                ],
                "selections": {
                    "land_cover": {
                        "mode": "manual",
                        "source_id": "classes-fixture",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    samples = ConfiguredSurfaceSampler((config,)).sample(
        np.asarray([1.5]),
        np.asarray([0.5]),
    )

    assert samples.valid.tolist() == [True]
    assert samples.class_ids.tolist() == [104]
    assert samples.source_ids.tolist() == [1]
    assert samples.rgba_linear[0, 3] == 255
