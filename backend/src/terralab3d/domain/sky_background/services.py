"""Serveis de domini per al fons celeste."""
from typing import Protocol
from terralab3d.domain.atmosphere.models import AtmosphereParameters
from terralab3d.domain.climate.models import ClimateState
from terralab3d.domain.geometry import CartesianDirection
from terralab3d.domain.light_pollution.models import LightPollutionState
from .models import SkyBackgroundState

class SkyBackgroundModel(Protocol):
    """Combina resultats atmosfèrics, solars i de contaminació en un estat de cel."""
    def resolve(self, *, sun_direction: CartesianDirection, atmosphere: AtmosphereParameters, light_pollution: LightPollutionState, climate: ClimateState | None) -> SkyBackgroundState: ...
