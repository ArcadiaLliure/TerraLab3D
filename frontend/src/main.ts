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
import { ResourceManager } from "./application/ResourceManager";
import { CameraRigImpl } from "./view/three/CameraRigImpl";
import { RenderLoopImpl } from "./view/three/RenderLoopImpl";
import { ThreeSceneHostImpl } from "./view/three/ThreeSceneHostImpl";
import { AtmosphereRenderer } from "./view/three/AtmosphereRenderer";
import type { GalacticTextureResource } from "./view/three/GalacticSkyRenderer";
import type { OverlayVisibility } from "./view/three/ThreeSceneHostImpl";
import { DiagnosticsOverlay } from "./view/ui/DiagnosticsOverlay";
import { NavigationWorld } from "./view/three/terrain/NavigationWorld";
import { GroundFollower } from "./view/three/terrain/GroundFollower";
import { ResourceManagerModal } from "./view/ui/modals/ResourceManagerModal";

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
import { DeepSkyPickProvider } from "./view/three/picking/DeepSkyPickProvider";
import { CelestialPickProvider } from "./view/three/picking/CelestialPickProvider";
import { ScenePickingController } from "./view/three/picking/ScenePickingController";
import { TrackingTargetResolver } from "./view/three/picking/TrackingTargetResolver";
import { FocusTrackingController } from "./view/three/picking/FocusTrackingController";

// ─── Bootstrap ───────────────────────────────────────────────────────

