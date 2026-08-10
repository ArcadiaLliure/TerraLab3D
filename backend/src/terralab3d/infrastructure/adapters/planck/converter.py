"""Conversió del mapa HEALPix de pols Planck a cache equirectangular.

La implementació adapta el conversor de TerraLab, però el resultat és ara un
asset derivat d'infraestructura: el FITS oficial continua sent la font local i
el renderer només consumeix el PNG normalitzat generat al directori gestionat.
"""

from __future__ import annotations

import math
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hpgeom
import numpy as np
from astropy.io import fits
from PIL import Image


_WORKER_HDU_LIST: fits.HDUList | None = None
_WORKER_VALUES: np.ndarray | None = None
_WORKER_NSIDE = 0
_WORKER_NEST = False
_WORKER_WIDTH = 0
_WORKER_HEIGHT = 0
_WORKER_LONGITUDES: np.ndarray | None = None


@dataclass(frozen=True, slots=True)
class PlanckDustConversion:
    output_path: Path
    width: int
    height: int
    nside: int
    ordering: str
    coordinate_system: str
    source_column: str
    normalization_low: float
    normalization_high: float


def _first_healpix_table(hdu_list: fits.HDUList) -> fits.BinTableHDU:
    for hdu in hdu_list:
        if isinstance(hdu, fits.BinTableHDU):
            return hdu
    raise ValueError("El FITS Planck no conté cap taula binària HEALPix")


def _dust_column_name(hdu: fits.BinTableHDU) -> str:
    names = tuple(str(name) for name in (hdu.columns.names or ()))
    for candidate in ("TAU353", "TAU", "I_STOKES"):
        if candidate in names:
            return candidate
    if names:
        return names[0]
    raise ValueError("La taula HEALPix no conté cap camp de pols")


def _inspect_source(source_path: Path) -> tuple[str, int, bool, str, str, int]:
    with fits.open(source_path, memmap=True) as hdu_list:
        hdu = _first_healpix_table(hdu_list)
        column = _dust_column_name(hdu)
        values = np.asarray(hdu.data[column]).reshape(-1)
        if values.size == 0:
            raise ValueError(f"El camp {column} del FITS Planck és buit")

        nside = int(hdu.header.get("NSIDE", 0))
        if nside <= 0:
            nside = int(round(math.sqrt(values.size / 12.0)))
        if nside <= 0 or 12 * nside * nside != int(values.size):
            raise ValueError("No es pot deduir un NSIDE vàlid del FITS Planck")

        ordering = str(hdu.header.get("ORDERING", "RING")).upper()
        coordinate_system = str(hdu.header.get("COORDSYS", "G")).upper()
        if not coordinate_system.startswith("G"):
            raise ValueError(
                "El mapa de pols ha d'estar en coordenades galàctiques "
                f"(COORDSYS=G), no {coordinate_system!r}"
            )
        return column, nside, ordering.startswith("NEST"), ordering, coordinate_system, int(values.size)


def _initialise_worker(
    source_path: str,
    column: str,
    nside: int,
    nest: bool,
    width: int,
    height: int,
) -> None:
    global _WORKER_HDU_LIST, _WORKER_VALUES, _WORKER_NSIDE
    global _WORKER_NEST, _WORKER_WIDTH, _WORKER_HEIGHT, _WORKER_LONGITUDES

    _WORKER_HDU_LIST = fits.open(source_path, memmap=True)
    hdu = _first_healpix_table(_WORKER_HDU_LIST)
    _WORKER_VALUES = np.asarray(hdu.data[column]).reshape(-1)
    _WORKER_NSIDE = nside
    _WORKER_NEST = nest
    _WORKER_WIDTH = width
    _WORKER_HEIGHT = height
    _WORKER_LONGITUDES = (
        np.linspace(0.0, 360.0, num=width, endpoint=False, dtype=np.float64)
        + 180.0 / width
    )


def _close_local_worker() -> None:
    global _WORKER_HDU_LIST, _WORKER_VALUES, _WORKER_LONGITUDES
    if _WORKER_HDU_LIST is not None:
        _WORKER_HDU_LIST.close()
    _WORKER_HDU_LIST = None
    _WORKER_VALUES = None
    _WORKER_LONGITUDES = None


