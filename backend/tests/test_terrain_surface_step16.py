from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from terralab3d.infrastructure.adapters.surface import ConfiguredSurfaceSampler


def test_surface_rgb_is_selected_from_config_and_sampled_in_its_native_crs(tmp_path: Path) -> None:
    raster = tmp_path / "surface.tif"
    with rasterio.open(
        raster,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
    ) as dataset:
        dataset.write(np.asarray([
            [[255, 10], [10, 10]],
            [[128, 10], [10, 10]],
            [[0, 10], [10, 10]],
        ], dtype=np.uint8))
    config = tmp_path / "data_sources.json"
    config.write_text(json.dumps({
        "sources": [{
            "id": "surface-fixture",
            "display_name": "Fixture RGB",
            "layer_type": "surface_rgb",
            "path": str(raster),
            "priority": 1,
            "enabled": True,
            "coverage": [0, 0, 2, 2],
        }],
        "selections": {"surface": {"mode": "automatic", "source_id": None}},
    }), encoding="utf-8")

    samples = ConfiguredSurfaceSampler((config,)).sample(
        np.asarray([1.5, 5.0]), np.asarray([0.5, 5.0]),
    )

    assert samples.valid.tolist() == [True, False]
    # Values are linearized exactly once before they become a Three.js colour attribute.
    assert samples.rgba_linear[0].tolist() == [255, 55, 0, 255]
    assert samples.class_ids.tolist() == [0, 0]
    assert samples.source_ids.tolist() == [1, 0]
    assert samples.source_label == "Fixture RGB"


def test_palette_surface_keeps_the_discrete_category_id_for_picking(tmp_path: Path) -> None:
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
    ) as dataset:
        dataset.write(np.asarray([[[62, 0], [0, 0]]], dtype=np.uint8))
        dataset.write_colormap(1, {62: (210, 0, 0, 255), 0: (0, 0, 0, 0)})
    config = tmp_path / "data_sources.json"
    config.write_text(json.dumps({
        "sources": [{
            "id": "classes-fixture",
            "display_name": "Fixture categories",
            "layer_type": "land_cover_categorical",
            "path": str(raster),
            "priority": 1,
            "enabled": True,
            "coverage": [0, 0, 2, 2],
        }],
        "selections": {"surface": {"mode": "manual", "source_id": "classes-fixture"}},
    }), encoding="utf-8")

    samples = ConfiguredSurfaceSampler((config,)).sample(
        np.asarray([1.5]), np.asarray([0.5]),
    )

    assert samples.valid.tolist() == [True]
    assert samples.class_ids.tolist() == [62]
    assert samples.source_ids.tolist() == [1]
    assert samples.rgba_linear[0, 3] == 255
