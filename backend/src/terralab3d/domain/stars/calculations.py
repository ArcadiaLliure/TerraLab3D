"""Càlculs científics purs per a estrelles.

Conversions executades una vegada per versió de recurs, NO per frame:
- RA/Dec → vector unitari equatorial XYZ
- BP-RP → RGB uint8
- Matriu equatorial→ENU

La matriu equatorial→ENU es recalcula quan canvia LST/latitud (no per frame visual).
"""

from __future__ import annotations

import math
from typing import Protocol

import numpy as np

from terralab3d.domain.stars.models import StarRecord


# ─── Càlculs de visibilitat ────────────────────────────────────────────

class StarVisibilityCalculator(Protocol):
    """Defineix els càlculs purs de visibilitat sense I/O ni renderitzat."""
    def visible(self, record: StarRecord, magnitude_limit: float, extinction: float) -> bool: ...
    def apparent_magnitude(self, record: StarRecord, extinction: float) -> float: ...


# ─── RA/Dec → vector unitari equatorial ────────────────────────────────

def ra_dec_to_unit_vectors(
    ra_deg: np.ndarray,
    dec_deg: np.ndarray,
) -> np.ndarray:
    """Converteix RA/Dec (graus) a vectors unitaris equatorials XYZ (float32).

    Convencions equatorials:
        X = cos(Dec) * cos(RA)
        Y = cos(Dec) * sin(RA)
        Z = sin(Dec)

    S'executa UNA VEGADA per versió de recurs.

    Returns:
        ndarray float32 [N, 3]
    """
    ra_rad = np.radians(np.asarray(ra_deg, dtype=np.float64))
    dec_rad = np.radians(np.asarray(dec_deg, dtype=np.float64))

    cos_dec = np.cos(dec_rad)
    x = (cos_dec * np.cos(ra_rad)).astype(np.float32)
    y = (cos_dec * np.sin(ra_rad)).astype(np.float32)
    z = np.sin(dec_rad).astype(np.float32)

    return np.column_stack((x, y, z))


# ─── Matriu equatorial → ENU ───────────────────────────────────────────

def equatorial_to_enu_matrix(
    latitude_rad: float,
    lst_rad: float,
) -> np.ndarray:
    """Calcula la matriu 3×3 de rotació equatorial→ENU.

    Paràmetres:
        latitude_rad: Latitud geodèsica de l'observador (radians).
        lst_rad: Temps sideral local (radians, angle horari del punt vernal).

    Convencions de sortida (ENU → Three.js):
        E = +X
        N = +Z (negatiu per a Three.js on -Z és nord, s'inverteix al frontend)
        U = +Y

    Retorna:
        ndarray float64 [3, 3] row-major.
    """
    sin_lat = math.sin(latitude_rad)
    cos_lat = math.cos(latitude_rad)
    sin_lst = math.sin(lst_rad)
    cos_lst = math.cos(lst_rad)

    # Rotació equatorial (RA,Dec) → horari (H,Dec) → ENU
    # H = LST - RA, per tant la rotació per LST s'aplica a l'eix Z equatorial.
    #
    # Matriu completa: R_lat · R_lst
    # On R_lst rota al voltant de l'eix polar Z equatorial per LST
    # i R_lat projecta des del pla equatorial al marc horitzontal.
    #
    # ENU des d'equatorial:
    # E =  -sin(LST)*x + cos(LST)*y
    # N = -sin(lat)*cos(LST)*x - sin(lat)*sin(LST)*y + cos(lat)*z
    # U =  cos(lat)*cos(LST)*x + cos(lat)*sin(LST)*y + sin(lat)*z

    matrix = np.array([
        [-sin_lst,             cos_lst,             0.0      ],
        [-sin_lat * cos_lst,  -sin_lat * sin_lst,   cos_lat  ],
        [ cos_lat * cos_lst,   cos_lat * sin_lst,   sin_lat  ],
    ], dtype=np.float64)

    return matrix


def enu_to_threejs_matrix(enu_matrix: np.ndarray) -> np.ndarray:
    """Converteix la matriu ENU a convencions Three.js.

    Three.js: +X=est, +Y=amunt, -Z=nord
    ENU:      E=fila0, N=fila1, U=fila2

    Sortida Three.js:
        fila 0 (X) = E  (fila 0 ENU)
        fila 1 (Y) = U  (fila 2 ENU)
        fila 2 (Z) = -N (negat de fila 1 ENU, perquè Three.js nord=-Z)
    """
    result = np.empty((3, 3), dtype=np.float64)
    result[0] = enu_matrix[0]    # X = Est
    result[1] = enu_matrix[2]    # Y = Amunt
    result[2] = -enu_matrix[1]   # Z = -Nord (Three.js: nord = -Z)
    return result


def compute_celestial_transform_matrix(
    latitude_deg: float,
    lst_deg: float,
) -> tuple[float, ...]:
    """Calcula la matriu completa equatorial→Three.js (9 floats row-major).

    Aquesta funció es crida quan canvia LST o latitud, NO per frame visual.
    """
    lat_rad = math.radians(latitude_deg)
    lst_rad = math.radians(lst_deg)
    enu = equatorial_to_enu_matrix(lat_rad, lst_rad)
    threejs = enu_to_threejs_matrix(enu)
    return tuple(float(v) for v in threejs.flatten())