def _convert_row_range(row_range: tuple[int, int]) -> tuple[int, np.ndarray]:
    if _WORKER_VALUES is None or _WORKER_LONGITUDES is None:
        raise RuntimeError("El worker Planck no està inicialitzat")

    row_start, row_end = row_range
    output = np.empty((row_end - row_start, _WORKER_WIDTH), dtype=np.float32)
    for local_row, row in enumerate(range(row_start, row_end)):
        latitude_deg = 90.0 - ((row + 0.5) / _WORKER_HEIGHT) * 180.0
        latitudes = np.full(_WORKER_WIDTH, latitude_deg, dtype=np.float64)
        pixels = hpgeom.angle_to_pixel(
            _WORKER_NSIDE,
            _WORKER_LONGITUDES,
            latitudes,
            nest=_WORKER_NEST,
            lonlat=True,
            degrees=True,
        )
        output[local_row] = np.asarray(_WORKER_VALUES[pixels], dtype=np.float32)
    return row_start, output


def _normalise_visual_opacity(
    values: np.ndarray,
    percentile_low: float,
    percentile_high: float,
) -> tuple[np.ndarray, float, float]:
    finite = np.isfinite(values)
    if not np.any(finite):
        raise ValueError("El mapa Planck no conté cap valor finit")

    low = float(np.percentile(values[finite], percentile_low))
    high = float(np.percentile(values[finite], percentile_high))
    if high <= low:
        high = low + 1e-12
    normalized = np.clip((values - low) / (high - low), 0.0, 1.0)
    normalized = np.where(np.isfinite(normalized), normalized, 0.0)
    opacity_u8 = np.asarray(np.rint(normalized * 255.0), dtype=np.uint8)
    return opacity_u8, low, high


def convert_planck_fits_to_texture(
    source_path: Path,
    output_path: Path,
    *,
    width: int = 3600,
    height: int = 1800,
    workers: int = 1,
    chunk_rows: int = 64,
    percentile_low: float = 1.0,
    percentile_high: float = 99.5,
) -> PlanckDustConversion:
    """Genera un PNG gris equirectangular en longitud/latitud galàctiques.

    Convenció del derivat: ``u=0`` és ``l=0°``, la longitud creix cap a la
    dreta, ``v=0`` és ``b=+90°`` i ``v=1`` és ``b=-90°``. El renderer aplica
    la matriu IAU ICRS→galàctic quan mostreja aquesta textura.
    """

    source_path = Path(source_path).resolve(strict=True)
    output_path = Path(output_path).resolve(strict=False)
    width = max(16, int(width))
    height = max(8, int(height))
    workers = max(1, int(workers))
    chunk_rows = max(1, int(chunk_rows))
    if not 0.0 <= percentile_low < percentile_high <= 100.0:
        raise ValueError("Els percentils de normalització Planck no són vàlids")

    column, nside, nest, ordering, coordinate_system, value_count = _inspect_source(source_path)
    if value_count != 12 * nside * nside:
        raise ValueError("La mida del mapa Planck no és coherent amb NSIDE")

    tasks = [
        (row, min(height, row + chunk_rows))
        for row in range(0, height, chunk_rows)
    ]
    result = np.empty((height, width), dtype=np.float32)
    worker_args = (str(source_path), column, nside, nest, width, height)

    if workers == 1:
        _initialise_worker(*worker_args)
        try:
            for task in tasks:
                row_start, rows = _convert_row_range(task)
                result[row_start : row_start + rows.shape[0]] = rows
        finally:
            _close_local_worker()
    else:
        context = mp.get_context("spawn")
        with context.Pool(
            processes=workers,
            initializer=_initialise_worker,
            initargs=worker_args,
        ) as pool:
            for row_start, rows in pool.imap_unordered(_convert_row_range, tasks):
                result[row_start : row_start + rows.shape[0]] = rows

    opacity_u8, low, high = _normalise_visual_opacity(
        result,
        percentile_low,
        percentile_high,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    Image.fromarray(opacity_u8).save(temporary_path, format="PNG")
    temporary_path.replace(output_path)

    return PlanckDustConversion(
        output_path=output_path,
        width=width,
        height=height,
        nside=nside,
        ordering=ordering,
        coordinate_system=coordinate_system,
        source_column=column,
        normalization_low=low,
        normalization_high=high,
    )
