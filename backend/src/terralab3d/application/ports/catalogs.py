"""Ports d’accés a catàlegs propietat de la capa d’aplicació."""
from typing import Protocol, Sequence, Any
from terralab3d.domain.deep_sky.models import DeepSkyObject
from terralab3d.domain.stars.models import StarCatalogQuery, StarRecord

class StarCatalogPort(Protocol):
    def query(self, query: StarCatalogQuery) -> Sequence[StarRecord]: ...
    def close(self) -> None: ...

class DeepSkyCatalogPort(Protocol):
    def load_index(self) -> tuple[dict[str, Any], bytes] | None: ...
