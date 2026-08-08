/**
 * Frontend entry point.
 *
 * Wires together:
 *   WebSocketBridge → CameraRigImpl → ThreeSceneHostImpl → RenderLoopImpl
 *   NavigationWorld → TerrainSampler → GroundFollower → CameraRigImpl
 *   DiagnosticsOverlay for bridge status / FPS / session
 *   Phase 4: HorizontalGrid, CelestialLabels, CelestialEquator, AstronomicalHUD
 *
 * This module is the single bundle entry point compiled by esbuild.
 */

import { WebSocketBridge } from "./bridge/WebSocketBridge";
import type { BackendMessageListener } from "./bridge/WebSocketBridge";
import { CameraRigImpl } from "./view/three/CameraRigImpl";
import { RenderLoopImpl } from "./view/three/RenderLoopImpl";
import { ThreeSceneHostImpl } from "./view/three/ThreeSceneHostImpl";
import { AtmosphereRenderer } from "./view/three/AtmosphereRenderer";
import type { OverlayVisibility } from "./view/three/ThreeSceneHostImpl";
import { DiagnosticsOverlay } from "./view/ui/DiagnosticsOverlay";
import { NavigationWorld } from "./view/three/terrain/NavigationWorld";
import { GroundFollower } from "./view/three/terrain/GroundFollower";

import { LocationPage } from "./view/ui/drawer_pages/LocationPage";
import { SkyPage } from "./view/ui/drawer_pages/SkyPage";
import { EarthPage } from "./view/ui/drawer_pages/EarthPage";
import { ToolsPage } from "./view/ui/drawer_pages/ToolsPage";
import { LocationHUD } from "./view/ui/panels/LocationHUD";
import { Shell } from "./view/ui/Shell";
import { TimeBar } from "./view/ui/components/TimeBar";

// ─── Picking (Pas 6) ─────────────────────────────────────────────────
import { CelestialTransformState } from "./view/three/CelestialTransformState";
import { PointerGestureRouter } from "./view/three/picking/PointerGestureRouter";
import { StarPickProvider } from "./view/three/picking/StarPickProvider";
import { SolarSystemPickProvider } from "./view/three/picking/SolarSystemPickProvider";
import { CelestialPickProvider } from "./view/three/picking/CelestialPickProvider";
import { ScenePickingController } from "./view/three/picking/ScenePickingController";

// ─── Bootstrap ───────────────────────────────────────────────────────

