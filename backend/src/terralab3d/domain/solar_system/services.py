"""Contractes de servei purs per a la capacitat sistema solar."""


from datetime import datetime
from typing import Protocol, Sequence
from terralab3d.domain.observer.models import ObserverProfile
from .models import ApparentBodyState, EclipseState

class SolarSystemModel(Protocol):
    """Resol l’estat aparent dels cossos des d’efemèrides autoritatives."""
    def apparent_states(self, instant_utc: datetime, observer: ObserverProfile) -> Sequence[ApparentBodyState]: ...
    def eclipse_state(self, bodies: Sequence[ApparentBodyState]) -> EclipseState: ...
