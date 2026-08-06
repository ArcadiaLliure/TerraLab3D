"""Agregat immutable de la sessió completa de TerraLab3D."""
from dataclasses import dataclass
from terralab3d.domain.atmosphere.models import AtmosphereParameters
from terralab3d.domain.climate.models import ClimateState
from terralab3d.domain.constellations.models import EditableConstellation
from terralab3d.domain.deep_sky.models import DeepSkyObject
from terralab3d.domain.eclipses.models import EclipseInstantState
from terralab3d.domain.feedback.models import OperationStatus, UserFacingIssue
from terralab3d.domain.galactic.models import GalacticAppearance
from terralab3d.domain.horizon.models import HorizonProfile
from terralab3d.domain.imaging.models import ImagingSession
from terralab3d.domain.layers.models import LayerState
from terralab3d.domain.light_pollution.models import LightPollutionState
from terralab3d.domain.measurements.models import Measurement
from terralab3d.domain.navigation.models import CameraNavigationState
from terralab3d.domain.observer.models import ObserverProfile
from terralab3d.domain.optics.models import ExposureSettings, OpticalInstrument
from terralab3d.domain.resources.models import DatasetState
from terralab3d.domain.selection.models import SelectionState
from terralab3d.domain.sky_background.models import SkyBackgroundState
from terralab3d.domain.solar_system.models import ApparentBodyState
from terralab3d.domain.star_trails.models import StarTrailRequest
from terralab3d.domain.stars.models import StarCatalogResource
from terralab3d.domain.surface.models import SurfaceMaterialDescriptor
from terralab3d.domain.terrain.models import TerrainMeshResource
from terralab3d.domain.time.models import ClockState

@dataclass(frozen=True, slots=True)
class ApplicationSession:
    revision: int
    observer: ObserverProfile
    clock: ClockState
    camera: CameraNavigationState
    layers: LayerState
    atmosphere: AtmosphereParameters
    climate: ClimateState | None
    light_pollution: LightPollutionState
    sky_background: SkyBackgroundState
    selection: SelectionState
    instrument: OpticalInstrument | None
    exposure: ExposureSettings | None
    imaging: ImagingSession | None
    star_catalog: StarCatalogResource | None
    star_trails: StarTrailRequest | None
    solar_system_bodies: tuple[ApparentBodyState, ...]
    eclipse: EclipseInstantState | None
    galactic: GalacticAppearance | None
    deep_sky_objects: tuple[DeepSkyObject, ...]
    horizon: HorizonProfile | None
    terrain_meshes: tuple[TerrainMeshResource, ...]
    surface_materials: tuple[SurfaceMaterialDescriptor, ...]
    measurements: tuple[Measurement, ...]
    constellations: tuple[EditableConstellation, ...]
    datasets: tuple[DatasetState, ...]
    operations: tuple[OperationStatus, ...]
    issues: tuple[UserFacingIssue, ...]
