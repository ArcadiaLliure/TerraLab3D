"""Comandes tipades acceptades per la capa d’aplicació de TerraLab3D."""
from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.layers.models import LayerId
from terralab3d.domain.measurements.models import MeasurementKind
from terralab3d.domain.navigation.models import CameraPose
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.optics.models import ExposureSettings, FramingShape, OpticalInstrument
from terralab3d.domain.selection.models import PickResult
from terralab3d.domain.star_trails.models import StarTrailRequest

@dataclass(frozen=True, slots=True)
class SetObserverLocation:
    location: GeoLocation
    height_offset_m: float

@dataclass(frozen=True, slots=True)
class SetSimulationTime:
    instant_utc: datetime

@dataclass(frozen=True, slots=True)
class SetTimeRate:
    rate: float

@dataclass(frozen=True, slots=True)
class SetRealtimeMode:
    enabled: bool

@dataclass(frozen=True, slots=True)
class SetCameraPose:
    pose: CameraPose

@dataclass(frozen=True, slots=True)
class FocusCoordinate:
    coordinate: EquatorialCoordinate

@dataclass(frozen=True, slots=True)
class SetLayerVisibility:
    layer_id: LayerId
    visible: bool

@dataclass(frozen=True, slots=True)
class ConfigureOptics:
    instrument: OpticalInstrument
    exposure: ExposureSettings
    framing_shape: FramingShape
    aspect_ratio_override: float | None

@dataclass(frozen=True, slots=True)
class StartMeasurement:
    kind: MeasurementKind

@dataclass(frozen=True, slots=True)
class ApplyPickResult:
    result: PickResult

@dataclass(frozen=True, slots=True)
class SearchAstronomicalTarget:
    query_text: str

@dataclass(frozen=True, slots=True)
class StartStarTrails:
    request: StarTrailRequest

@dataclass(frozen=True, slots=True)
class StopStarTrails:
    pass

@dataclass(frozen=True, slots=True)
class LoadDataset:
    dataset_id: str

@dataclass(frozen=True, slots=True)
class CancelOperation:
    operation_id: str

ApplicationCommand: TypeAlias = (
    SetObserverLocation | SetSimulationTime | SetTimeRate | SetRealtimeMode |
    SetCameraPose | FocusCoordinate | SetLayerVisibility | ConfigureOptics |
    StartMeasurement | ApplyPickResult | SearchAstronomicalTarget |
    StartStarTrails | StopStarTrails | LoadDataset | CancelOperation
)
