/**
 * WebSocket-based bridge connecting the Three.js frontend to the Python backend.
 *
 * Owns:
 * - WebSocket lifecycle (connect, reconnect, disconnect)
 * - Typed message serialisation/deserialisation
 * - Handshake protocol (frontend_ready → handshake_ack)
 * - Shutdown coordination
 * - Error display when the bridge drops
 */

import type {
  BackendMessage,
  CameraChangedMessage,
  FrontendMessage,
  HandshakeAckMessage,
  ViewportResizedMessage,
  SetObserverLocationMessage,
  NavigationModeChangedMessage,
  CameraPoseChangedMessage,
  CameraMotionStartedMessage,
  CameraMotionStoppedMessage,
  CameraResetCompletedMessage,
  FrontendPerformanceMetricsMessage,
} from "../contracts/bridge_messages";
import type { NavigationCameraPose, MotionState } from "../contracts/navigation";
import type { LightingEnvironmentSnapshot } from "../contracts/lighting_environment_contracts";
import type {
  HorizonProfileSettingsMessage,
  HorizonStatusMessage,
} from "../contracts/horizon_contracts";
import type {
  ApparentTrajectoryMetadata,
  AngularSeparationResult,
  AstronomicalEventSearchResult,
  AstronomicalEventSnapshot,
} from "../contracts/astronomical_event_contracts";
import type {
  MoonSurfaceResourceDescriptor,
  PlanetTextureManifest,
  SatelliteCatalogManifest,
  SolarSystemSnapshot,
} from "../contracts/solar_system_contracts";
import type {
  CalculateRefinementPlanMessage,
  CancelRefinementDownloadMessage,
  CancelRefinementQueryMessage,
  ConfirmRefinementDownloadMessage,
  QueryRefinementProductsMessage,
  RefinementCandidatesMessage,
  RefinementCoverageUpdatedMessage,
  RefinementDownloadProgressMessage,
  RefinementInstallationRemovedMessage,
  RefinementOperationErrorMessage,
  RefinementPlanSummaryMessage,
  RefinementWorkspaceSnapshotMessage,
  RemoveRefinementInstallationMessage,
  RequestRefinementWorkspaceMessage,
} from "../contracts/refinement_contracts";

export type BridgeState = "connecting" | "connected" | "disconnected" | "error";

export interface BridgeStateListener {
  onBridgeStateChanged(state: BridgeState, detail?: string): void;
}

export interface CameraPoseFromBackend {
  azimuthDeg: number;
  altitudeDeg: number;
  horizontalFovDeg: number;
  rollDeg: number;
  transitionMs?: number | undefined;
}

export interface FocusFromBackend {
  azimuthDeg: number;
  altitudeDeg: number;
  transitionMs?: number | undefined;
}

