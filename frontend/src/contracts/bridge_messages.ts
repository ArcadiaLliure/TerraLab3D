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

export type FrontendMessage =
  | FrontendReadyMessage
  | CameraChangedMessage
  | ViewportResizedMessage
  | ShutdownCompleteMessage
  | BridgeErrorMessage
  | SetObserverLocationMessage;

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

export type BackendMessage =
  | HandshakeAckMessage
  | SetCameraPoseMessage
  | FocusDirectionMessage
  | ShutdownRequestedMessage
  | ObserverLocationChangedMessage
  | LocationErrorMessage;

// ─── Union of all messages ───────────────────────────────────────────

export type BridgeMessage = FrontendMessage | BackendMessage;