# ─── BP-RP → RGB uint8 ────────────────────────────────────────────────

# LUT materialitzada un cop (referència: TerraLab/util/color.py)
_BP_RP_LUT: np.ndarray | None = None
_BP_RP_LUT_MIN = -0.5
_BP_RP_LUT_MAX = 2.5
_BP_RP_LUT_SIZE = 4097


def _bp_rp_formula_arrays(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Transformació piecewise de referència per materialitzar la LUT de color."""
    r = np.empty(arr.shape, dtype=np.uint8)
    g = np.empty(arr.shape, dtype=np.uint8)
    b = np.empty(arr.shape, dtype=np.uint8)

    m0 = arr <= 0.0
    m1 = (arr > 0.0) & (arr <= 0.5)
    m2 = (arr > 0.5) & (arr <= 1.0)
    m3 = (arr > 1.0) & (arr <= 1.6)
    m4 = arr > 1.6

    # Blau profund
    r[m0] = 175
    g[m0] = np.clip(205 + (arr[m0] * 36.0), 187, 223).astype(np.uint8)
    b[m0] = 255

    # Blau → blanc
    if np.any(m1):
        t = (arr[m1] - 0.0) / 0.5
        r[m1] = np.clip(175 + 60.0 * t, 0, 255).astype(np.uint8)
        g[m1] = np.clip(205 + 33.0 * t, 0, 255).astype(np.uint8)
        b[m1] = 255

    # Blanc → groc
    if np.any(m2):
        t = (arr[m2] - 0.5) / 0.5
        r[m2] = 255
        g[m2] = np.clip(238 + 6.0 * t, 0, 255).astype(np.uint8)
        b[m2] = np.clip(255 - 41.0 * t, 0, 255).astype(np.uint8)

    # Groc → taronja
    if np.any(m3):
        t = (arr[m3] - 1.0) / 0.6
        r[m3] = 255
        g[m3] = np.clip(244 - 32.0 * t, 0, 255).astype(np.uint8)
        b[m3] = np.clip(214 - 64.0 * t, 0, 255).astype(np.uint8)

    # Taronja → vermell
    if np.any(m4):
        t = np.clip((arr[m4] - 1.6) / 0.9, 0.0, 1.0)
        r[m4] = 255
        g[m4] = np.clip(212 - 38.0 * t, 0, 255).astype(np.uint8)
        b[m4] = np.clip(150 - 30.0 * t, 0, 255).astype(np.uint8)

    return r, g, b


def _ensure_lut() -> np.ndarray:
    """Materialitza la LUT de color BP-RP si no existeix."""
    global _BP_RP_LUT
    if _BP_RP_LUT is None:
        samples = np.linspace(
            _BP_RP_LUT_MIN,
            _BP_RP_LUT_MAX,
            _BP_RP_LUT_SIZE,
            dtype=np.float32,
        )
        r, g, b = _bp_rp_formula_arrays(samples)
        _BP_RP_LUT = np.stack((r, g, b), axis=1)
        _BP_RP_LUT.setflags(write=False)
    return _BP_RP_LUT


def bp_rp_to_rgb_uint8(bp_rp: np.ndarray) -> np.ndarray:
    """Converteix BP-RP a RGB uint8 [N, 3] via LUT.

    Fallback determinista per NaN/Inf: BP-RP=0.8 (blanc-groc neutre).
    S'executa UNA VEGADA per versió de recurs, NO per frame.
    """
    lut = _ensure_lut()

    arr = np.asarray(bp_rp, dtype=np.float32)
    arr = np.nan_to_num(
        arr,
        nan=0.8,
        posinf=_BP_RP_LUT_MAX,
        neginf=_BP_RP_LUT_MIN,
    )

    scale = (_BP_RP_LUT_SIZE - 1) / (_BP_RP_LUT_MAX - _BP_RP_LUT_MIN)
    indices = np.asarray(
        np.clip(
            np.rint((arr - _BP_RP_LUT_MIN) * scale),
            0,
            _BP_RP_LUT_SIZE - 1,
        ),
        dtype=np.int32,
    )

    # Preservar les fronteres de la fórmula piecewise
    mapped = _BP_RP_LUT_MIN + indices.astype(np.float32) / scale
    for boundary in (0.0, 0.5, 1.0, 1.6):
        indices += ((arr > boundary) & (mapped <= boundary)).astype(np.int32)
        indices -= ((arr <= boundary) & (mapped > boundary)).astype(np.int32)
    indices = np.clip(indices, 0, _BP_RP_LUT_SIZE - 1)

    return lut[indices]  # [N, 3] uint8


# ─── Deduplicació ──────────────────────────────────────────────────────

def deduplicate_positive_source_ids(
    source_id: np.ndarray,
) -> np.ndarray:
    """Retorna màscara booleana mantenint el primer (més brillant) per source_id positiu.

    Els IDs negatius/zero es conserven sempre (sintètics).
    """
    keep = np.ones(source_id.shape[0], dtype=bool)
    positive_mask = source_id > 0
    positive_positions = np.flatnonzero(positive_mask)

    if positive_positions.size > 0:
        _, first_indices = np.unique(
            source_id[positive_positions], return_index=True
        )
        positive_keep = np.zeros(positive_positions.size, dtype=bool)
        positive_keep[first_indices] = True
        keep[positive_positions] = positive_keep

    return keep
