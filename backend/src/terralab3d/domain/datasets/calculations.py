"""Contractes de càlcul científic pur per a datasets, descàrregues i validació."""

from typing import Protocol
from terralab3d.domain.datasets.models import DatasetManifest

class DatasetIntegrityCalculator(Protocol):
    """Defineix els càlculs purs de datasets, descàrregues i validació sense I/O ni renderitzat."""
    def checksum_matches(self, manifest: DatasetManifest, observed_checksum: str) -> bool: ...
    def compatible(self, manifest: DatasetManifest, application_version: str) -> bool: ...