export interface BackendMessageListener {
  onSetCameraPose?(pose: CameraPoseFromBackend): void;
  onFocusDirection?(focus: FocusFromBackend): void;
  onShutdownRequested?(): void;
  onObserverLocationChanged?(
    lat: number,
    lon: number,
    elevation: number | null,
    heightOffset: number,
    effectiveHeight: number | null,
    elevationSource: string,
    navigation: boolean,
  ): void;
  onNavigationCoordinatesChanged?(lat: number, lon: number): void;
  onLocationError?(message: string): void;
  onSimulationTimeSnapshot?(
    currentTimeIso: string,
    julianDay: number,
    lstDeg: number,
    sunAltitudes: number[],
    isRealtime: boolean
  ): void;
  onStarCatalogStatus?(status: {
    gaiaAvailability: string;
    effectiveSource: string;
    generalStarCount: number;
    fallbackStarCount: number;
    deepResidentCount: number;
    errorMessage?: string;
  }): void;
  onCelestialFrameTransform?(generation: number, matrix3x3: number[]): void;
  onStarResourceReady?(metadata: any, bufferPayload: ArrayBuffer): void;
  onBinaryResourceReady?(metadata: any, bufferPayload: ArrayBuffer): void;
  onStarPickResolved?(msg: BackendMessage & { type: "star_pick_resolved" }): void;
  onSkyEnvironmentSnapshot?(snapshot: import("../contracts/sky_environment_contracts").SkyEnvironmentSnapshot): void;
  onSolarSystemSnapshot?(snapshot: SolarSystemSnapshot): void;
  onSurfaceProgress?(msg: any): void;
  onLandCoverLegend?(msg: any): void;
  onLightingEnvironmentSnapshot?(snapshot: LightingEnvironmentSnapshot): void;
  onMoonSurfaceResource?(resource: MoonSurfaceResourceDescriptor): void;
  onPlanetTextureManifest?(manifest: PlanetTextureManifest): void;
  onSolarSystemCatalogManifest?(manifest: SatelliteCatalogManifest): void;
  onAstronomicalEventSnapshot?(snapshot: AstronomicalEventSnapshot): void;
  onEventSearchResult?(result: AstronomicalEventSearchResult): void;
  onApparentTrajectoryResource?(metadata: ApparentTrajectoryMetadata, bufferPayload: ArrayBuffer): void;
  onAngularSeparationResult?(result: AngularSeparationResult): void;
  onResourceCatalogSnapshot?(msg: import("../contracts/bridge_messages").ResourceCatalogSnapshotMessage): void;
  onDownloadJobSnapshot?(msg: import("../contracts/bridge_messages").DownloadJobSnapshotMessage): void;
  onAstronomicalSearchResult?(msg: import("../contracts/bridge_messages").AstronomicalSearchResultMessage): void;
  onStarTrailsSnapshot?(snapshot: import("../contracts/bridge_messages").StarTrailsSnapshotMessage): void;
  onHorizonStatus?(status: HorizonStatusMessage): void;
  onOperationProgressed?(msg: import("../contracts/events").OperationProgressedEvent): void;
  onRefinementWorkspaceSnapshot?(msg: RefinementWorkspaceSnapshotMessage): void;
  onRefinementCandidates?(msg: RefinementCandidatesMessage): void;
  onRefinementPlanSummary?(msg: RefinementPlanSummaryMessage): void;
  onRefinementDownloadProgress?(msg: RefinementDownloadProgressMessage): void;
  onRefinementCoverageUpdated?(msg: RefinementCoverageUpdatedMessage): void;
  onRefinementInstallationRemoved?(msg: RefinementInstallationRemovedMessage): void;
  onRefinementOperationError?(msg: RefinementOperationErrorMessage): void;
}

export class WebSocketBridge {
  private ws: WebSocket | null = null;
  private _state: BridgeState = "disconnected";
  private _sessionId: string | null = null;
  private readonly stateListeners: Set<BridgeStateListener> = new Set();
  private readonly messageListeners: Set<BackendMessageListener> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _disposed = false;

  get state(): BridgeState {
    return this._state;
  }

  get sessionId(): string | null {
    return this._sessionId;
  }

  addStateListener(listener: BridgeStateListener): () => void {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  addMessageListener(listener: BackendMessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  connect(): void {
    if (this._disposed) return;
    this.setState("connecting");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(url);
      this.ws.binaryType = "arraybuffer";
    } catch {
      this.setState("error", "Failed to create WebSocket");
      return;
    }

    this.ws.onopen = () => {
      this.sendMessage({ type: "frontend_ready", protocolVersion: 2 });
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        if (event.data instanceof ArrayBuffer) {
          this.handleBinaryMessage(event.data);
        } else {
          const msg = JSON.parse(event.data as string) as BackendMessage;
          this.handleBackendMessage(msg);
        }
      } catch (err) {
        console.error("[Bridge] Failed to parse message:", err);
      }
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.ws = null;
      if (this._disposed) return;
      if (event.code === 4001) {
        this.setState("disconnected", "S'ha obert en una altra pestanya");
        return; // DO NOT reconnect
      }
      this.setState("disconnected", "Connection closed");
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws = null;
      if (this._disposed) return;
      this.setState("error", "WebSocket error");
    };
  }

  private handleBinaryMessage(arrayBuffer: ArrayBuffer): void {
    if (arrayBuffer.byteLength < 4) return;
    const view = new DataView(arrayBuffer);
    const headerLen = view.getUint32(0, true);
    if (arrayBuffer.byteLength < 4 + headerLen) return;

    const headerBytes = new Uint8Array(arrayBuffer, 4, headerLen);
    const decoder = new TextDecoder("utf-8");
    const headerJsonStr = decoder.decode(headerBytes);
    const metadata = JSON.parse(headerJsonStr);

    const payloadBuffer = arrayBuffer.slice(4 + headerLen);
    const isLandCover = metadata.role === "land_cover_tile";
    if (isLandCover) console.info("MGP: WebSocketBridge.handleBinaryMessage [INICI]");

    for (const l of this.messageListeners) {
      if (metadata.role === "apparent_trajectory") {
        l.onApparentTrajectoryResource?.(metadata as ApparentTrajectoryMetadata, payloadBuffer);
      }
      if (l.onBinaryResourceReady) l.onBinaryResourceReady(metadata, payloadBuffer);
      else l.onStarResourceReady?.(metadata, payloadBuffer);
    }
    if (isLandCover) console.info("MGP: WebSocketBridge.handleBinaryMessage [FI]");
  }

