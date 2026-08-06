/**
 * Frontend entry point.
 *
 * Wires together:
 *   WebSocketBridge → CameraRigImpl → ThreeSceneHostImpl → RenderLoopImpl
 *   DiagnosticsOverlay for bridge status / FPS / session
 *
 * This module is the single bundle entry point compiled by esbuild.
 */

import { WebSocketBridge } from "./bridge/WebSocketBridge";
import type { BackendMessageListener } from "./bridge/WebSocketBridge";
import { CameraRigImpl } from "./view/three/CameraRigImpl";
import { RenderLoopImpl } from "./view/three/RenderLoopImpl";
import { ThreeSceneHostImpl } from "./view/three/ThreeSceneHostImpl";
import { DiagnosticsOverlay } from "./view/ui/DiagnosticsOverlay";

// ─── Bootstrap ───────────────────────────────────────────────────────

function main(): void {
  const container = document.getElementById("scene-container");
  if (!container) {
    console.error("[TerraLab3D] #scene-container not found");
    return;
  }

  // 1. Create subsystems
  const bridge = new WebSocketBridge();
  const sceneHost = new ThreeSceneHostImpl();
  const cameraRig = new CameraRigImpl(sceneHost.camera);
  const renderLoop = new RenderLoopImpl();
  const diagnostics = new DiagnosticsOverlay();

  // 2. Mount scene + UI
  sceneHost.mount(container);
  diagnostics.mount(container);
  cameraRig.attach(container);

  // Initial resize
  const rect = container.getBoundingClientRect();
  cameraRig.resize(rect.width, rect.height);

  // 3. Bridge ↔ Camera wiring
  cameraRig.onPoseChanged((pose) => {
    bridge.sendCameraChanged(
      pose.azimuthDeg,
      pose.altitudeDeg,
      pose.horizontalFovDeg,
      pose.rollDeg,
    );
  });

  const backendListener: BackendMessageListener = {
    onSetCameraPose(p) {
      cameraRig.animateTo(
        p.azimuthDeg,
        p.altitudeDeg,
        p.horizontalFovDeg,
        p.transitionMs ?? 600,
      );
    },
    onFocusDirection(f) {
      const currentPose = cameraRig.pose();
      cameraRig.animateTo(
        f.azimuthDeg,
        f.altitudeDeg,
        currentPose.horizontalFovDeg,
        f.transitionMs ?? 600,
      );
    },
    onShutdownRequested() {
      renderLoop.stop();
      cameraRig.detach();
      sceneHost.dispose();
      diagnostics.dispose();
      bridge.dispose();
    },
  };

  bridge.addMessageListener(backendListener);

  // 4. Bridge state → diagnostics
  bridge.addStateListener(diagnostics);
  bridge.addStateListener({
    onBridgeStateChanged(state) {
      if (state === "connected") {
        diagnostics.updateSession(bridge.sessionId);
      }
    },
  });

  // 5. Render loop
  let fpsUpdateAccum = 0;
  renderLoop.start((timestampMs: number) => {
    cameraRig.updateMatrices();
    sceneHost.render(timestampMs);

    // Update FPS display at ~1 Hz
    fpsUpdateAccum += 1;
    if (fpsUpdateAccum >= 30) {
      fpsUpdateAccum = 0;
      diagnostics.updateFps(renderLoop.fps);
    }
  });

  // 6. Resize handling
  const resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        sceneHost.resize(width, height);
        cameraRig.resize(width, height);
        bridge.sendViewportResized(width, height, window.devicePixelRatio);
      }
    }
  });
  resizeObserver.observe(container);

  // 7. Connect bridge (last step — everything is wired)
  bridge.connect();

  // 8. Before-unload cleanup
  window.addEventListener("beforeunload", () => {
    resizeObserver.disconnect();
    renderLoop.stop();
    cameraRig.detach();
    sceneHost.dispose();
    diagnostics.dispose();
    bridge.dispose();
  });
}

// Run when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", main);
} else {
  main();
}
