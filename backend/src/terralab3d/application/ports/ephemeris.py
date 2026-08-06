"""Port d’accés a efemèrides."""
from datetime import datetime
from typing import Protocol, Sequence
from terralab3d.domain.observer.models import ObserverProfile
from terralab3d.domain.solar_system.models import ApparentBodyState

class EphemerisPort(Protocol):
    def apparent_bodies(self, instant_utc: datetime, observer: ObserverProfile) -> Sequence[ApparentBodyState]: ...
