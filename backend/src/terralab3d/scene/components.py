"""Components renderer-neutral de l’escena retinguda."""
from dataclasses import dataclass
from terralab3d.domain.geometry import CartesianDirection, EquatorialCoordinate
from .ids import SceneResourceId

@dataclass(frozen=True, slots=True)
class TransformComponent:
    position_x: float
    position_y: float
    position_z: float
    rotation_x_rad: float
    rotation_y_rad: float
    rotation_z_rad: float
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0

@dataclass(frozen=True, slots=True)
class CameraComponent:
    forward: CartesianDirection
    up: CartesianDirection
    horizontal_fov_deg: float
    near_plane: float
    far_plane: float

@dataclass(frozen=True, slots=True)
class CelestialSphereComponent:
    sidereal_rotation_rad: float
    axial_tilt_rad: float

@dataclass(frozen=True, slots=True)
class SkyUniformComponent:
    sun_direction: CartesianDirection
    zenith_luminance: float
    horizon_luminance: float
    turbidity: float
    twilight_factor: float
    cloud_cover: float

@dataclass(frozen=True, slots=True)
class StarFieldComponent:
    catalog_resource: SceneResourceId
    magnitude_limit: float
    point_scale: float
    diffraction_threshold: float

@dataclass(frozen=True, slots=True)
class StarTrailComponent:
    trail_resource: SceneResourceId
    opacity: float

@dataclass(frozen=True, slots=True)
class CelestialBodyComponent:
    body_id: str
    direction: CartesianDirection
    angular_diameter_deg: float
    illuminated_fraction: float
    texture_resource: SceneResourceId | None

@dataclass(frozen=True, slots=True)
class TexturedDomeComponent:
    texture_resource: SceneResourceId
    opacity: float
    rotation_rad: float

@dataclass(frozen=True, slots=True)
class DeepSkyFieldComponent:
    instance_resource: SceneResourceId
    magnitude_limit: float

@dataclass(frozen=True, slots=True)
class HorizonComponent:
    profile_resource: SceneResourceId
    clipping_enabled: bool

@dataclass(frozen=True, slots=True)
class TerrainTileComponent:
    mesh_resource: SceneResourceId
    material_resource: SceneResourceId
    visible: bool

@dataclass(frozen=True, slots=True)
class WeatherComponent:
    cloud_resource: SceneResourceId | None
    precipitation_kind: str
    intensity: float

@dataclass(frozen=True, slots=True)
class ScopeComponent:
    center: EquatorialCoordinate
    width_deg: float
    height_deg: float
    shape: str

@dataclass(frozen=True, slots=True)
class MeasurementBatchComponent:
    geometry_resource: SceneResourceId
    selected_measurement_id: str | None

@dataclass(frozen=True, slots=True)
class ConstellationBatchComponent:
    geometry_resource: SceneResourceId
    label_resource: SceneResourceId | None

@dataclass(frozen=True, slots=True)
class OverlayBatchComponent:
    geometry_resource: SceneResourceId
    style_key: str

@dataclass(frozen=True, slots=True)
class PickableComponent:
    target_id: str
    target_kind: str
    priority: int
