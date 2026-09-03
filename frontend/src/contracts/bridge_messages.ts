/**
 * Typed bridge messages exchanged over the WebSocket between Python and the
 * Three.js frontend.  Every message carries a `type` discriminant so both
 * sides can switch on it safely.
 */

import type { SkyEnvironmentSnapshot } from "./sky_environment_contracts";
import type { LightingEnvironmentSnapshot } from "./lighting_environment_contracts";
import type {
  AstronomicalEventSearchResult,
  AstronomicalEventSnapshot,
  AngularSeparationResult,
} from "./astronomical_event_contracts";
import type {
  MoonSurfaceResourceDescriptor,
  PlanetTextureManifest,
  SatelliteCatalogManifest,
  SolarSystemSnapshot,
} from "./solar_system_contracts";
import type { TemporalSceneState } from "./temporal_scene_contracts";
import type {
  ResourceDescriptor,
  DownloadJobSnapshot,
  ResourceInstallState,
} from "./resource_manager_contracts";
import type {
  HorizonProfileSettingsMessage,
  HorizonStatusMessage,
} from "./horizon_contracts";

// ─── Frontend → Python ───────────────────────────────────────────────

export interface AstronomicalSearchRequestMessage {
  readonly type: "astronomical_search_request";
  readonly requestId: string;
  readonly generation: number;
  readonly query: string;
  readonly limit: number;
}


export interface FrontendReadyMessage {
  readonly type: "frontend_ready";
  readonly protocolVersion: 2;
}

