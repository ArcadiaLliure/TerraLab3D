"""Scientific boundary for resolving renderer-neutral apparent positions."""

from datetime import datetime
from typing import Protocol

from terralab3d.domain.solar_system.models import ScientificObserver
from terralab3d.domain.visibility.models import ApparentPosition, ObservableObject


class ObservablePositionPort(Protocol):
    @property
    def generation(self) -> str: ...

    def position_at(
        self,
        observable: ObservableObject,
        instant_utc: datetime,
        observer: ScientificObserver,
    ) -> ApparentPosition: ...

