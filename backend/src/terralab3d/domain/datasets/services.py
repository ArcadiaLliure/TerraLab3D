"""Serveis de domini per a datasets i validació."""
from typing import Protocol
from .models import DatasetInstallation, DatasetManifest

class DatasetValidationModel(Protocol):
    """Valida versió, checksum i compatibilitat d’una instal·lació."""
    def validate(self, manifest: DatasetManifest, installation: DatasetInstallation) -> DatasetInstallation: ...
