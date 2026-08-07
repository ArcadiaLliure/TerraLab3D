"""Models de domini tipats per a la capacitat estrelles.

Inclou enumeracions d'estat Gaia, rols de recurs, descriptors
versionats i el batch immutable de catàleg.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import ResourceId, StarId


# ─── Enumeracions ─────────────────────────────────────────────────────

class GaiaAvailability(str, Enum):
    """Estat de disponibilitat del catàleg Gaia."""
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    MANIFEST_MISSING = "manifest_missing"
    MANIFEST_INVALID = "manifest_invalid"
    AVAILABLE = "available"
    LOADING = "loading"
    READY = "ready"
    PARTIAL = "partial"
    ERROR = "error"


class StarResourceRole(str, Enum):
    """Rol d'un recurs estel·lar dins del camp."""
    GENERAL = "general"
    FALLBACK = "fallback"
    SUPPLEMENT = "supplement"
    DEEP_TILE = "deep_tile"


class StarResourceLifecycle(str, Enum):
    """Cicle de vida d'un recurs estel·lar."""
    UNREGISTERED = "unregistered"
    LOADING = "loading"
    CPU_READY = "cpu_ready"
    TRANSFERRING = "transferring"
    GPU_READY = "gpu_ready"
    RESIDENT = "resident"
    EVICTING = "evicting"
    DISPOSED = "disposed"
    ERROR = "error"


# ─── Records ──────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class StarRecord:
    star_id: StarId
    coordinate: EquatorialCoordinate
    magnitude: float
    color_index: float | None


@dataclass(frozen=True, slots=True)
class StarCatalogQuery:
    center: EquatorialCoordinate | None
    radius_deg: float | None
    magnitude_limit: float


# ─── Descriptors de recurs ────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class StarResourceDescriptor:
    """Descriptor versionat d'un recurs estel·lar."""
    resource_id: str
    version: str
    owner: str
    star_count: int
    byte_length: int
    role: StarResourceRole
    content_hash: str = ""


@dataclass(frozen=True, slots=True)
class StarCatalogResource:
    """Recurs complet amb claus de buffer."""
    resource_id: ResourceId
    version: int
    star_count: int
    position_buffer_key: str
    magnitude_buffer_key: str
    color_buffer_key: str
    identifier_buffer_key: str


# ─── Transformació celeste ────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class CelestialFrameTransform:
    """Transformació equatorial→ENU. Python la calcula; frontend l'aplica."""
    generation: int
    matrix_3x3: tuple[float, ...]  # 9 floats, row-major

    def __post_init__(self) -> None:
        if len(self.matrix_3x3) != 9:
            raise ValueError("matrix_3x3 ha de tenir exactament 9 elements")


# ─── Batch immutable ──────────────────────────────────────────────────

@dataclass(frozen=True)
class StarBatch:
    """Chunk immutable de catàleg; el color es deriva del BP-RP."""

    ra: np.ndarray       # float64
    dec: np.ndarray      # float64
    mag: np.ndarray      # float32
    bp_rp: np.ndarray    # float32
    source_id: np.ndarray  # int64

    def __post_init__(self) -> None:
        arrays = (
            np.asarray(self.ra, dtype=np.float64),
            np.asarray(self.dec, dtype=np.float64),
            np.asarray(self.mag, dtype=np.float32),
            np.asarray(self.bp_rp, dtype=np.float32),
            np.asarray(self.source_id, dtype=np.int64),
        )
        size = arrays[0].size
        for name, array in zip(
            ("ra", "dec", "mag", "bp_rp", "source_id"), arrays
        ):
            if array.ndim != 1 or array.size != size:
                raise ValueError(
                    f"Les columnes del batch han d'estar alineades: "
                    f"{name} té mida {array.size}, esperada {size}"
                )
            array.setflags(write=False)
            object.__setattr__(self, name, array)

    def __len__(self) -> int:
        return int(self.ra.size)

    @property
    def nbytes(self) -> int:
        return int(
            self.ra.nbytes
            + self.dec.nbytes
            + self.mag.nbytes
            + self.bp_rp.nbytes
            + self.source_id.nbytes
        )


# ─── Estat del catàleg per UI ─────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class StarCatalogStatus:
    """Estat publicable del catàleg estel·lar per a la UI."""
    gaia_availability: GaiaAvailability
    effective_source: str  # "gaia", "fallback", "partial"
    general_star_count: int
    fallback_star_count: int
    deep_resident_count: int
    error_message: str = ""