  sendCameraChanged(
    azimuthDeg: number,
    altitudeDeg: number,
    horizontalFovDeg: number,
    rollDeg: number,
  ): void {
    const msg: CameraChangedMessage = {
      type: "camera_changed",
      azimuthDeg,
      altitudeDeg,
      horizontalFovDeg,
      rollDeg,
    };
    this.sendMessage(msg);
  }

  sendViewportResized(
    widthPx: number,
    heightPx: number,
    devicePixelRatio: number,
  ): void {
    const msg: ViewportResizedMessage = {
      type: "viewport_resized",
      widthPx,
      heightPx,
      devicePixelRatio,
    };
    this.sendMessage(msg);
  }

  sendSetObserverLocation(lat: number, lon: number, extraHeight: number): void {
    const msg: SetObserverLocationMessage = {
      type: "set_observer_location",
      lat,
      lon,
      extraHeight,
    };
    this.sendMessage(msg);
  }

  sendHorizonSettings(settings: Omit<HorizonProfileSettingsMessage, "type">): void {
    this.sendMessage({ type: "set_horizon_settings", ...settings });
  }

  recalculateHorizon(): void {
    this.sendMessage({ type: "recalculate_horizon" });
  }

  cancelHorizon(): void {
    this.sendMessage({ type: "cancel_horizon" });
  }

  sendSurfaceMode(mode: string): void {
    console.info("MGP: WebSocketBridge.sendSurfaceMode [INICI]");
    this.sendMessage({ type: "set_surface_mode", mode });
    console.info("MGP: WebSocketBridge.sendSurfaceMode [FI]");
  }

  sendFrontendReady(): void {
    this.sendMessage({ type: "frontend_ready", protocolVersion: 2 });
  }

  private shutdownRequested = false;

