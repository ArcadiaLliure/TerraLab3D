"""Explicit pyproj infrastructure for observer-centred AEQD radial sampling."""

from __future__ import annotations

import numpy as np
from pyproj import CRS, Transformer


class PyprojAeqdProjector:
    def __init__(self) -> None:
        self._working_crs = ""
        self._transformer: Transformer | None = None
        self._observer: tuple[float, float] | None = None

    @property
    def working_crs(self) -> str:
        return self._working_crs

    def project(
        self,
        latitude_deg: float,
        longitude_deg: float,
        azimuth_deg: object,
        distance_m: object,
    ) -> tuple[np.ndarray, np.ndarray]:
        observer = (float(latitude_deg), float(longitude_deg))
        if observer != self._observer:
            aeqd = CRS.from_proj4(
                f"+proj=aeqd +lat_0={observer[0]:.12f} +lon_0={observer[1]:.12f} "
                "+datum=WGS84 +units=m +no_defs"
            )
            self._working_crs = aeqd.to_string()
            self._transformer = Transformer.from_crs(aeqd, "EPSG:4326", always_xy=True)
            self._observer = observer
        azimuth = np.radians(np.asarray(azimuth_deg, dtype=np.float64))
        distance = np.asarray(distance_m, dtype=np.float64)
        east = np.sin(azimuth) * distance
        north = np.cos(azimuth) * distance
        assert self._transformer is not None
        longitude, latitude = self._transformer.transform(east, north)
        return np.asarray(latitude, dtype=np.float64), np.asarray(longitude, dtype=np.float64)
