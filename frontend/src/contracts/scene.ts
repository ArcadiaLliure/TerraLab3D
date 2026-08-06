export type SceneEntityId = string;
export type SceneResourceId = string;
export type SceneGeneration = number;

export type ResourceKind =
  | "buffer"
  | "index_buffer"
  | "texture_2d"
  | "texture_cube"
  | "texture_array"
  | "font_atlas"
  | "material_parameters";

export type ResourceLifetime = "static" | "session" | "view" | "transient";

export interface SceneResourceDescriptor {
  readonly resourceId: SceneResourceId;
  readonly version: number;
  readonly kind: ResourceKind;
  readonly lifetime: ResourceLifetime;
  readonly ownerId: string;
  readonly contentKey: string;
  readonly byteLength: number;
  readonly dependencies: readonly SceneResourceId[];
}

export interface CameraComponentPayload {
  readonly forward: readonly [number, number, number];
  readonly up: readonly [number, number, number];
  readonly horizontalFovDeg: number;
  readonly nearPlane: number;
  readonly farPlane: number;
}

export interface CelestialSphereComponentPayload {
  readonly siderealRotationRad: number;
  readonly axialTiltRad: number;
}

export interface SkyUniformComponentPayload {
  readonly sunDirection: readonly [number, number, number];
  readonly zenithLuminance: number;
  readonly horizonLuminance: number;
  readonly turbidity: number;
  readonly twilightFactor: number;
  readonly cloudCover: number;
}

export interface StarFieldComponentPayload {
  readonly catalogResource: SceneResourceId;
  readonly magnitudeLimit: number;
  readonly pointScale: number;
  readonly diffractionThreshold: number;
}

export interface ResourceBackedComponentPayload {
  readonly resourceId: SceneResourceId;
  readonly opacity?: number;
  readonly visible?: boolean;
}

export interface TerrainTileComponentPayload {
  readonly meshResource: SceneResourceId;
  readonly materialResource: SceneResourceId;
  readonly visible: boolean;
}

export interface ScopeComponentPayload {
  readonly rightAscensionDeg: number;
  readonly declinationDeg: number;
  readonly widthDeg: number;
  readonly heightDeg: number;
  readonly shape: "circle" | "rectangle";
}

export interface PickableComponentPayload {
  readonly targetId: string;
  readonly targetKind: string;
  readonly priority: number;
}

export type ComponentEnvelope =
  | { readonly componentType: "camera"; readonly payloadVersion: 1; readonly payload: CameraComponentPayload }
  | { readonly componentType: "celestial_sphere"; readonly payloadVersion: 1; readonly payload: CelestialSphereComponentPayload }
  | { readonly componentType: "sky_uniform"; readonly payloadVersion: 1; readonly payload: SkyUniformComponentPayload }
  | { readonly componentType: "star_field"; readonly payloadVersion: 1; readonly payload: StarFieldComponentPayload }
  | { readonly componentType: "star_trails"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "galactic_dome"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "deep_sky_field"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "horizon"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "terrain_tile"; readonly payloadVersion: 1; readonly payload: TerrainTileComponentPayload }
  | { readonly componentType: "weather"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "scope"; readonly payloadVersion: 1; readonly payload: ScopeComponentPayload }
  | { readonly componentType: "measurements"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "constellations"; readonly payloadVersion: 1; readonly payload: ResourceBackedComponentPayload }
  | { readonly componentType: "pickable"; readonly payloadVersion: 1; readonly payload: PickableComponentPayload };

export interface SceneEntity {
  readonly entityId: SceneEntityId;
  readonly components: readonly ComponentEnvelope[];
}

export type SceneOperation =
  | { readonly op: "register_resource"; readonly descriptor: SceneResourceDescriptor }
  | { readonly op: "update_resource"; readonly descriptor: SceneResourceDescriptor }
  | { readonly op: "dispose_resource"; readonly resourceId: SceneResourceId; readonly expectedVersion: number }
  | { readonly op: "create_entity"; readonly entity: SceneEntity }
  | { readonly op: "replace_component"; readonly entityId: SceneEntityId; readonly component: ComponentEnvelope }
  | { readonly op: "remove_entity"; readonly entityId: SceneEntityId };

export interface SceneDelta {
  readonly baseGeneration: SceneGeneration;
  readonly generation: SceneGeneration;
  readonly operations: readonly SceneOperation[];
}
