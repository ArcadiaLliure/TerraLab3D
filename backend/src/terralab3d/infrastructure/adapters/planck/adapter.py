"""Adaptador de processament del mapa de pols Planck."""

from __future__ import annotations

import logging
from pathlib import Path

from terralab3d.application.ports.resource_processing import ProcessedResource
from terralab3d.infrastructure.adapters.planck.converter import (
    convert_planck_fits_to_texture,
)


log = logging.getLogger("terralab3d.resources.planck")


class PlanckDustAdapter:
    """Materialitza una cache GPU local a partir del FITS HEALPix oficial."""

    def __init__(
        self,
        *,
        width: int = 3600,
        height: int = 1800,
        workers: int = 1,
    ) -> None:
        self._width = width
        self._height = height
        self._workers = workers

    def process(self, source_path: Path, output_dir: Path) -> ProcessedResource:
        output_path = output_dir / f"{source_path.stem}.galactic-opacity.png"
        log.debug(
            "MGP: [PlanckDustAdapter] [Convertint %s a %dx%d]",
            source_path.name,
            self._width,
            self._height,
        )
        conversion = convert_planck_fits_to_texture(
            source_path,
            output_path,
            width=self._width,
            height=self._height,
            workers=self._workers,
        )
        return ProcessedResource(
            render_path=conversion.output_path,
            metadata={
                "renderFormat": "png",
                "renderWidth": conversion.width,
                "renderHeight": conversion.height,
                "coordinateFrame": "GALACTIC",
                "projection": "plate-carree/equirectangular",
                "longitudeAtLeftEdgeDeg": 0.0,
                "longitudeIncreases": "right",
                "latitudeIncreases": "up",
                "sourceField": conversion.source_column,
                "sourceNside": conversion.nside,
                "sourceOrdering": conversion.ordering,
                "normalizationLow": conversion.normalization_low,
                "normalizationHigh": conversion.normalization_high,
            },
        )
