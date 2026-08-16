"""
Step 17 Comprehensive Unit Tests: Land Cover & Categorical Surface Representation.
"""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from terralab3d.application.land_cover_coordinator import (
    LandCoverCoordinator,
    pack_surface_resource,
)
from terralab3d.domain.identifiers import ResourceId
from terralab3d.domain.surface.calculations import (
    categorical_modal_downsample,
    decode_rgb_to_class,
    build_palette_index_map,
    srgb_to_linear_float,
    linear_u8_to_srgb_u8,
)
from terralab3d.domain.surface.models import (
    CategoricalSurfaceResource,
    LandCoverLegend,
    LandCoverLegendEntry,
    LandCoverProvenance,
    LandCoverSampleGrid,
    LandCoverSamplingRequest,
    LandCoverSourceDescriptor,
    LandCoverSourceType,
    SurfaceStyle,
)
from terralab3d.domain.surface.services import (
    select_sources_automatic,
    select_sources_manual,
    select_lod_tier,
    lod_block_size,
)
from terralab3d.domain.terrain.models import TerrainChunkIdentity
from terralab3d.infrastructure.adapters.cache.adapter import ByteLRUCache
from terralab3d.infrastructure.adapters.landcover.adapter import (
    RasterLandCoverAdapter,
    STANDARD_LEGENDS,
)


