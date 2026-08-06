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
} from "../contracts/bridge_messages";

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
    } catch {
      this.setState("error", "Failed to create WebSocket");
      return;
    }

    this.ws.onopen = () => {
      this.sendMessage({ type: "frontend_ready", protocolVersion: 1 });
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as BackendMessage;
        this.handleBackendMessage(msg);
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

  dispose(): void {
    this._disposed = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      // Send shutdown_complete before closing if we were asked to shut down
      this.sendMessage({ type: "shutdown_complete" });
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
    }
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
