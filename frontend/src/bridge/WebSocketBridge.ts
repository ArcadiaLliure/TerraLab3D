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
} from "../contracts/bridge_messages";
import type { NavigationCameraPose, MotionState } from "../contracts/navigation";

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
  onObserverLocationChanged?(lat: number, lon: number, elevation: number, effectiveHeight: number, elevationSource: string): void;
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
      this.sendMessage({ type: "frontend_ready", protocolVersion: 1 });
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

    this.ws.onclose = () => {
      if (this._disposed) return;
      this.setState("disconnected", "Connection closed");
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
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

    for (const l of this.messageListeners) {
      l.onStarResourceReady?.(metadata, payloadBuffer);
    }
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
            msg.effectiveHeight,
            msg.elevationSource,
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
    }
  }

  public sendSetSimulationTime(currentTimeIso: string): void {
    this.sendMessage({
      type: "set_simulation_time",
      currentTimeIso
    } as any);
  }

  public sendSetRealtimeMode(enabled: boolean): void {
    this.sendMessage({
      type: "set_realtime_mode",
      enabled
    } as any);
  }

  public sendTimelineDragStarted(): void {
    this.sendMessage({ type: "timeline_drag_started" } as any);
  }

  public sendTimelineDragFinished(currentTimeIso?: string): void {
    const payload: any = { type: "timeline_drag_finished" };
    if (currentTimeIso) payload.currentTimeIso = currentTimeIso;
    this.sendMessage(payload);
  }

  public sendRequestOffsetDay(offsetDays: number): void {
    this.sendMessage({
      type: "request_offset_day",
      offsetDays
    } as any);
  }

  // ─── Navigation messages (Phase 3.5) ────────────────────────────

  public sendNavigationModeChanged(mode: "walk" | "flight"): void {
    const msg: NavigationModeChangedMessage = { type: "navigation_mode_changed", mode };
    this.sendMessage(msg);
  }

  public sendCameraPoseChanged(pose: NavigationCameraPose, speedMps: number): void {
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
      speedMps,
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
