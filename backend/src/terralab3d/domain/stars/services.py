"""Contractes de servei purs per a la capacitat estrelles."""


from typing import Protocol, Sequence
from .models import StarCatalogQuery, StarCatalogResource, StarRecord

class StarCatalogModel(Protocol):
    """Proporciona dades de catàleg tipades sense posseir emmagatzematge ni threads."""
    def select(self, records: Sequence[StarRecord], query: StarCatalogQuery) -> Sequence[StarRecord]: ...

class StarPhotometryModel(Protocol):
    """Resol visibilitat científica i intensitat aparent."""
    def apparent_intensity(self, *, magnitude: float, extinction: float, instrument_gain: float) -> float: ...

class StarResourceBuilder(Protocol):
    """Construeix o versiona descriptors persistents de recursos estel·lars."""
    def describe(self, records: Sequence[StarRecord], version: int) -> StarCatalogResource: ...
