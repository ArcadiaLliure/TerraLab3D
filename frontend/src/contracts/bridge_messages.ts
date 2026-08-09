/**
 * Typed bridge messages exchanged over the WebSocket between Python and the
 * Three.js frontend.  Every message carries a `type` discriminant so both
 * sides can switch on it safely.
 */

import type { SkyEnvironmentSnapshot } from "./sky_environment_contracts";
import type {
  MoonSurfaceResourceDescriptor,
  PlanetTextureManifest,
  SatelliteCatalogManifest,
  SolarSystemSnapshot,
} from "./solar_system_contracts";

// ─── Frontend → Python ───────────────────────────────────────────────

export interface FrontendReadyMessage {
  readonly type: "frontend_ready";
  readonly protocolVersion: 2;
}

export interface CameraChangedMessage {
  readonly type: "camera_changed";
  readonly azimuthDeg: number;
  readonly altitudeDeg: number;
  readonly horizontalFovDeg: number;
  readonly rollDeg: number;
}

export interface ViewportResizedMessage {
  readonly type: "viewport_resized";
  readonly widthPx: number;
  readonly heightPx: number;
  readonly devicePixelRatio: number;
}

export interface ShutdownCompleteMessage {
  readonly type: "shutdown_complete";
}

export interface BridgeErrorMessage {
  readonly type: "bridge_error";
  readonly code: string;
  readonly message: string;
}

export interface SetObserverLocationMessage {
  readonly type: "set_observer_location";
  readonly lat: number;
  readonly lon: number;
  readonly extraHeight: number;
}

export interface SetSimulationTimeMessage {
  readonly type: "set_simulation_time";
  readonly currentTimeIso: string;
}

export interface SetRealtimeModeMessage {
  readonly type: "set_realtime_mode";
  readonly enabled: boolean;
}

export interface SetTimePlayingMessage {
  readonly type: "set_time_playing";
  readonly enabled: boolean;
}

export interface TimelineDragStartedMessage {
  readonly type: "timeline_drag_started";
}

export interface TimelineDragFinishedMessage {
  readonly type: "timeline_drag_finished";
  readonly currentTimeIso?: string;
}

export interface RequestOffsetDayMessage {
  readonly type: "request_offset_day";
  readonly offsetDays: number;
}

export interface SetSatelliteSystemsMessage {
  readonly type: "set_satellite_systems";
  readonly systems: readonly string[];
}

export interface RequestSatelliteOrbitMessage {
  readonly type: "request_satellite_orbit";
  readonly bodyId: string;
  readonly intervalDays: number;
  readonly sampleCount: number;
}

// ─── Navigation messages (Phase 3.5) ─────────────────────────────────

export interface NavigationModeChangedMessage {
  readonly type: "navigation_mode_changed";
  readonly mode: "walk" | "flight";
}

export interface CameraPoseChangedMessage {
  readonly type: "camera_pose_changed";
  readonly positionEastM: number;
  readonly positionUpM: number;
  readonly positionNorthM: number;
  readonly azimuthDeg: number;
  readonly altitudeDeg: number;
  readonly rollDeg: number;
  readonly fovDeg: number;
  readonly navigationMode: "walk" | "flight";
  readonly speedMps: number;
}

export interface CameraMotionStartedMessage {
  readonly type: "camera_motion_started";
  readonly mode: "walk" | "flight";
}

export interface CameraMotionStoppedMessage {
  readonly type: "camera_motion_stopped";
  readonly positionEastM: number;
  readonly positionUpM: number;
  readonly positionNorthM: number;
}

export interface CameraResetCompletedMessage {
  readonly type: "camera_reset_completed";
}

// ─── Star Picking messages (Pas 6) ───────────────────────────────────

export interface ResolveStarPickMessage {
  readonly type: "resolve_star_pick";
  readonly requestId: string;
  readonly generation: number;
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
  readonly purpose: "select" | "hover";
}

// ─── Cel i Atmosfera (Pas 7) ─────────────────────────────────────────

export interface SetAtmosphereEnabledMessage {
  readonly type: "set_atmosphere_enabled";
  readonly enabled: boolean;
}

export interface SetLightPollutionEnabledMessage {
  readonly type: "set_light_pollution_enabled";
  readonly enabled: boolean;
}

export interface SetLightPollutionModeMessage {
  readonly type: "set_light_pollution_mode";
  readonly mode: "automatic" | "bortle" | "magnitude";
}

export interface SetBortleClassMessage {
  readonly type: "set_bortle_class";
  readonly bortleClass: number;
}

export interface SetManualMagnitudeLimitMessage {
  readonly type: "set_manual_magnitude_limit";
  readonly magnitudeLimit: number;
}

export interface FrontendPerformanceMetricsMessage {
  readonly type: "frontend_performance_metrics";
  readonly frameMsP50: number;
  readonly frameMsP95: number;
  readonly frameSampleCount: number;
  readonly solarSystemEntityBuildCount: number;
  readonly solarBodyGeometryBuildCount: number;
  readonly solarBodyMaterialBuildCount: number;
  readonly solarSystemMaterialBuildCount: number;
  readonly solarSystemSnapshotApplyCount: number;
  readonly solarSystemStaleSnapshotCount: number;
  readonly solarSystemBridgeBytes: number;
  readonly planetTextureLoadCount: number;
  readonly planetTextureUploadBytes: number;
  readonly satelliteCatalogCount: number;
  readonly satelliteStateCountPerTick: number;
  readonly ringGeometryBuildCount: number;
  readonly ringMaterialBuildCount: number;
  readonly orbitGeometryBuildCount: number;
  readonly orbitBridgeBytes: number;
  readonly gpuMemoryEstimateBytes: number;
  readonly moonGeometryBuildCount: number;
  readonly moonMaterialBuildCount: number;
  readonly moonAlbedoTextureLoadCount: number;
  readonly moonNormalTextureLoadCount: number;
  readonly moonTextureUploadBytes: number;
  readonly moonBridgeTextureBytes: 0;
}