export interface SetSurfaceModeMessage {
  readonly type: "set_surface_mode";
  readonly mode: string;
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

export interface RecalculateHorizonMessage {
  readonly type: "recalculate_horizon";
}

export interface CancelHorizonMessage {
  readonly type: "cancel_horizon";
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

export interface RequestEventSearchMessage {
  readonly type: "request_event_search";
  readonly requestId: string;
  readonly eventType: "solar" | "lunar";
  readonly startUtc: string;
  readonly endUtc: string;
}

export interface RequestApparentTrajectoryMessage {
  readonly type: "request_apparent_trajectory";
  readonly requestId: string;
  readonly bodyId: string;
  readonly startUtc: string;
  readonly endUtc: string;
  readonly sampleCount: number;
}

export interface RequestAngularSeparationMessage {
  readonly type: "request_angular_separation";
  readonly requestId: string;
  readonly bodyA: string;
  readonly bodyB: string;
  readonly utc: string;
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
  /** Local ENU velocity lets the backend lead a streaming terrain chunk. */
  readonly velocityEastMps: number;
  readonly velocityNorthMps: number;
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

export interface SurfaceProgressMessage {
  readonly type: "surface_progress";
  readonly tilesAvailable: number;
  readonly tilesLoaded: number;
}

export interface LandCoverLegendMessage {
  readonly type: "land_cover_legend";
  readonly legendId: string;
  readonly entries: Array<{
    classId: number;
    label: string;
    colorRgba: [number, number, number, number];
  }>;
}

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

// ─── Resource Manager (Pas 8.6, 9) ───────────────────────────────────

export interface RequestCatalogSnapshotMessage {
  readonly type: "request_catalog_snapshot";
}

export interface RequestResourceDownloadMessage {
  readonly type: "request_resource_download";
  readonly resourceId: string;
  readonly variantId: string;
}

export interface PauseDownloadMessage {
  readonly type: "pause_download";
  readonly resourceId: string;
  readonly variantId: string;
}

export interface CancelDownloadMessage {
  readonly type: "cancel_download";
  readonly resourceId: string;
  readonly variantId: string;
}

export interface DeleteResourceMessage {
  readonly type: "delete_resource";
  readonly resourceId: string;
  readonly variantId: string;
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
  readonly trajectoryGeometryBuildCount: number;
  readonly trajectoryMaterialBuildCount: number;
  readonly trajectoryResourceApplyCount: number;
  readonly trajectoryStaleResourceCount: number;
  readonly trajectoryBridgeBytes: number;
  readonly solarTotalityGeometryBuildCount: number;
  readonly solarTotalityMaterialBuildCount: number;
  readonly galacticGeometryBuildCount: number;
  readonly galacticMaterialBuildCount: number;
  readonly milkyWayTextureLoadCount: number;
  readonly planckTextureLoadCount: number;
  readonly galacticStaleTextureCount: number;
  readonly galacticTextureUploadBytes: number;
  readonly galacticActiveTextureCount: number;
  readonly gpuMemoryEstimateBytes: number;
  readonly moonGeometryBuildCount: number;
  readonly moonMaterialBuildCount: number;
  readonly moonAlbedoTextureLoadCount: number;
  readonly moonNormalTextureLoadCount: number;
  readonly moonTextureUploadBytes: number;
  readonly moonBridgeTextureBytes: 0;
  readonly sunLightBuildCount: number;
  readonly moonLightBuildCount: number;
  readonly diffuseLightBuildCount: number;
  readonly pbrMaterialBuildCount: number;
  readonly sunShadowUpdateCount: number;
  readonly moonShadowUpdateCount: number;
  readonly lightingSnapshotCount: number;
  readonly lightingStaleCount: number;
  readonly lightingBridgeBytes: number;
  readonly rendererRenderCalls: number;
  readonly rendererMemoryGeometries: number;
  readonly rendererMemoryTextures: number;
  readonly shadowMapEstimateBytes: number;
  readonly shadowOffFrameMsP50: number;
  readonly shadowOffFrameMsP95: number;
  readonly shadowMediumFrameMsP50: number;
  readonly shadowMediumFrameMsP95: number;
  readonly shadowHighFrameMsP50: number;
  readonly shadowHighFrameMsP95: number;
  readonly horizonUploadBytes?: number;
  readonly horizonTextureBuildCount?: number;
  readonly horizonGeometryBuildCount?: number;
  readonly horizonDrawCalls?: number;
  readonly horizonLookupCpuP50?: number;
  readonly horizonLookupCpuP95?: number;
}

export interface SetTimeRateMessage {
  readonly type: "set_time_rate";
  readonly rate: number;
}

export interface StartStarTrailsMessage {
  readonly type: "start_star_trails";
  readonly durationSeconds: number;
  readonly sampleIntervalSeconds: number;
  readonly magnitudeLimit: number;
  readonly playbackRate: number;
}

export interface PauseStarTrailsMessage {
  readonly type: "pause_star_trails";
}

export interface ResumeStarTrailsMessage {
  readonly type: "resume_star_trails";
}

export interface StopStarTrailsMessage {
  readonly type: "stop_star_trails";
}

export interface ClearStarTrailsMessage {
  readonly type: "clear_star_trails";
}

export type FrontendMessage =
  | FrontendReadyMessage
  | SetSurfaceModeMessage
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
  | RequestEventSearchMessage
  | RequestApparentTrajectoryMessage
  | RequestAngularSeparationMessage
  | RequestCatalogSnapshotMessage
  | RequestResourceDownloadMessage
  | PauseDownloadMessage
  | CancelDownloadMessage
  | DeleteResourceMessage
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
  | FrontendPerformanceMetricsMessage
  | AstronomicalSearchRequestMessage
  | StartStarTrailsMessage
  | PauseStarTrailsMessage
  | ResumeStarTrailsMessage
  | StopStarTrailsMessage
  | ClearStarTrailsMessage
  | HorizonProfileSettingsMessage
  | RecalculateHorizonMessage
  | CancelHorizonMessage;

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
  readonly elevation: number | null;
  readonly heightOffset: number;
  readonly effectiveHeight: number | null;
  readonly elevationSource: string;
  readonly navigation?: boolean;
}

export interface NavigationCoordinatesChangedMessage {
  readonly type: "navigation_coordinates_changed";
  readonly lat: number;
  readonly lon: number;
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
  readonly transitionMs?: number;
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

export interface LightingEnvironmentSnapshotMessage extends LightingEnvironmentSnapshot {
  readonly type: "lighting_environment_snapshot";
}

export type TemporalSceneStateMessage = TemporalSceneState & {
  readonly type: "temporal_scene_state";
};

export interface MoonSurfaceResourceMessage extends MoonSurfaceResourceDescriptor {
  readonly type: "moon_surface_resource";
}

export interface PlanetTextureManifestMessage extends PlanetTextureManifest {
  readonly type: "planet_texture_manifest";
}

export interface SolarSystemCatalogManifestMessage extends SatelliteCatalogManifest {
  readonly type: "solar_system_catalog_manifest";
}

// ─── Events astronòmics (Pas 8.5) ────────────────────────────────────

export interface AstronomicalEventSnapshotMessage extends AstronomicalEventSnapshot {
  readonly type: "astronomical_event_snapshot";
}

export interface EventSearchResultMessage extends AstronomicalEventSearchResult {
  readonly type: "event_search_result";
}

export interface AngularSeparationResultMessage extends AngularSeparationResult {
  readonly type: "angular_separation_result";
}

// ─── Gestió de Recursos (Pas 8.6, 9) ─────────────────────────────────

export interface ResourceCatalogSnapshotMessage {
  readonly type: "resource_catalog_snapshot";
  readonly descriptors: ResourceDescriptor[];
  readonly installedStates: Record<
    string,
    {
      status: ResourceInstallState;
      variantId: string | null;
      downloadedBytes: number;
      verifiedAt: string | null;
      error: string | null;
      manifestData: Record<string, string | number | boolean> | null;
    }
  >;
}

export interface DownloadJobSnapshotMessage extends DownloadJobSnapshot {
  readonly type: "download_job_snapshot";
}

// ─── Astronomical Search (Pas 12) ────────────────────────────────────

export interface AstronomicalSearchResultPayload {
  readonly targetRef: string;
  readonly kind: "star" | "body" | "deep_sky" | "coordinate";
  readonly displayName: string;
  readonly score: number;
  readonly availability: string;
  readonly coordinateSnapshot?: { raDeg: number; decDeg: number };
  readonly resourceId?: string;
  readonly matchedAlias?: string;
}

export interface AstronomicalSearchResultMessage {
  readonly type: "astronomical_search_result";
  readonly requestId: string;
  readonly generation: number;
  readonly status: "ok" | "stale" | "invalid" | "error";
  readonly results: AstronomicalSearchResultPayload[];
}

export interface StarTrailsSnapshotMessage {
  readonly type: "star_trails_snapshot";
  readonly sessionId: string;
  readonly sessionVersion: number;
  readonly state: string;
  readonly reason?: string;
  readonly accumulatedExposureSeconds: number;
  readonly durationSeconds: number;
  readonly playbackRate: number;
  readonly starCount: number;
  readonly segmentCount: number;
  readonly gpuBytes: number;
  readonly magnitudeLimit: number;
  readonly startUtcIso?: string;
}

// ─── Tipus Unió ──────────────────────────────────────────────────────

export type BackendMessage =
  | HandshakeAckMessage
  | SetCameraPoseMessage
  | FocusDirectionMessage
  | ShutdownRequestedMessage
  | ObserverLocationChangedMessage
  | NavigationCoordinatesChangedMessage
  | LocationErrorMessage
  | SimulationTimeSnapshotMessage
  | StarCatalogStatusMessage
  | CelestialFrameTransformMessage
  | StarPickResolvedMessage
  | SkyEnvironmentSnapshotMessage
  | SolarSystemSnapshotMessage
  | LightingEnvironmentSnapshotMessage
  | TemporalSceneStateMessage
  | MoonSurfaceResourceMessage
  | PlanetTextureManifestMessage
  | SolarSystemCatalogManifestMessage
  | AstronomicalEventSnapshotMessage
  | EventSearchResultMessage
  | AngularSeparationResultMessage
  | DownloadJobSnapshotMessage
  | ResourceCatalogSnapshotMessage
  | AstronomicalSearchResultMessage
  | StarTrailsSnapshotMessage
  | HorizonStatusMessage
  | SurfaceProgressMessage
  | LandCoverLegendMessage;

// ─── Union of all messages ───────────────────────────────────────────

export type BridgeMessage = FrontendMessage | BackendMessage;

