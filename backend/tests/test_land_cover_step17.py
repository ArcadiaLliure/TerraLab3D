import json
import tempfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from terralab3d.infrastructure.adapters.surface.adapter import ConfiguredSurfaceSampler
from terralab3d.infrastructure.adapters.surface.land_cover_port import RasterioLandCoverPort
from terralab3d.domain.surface.land_cover import LandCoverTileRequest


def test_land_cover_resolution_and_port():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # 1. Create a dummy GeoTIFF
        tif_path = temp_dir_path / "test_data.tif"
        data = np.array([[255, 104], [104, 255]], dtype=np.uint8)
        
        # Raster boundaries: X from 100000 to 100020, Y from 199980 to 200000.
        # Top left corner is (100000, 200000)
        transform = from_origin(100000, 200000, 10, 10)  # minx, maxy, xsize, ysize
        with rasterio.open(
            tif_path,
            'w',
            driver='GTiff',
            height=2,
            width=2,
            count=1,
            dtype=data.dtype,
            crs='EPSG:3035',
            transform=transform,
            nodata=255
        ) as dst:
            dst.write(data, 1)
            
        # 2. Create data_sources.json
        config_path = temp_dir_path / "data_sources.json"
        config = {
            "selections": {
                "land_cover": {
                    "mode": "manual",
                    "source_id": "test_lc"
                }
            },
            "sources": [
                {
                    "id": "test_lc",
                    "layer_type": "land_cover_categorical",
                    "enabled": True,
                    "path": str(temp_dir_path),  # Directory path
                    "metadata": {
                        "rasters": [
                            {"paths": ["test_data.tif"]}
                        ]
                    }
                },
                {
                    "id": "fallback_lc",
                    "layer_type": "land_cover_categorical",
                    "enabled": True,
                    "path": str(tif_path)
                }
            ]
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)
            
        # 3. Test ConfiguredSurfaceSampler
        sampler = ConfiguredSurfaceSampler(config_paths=(config_path,))
        
        # Test no fallback in manual mode (request non-existent)
        none_resolved = sampler.resolve_land_cover_source(override_mode="manual", override_source_id="invalid")
        assert none_resolved is None
        
        # Test valid manual selection
        resolved = sampler.resolve_land_cover_source()
        assert resolved is not None
        assert resolved.source_id == "test_lc"
        assert resolved.crs == "EPSG:3035"
        assert resolved.nodata == 255
        assert len(resolved.raster_paths) == 1
        assert resolved.raster_paths[0].name == "test_data.tif"
        
        # 4. Test RasterioLandCoverPort
        port = RasterioLandCoverPort(sampler)
        
        request_exact = LandCoverTileRequest(
            min_x=100000.0,
            min_y=199980.0,
            max_x=100020.0,
            max_y=200000.0,
            resolution=10.0,
            crs="EPSG:3035",
            source_mode="manual",
            source_id=None
        )
        tile_exact = port.read_tile(request_exact)
        assert tile_exact is not None
        
        buffer_exact = np.frombuffer(tile_exact.class_buffer, dtype=np.uint16).reshape(2, 2)
        
        # Nearest neighbour sampling and Nodata 255 -> 0 mapping.
        # Raster original data: [[255, 104], [104, 255]] (2x2)
        assert buffer_exact[0, 0] == 0
        assert buffer_exact[0, 1] == 104
        assert buffer_exact[1, 0] == 104
        assert buffer_exact[1, 1] == 0
        
        # Empty tile
        request_empty = LandCoverTileRequest(
            min_x=0.0,
            min_y=0.0,
            max_x=20.0,
            max_y=20.0,
            resolution=10.0,
            crs="EPSG:3035",
            source_mode="manual",
            source_id=None
        )
        tile_empty = port.read_tile(request_empty)
        assert tile_empty is not None
        assert tile_empty.valid_pixels == 0
        
        buffer_empty = np.frombuffer(tile_empty.class_buffer, dtype=np.uint16)
        assert np.all(buffer_empty == 0)
        
        port.close()
