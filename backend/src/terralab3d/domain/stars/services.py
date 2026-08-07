"""Contractes de servei purs per a la capacitat estrelles.

Defineix el port de catàleg (StarCatalogPort) desacoblat
de HEALPix/NPZ/manifests/paths.
"""

from __future__ import annotations

from typing import Protocol, Sequence, Iterator
from .models import (
    StarBatch,
    StarCatalogQuery,
    StarCatalogResource,
    StarCatalogStatus,
    StarRecord,
    GaiaAvailability,
)


class StarCatalogPort(Protocol):
    """Port de catàleg estel·lar. Desacoblat de format/path concrets."""

    def get_availability(self) -> GaiaAvailability:
        """Retorna l'estat de disponibilitat del catàleg."""
        ...

    def load_general_catalog(self, *, mag_limit: float = 8.0) -> StarBatch | None:
        """Carrega el catàleg general (full-sky brillant/moderat)."""
        ...

    def load_fallback_catalog(self) -> StarBatch | None:
        """Carrega el catàleg fallback inclòs."""
        ...

    def query_cone(
        self,
        ra_deg: float,
        dec_deg: float,
        radius_deg: float,
        mag_limit: float,
        *,
        max_batch_rows: int = 1_000_000,
    ) -> Iterator[StarBatch]:
        """Consulta de con out-of-core amb batches."""
        ...

    def close(self) -> None:
        """Tanca stores, memmaps i recursos."""
        ...


class StarCatalogModel(Protocol):
    """Proporciona dades de catàleg tipades sense posseir emmagatzematge ni threads."""
    def select(self, records: Sequence[StarRecord], query: StarCatalogQuery) -> Sequence[StarRecord]: ...


class StarPhotometryModel(Protocol):
    """Resol visibilitat científica i intensitat aparent."""
    def apparent_intensity(self, *, magnitude: float, extinction: float, instrument_gain: float) -> float: ...


class StarResourceBuilder(Protocol):
    """Construeix o versiona descriptors persistents de recursos estel·lars."""
    def describe(self, records: Sequence[StarRecord], version: int) -> StarCatalogResource: ...