export interface SetTimeRateMessage {
  readonly type: "set_time_rate";
  readonly rate: number;
}

export type FrontendMessage =
  | FrontendReadyMessage
  | CameraChangedMessage
  | ViewportResizedMessage
  | ShutdownCompleteMessage
  | BridgeErrorMessage
  | SetObserverLocationMessage
  | SetSimulationTimeMessage
  | SetRealtimeModeMessage
  | SetTimePlayingMessage
  | SetTimeRateMessage
  | TimelineDragStartedMessage
  | TimelineDragFinishedMessage
  | RequestOffsetDayMessage
  | SetSatelliteSystemsMessage
  | RequestSatelliteOrbitMessage
  | NavigationModeChangedMessage
  | CameraPoseChangedMessage
  | CameraMotionStartedMessage
  | CameraMotionStoppedMessage
  | CameraResetCompletedMessage
  | ResolveStarPickMessage
  | SetAtmosphereEnabledMessage
  | SetLightPollutionEnabledMessage
  | SetLightPollutionModeMessage
  | SetBortleClassMessage
  | SetManualMagnitudeLimitMessage
  | FrontendPerformanceMetricsMessage;

// ─── Python → Frontend ───────────────────────────────────────────────

export interface HandshakeAckMessage {
  readonly type: "handshake_ack";
  readonly sessionId: string;
  readonly protocolVersion: 2;
  readonly capabilities: readonly string[];
}

export interface SetCameraPoseMessage {
  readonly type: "set_camera_pose";
  readonly azimuthDeg: number;
  readonly altitudeDeg: number;
  readonly horizontalFovDeg: number;
  readonly rollDeg: number;
  readonly transitionMs?: number;
}

export interface FocusDirectionMessage {
  readonly type: "focus_direction";
  readonly azimuthDeg: number;
  readonly altitudeDeg: number;
  readonly transitionMs?: number;
}

export interface ShutdownRequestedMessage {
  readonly type: "shutdown_requested";
}

export interface ObserverLocationChangedMessage {
  readonly type: "observer_location_changed";
  readonly lat: number;
  readonly lon: number;
  readonly elevation: number;
  readonly effectiveHeight: number;
  readonly elevationSource: string;
}

export interface SimulationTimeSnapshotMessage {
  readonly type: "simulation_time_snapshot";
  readonly currentTimeIso: string;
  readonly julianDay: number;
  readonly lstDeg: number;
  readonly sunAltitudes: readonly number[];
  readonly isRealtime: boolean;
}

export interface LocationErrorMessage {
  readonly type: "location_error";
  readonly message: string;
}

export interface StarCatalogStatusMessage {
  readonly type: "star_catalog_status";
  readonly gaiaAvailability: string;
  readonly effectiveSource: string;
  readonly generalStarCount: number;
  readonly fallbackStarCount: number;
  readonly deepResidentCount: number;
  readonly errorMessage?: string;
}

export interface CelestialFrameTransformMessage {
  readonly type: "celestial_frame_transform";
  readonly generation: number;
  readonly matrix3x3: readonly number[];
}

// ─── Star Picking resolved (Pas 6) ──────────────────────────────────

export interface StarPickResolvedPayloadStar {
  readonly kind: "star";
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
  readonly sourceId: string;
  readonly raDeg: number;
  readonly decDeg: number;
  readonly magnitude: number;
  readonly bpRp: number | null;
  readonly sourceRole: string;
}

export interface StarPickResolvedMessage {
  readonly type: "star_pick_resolved";
  readonly requestId: string;
  readonly generation: number;
  readonly status: "ok" | "stale" | "missing" | "invalid";
  readonly star?: StarPickResolvedPayloadStar;
}

// ─── Cel i Atmosfera (Pas 7) ─────────────────────────────────────────

export interface SkyEnvironmentSnapshotMessage extends SkyEnvironmentSnapshot {
  readonly type: "sky_environment_snapshot";
}

export interface SolarSystemSnapshotMessage extends SolarSystemSnapshot {
  readonly type: "solar_system_snapshot";
}

export interface MoonSurfaceResourceMessage extends MoonSurfaceResourceDescriptor {
  readonly type: "moon_surface_resource";
}

export interface PlanetTextureManifestMessage extends PlanetTextureManifest {
  readonly type: "planet_texture_manifest";
}

export interface SolarSystemCatalogManifestMessage extends SatelliteCatalogManifest {
  readonly type: "solar_system_catalog_manifest";
}

export type BackendMessage =
  | HandshakeAckMessage
  | SetCameraPoseMessage
  | FocusDirectionMessage
  | ShutdownRequestedMessage
  | ObserverLocationChangedMessage
  | LocationErrorMessage
  | SimulationTimeSnapshotMessage
  | StarCatalogStatusMessage
  | CelestialFrameTransformMessage
  | StarPickResolvedMessage
  | SkyEnvironmentSnapshotMessage
  | SolarSystemSnapshotMessage
  | MoonSurfaceResourceMessage
  | PlanetTextureManifestMessage
  | SolarSystemCatalogManifestMessage;

// ─── Union of all messages ───────────────────────────────────────────

export type BridgeMessage = FrontendMessage | BackendMessage;
