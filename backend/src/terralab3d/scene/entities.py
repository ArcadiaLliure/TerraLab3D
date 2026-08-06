"""DTO d’entitats de l’escena retinguda."""
from dataclasses import dataclass
from typing import TypeAlias
from .components import (
    CameraComponent, CelestialBodyComponent, CelestialSphereComponent,
    ConstellationBatchComponent, DeepSkyFieldComponent, HorizonComponent,
    MeasurementBatchComponent, OverlayBatchComponent, PickableComponent,
    ScopeComponent, SkyUniformComponent, StarFieldComponent, StarTrailComponent,
    TerrainTileComponent, TexturedDomeComponent, TransformComponent, WeatherComponent,
)
from .ids import SceneEntityId

SceneComponent: TypeAlias = (
    TransformComponent | CameraComponent | CelestialSphereComponent |
    SkyUniformComponent | StarFieldComponent | StarTrailComponent |
    CelestialBodyComponent | TexturedDomeComponent | DeepSkyFieldComponent |
    HorizonComponent | TerrainTileComponent | WeatherComponent | ScopeComponent |
    MeasurementBatchComponent | ConstellationBatchComponent |
    OverlayBatchComponent | PickableComponent
)

@dataclass(frozen=True, slots=True)
class SceneEntity:
    entity_id: SceneEntityId
    components: tuple[SceneComponent, ...]