function main(): void {
  console.info(`[TerraLab3D] main() iniciat a ${new Date().toISOString()}`);
  const container = document.getElementById("scene-container");
  if (!container) {
    console.error("[TerraLab3D] #scene-container not found");
    return;
  }

  // 1. Create subsystems. The bridge connects after all listeners are wired so
  // the initial celestial transform and resource catalogue cannot be lost.
  const bridge = new WebSocketBridge();
  const resourceManager = new ResourceManager(bridge);
  const sceneHost = new ThreeSceneHostImpl();
  const cameraRig = new CameraRigImpl(sceneHost.camera);
  const renderLoop = new RenderLoopImpl();
  const diagnostics = new DiagnosticsOverlay();

  // Phase 3.5: Navigation world and terrain
  const navigationWorld = new NavigationWorld();
  const groundFollower = new GroundFollower();

  const resourceManagerModal = new ResourceManagerModal(resourceManager);

  const shell = new Shell({
    onSetRealtime: (enabled) => bridge.sendSetRealtimeMode(enabled),
    onOpenResourceManager: () => resourceManagerModal.open(),
  });
  shell.mount(container);

  // 1.5. Sky environment
  const atmosphereRenderer = new AtmosphereRenderer(sceneHost.getCelestialRoot());
  // Default to true, SkyPage will manage this later
  atmosphereRenderer.setPureColors(false);
  let enabledSatelliteSystems: readonly string[] = [];
  let satelliteOrbitsVisible = false;
  let latestSimulationTimeIso = new Date().toISOString();
  let lastEventSearchKey = "";
  const representativeOrbitBody: Readonly<Record<string, { bodyId: string; intervalDays: number }[]>> = {
    mars: [{ bodyId: "naif-401", intervalDays: 0.4 }, { bodyId: "naif-402", intervalDays: 1.5 }],
    jupiter: [{ bodyId: "naif-501", intervalDays: 2 }, { bodyId: "naif-502", intervalDays: 4 }, { bodyId: "naif-503", intervalDays: 7 }, { bodyId: "naif-504", intervalDays: 17 }],
    saturn: [{ bodyId: "naif-606", intervalDays: 16 }, { bodyId: "naif-605", intervalDays: 5 }, { bodyId: "naif-604", intervalDays: 3 }, { bodyId: "naif-608", intervalDays: 80 }],
    uranus: [{ bodyId: "naif-703", intervalDays: 9 }, { bodyId: "naif-704", intervalDays: 14 }],
    neptune: [{ bodyId: "naif-801", intervalDays: 6 }],
    pluto: [{ bodyId: "naif-901", intervalDays: 7 }],
  };
  const requestRepresentativeOrbits = () => {
    if (!satelliteOrbitsVisible) return;
    for (const system of enabledSatelliteSystems) {
      const orbits = representativeOrbitBody[system];
      if (orbits !== undefined) {
        for (const orbit of orbits) {
          bridge.requestSatelliteOrbit(orbit.bodyId, orbit.intervalDays);
        }
      }
    }
  };
  const requestDefaultApparentTrajectories = () => {
    const center = Date.parse(latestSimulationTimeIso);
    if (!Number.isFinite(center)) return;
    const startUtc = new Date(center - 12 * 3_600_000).toISOString();
    const endUtc = new Date(center + 12 * 3_600_000).toISOString();
    for (const bodyId of ["sun", "moon", "mars"]) {
      bridge.requestApparentTrajectory(
        `trajectory:${bodyId}:${latestSimulationTimeIso}`,
        bodyId,
        startUtc,
        endUtc,
        256,
      );
    }
  };

  const readyGalacticResource = (
    resourceId: "sky.milky_way" | "sky.planck_dust",
  ): GalacticTextureResource => {
    const descriptor = resourceManager.getDescriptor(resourceId);
    const state = resourceManager.getInstallState(resourceId);
    if (!descriptor || state.status !== "READY" || state.variantId === null) {
      throw new Error("El recurs encara no està disponible");
    }
    const variant = descriptor.variants.find((candidate) => candidate.id === state.variantId);
    if (!variant) throw new Error("La variant instal·lada no existeix al catàleg");
    const renderWidth = Number(state.manifestData?.renderWidth ?? variant.width ?? 0);
    const renderHeight = Number(state.manifestData?.renderHeight ?? variant.height ?? 0);
    const version = `${state.variantId}:${state.verifiedAt ?? "ready"}`;
    return {
      resourceId,
      version,
      url: `/managed-galactic-assets/${encodeURIComponent(resourceId)}?v=${encodeURIComponent(version)}`,
      width: renderWidth,
      height: renderHeight,
    };
  };

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

  const skyPage = new SkyPage(bridge, resourceManager, {
    onSearchSelected: (selection) => {
      // Ens assegurem que el locationHUD s'actualitza i comença el seguiment
      locationHUD.setSelectedCelestial(selection as any);
      if (selection) {
        focusTrackingController.startTracking(selection);
      }
    },
    onStarLayerToggled: (visible) => sceneHost.getStarFieldRenderer().setVisible(visible),
    onNgcToggled: (visible) => sceneHost.getDeepSkyRenderer().setVisible(visible),
    onAtmosphereToggled: (enabled) => bridge.sendSetAtmosphereEnabled(enabled),
    onLightPollutionToggled: (enabled) => bridge.sendSetLightPollutionEnabled(enabled),
    onLightPollutionModeChanged: (mode) => bridge.sendSetLightPollutionMode(mode),
    onBortleClassChanged: (bortle) => bridge.sendSetBortleClass(bortle),
    onMagnitudeLimitChanged: (mag) => bridge.sendSetManualMagnitudeLimit(mag),
    onPureColorsToggled: (pure) => atmosphereRenderer.setPureColors(pure),
    onSolarSystemVisibilityChanged: (part, visible) => {
      sceneHost.getSolarSystemRenderer().setVisibility(part, visible);
      if (part === "orbits") {
        satelliteOrbitsVisible = visible;
        requestRepresentativeOrbits();
      }
      if (part === "trajectories" && visible) requestDefaultApparentTrajectories();
    },
    onMoonSurfaceToggled: (enabled) => {
      sceneHost.getSolarSystemRenderer().setMoonSurfaceEnabled(enabled);
    },
    onSatelliteSystemsChanged: (systems) => {
      enabledSatelliteSystems = [...systems];
      bridge.setSatelliteSystems(systems);
      requestRepresentativeOrbits();
    },
    onSatelliteLodChanged: (mode) => {
      sceneHost.getSolarSystemRenderer().setSatelliteLodMode(mode);
    },
    onSatelliteLabelsToggled: (enabled) => {
      sceneHost.getSolarSystemLabels().setSatelliteLabelsEnabled(enabled);
    },
    onShadowQualityChanged: (quality) => {
      sceneHost.getLightingController().setShadowQuality(quality);
    },
    onMilkyWayToggled: async (visible) => {
      const renderer = sceneHost.getGalacticSkyRenderer();
      if (visible) await renderer.installMilkyWay(readyGalacticResource("sky.milky_way"));
      renderer.setMilkyWayVisible(visible);
    },
    onPlanckDustToggled: async (visible) => {
      const renderer = sceneHost.getGalacticSkyRenderer();
      if (visible) await renderer.installPlanckDust(readyGalacticResource("sky.planck_dust"));
      renderer.setPlanckDustVisible(visible);
    },
  });
  const skyContainer = shell.getPageContainer("sky");
  if (skyContainer) skyPage.mount(skyContainer);

  const earthPage = new EarthPage();
  const earthContainer = shell.getPageContainer("earth");
  if (earthContainer) earthPage.mount(earthContainer);

  const toolsPage = new ToolsPage(() => resourceManagerModal.open());
  const toolsContainer = shell.getPageContainer("tools");
  if (toolsContainer) toolsPage.mount(toolsContainer);

  const timeBar = new TimeBar(bridge);
  timeBar.mount(shell.getTimelineContainer());

  const locationHUD = new LocationHUD();

  // ─── Picking Initialization (Pas 6) ──────────────────────────────
  const celestialTransformState = new CelestialTransformState();
  sceneHost.getStarFieldRenderer().setTransformState(celestialTransformState);
  sceneHost.getDeepSkyRenderer().setTransformState(celestialTransformState);
  sceneHost.getGalacticSkyRenderer().setTransformState(celestialTransformState);

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
  const deepSkyPickProvider = new DeepSkyPickProvider({
    camera: sceneHost.camera,
    transformState: celestialTransformState,
    renderer: sceneHost.renderer,
    deepSkyRenderer: sceneHost.getDeepSkyRenderer(),
    getSkyVisibilityState: () => currentSkyVisibilityState,
    isDeepSkyLayerVisible: () => sceneHost.getDeepSkyRenderer().visible,
  });
  const pickProvider = new CelestialPickProvider({
    starPicker: starPickProvider,
    solarSystemPicker: solarSystemPickProvider,
    deepSkyPicker: deepSkyPickProvider,
  });

  const pickingController = new ScenePickingController({
    gestureRouter,
    pickProvider,
    resolveCallback: (reqId, gen, resId, resVer, catIdx, purpose) => {
      bridge.sendResolveStarPick(reqId, gen, resId, resVer, catIdx, purpose);
    },
    selectionChangedCallback: (selection) => {
      locationHUD.setSelectedCelestial(selection);
      if (selection) {
        focusTrackingController.startTracking(selection);
      } else {
        focusTrackingController.stopTracking();
      }
    },
  });

  // Tracking (Pas 12)
  const trackingResolver = new TrackingTargetResolver();
  trackingResolver.updateCelestialTransform(celestialTransformState);
  const focusTrackingController = new FocusTrackingController(cameraRig, trackingResolver);
  
  cameraRig.onUserInteraction(() => {
    focusTrackingController.stopTracking();
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
  sceneHost.getLightingController().invalidateShadowGeometry();
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
      latestSimulationTimeIso = currentTimeIso;
      timeBar.updateState(currentTimeIso, sunAltitudes, isRealtime);
      locationPage.updateTimeState(currentTimeIso, isRealtime);
      shell.updateRealtimeUI(isRealtime);
      sceneHost.setSiderealTime(lstDeg);
    },
    onStarCatalogStatus(status) {
      skyPage.updateStarCatalogStatus(status);
    },
    onCelestialFrameTransform(generation, matrix3x3) {
      celestialTransformState.update(generation, matrix3x3 as number[]);
    },
    onBinaryResourceReady(metadata, bufferPayload) {
      if (metadata.role === "solar_system_orbit") {
        sceneHost.getSolarSystemRenderer().registerOrbitResource(metadata, bufferPayload);
        return;
      }
      if (metadata.role === "apparent_trajectory") {
        sceneHost.getSolarSystemRenderer().registerApparentTrajectoryResource(metadata, bufferPayload);
        return;
      }
      if (metadata.role === "deep_sky_catalog") {
        sceneHost.getDeepSkyRenderer().registerBinaryResource(metadata, bufferPayload);
        return;
      }
      sceneHost.getStarFieldRenderer().registerBinaryResource(metadata, bufferPayload);
      const resourceId = metadata.resourceId as string;
      const entry = sceneHost.getStarFieldRenderer().getResource(resourceId);
      if (entry) starPickProvider.buildIndex(resourceId, entry);
    },
    onStarPickResolved(msg) {
      pickingController.handleResolveResponse(msg as any);
    },
    onSkyEnvironmentSnapshot(snapshot) {
      currentSkyVisibilityState = snapshot.visibility;
      atmosphereRenderer.updateEnvironment(snapshot);
      sceneHost.getSolarSystemRenderer().updateEnvironment(snapshot);
      sceneHost.getStarFieldRenderer().updateVisibilityUniforms(snapshot.visibility);
      sceneHost.getDeepSkyRenderer().updateVisibilityUniforms(snapshot.visibility);
      sceneHost.getGalacticSkyRenderer().updateEnvironment(snapshot);
      // Passem qualsevol nova UI d'aquí a una funció que pugui actualizar LocationHUD o SkyPage
      (locationHUD as any).updateSkyEnvironment?.(snapshot);
      (skyPage as any).updateSkyEnvironment?.(snapshot);
    },
    onSolarSystemSnapshot(snapshot) {
      const bridgeBytes = new TextEncoder().encode(JSON.stringify(snapshot)).byteLength;
      sceneHost.getSolarSystemRenderer().updateSnapshot(snapshot, bridgeBytes);
      skyPage.updateSolarSystem(snapshot);
      diagnostics.updateSolarSystem(snapshot, sceneHost.getSolarSystemRenderer().metrics());
      trackingResolver.updateSolarSystemSnapshot(snapshot);
    },
    onLightingEnvironmentSnapshot(snapshot) {
      const bridgeBytes = new TextEncoder().encode(JSON.stringify(snapshot)).byteLength;
      sceneHost.getLightingController().applySnapshot(snapshot, bridgeBytes);
      diagnostics.updateLighting(snapshot, sceneHost.getLightingController().metrics());
    },
    onAstronomicalEventSnapshot(snapshot) {
      sceneHost.getSolarSystemRenderer().updateEventSnapshot(snapshot);
      sceneHost.getLightingController().setEclipseAppearance(snapshot.sceneAppearance);
      locationHUD.updateAstronomicalEvent(snapshot);
      const eventType = snapshot.solar.classification !== "none"
        ? "solar"
        : snapshot.lunar.classification !== "none" ? "lunar" : null;
      if (eventType !== null) {
        const timestamp = Date.parse(snapshot.timestampUtc);
        const dayKey = `${eventType}:${snapshot.observerGeneration}:${snapshot.timestampUtc.slice(0, 10)}`;
        if (Number.isFinite(timestamp) && dayKey !== lastEventSearchKey) {
          lastEventSearchKey = dayKey;
          bridge.requestEventSearch(
            `event:${dayKey}`,
            eventType,
            new Date(timestamp - 12 * 3_600_000).toISOString(),
            new Date(timestamp + 12 * 3_600_000).toISOString(),
          );
        }
      }
    },
    onEventSearchResult(result) {
      locationHUD.updateEventSearchResult(result);
    },
    onAngularSeparationResult(result) {
      locationHUD.updateAngularSeparation(result);
    },
    onMoonSurfaceResource(resource) {
      const moonMetrics = sceneHost.getSolarSystemRenderer().configureMoonSurface(
        resource,
        sceneHost.renderer.capabilities.maxTextureSize,
      );
      skyPage.updateMoonSurfaceResource(resource, moonMetrics.selectedResource);
    },
    onPlanetTextureManifest(manifest) {
      sceneHost.getSolarSystemRenderer().configurePlanetTextures(
        manifest,
        sceneHost.renderer.capabilities.maxTextureSize,
      );
    },
    onSolarSystemCatalogManifest(manifest) {
      sceneHost.getSolarSystemRenderer().configureSatelliteCatalog(manifest);
      sceneHost.getSolarSystemLabels().configureSatelliteCatalog(manifest);
      skyPage.updateSatelliteCatalog(manifest);
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
      resourceManagerModal.dispose();
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

  bridge.connect();

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

    // Actualitza el seguiment automàtic de càmera
    focusTrackingController.update();

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
      const galactic = sceneHost.getGalacticSkyRenderer().metrics();
      const lighting = sceneHost.getLightingController().metrics();
      const navigation = navigationWorld.metrics();
      const rendererInfo = sceneHost.renderer.info;
      bridge.sendPerformanceMetrics({
        frameMsP50: frames.p50Ms,
        frameMsP95: frames.p95Ms,
        frameSampleCount: frames.sampleCount,
        solarSystemEntityBuildCount: solar.entityBuildCount,
        solarBodyGeometryBuildCount: solar.geometryBuildCount,
        solarBodyMaterialBuildCount: solar.materialBuildCount,
        solarSystemMaterialBuildCount: solar.materialBuildCount,
        solarSystemSnapshotApplyCount: solar.snapshotApplyCount,
        solarSystemStaleSnapshotCount: solar.staleSnapshotCount,
        solarSystemBridgeBytes: solar.lastBridgeBytes,
        planetTextureLoadCount: solar.planetTextureLoadCount,
        planetTextureUploadBytes: solar.planetTextureUploadBytes,
        satelliteCatalogCount: solar.satellites.catalogCount,
        satelliteStateCountPerTick: solar.satellites.stateCount,
        ringGeometryBuildCount: solar.rings.geometryBuildCount,
        ringMaterialBuildCount: solar.rings.materialBuildCount,
        orbitGeometryBuildCount: solar.orbits.geometryBuildCount,
        orbitBridgeBytes: solar.orbits.bridgeBytes,
        trajectoryGeometryBuildCount: solar.trajectories.geometryBuildCount,
        trajectoryMaterialBuildCount: solar.trajectories.materialBuildCount,
        trajectoryResourceApplyCount: solar.trajectories.resourceApplyCount,
        trajectoryStaleResourceCount: solar.trajectories.staleResourceCount,
        trajectoryBridgeBytes: solar.trajectories.bridgeBytes,
        solarTotalityGeometryBuildCount: solar.totality.geometryBuildCount,
        solarTotalityMaterialBuildCount: solar.totality.materialBuildCount,
        galacticGeometryBuildCount: galactic.geometryBuildCount,
        galacticMaterialBuildCount: galactic.materialBuildCount,
        milkyWayTextureLoadCount: galactic.milkyWayTextureLoadCount,
        planckTextureLoadCount: galactic.planckTextureLoadCount,
        galacticStaleTextureCount: galactic.staleTextureCount,
        galacticTextureUploadBytes: galactic.textureUploadBytes,
        galacticActiveTextureCount: galactic.activeTextureCount,
        gpuMemoryEstimateBytes: solar.planetTextureUploadBytes
          + solar.moon.textureUploadBytes
          + solar.rings.textureUploadBytes
          + solar.satellites.catalogCount * 3 * Float32Array.BYTES_PER_ELEMENT * 2
          + solar.orbits.bridgeBytes
          + galactic.textureUploadBytes,
        moonGeometryBuildCount: solar.moon.geometryBuildCount,
        moonMaterialBuildCount: solar.moon.materialBuildCount,
        moonAlbedoTextureLoadCount: solar.moon.albedoTextureLoadCount,
        moonNormalTextureLoadCount: solar.moon.normalTextureLoadCount,
        moonTextureUploadBytes: solar.moon.textureUploadBytes,
        moonBridgeTextureBytes: solar.moon.bridgeTextureBytes,
        sunLightBuildCount: lighting.sunLightBuildCount,
        moonLightBuildCount: lighting.moonLightBuildCount,
        diffuseLightBuildCount: lighting.diffuseLightBuildCount,
        pbrMaterialBuildCount: navigation.pbrMaterialBuildCount,
        sunShadowUpdateCount: lighting.shadow.sunShadowUpdateCount,
        moonShadowUpdateCount: lighting.shadow.moonShadowUpdateCount,
        lightingSnapshotCount: lighting.snapshotApplyCount,
        lightingStaleCount: lighting.staleSnapshotCount,
        lightingBridgeBytes: lighting.lastBridgeBytes,
        rendererRenderCalls: rendererInfo.render.calls,
        rendererMemoryGeometries: rendererInfo.memory.geometries,
        rendererMemoryTextures: rendererInfo.memory.textures,
        shadowMapEstimateBytes: lighting.shadow.shadowMapEstimateBytes,
        shadowOffFrameMsP50: lighting.shadow.timings.off.p50Ms,
        shadowOffFrameMsP95: lighting.shadow.timings.off.p95Ms,
        shadowMediumFrameMsP50: lighting.shadow.timings.medium.p50Ms,
        shadowMediumFrameMsP95: lighting.shadow.timings.medium.p95Ms,
        shadowHighFrameMsP50: lighting.shadow.timings.high.p50Ms,
        shadowHighFrameMsP95: lighting.shadow.timings.high.p95Ms,
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
    resourceManagerModal.dispose();
    bridge.dispose();
  });
}

// Run when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", main);
} else {
  main();
}
