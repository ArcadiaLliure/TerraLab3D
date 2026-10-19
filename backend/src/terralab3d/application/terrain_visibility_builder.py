"""DEM autoritatiu → superfície física immutable, sense ciència a l'adaptador."""

from __future__ import annotations

import json
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from terralab3d.application.ports.terrain import ElevationPort
from terralab3d.domain.elevation.models import ElevationBatchRequest
from terralab3d.domain.light_pollution.geometric_transport import SphericalFrame
from terralab3d.domain.light_pollution.source_model import GeodeticPosition
from terralab3d.domain.light_pollution.terrain_visibility import (
    TerrainCoverageError,
    TerrainSurface,
)


def build_terrain_surface(
    dem: ElevationPort,
    latitudes_deg: tuple[float, ...],
    longitudes_deg: tuple[float, ...],
    frame: SphericalFrame,
    *,
    upper_envelope_m: float,
    height_interpretation: str,
    height_to_radial: Callable[[NDArray[np.float64]], NDArray[np.float64]],
    cancelled: Callable[[], bool] | None = None,
    max_vertices: int = 65536,
) -> TerrainSurface:
    """Graella de nusos sud→nord/oest→est; diagonal SW→NE explícita.

    EPSG:4326 només identifica el CRS horitzontal. La conversió vertical
    és obligatòria i declarada; no es confon altitud ortomètrica amb ECEF.
    Cap resampleig no pot recuperar muntanyes absents de la graella triada.
    """
    if (
        len(latitudes_deg) < 2
        or len(longitudes_deg) < 2
        or any(
            b <= a
            for seq in (latitudes_deg, longitudes_deg)
            for a, b in zip(seq, seq[1:])
        )
        or not height_interpretation
    ):
        raise ValueError("Graella DEM desordenada o convenció vertical absent")
    if (
        type(max_vertices) is not int
        or max_vertices < 4
        or len(latitudes_deg) * len(longitudes_deg) > max_vertices
    ):
        raise ValueError(
            "Pressupost de vèrtexs DEM excedit; cal graella explícita més petita"
        )
    lat, lon = np.meshgrid(latitudes_deg, longitudes_deg, indexing="ij")
    batch = dem.sample_points(
        ElevationBatchRequest(lat, lon, cancellation_check=cancelled)
    )
    if cancelled and cancelled():
        raise InterruptedError("Construcció de terreny cancel·lada")
    if not np.all(batch.valid_mask):
        raise TerrainCoverageError("DEM incomplet: no s'omplen buits amb altura zero")
    heights = np.asarray(
        height_to_radial(batch.values_m.astype(np.float64)), dtype=np.float64
    )
    if heights.shape != lat.shape or not np.all(np.isfinite(heights)):
        raise ValueError("Conversió vertical DEM invàlida")
    vertices = tuple(
        frame.position_ecef(GeodeticPosition(float(a), float(b), float(h)))
        for a, b, h in zip(lat.ravel(), lon.ravel(), heights.ravel())
    )
    ny, nx = lat.shape
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            sw = j * nx + i
            faces.extend(((sw, sw + 1, sw + nx + 1), (sw, sw + nx + 1, sw + nx)))
    boundary = tuple(
        list(range(nx))
        + [j * nx + nx - 1 for j in range(1, ny)]
        + list(range(ny * nx - 2, (ny - 1) * nx - 1, -1))
        + [j * nx for j in range(ny - 2, 0, -1)]
    )
    metadata = dem.metadata()
    assert batch.source_indices is not None
    provenance = json.dumps(
        {
            "source": metadata.source_id,
            "fingerprint": metadata.fingerprint,
            "nativeCrs": metadata.native_crs,
            "sourceIds": metadata.source_ids,
            "horizontalCrs": "EPSG:4326",
            "triangulation": "SW-NE;piecewise_planar_ECEF",
            "sampleSourceIndices": batch.source_indices.tolist(),
        },
        sort_keys=True,
    )
    return TerrainSurface(
        vertices,
        tuple(faces),
        boundary,
        frame.radius_m,
        upper_envelope_m,
        provenance,
        height_interpretation,
    )
