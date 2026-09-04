"""Atomic renderer-neutral state for one interactive simulation instant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


TemporalAuthority = Literal["preview", "authoritative"]


@dataclass(frozen=True, slots=True)
class TemporalSceneState:
    generation_id: int
    simulation_time: datetime
    observer_generation: int
    authority: TemporalAuthority
    solar_system: Any
    sky_environment: Any
    lighting_environment: Any
    astronomical_event: Any

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.simulation_time.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        return {
            "generationId": self.generation_id,
            "simulationTime": timestamp,
            "observerGeneration": self.observer_generation,
            "authority": self.authority,
            "solarSystem": self.solar_system.to_dict(),
            "skyEnvironment": self.sky_environment.to_dict(),
            "lightingEnvironment": self.lighting_environment.to_dict(),
            "astronomicalEvent": self.astronomical_event.to_dict(),
        }
