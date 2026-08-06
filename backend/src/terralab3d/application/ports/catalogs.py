"""Ports d’accés a catàlegs propietat de la capa d’aplicació."""
from typing import Protocol, Sequence
from terralab3d.domain.deep_sky.models import DeepSkyObject
from terralab3d.domain.stars.models import StarCatalogQuery, StarRecord

class StarCatalogPort(Protocol):
    def query(self, query: StarCatalogQuery) -> Sequence[StarRecord]: ...
    def close(self) -> None: ...

class DeepSkyCatalogPort(Protocol):
    def all_objects(self) -> Sequence[DeepSkyObject]: ...
