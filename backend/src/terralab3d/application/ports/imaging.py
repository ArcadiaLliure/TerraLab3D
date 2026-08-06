"""Ports per exportar captures i productes de simulació fotogràfica."""
from typing import Protocol
from terralab3d.domain.imaging.models import ImagingSession

class ImagingExportPort(Protocol):
    def request_export(self, session: ImagingSession, destination: str) -> str: ...
