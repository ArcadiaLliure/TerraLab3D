"""Diagnostic entry point for TerraLab3D's configured land-cover source."""

from __future__ import annotations

from .adapter import ConfiguredSurfaceSampler


def main() -> int:
    source = ConfiguredSurfaceSampler().resolve_land_cover_source()
    if source is None:
        print("LAND_COVER_SOURCE=UNAVAILABLE")
        return 1

    print("LAND_COVER_SOURCE=OK")
    print(f"SOURCE_ID={source.source_id}")
    print(f"DISPLAY_NAME={source.display_name}")
    print(f"CONFIG={source.config_path}")
    print(f"RASTER={source.raster_paths[0]}")
    print(f"CRS={source.crs}")
    print(f"RESOLUTION_M={source.resolution_m}")
    print(f"NODATA={source.nodata}")
    print(f"LEGEND_ID={source.legend_id}")
    print(f"RASTER_COUNT={len(source.raster_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
