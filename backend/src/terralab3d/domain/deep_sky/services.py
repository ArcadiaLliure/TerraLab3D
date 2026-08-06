"""Contractes de servei purs per a la capacitat cel profund."""


from typing import Protocol, Sequence
from .models import DeepSkyObject

class DeepSkyVisibilityModel(Protocol):
    """Selecciona objectes de cel profund des d’entrades de visibilitat científica."""
    def visible_objects(self, objects: Sequence[DeepSkyObject], *, magnitude_limit: float, extinction: float) -> Sequence[DeepSkyObject]: ...
