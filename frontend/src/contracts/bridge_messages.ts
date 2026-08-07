/**
 * Typed bridge messages exchanged over the WebSocket between Python and the
 * Three.js frontend.  Every message carries a `type` discriminant so both
 * sides can switch on it safely.
 */

// ─── Frontend → Python ───────────────────────────────────────────────

export interface FrontendReadyMessage {
  readonly type: "frontend_ready";
  readonly protocolVersion: 1;
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

export type FrontendMessage =
  | FrontendReadyMessage
  | CameraChangedMessage
  | ViewportResizedMessage
  | ShutdownCompleteMessage
  | BridgeErrorMessage
  | SetObserverLocationMessage
  | NavigationModeChangedMessage
  | CameraPoseChangedMessage
  | CameraMotionStartedMessage
  | CameraMotionStoppedMessage
  | CameraResetCompletedMessage;

// ─── Python → Frontend ───────────────────────────────────────────────

export interface HandshakeAckMessage {
  readonly type: "handshake_ack";
  readonly sessionId: string;
  readonly protocolVersion: 1;
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

export type BackendMessage =
  | HandshakeAckMessage
  | SetCameraPoseMessage
  | FocusDirectionMessage
  | ShutdownRequestedMessage
  | ObserverLocationChangedMessage
  | LocationErrorMessage
  | SimulationTimeSnapshotMessage
  | StarCatalogStatusMessage
  | CelestialFrameTransformMessage;

// ─── Union of all messages ───────────────────────────────────────────

export type BridgeMessage = FrontendMessage | BackendMessage;