  dispose(): void {
    this._disposed = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      // Send shutdown_complete before closing ONLY if the backend explicitly requested shutdown
      if (this.shutdownRequested) {
        this.sendMessage({ type: "shutdown_complete" });
      }
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.close();
      this.ws = null;
    }
    this.stateListeners.clear();
    this.messageListeners.clear();
  }

  // ─── Star Picking ──────────────────────────────────────────

  sendResolveStarPick(
    requestId: string,
    generation: number,
    resourceId: string,
    resourceVersion: string,
    catalogIndex: number,
    purpose: "select" | "hover",
  ): void {
    this.sendMessage({
      type: "resolve_star_pick",
      requestId,
      generation,
      resourceId,
      resourceVersion,
      catalogIndex,
      purpose,
    });
  }

  sendSetAtmosphereEnabled(enabled: boolean): void {
    this.sendMessage({ type: "set_atmosphere_enabled", enabled });
  }

  sendSetLightPollutionEnabled(enabled: boolean): void {
    this.sendMessage({ type: "set_light_pollution_enabled", enabled });
  }

  sendSetLightPollutionMode(mode: "automatic" | "bortle" | "magnitude"): void {
    this.sendMessage({ type: "set_light_pollution_mode", mode });
  }

  sendSetBortleClass(bortleClass: number): void {
    this.sendMessage({ type: "set_bortle_class", bortleClass });
  }

  sendSetManualMagnitudeLimit(magnitudeLimit: number): void {
    this.sendMessage({ type: "set_manual_magnitude_limit", magnitudeLimit });
  }

  // ─── Private ────────────────────────────────────────────────────────

  private handleBackendMessage(msg: BackendMessage): void {
    switch (msg.type) {
      case "handshake_ack": {
        const ack = msg as HandshakeAckMessage;
        this._sessionId = ack.sessionId;
        this.setState("connected");
        break;
      }
      case "set_camera_pose":
        for (const l of this.messageListeners) {
          l.onSetCameraPose?.({
            azimuthDeg: msg.azimuthDeg,
            altitudeDeg: msg.altitudeDeg,
            horizontalFovDeg: msg.horizontalFovDeg,
            rollDeg: msg.rollDeg,
            transitionMs: msg.transitionMs,
          });
        }
        break;
      case "focus_direction":
        for (const l of this.messageListeners) {
          l.onFocusDirection?.({
            azimuthDeg: msg.azimuthDeg,
            altitudeDeg: msg.altitudeDeg,
            transitionMs: msg.transitionMs,
          });
        }
        break;
      case "shutdown_requested":
        this.shutdownRequested = true;
        for (const l of this.messageListeners) {
          l.onShutdownRequested?.();
        }
        break;
      case "observer_location_changed":
        for (const l of this.messageListeners) {
          l.onObserverLocationChanged?.(
            msg.lat,
            msg.lon,
            msg.elevation,
            msg.heightOffset,
            msg.effectiveHeight,
            msg.elevationSource,
            msg.navigation === true,
          );
        }
        break;
      case "location_error":
        for (const l of this.messageListeners) {
          l.onLocationError?.(msg.message);
        }
        break;
      case "simulation_time_snapshot":
        for (const l of this.messageListeners) {
          l.onSimulationTimeSnapshot?.(
            msg.currentTimeIso,
            msg.julianDay,
            msg.lstDeg,
            [...msg.sunAltitudes],
            msg.isRealtime,
          );
        }
        break;
      case "star_catalog_status":
        for (const l of this.messageListeners) {
          l.onStarCatalogStatus?.(msg as any);
        }
        break;
      case "celestial_frame_transform":
        for (const l of this.messageListeners) {
          l.onCelestialFrameTransform?.(
            (msg as any).generation,
            [...(msg as any).matrix3x3],
          );
        }
        break;
      case "star_pick_resolved":
        for (const l of this.messageListeners) {
          l.onStarPickResolved?.(msg as any);
        }
        break;
      case "sky_environment_snapshot":
        for (const l of this.messageListeners) {
          l.onSkyEnvironmentSnapshot?.(msg as any);
        }
        break;
      case "solar_system_snapshot":
        for (const l of this.messageListeners) {
          l.onSolarSystemSnapshot?.(msg);
        }
        break;
      case "lighting_environment_snapshot":
        for (const l of this.messageListeners) {
          l.onLightingEnvironmentSnapshot?.(msg);
        }
        break;
      case "moon_surface_resource":
        for (const l of this.messageListeners) {
          l.onMoonSurfaceResource?.(msg);
        }
        break;
      case "planet_texture_manifest":
        for (const l of this.messageListeners) {
          l.onPlanetTextureManifest?.(msg);
        }
        break;
      case "solar_system_catalog_manifest":
        for (const l of this.messageListeners) {
          l.onSolarSystemCatalogManifest?.(msg);
        }
        break;
      case "astronomical_event_snapshot":
        for (const l of this.messageListeners) {
          l.onAstronomicalEventSnapshot?.(msg);
        }
        break;
      case "event_search_result":
        for (const l of this.messageListeners) {
          l.onEventSearchResult?.(msg);
        }
        break;
      case "angular_separation_result":
        for (const l of this.messageListeners) {
          l.onAngularSeparationResult?.(msg);
        }
        break;
      case "resource_catalog_snapshot":
        for (const l of this.messageListeners) {
          l.onResourceCatalogSnapshot?.(msg);
        }
        break;
      case "download_job_snapshot":
        for (const l of this.messageListeners) {
          l.onDownloadJobSnapshot?.(msg);
        }
        break;
      case "astronomical_search_result":
        for (const l of this.messageListeners) {
          l.onAstronomicalSearchResult?.(msg);
        }
        break;
      case "star_trails_snapshot":
        for (const l of this.messageListeners) {
          l.onStarTrailsSnapshot?.(msg as any);
        }
        break;
      case "horizon_status":
        for (const l of this.messageListeners) {
          l.onHorizonStatus?.(msg);
        }
        break;
      case "navigation_coordinates_changed":
        for (const l of this.messageListeners) {
          l.onNavigationCoordinatesChanged?.(msg.lat, msg.lon);
        }
        break;
      case "surface_progress":
        for (const l of this.messageListeners) {
          l.onSurfaceProgress?.(msg);
        }
        break;
      case "land_cover_legend":
        for (const l of this.messageListeners) {
          l.onLandCoverLegend?.(msg);
        }
        break;
      case "operation_progressed":
        for (const l of this.messageListeners) {
          l.onOperationProgressed?.(msg as any);
        }
        break;
      case "refinement_workspace_snapshot":
        for (const l of this.messageListeners) l.onRefinementWorkspaceSnapshot?.(msg);
        break;
      case "refinement_candidates":
        for (const l of this.messageListeners) l.onRefinementCandidates?.(msg);
        break;
      case "refinement_plan_summary":
        for (const l of this.messageListeners) l.onRefinementPlanSummary?.(msg);
        break;
      case "refinement_download_progress":
        for (const l of this.messageListeners) l.onRefinementDownloadProgress?.(msg);
        break;
      case "refinement_coverage_updated":
        for (const l of this.messageListeners) l.onRefinementCoverageUpdated?.(msg);
        break;
      case "refinement_installation_removed":
        for (const l of this.messageListeners) l.onRefinementInstallationRemoved?.(msg);
        break;
      case "refinement_operation_error":
        for (const l of this.messageListeners) l.onRefinementOperationError?.(msg);
        break;
      default:
        console.warn("[Bridge] Unknown message payload");
    }
  }

  public sendSetSimulationTime(currentTimeIso: string) {
    this.sendMessage({
      type: "set_simulation_time",
      currentTimeIso,
    });
  }

  public sendSetRealtimeMode(enabled: boolean): void {
    this.sendMessage({
      type: "set_realtime_mode",
      enabled
    });
  }

  public sendSetTimePlaying(enabled: boolean): void {
    this.sendMessage({
      type: "set_time_playing",
      enabled
    });
  }

  public sendSetTimeRate(rate: number): void {
    this.sendMessage({
      type: "set_time_rate",
      rate
    });
  }

  public sendTimelineDragStarted(): void {
    this.sendMessage({ type: "timeline_drag_started" });
  }

  public sendTimelineDragFinished(currentTimeIso?: string): void {
    const payload: import("../contracts/bridge_messages").TimelineDragFinishedMessage = currentTimeIso
      ? { type: "timeline_drag_finished", currentTimeIso }
      : { type: "timeline_drag_finished" };
    this.sendMessage(payload);
  }

  public sendRequestOffsetDay(offsetDays: number): void {
    this.sendMessage({
      type: "request_offset_day",
      offsetDays
    });
  }

  public setSatelliteSystems(systems: readonly string[]): void {
    this.sendMessage({ type: "set_satellite_systems", systems });
  }

  public requestSatelliteOrbit(bodyId: string, intervalDays = 30, sampleCount = 256): void {
    this.sendMessage({
      type: "request_satellite_orbit",
      bodyId,
      intervalDays,
      sampleCount,
    });
  }

  public requestEventSearch(
    requestId: string,
    eventType: "solar" | "lunar",
    startUtc: string,
    endUtc: string,
  ): void {
    this.sendMessage({ type: "request_event_search", requestId, eventType, startUtc, endUtc });
  }

  public requestApparentTrajectory(
    requestId: string,
    bodyId: string,
    startUtc: string,
    endUtc: string,
    sampleCount = 256,
  ): void {
    this.sendMessage({
      type: "request_apparent_trajectory",
      requestId,
      bodyId,
      startUtc,
      endUtc,
      sampleCount,
    });
  }

  public requestAngularSeparation(
    requestId: string,
    bodyA: string,
    bodyB: string,
    utc: string,
  ): void {
    this.sendMessage({ type: "request_angular_separation", requestId, bodyA, bodyB, utc });
  }

  // ─── Resource Manager (Pas 8.6, 9) ──────────────────────────────────

  public requestCatalogSnapshot(): void {
    this.sendMessage({ type: "request_catalog_snapshot" });
  }

  public requestRefinementWorkspace(message: RequestRefinementWorkspaceMessage): void {
    this.sendMessage(message);
  }

  public queryRefinementProducts(message: QueryRefinementProductsMessage): void {
    this.sendMessage(message);
  }

  public cancelRefinementQuery(message: CancelRefinementQueryMessage): void {
    this.sendMessage(message);
  }

  public calculateRefinementPlan(message: CalculateRefinementPlanMessage): void {
    this.sendMessage(message);
  }

  public confirmRefinementDownload(message: ConfirmRefinementDownloadMessage): void {
    this.sendMessage(message);
  }

  public cancelRefinementDownload(message: CancelRefinementDownloadMessage): void {
    this.sendMessage(message);
  }

  public removeRefinementInstallation(message: RemoveRefinementInstallationMessage): void {
    this.sendMessage(message);
  }

  // ─── Astronomical Search (Pas 12) ──────────────────────────────────

  public requestAstronomicalSearch(requestId: string, generation: number, query: string, limit = 20): void {
    this.sendMessage({
      type: "astronomical_search_request",
      requestId,
      generation,
      query,
      limit,
    });
  }

  public requestResourceDownload(resourceId: string, variantId: string): void {
    this.sendMessage({ type: "request_resource_download", resourceId, variantId });
  }

  public pauseDownload(resourceId: string, variantId: string): void {
    this.sendMessage({ type: "pause_download", resourceId, variantId });
  }

  public cancelDownload(resourceId: string, variantId: string): void {
    this.sendMessage({ type: "cancel_download", resourceId, variantId });
  }

  public deleteResource(resourceId: string, variantId: string): void {
    this.sendMessage({ type: "delete_resource", resourceId, variantId });
  }

  // ─── Navigation messages (Phase 3.5) ────────────────────────────

  public sendNavigationModeChanged(mode: "walk" | "flight"): void {
    const msg: NavigationModeChangedMessage = { type: "navigation_mode_changed", mode };
    this.sendMessage(msg);
  }

  public sendCameraPoseChanged(pose: NavigationCameraPose, motion: MotionState): void {
    const msg: CameraPoseChangedMessage = {
      type: "camera_pose_changed",
      positionEastM: pose.positionEastM,
      positionUpM: pose.positionUpM,
      positionNorthM: pose.positionNorthM,
      azimuthDeg: pose.azimuthDeg,
      altitudeDeg: pose.altitudeDeg,
      rollDeg: pose.rollDeg,
      fovDeg: pose.fovDeg,
      navigationMode: pose.navigationMode,
      speedMps: motion.speedMps,
      velocityEastMps: motion.velocityEast,
      velocityNorthMps: motion.velocityNorth,
    };
    this.sendMessage(msg);
  }

  public sendCameraMotionStarted(mode: "walk" | "flight"): void {
    const msg: CameraMotionStartedMessage = { type: "camera_motion_started", mode };
    this.sendMessage(msg);
  }

  public sendCameraMotionStopped(eastM: number, upM: number, northM: number): void {
    const msg: CameraMotionStoppedMessage = {
      type: "camera_motion_stopped",
      positionEastM: eastM,
      positionUpM: upM,
      positionNorthM: northM,
    };
    this.sendMessage(msg);
  }

  public sendCameraResetCompleted(): void {
    const msg: CameraResetCompletedMessage = { type: "camera_reset_completed" };
    this.sendMessage(msg);
  }

  public sendPerformanceMetrics(
    metrics: Omit<FrontendPerformanceMetricsMessage, "type">,
  ): void {
    this.sendMessage({ type: "frontend_performance_metrics", ...metrics });
  }

  public startStarTrails(
    durationSeconds: number,
    sampleIntervalSeconds: number,
    magnitudeLimit: number,
    playbackRate: number,
  ): void {
    try {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        console.warn("[Bridge] WebSocket no connectat per startStarTrails");
        return;
      }
      this.sendMessage({
        type: "start_star_trails",
        durationSeconds,
        sampleIntervalSeconds,
        magnitudeLimit,
        playbackRate,
      });
    } catch (err) {
      console.error("[Bridge] Error enviant start_star_trails:", err);
    }
  }

  public pauseStarTrails(): void {
    this.sendMessage({ type: "pause_star_trails" });
  }

  public resumeStarTrails(): void {
    this.sendMessage({ type: "resume_star_trails" });
  }

  public stopStarTrails(): void {
    this.sendMessage({ type: "stop_star_trails" });
  }

  public clearStarTrails(): void {
    this.sendMessage({ type: "clear_star_trails" });
  }

  private sendMessage(msg: FrontendMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private setState(state: BridgeState, detail?: string): void {
    this._state = state;
    for (const l of this.stateListeners) {
      l.onBridgeStateChanged(state, detail);
    }
  }

  private scheduleReconnect(): void {
    if (this._disposed) return;
    if (this.reconnectTimer !== null) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (!this._disposed) {
        this.connect();
      }
    }, 2000);
  }
}
