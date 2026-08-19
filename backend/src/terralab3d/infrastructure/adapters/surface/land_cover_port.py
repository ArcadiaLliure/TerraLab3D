"""Adaptador per al port de cobertura terrestre usant Rasterio."""

import logging
from dataclasses import replace
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from terralab3d.application.ports.land_cover import LandCoverPort
from terralab3d.domain.surface.land_cover import (
    LandCoverLegend,
    LandCoverLegendEntry,
    LandCoverProvenance,
    LandCoverTile,
    LandCoverTileRequest,
)
from terralab3d.infrastructure.adapters.surface.adapter import (
    ConfiguredSurfaceSampler,
    ResolvedLandCoverSource,
)

log = logging.getLogger("terralab3d.land_cover_port")


class RasterioLandCoverPort(LandCoverPort):
    """Implementació de LandCoverPort utilitzant rasterio."""

    def __init__(self, sampler: ConfiguredSurfaceSampler) -> None:
        self._sampler = sampler

    def read_tile(self, request: LandCoverTileRequest) -> LandCoverTile | None:
        log.info("MGP: RasterioLandCoverPort.read_tile [INICI]")
        resolved = self._sampler.resolve_land_cover_source(
            override_mode=request.source_mode,
            override_source_id=request.source_id,
        )
        if not resolved or not resolved.raster_paths:
            log.info("MGP: RasterioLandCoverPort.read_tile [FI]")
            return None

        # Definim l'espai de destinació
        # width = int(round((request.max_x - request.min_x) / request.resolution))
        # ... pero usarem math per assegurar cap desquadrament
        width = max(1, int(round((request.max_x - request.min_x) / request.resolution)))
        height = max(1, int(round((request.max_y - request.min_y) / request.resolution)))
        
        # from_bounds usa: west, south, east, north, width, height
        dst_transform = from_bounds(
            request.min_x, request.min_y, request.max_x, request.max_y, width, height
        )

        dst_array = np.zeros((1, height, width), dtype=np.uint16)
        
        # Mantenim el seguiment dels píxels vàlids combinats per si hi ha múltiples rasters
        # (Encara que reproject sobreescriurà, podem pintar sobre els zeros successivament).
        temp_dst = np.zeros((1, height, width), dtype=np.uint16)
        
        # El requeriment "nodata del raster, por ejemplo 255, debe transformarse a clase interna 0"
        # S'implementa re-mapejant el nodata un cop s'ha fet la reprojecció.
        
        valid_pixels = 0
        
        log.debug("MGP: [land_cover_port] Resolved %d raster paths for source %s", len(resolved.raster_paths), resolved.source_id)
        log.debug("MGP: [land_cover_port] Destination bounding box: (%.2f, %.2f, %.2f, %.2f) with shape (%d, %d)",
                 request.min_x, request.min_y, request.max_x, request.max_y, height, width)

        for raster_path in resolved.raster_paths:
            try:
                with rasterio.open(raster_path) as src:
                    src_nodata = src.nodata
                    log.debug("MGP: [land_cover_port] Reading %s with nodata=%s. Dest CRS='%s'",
                             raster_path, src_nodata, request.crs)
                    
                    # Reproject només Resampling.nearest per preservar IDs categòrics
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=temp_dst,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=dst_transform,
                        dst_crs=request.crs,
                        resampling=Resampling.nearest,
                        src_nodata=src_nodata,
                        dst_nodata=0,  # La nostra classe interna per nodata és 0
                    )
                    
                    if src_nodata is not None:
                        temp_dst[temp_dst == src_nodata] = 0
                        
                    # Tot allò que no sigui 0 al temp_dst i sigui 0 al dst_array s'actualitza.
                    # Només volem tapar on no teníem dades (0).
                    mask = (temp_dst > 0) & (dst_array == 0)
                    dst_array[mask] = temp_dst[mask]
                    
            except Exception as exc:
                log.warning("Error reprojectant %s: %s", raster_path, exc)
                continue
                
        valid_pixels = int(np.count_nonzero(dst_array))
        
        tile = LandCoverTile(
            resource_id=f"landcover_{resolved.source_id}",
            provenance=LandCoverProvenance(
                source_id=resolved.source_id,
                version=1,
            ),
            legend_id=resolved.legend_id or "s2glc_europe_2017",
            min_x=request.min_x,
            min_y=request.min_y,
            max_x=request.max_x,
            max_y=request.max_y,
            width=width,
            height=height,
            resolution=request.resolution,
            crs=request.crs,
            valid_pixels=valid_pixels,
            class_buffer=dst_array.tobytes(),
        )
        log.info("MGP: RasterioLandCoverPort.read_tile [FI]")
        return tile

    def legend(self, legend_id: str) -> LandCoverLegend | None:
        log.info("MGP: RasterioLandCoverPort.legend [INICI]")
        if legend_id != "s2glc_europe_2017":
            log.info("MGP: RasterioLandCoverPort.legend [FI]")
            return None

        res = LandCoverLegend(
            legend_id=legend_id,
            entries=(
                LandCoverLegendEntry(class_id=0, name="Sense dades", color_rgba=(0, 0, 0, 0)),
                LandCoverLegendEntry(class_id=62, name="Superfícies artificials", color_rgba=(210, 0, 0, 255)),
                LandCoverLegendEntry(class_id=73, name="Terres de conreu", color_rgba=(253, 211, 39, 255)),
                LandCoverLegendEntry(class_id=82, name="Bosc de frondoses", color_rgba=(176, 91, 16, 255)),
                LandCoverLegendEntry(class_id=83, name="Bosc de coníferes", color_rgba=(35, 152, 0, 255)),
                LandCoverLegendEntry(class_id=102, name="Vegetació herbàcia", color_rgba=(8, 98, 0, 255)),
                LandCoverLegendEntry(class_id=103, name="Matollars i landes", color_rgba=(128, 255, 0, 255)),
                LandCoverLegendEntry(class_id=104, name="Pastius i pastures", color_rgba=(141, 139, 0, 255)),
                LandCoverLegendEntry(class_id=105, name="Torberes", color_rgba=(95, 53, 7, 255)),
                LandCoverLegendEntry(class_id=106, name="Aiguamolls", color_rgba=(43, 115, 149, 255)),
                LandCoverLegendEntry(class_id=121, name="Sòl nu", color_rgba=(79, 79, 79, 255)),
                LandCoverLegendEntry(class_id=123, name="Espais amb vegetació esparsa", color_rgba=(204, 204, 204, 255)),
                LandCoverLegendEntry(class_id=162, name="Neu i glaceres", color_rgba=(255, 255, 255, 255)),
                LandCoverLegendEntry(class_id=211, name="Masses d'aigua", color_rgba=(0, 50, 200, 255)),
            ),
        )
        log.info("MGP: RasterioLandCoverPort.legend [FI]")
        return res

    def close(self) -> None:
        pass
