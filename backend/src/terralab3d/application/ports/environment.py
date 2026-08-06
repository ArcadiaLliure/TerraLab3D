"""Ports de dades meteorològiques i contaminació lumínica."""
from datetime import datetime
from typing import Protocol
from terralab3d.domain.climate.models import ClimateState
from terralab3d.domain.light_pollution.models import LightPollutionState
from terralab3d.domain.observer.models import GeoLocation

class WeatherPort(Protocol):
    def climate(self, location: GeoLocation, instant_utc: datetime) -> ClimateState: ...

class LightPollutionDataPort(Protocol):
    def estimate(self, location: GeoLocation) -> LightPollutionState: ...