def create_synthetic_categorical_geotiff(
    width: int = 100,
    height: int = 100,
    crs: str = "EPSG:4326",
    west: float = 2.0,
    north: float = 42.0,
    pixel_size: float = 0.001,
    fill_class: int = 10,
    nodata: int = 0,
) -> bytes:
    """Create in-memory GeoTIFF with single categorical band."""
    data = np.full((1, height, width), fill_class, dtype=np.uint16)
    # Add a nodata region
    data[0, 0:10, 0:10] = nodata
    # Add a special class region
    data[0, 50:70, 50:70] = 42

    transform = from_origin(west, north, pixel_size, pixel_size)
    mem_file = io.BytesIO()
    with rasterio.open(
        mem_file,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dataset:
        dataset.write(data)
        dataset.write_colormap(
            1,
            {
                0: (0, 0, 0, 0),
                10: (34, 139, 34, 255),  # Forest Green
                42: (255, 215, 0, 255),  # Golden Yellow
            },
        )
    return mem_file.getvalue()


@pytest.fixture
def synthetic_landcover_env(tmp_path):
    tiff_bytes = create_synthetic_categorical_geotiff()
    tiff_path = tmp_path / "synthetic_landcover.tif"
    tiff_path.write_bytes(tiff_bytes)

    config_data = {
        "sources": [
            {
                "id": "synthetic_lc",
                "display_name": "Synthetic Land Cover",
                "layer_type": "land_cover_categorical",
                "path": str(tiff_path),
                "priority": 100,
                "enabled": True,
                "coverage": [2.0, 41.9, 2.1, 42.0],
            }
        ]
    }
    config_path = tmp_path / "data_sources.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    return config_path


def test_raster_adapter_sampling_and_colormap(synthetic_landcover_env):
    adapter = RasterLandCoverAdapter(config_paths=(synthetic_landcover_env,))

    # Sample within valid class 10 region, class 42 region, and nodata region
    lats = np.array([41.98, 41.94, 41.995], dtype=np.float64)
    lons = np.array([2.05, 2.06, 2.005], dtype=np.float64)
    req = LandCoverSamplingRequest(
        terrain_content_key="key-test",
        terrain_version=1,
        latitude_deg=lats,
        longitude_deg=lons,
        generation=1,
        lod_tier=0,
    )

    grid = adapter.sample_classes(req)
    assert grid.sample_count == 3
    assert grid.class_ids[0] == 10
    assert grid.class_ids[1] == 42
    assert grid.valid[0] == True
    assert grid.valid[1] == True
    assert grid.valid[2] == False  # nodata

    # Verify legend extraction from embedded colormap
    legend = adapter.legend("synthetic_lc")
    assert legend is not None
    entry_10 = legend.entry_by_class(10)
    assert entry_10 is not None
    assert entry_10.rgba == (34, 139, 34, 255)

    entry_42 = legend.entry_by_class(42)
    assert entry_42 is not None
    assert entry_42.rgba == (255, 215, 0, 255)

    adapter.close()


def test_modal_downsampling_preserves_dominant_and_small_features():
    # 8 samples: mostly class 10 (forest), with a water sample (class 80)
    classes = np.array([10, 10, 80, 10, 10, 10, 10, 10], dtype=np.uint16)
    valid = np.ones(8, dtype=bool)

    # Downsample by block_size 4 without protection: mode 10 wins
    downsampled, down_valid = categorical_modal_downsample(classes, valid, block_size=4)
    assert len(downsampled) == 2
    assert downsampled[0] == 10
    assert downsampled[1] == 10

    # Downsample with protected class 80: minority 80 is preserved!
    protected_down, _ = categorical_modal_downsample(
        classes, valid, block_size=4, protected_classes=frozenset([80])
    )
    assert protected_down[0] == 80
    assert protected_down[1] == 10


def test_decode_rgb_to_class():
    legend = LandCoverLegend(
        legend_id="test_leg",
        source_id="test_src",
        entries=(
            LandCoverLegendEntry(10, "Forest", (34, 139, 34, 255), is_nodata=False),
            LandCoverLegendEntry(80, "Water", (0, 0, 255, 255), is_nodata=False),
        ),
    )
    rgb_data = np.array([
        [34, 139, 34],
        [0, 0, 255],
        [100, 100, 100],  # unmatched
    ], dtype=np.uint8)

    class_ids, valid = decode_rgb_to_class(rgb_data, legend)
    assert len(class_ids) == 3
    assert class_ids[0] == 10
    assert valid[0] == True
    assert class_ids[1] == 80
    assert valid[1] == True
    assert valid[2] == False  # unmatched -> invalid


def test_build_palette_index_map():
    legend = LandCoverLegend(
        legend_id="test_leg",
        source_id="test_src",
        entries=(
            LandCoverLegendEntry(10, "Forest", (34, 139, 34, 255), is_nodata=False),
            LandCoverLegendEntry(80, "Water", (0, 0, 255, 255), is_nodata=False),
        ),
    )
    class_ids = np.array([10, 80, 10, 0, 999], dtype=np.uint16)
    source_slots = np.zeros(5, dtype=np.int16)
    palette_indices, palette_list = build_palette_index_map(class_ids, source_slots, legend)

    assert len(palette_indices) == 5
    assert len(palette_list) >= 2  # class 10 and 80 mapped
    # Forest is first unique -> index 1
    assert palette_indices[0] == 1
    assert palette_indices[1] == 2
    assert palette_indices[2] == 1


def test_source_selection_services():
    s1 = LandCoverSourceDescriptor(
        "s1", "High Res", LandCoverSourceType.CATEGORICAL_NATIVE,
        "EPSG:4326", 10.0, None, None, priority=100, legend_id=None, fingerprint="fp1"
    )
    s2 = LandCoverSourceDescriptor(
        "s2", "Low Res", LandCoverSourceType.CATEGORICAL_NATIVE,
        "EPSG:4326", 100.0, None, None, priority=50, legend_id=None, fingerprint="fp2"
    )
    s_disabled = LandCoverSourceDescriptor(
        "s3", "Off", LandCoverSourceType.CATEGORICAL_NATIVE,
        "EPSG:4326", 5.0, None, None, priority=200, legend_id=None, fingerprint="fp3", enabled=False
    )

    sources = [s1, s2, s_disabled]

    # Automatic selection
    auto_selected = select_sources_automatic(sources)
    assert [s.id for s in auto_selected] == ["s1", "s2"]

    # Manual selection: primary choice goes first, remaining sources follow
    manual_selected = select_sources_manual(sources, "s2")
    assert [s.id for s in manual_selected] == ["s2", "s1"]

    # Unknown manual selection falls back to automatic
    fallback_selected = select_sources_manual(sources, "unknown")
    assert [s.id for s in fallback_selected] == ["s1", "s2"]


def test_lod_hysteresis():
    tier0 = select_lod_tier(500, native_resolution_m=10.0, fov_deg=60, viewport_width_px=1920, current_tier=0)
    assert tier0 == 0

    tier_far = select_lod_tier(50_000, native_resolution_m=10.0, fov_deg=60, viewport_width_px=1920, current_tier=0)
    assert tier_far > 0
    assert lod_block_size(tier_far) > 1


def test_byte_lru_cache():
    cache = ByteLRUCache[str](max_bytes=1024, byte_sizer=lambda s: len(s.encode("utf-8")))
    cache.put("k1", "a" * 400)
    cache.put("k2", "b" * 400)
    assert cache.get("k1") == "a" * 400
    assert cache.current_bytes == 800

    # Overflows budget -> evicts oldest unaccessed
    cache.put("k3", "c" * 400)
    assert cache.current_bytes <= 1024
    assert cache.get("k2") is None  # evicted
    assert cache.get("k1") == "a" * 400
    assert cache.get("k3") == "c" * 400


def test_pack_surface_resource_binary_layout():
    class_ids = np.array([10, 20, 30], dtype=np.uint16)
    source_slots = np.array([0, 0, -1], dtype=np.int16)
    palette_indices = np.array([1, 2, 0], dtype=np.uint16)
    provenances = np.array([1, 1, 0], dtype=np.uint8)
    valid = np.array([True, True, False], dtype=bool)

    legend = LandCoverLegend(
        legend_id="leg-test",
        source_id="src-test",
        entries=(
            LandCoverLegendEntry(10, "Forest", (34, 139, 34, 255), is_nodata=False),
            LandCoverLegendEntry(20, "Urban", (255, 0, 0, 255), is_nodata=False),
        ),
    )

    grid = LandCoverSampleGrid(
        class_ids=class_ids,
        palette_indices=palette_indices,
        source_slots=source_slots,
        valid=valid,
        provenance=provenances,
        legend=legend,
        source_descriptors=(),
        resolved_fraction=0.667,
        fallback_fraction=0.0,
    )

    resource = CategoricalSurfaceResource(
        resource_id=ResourceId("earth.terrain.surface"),
        version=42,
        generation=1,
        terrain_content_key="test-key",
        compatible_terrain_version=1,
        sample_count=3,
        resolved_fraction=0.667,
        fallback_fraction=0.0,
        legend=legend,
        source_descriptors=(),
    )

    metadata, payload = pack_surface_resource(resource, grid)

    assert metadata["role"] == "surface_resource"
    assert metadata["resourceId"] == "earth.terrain.surface"
    assert metadata["version"] == 42
    assert metadata["terrainContentKey"] == "test-key"
    assert metadata["vertexCount"] == 3
    assert len(metadata["palette"]) >= 2
    assert len(metadata["legend"]) == 2

    # Verify binary offsets
    layout = metadata["bufferLayout"]
    c_off = layout["terrainClassId"]["offset"]
    unpacked_classes = np.frombuffer(payload, dtype=np.uint16, count=3, offset=c_off)
    np.testing.assert_array_equal(unpacked_classes, class_ids)

    p_off = layout["paletteIndex"]["offset"]
    unpacked_pal = np.frombuffer(payload, dtype=np.uint16, count=3, offset=p_off)
    np.testing.assert_array_equal(unpacked_pal, palette_indices)


@pytest.mark.anyio
async def test_coordinator_async_drain_and_cancellation(synthetic_landcover_env):
    adapter = RasterLandCoverAdapter(config_paths=(synthetic_landcover_env,))

    published_messages = []
    async def fake_surface_publisher(metadata, payload):
        published_messages.append((metadata, payload))

    published_statuses = []
    async def fake_status_publisher(status):
        published_statuses.append(status)

    coordinator = LandCoverCoordinator(
        adapter,
        surface_publisher=fake_surface_publisher,
        status_publisher=fake_status_publisher,
        cache_bytes=1024 * 1024,
    )

    lats = np.array([41.98, 41.94], dtype=np.float64)
    lons = np.array([2.05, 2.06], dtype=np.float64)

    chunk1 = TerrainChunkIdentity("key-1", 1, 2, 0.0, 0.0)
    await coordinator.schedule_sampling(chunk1, lats, lons, generation=1)

    chunk2 = TerrainChunkIdentity("key-2", 2, 2, 0.0, 0.0)
    await coordinator.schedule_sampling(chunk2, lats, lons, generation=2)

    # Give async drain loop time to execute
    for _ in range(20):
        if coordinator.published_count >= 1:
            break
        await asyncio.sleep(0.05)

    assert coordinator.published_count >= 1
    assert len(published_messages) >= 1

    # Verify coordinator status
    metrics = coordinator.metrics()
    assert metrics["surfaceRequests"] == 2
    assert metrics["surfacePublished"] >= 1

    await coordinator.close()
    adapter.close()