function main(): void {
  console.info(`[TerraLab3D] main() iniciat a ${new Date().toISOString()}`);
  const container = document.getElementById("scene-container");
  if (!container) {
    console.error("[TerraLab3D] #scene-container not found");
    return;
  }

  // 1. Create subsystems and connect bridge immediately (parallel with 3D/UI setup)
  const bridge = new WebSocketBridge();
  bridge.connect();
  const sceneHost = new ThreeSceneHostImpl();
  const cameraRig = new CameraRigImpl(sceneHost.camera);
  const renderLoop = new RenderLoopImpl();
  const diagnostics = new DiagnosticsOverlay();

  // Phase 3.5: Navigation world and terrain
  const navigationWorld = new NavigationWorld();
  const groundFollower = new GroundFollower();

  const shell = new Shell({
    onSetRealtime: (enabled) => bridge.sendSetRealtimeMode(enabled),
  });
  shell.mount(container);

  // 1.5. Sky environment
  const atmosphereRenderer = new AtmosphereRenderer(sceneHost.getCelestialRoot());
  // Default to true, SkyPage will manage this later
  atmosphereRenderer.setPureColors(false);

  // 2. Prepare UI pages
  const locationPage = new LocationPage({
    onRelocate: (lat, lon, height) => bridge.sendSetObserverLocation(lat, lon, height),
    onSetRealtime: (enabled) => bridge.sendSetRealtimeMode(enabled),
    onOffsetDay: (offsetDays) => bridge.sendRequestOffsetDay(offsetDays),
    onSetDate: (dateIso) => bridge.sendSetSimulationTime(dateIso),
    onToggleNavigationMode: () => cameraRig.toggleNavigationMode(),
    onResetToOrigin: () => cameraRig.resetToOrigin(),
    // Phase 4: Overlay toggles
    onOverlayToggle: (key, visible) => {
      sceneHost.setOverlayVisibility(key as keyof OverlayVisibility, visible);
    },
    onHudToggle: (visible) => {
      locationHUD.setVisible(visible);
    },
  });
  const locContainer = shell.getPageContainer("location");
  if (locContainer) locationPage.mount(locContainer);

  const skyPage = new SkyPage({
    onStarLayerToggled: (visible) => sceneHost.getStarFieldRenderer().setVisible(visible),
    onAtmosphereToggled: (enabled) => bridge.sendSetAtmosphereEnabled(enabled),
    onLightPollutionToggled: (enabled) => bridge.sendSetLightPollutionEnabled(enabled),
    onLightPollutionModeChanged: (mode) => bridge.sendSetLightPollutionMode(mode),
    onBortleClassChanged: (bortle) => bridge.sendSetBortleClass(bortle),
    onMagnitudeLimitChanged: (mag) => bridge.sendSetManualMagnitudeLimit(mag),
    onPureColorsToggled: (pure) => atmosphereRenderer.setPureColors(pure),
    onSolarSystemVisibilityChanged: (part, visible) => {
      sceneHost.getSolarSystemRenderer().setVisibility(part, visible);
    },
    onMoonSurfaceToggled: (enabled) => {
      sceneHost.getSolarSystemRenderer().setMoonSurfaceEnabled(enabled);
    },
  });
  const skyContainer = shell.getPageContainer("sky");
  if (skyContainer) skyPage.mount(skyContainer);

  const earthPage = new EarthPage();
  const earthContainer = shell.getPageContainer("earth");
  if (earthContainer) earthPage.mount(earthContainer);

  const toolsPage = new ToolsPage();
  const toolsContainer = shell.getPageContainer("tools");
  if (toolsContainer) toolsPage.mount(toolsContainer);

  const timeBar = new TimeBar(bridge);
  timeBar.mount(shell.getTimelineContainer());

  const locationHUD = new LocationHUD();

  // ─── Picking Initialization (Pas 6) ──────────────────────────────
  const celestialTransformState = new CelestialTransformState();
  sceneHost.getStarFieldRenderer().setTransformState(celestialTransformState);

  const gestureRouter = new PointerGestureRouter();
  
  let currentSkyVisibilityState: any = null;

  const starPickProvider = new StarPickProvider({
    camera: sceneHost.camera,
    transformState: celestialTransformState,
    renderer: sceneHost.renderer,
    worldRoot: sceneHost.getWorldRoot(),
    getStarResources: () => sceneHost.getStarFieldRenderer().getResources(),
    getMagnitudeLimit: () => sceneHost.getStarFieldRenderer().getMagnitudeLimit(),
    getSkyVisibilityState: () => currentSkyVisibilityState,
    getPointScale: () => sceneHost.getStarFieldRenderer().getPointScale(),
    isStarLayerVisible: () => sceneHost.getStarFieldRenderer().visible,
  });
  const solarSystemPickProvider = new SolarSystemPickProvider({
    camera: sceneHost.camera,
    getViewportRect: () => sceneHost.renderer.domElement.getBoundingClientRect(),
    getPickableBodies: () => sceneHost.getSolarSystemRenderer().getPickableBodies(),
  });
  const pickProvider = new CelestialPickProvider({
    starPicker: starPickProvider,
    solarSystemPicker: solarSystemPickProvider,
  });

  const pickingController = new ScenePickingController({
    gestureRouter,
    pickProvider,
    resolveCallback: (reqId, gen, resId, resVer, catIdx, purpose) => {
      bridge.sendResolveStarPick(reqId, gen, resId, resVer, catIdx, purpose);
    },
    selectionChangedCallback: (selection) => {
      locationHUD.setSelectedCelestial(selection);
    },
  });

  // 2. Mount scene + UI
  const canvasContainer = shell.getCanvasContainer();
  sceneHost.mount(canvasContainer);
  diagnostics.mount(canvasContainer);
  locationHUD.mount(canvasContainer);
  cameraRig.attach(sceneHost.renderer.domElement);
  gestureRouter.attach(sceneHost.renderer.domElement);
  pickingController.mount(canvasContainer);

  // Initial resize
  const rect = canvasContainer.getBoundingClientRect();
  cameraRig.resize(rect.width, rect.height);

  // 3. Phase 3.5: Prepare navigation world and wire terrain dependencies
  navigationWorld.prepare(sceneHost.getWorldRoot());
  sceneHost.setNavigationWorld(navigationWorld);
  const terrainSampler = navigationWorld.getTerrainSampler();
  cameraRig.setTerrainDependencies(terrainSampler, groundFollower);

  // Ground the camera at origin after terrain is ready
  cameraRig.resetToOrigin();

  // Wire navigation mode changes to UI and bridge
  cameraRig.onNavigationModeChanged((mode) => {
    locationPage.syncNavigationMode(mode);
    bridge.sendNavigationModeChanged(mode);
  });

  // Wire navigation pose updates (coalesced, not per-frame)
  cameraRig.onNavigationPoseChanged((pose, motion) => {
    bridge.sendCameraPoseChanged(pose, motion.speedMps);
  });

  // 4. Bridge ↔ Camera wiring
  cameraRig.onPoseChanged((pose) => {
    bridge.sendCameraChanged(
      pose.azimuthDeg,
      pose.altitudeDeg,
      pose.horizontalFovDeg,
      pose.rollDeg,
    );
    // Phase 4: Update FOV for grid LOD switching
    sceneHost.setCurrentFov(pose.horizontalFovDeg);
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
    onObserverLocationChanged(lat, lon, elevation, effectiveHeight, elevationSource) {
      locationPage.updateInputs(lat, lon);
      locationPage.notifySuccess();
      locationHUD.updateHUD(lat, lon, elevation, effectiveHeight, elevationSource);
      // Phase 4: Update observer latitude for celestial equator
      sceneHost.setObserverLatitude(lat);
    },
    onLocationError(msg) {
      locationPage.notifyError();
      alert("Error d'ubicació: " + msg);
    },
    onSimulationTimeSnapshot(currentTimeIso, julianDay, lstDeg, sunAltitudes, isRealtime) {
      timeBar.updateState(currentTimeIso, sunAltitudes, isRealtime);
      locationPage.updateTimeState(currentTimeIso, isRealtime);
      shell.updateRealtimeUI(isRealtime);
      sceneHost.setSiderealTime(lstDeg);
    },
    onStarCatalogStatus(status) {
      skyPage.updateStarCatalogStatus(status);
    },
    onCelestialFrameTransform(generation, matrix3x3) {
      sceneHost.getStarFieldRenderer().updateCelestialTransform(generation, matrix3x3);
      celestialTransformState.update(generation, matrix3x3 as number[]);
    },
    onStarResourceReady(metadata, bufferPayload) {
      sceneHost.getStarFieldRenderer().registerBinaryResource(metadata, bufferPayload);
      const resId = metadata.resourceId as string;
      const entry = sceneHost.getStarFieldRenderer().getResource(resId);
      if (entry) {
        starPickProvider.buildIndex(resId, entry);
      }
    },
    onStarPickResolved(msg) {
      pickingController.handleResolveResponse(msg as any);
    },
    onSkyEnvironmentSnapshot(snapshot) {
      currentSkyVisibilityState = snapshot.visibility;
      atmosphereRenderer.updateEnvironment(snapshot);
      sceneHost.getSolarSystemRenderer().updateEnvironment(snapshot);
      sceneHost.getStarFieldRenderer().updateVisibilityUniforms(snapshot.visibility);
      // Passem qualsevol nova UI d'aquí a una funció que pugui actualizar LocationHUD o SkyPage
      (locationHUD as any).updateSkyEnvironment?.(snapshot);
      (skyPage as any).updateSkyEnvironment?.(snapshot);
    },
    onSolarSystemSnapshot(snapshot) {
      const bridgeBytes = new TextEncoder().encode(JSON.stringify(snapshot)).byteLength;
      sceneHost.getSolarSystemRenderer().updateSnapshot(snapshot, bridgeBytes);
      skyPage.updateSolarSystem(snapshot);
      diagnostics.updateSolarSystem(snapshot, sceneHost.getSolarSystemRenderer().metrics());
    },
    onMoonSurfaceResource(resource) {
      const moonMetrics = sceneHost.getSolarSystemRenderer().configureMoonSurface(
        resource,
        sceneHost.renderer.capabilities.maxTextureSize,
      );
      skyPage.updateMoonSurfaceResource(resource, moonMetrics.selectedResource);
    },
    onShutdownRequested() {
      renderLoop.stop();
      cameraRig.detach();
      navigationWorld.dispose();
      atmosphereRenderer.dispose();
      sceneHost.dispose();
      diagnostics.dispose();
      locationPage.dispose();
      skyPage.dispose();
      earthPage.dispose();
      toolsPage.dispose();
      locationHUD.dispose();
      bridge.dispose();
    },
  };

  bridge.addMessageListener(backendListener);

  // 5. Bridge state → diagnostics
  bridge.addStateListener(diagnostics);
  bridge.addStateListener({
    onBridgeStateChanged(state) {
      if (state === "connected") {
        diagnostics.updateSession(bridge.sessionId);
      }
    },
  });

  // 6. Render loop with deltaTime for navigation
  let fpsUpdateAccum = 0;
  let performanceUpdateAccum = 0;
  let hudUpdateAccum = 0;
  renderLoop.start((timestampMs: number) => {
    // Phase 3.5: Update navigation physics
    cameraRig.updateNavigation(timestampMs);
    cameraRig.updateMatrices();
    sceneHost.render(timestampMs);
    
    // Actualitza el marker de selecció
    pickingController.updateMarker();

    // Update FPS display at ~1 Hz
    fpsUpdateAccum += 1;
    if (fpsUpdateAccum >= 30) {
      fpsUpdateAccum = 0;
      diagnostics.updateFps(renderLoop.fps, renderLoop.frameMetrics);
    }

    performanceUpdateAccum += 1;
    if (performanceUpdateAccum >= 300) {
      performanceUpdateAccum = 0;
      const frames = renderLoop.frameMetrics;
      const solar = sceneHost.getSolarSystemRenderer().metrics();
      bridge.sendPerformanceMetrics({
        frameMsP50: frames.p50Ms,
        frameMsP95: frames.p95Ms,
        frameSampleCount: frames.sampleCount,
        solarSystemEntityBuildCount: solar.entityBuildCount,
        solarSystemMaterialBuildCount: solar.materialBuildCount,
        solarSystemSnapshotApplyCount: solar.snapshotApplyCount,
        solarSystemStaleSnapshotCount: solar.staleSnapshotCount,
        solarSystemBridgeBytes: solar.lastBridgeBytes,
        moonGeometryBuildCount: solar.moon.geometryBuildCount,
        moonMaterialBuildCount: solar.moon.materialBuildCount,
        moonAlbedoTextureLoadCount: solar.moon.albedoTextureLoadCount,
        moonNormalTextureLoadCount: solar.moon.normalTextureLoadCount,
        moonTextureUploadBytes: solar.moon.textureUploadBytes,
        moonBridgeTextureBytes: solar.moon.bridgeTextureBytes,
      });
    }

    // Phase 4: Update celestial labels EVERY frame to eliminate lag when panning
    sceneHost.updateLabels();

    // Update HUD at ~4 Hz (not every frame)
    hudUpdateAccum += 1;
    if (hudUpdateAccum >= 8) {
      hudUpdateAccum = 0;
      const navPose = cameraRig.getNavigationPose();
      const motionState = cameraRig.getMotionState();
      locationHUD.updateCameraHUD(navPose, motionState);
      locationPage.updateNavigationState(
        navPose,
        motionState,
        navigationWorld.envelope.readiness,
      );
    }
  });

  // 7. Resize handling
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
  resizeObserver.observe(canvasContainer);

  // 9. Before-unload cleanup
  window.addEventListener("beforeunload", () => {
    resizeObserver.disconnect();
    renderLoop.stop();
    cameraRig.detach();
    navigationWorld.dispose();
    atmosphereRenderer.dispose();
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
