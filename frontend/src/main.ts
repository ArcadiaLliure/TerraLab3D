import { TerrainPickProvider } from "./view/three/picking/TerrainPickProvider";
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
import { TemporalSceneCoordinator } from "./application/TemporalSceneCoordinator";
import { CameraRigImpl } from "./view/three/CameraRigImpl";
import { RenderLoopImpl } from "./view/three/RenderLoopImpl";
import { ThreeSceneHostImpl } from "./view/three/ThreeSceneHostImpl";
import { AtmosphereRenderer } from "./view/three/AtmosphereRenderer";
import type { GalacticTextureResource } from "./view/three/GalacticSkyRenderer";
import type { OverlayVisibility } from "./view/three/ThreeSceneHostImpl";
import { DiagnosticsOverlay } from "./view/ui/DiagnosticsOverlay";
import { NavigationWorld } from "./view/three/terrain/NavigationWorld";
import { GroundFollower } from "./view/three/terrain/GroundFollower";
import { CelestialSelectionController, fromSearchResult } from "./application/CelestialSelectionController";
import { buildInspectionModel } from "./application/InspectionModelBuilder";
import { ResourceManagerModal } from "./view/ui/modals/ResourceManagerModal";
import {
  projectCoordinateToTerrainWorld,
  type TerrainWorldAnchor,
} from "./application/TerrainCoordinateProjector";

import { LocationPage } from "./view/ui/drawer_pages/LocationPage";
import { SkyPage } from "./view/ui/drawer_pages/SkyPage";
import { EarthPage } from "./view/ui/drawer_pages/EarthPage";
import { ToolsPage } from "./view/ui/drawer_pages/ToolsPage";
import { LocationHUD } from "./view/ui/panels/LocationHUD";
import { Shell } from "./view/ui/Shell";
import { TimeBar } from "./view/ui/components/TimeBar";
import { StarTrailsPanel } from "./view/ui/components/StarTrailsPanel";
import { StarTrailLayerRendererImpl } from "./view/three/layers/StarTrailLayerRendererImpl";

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
import { TerrainGotoController } from "./view/three/terrain/TerrainGotoController";

// ─── Bootstrap ───────────────────────────────────────────────────────

function main(): void {
  console.debug(`[TerraLab3D] main() iniciat a ${new Date().toISOString()}`);
  const container = document.getElementById("scene-container");
  if (!container) {
    console.error("[TerraLab3D] #scene-container not found");
    return;
  }

  // 1. Create subsystems. The bridge connects after all listeners are wired so
  // the initial celestial transform and resource catalogue cannot be lost.
  const sceneHost = new ThreeSceneHostImpl();
  const bridge = new WebSocketBridge();
  const resourceManager = new ResourceManager(bridge);
  const cameraRig = new CameraRigImpl(sceneHost.camera);
  const renderLoop = new RenderLoopImpl();
  const diagnostics = new DiagnosticsOverlay();

  // Phase 3.5: Navigation world and terrain
  const navigationWorld = new NavigationWorld();
  const groundFollower = new GroundFollower();
  // This anchor belongs to the persistent resident DEM, not to the live
  // observer position reported by the aircraft/HUD.
  let terrainWorldAnchor: TerrainWorldAnchor | null = null;

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
  let satelliteOrbitsVisible = false;
  let enabledSatelliteSystems: readonly string[] = ["mars", "jupiter", "saturn", "uranus", "neptune", "pluto"];
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
    const state = descriptor?.variants
      .map((variant) => resourceManager.getInstallState(resourceId, variant.id))
      .find((candidate) => candidate.status === "READY");
    if (!descriptor || !state || state.status !== "READY" || state.variantId === null) {
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
      url: `/managed-galactic-assets/${encodeURIComponent(resourceId)}?variant=${encodeURIComponent(state.variantId)}&v=${encodeURIComponent(version)}`,
      width: renderWidth,
      height: renderHeight,
    };
  };

  // 2. Prepare UI pages
  const locationPage = new LocationPage({
    onRelocate: (lat, lon, height) => {
      const terrainLayer = sceneHost.getDemTerrainLayerRenderer();
      const hasResidentTerrain = terrainLayer.getNavigationMesh() !== null;
      if (!hasResidentTerrain || !terrainWorldAnchor) {
        bridge.sendSetObserverLocation(lat, lon, height);
        return "terrain-reload";
      }

      const destination = projectCoordinateToTerrainWorld(terrainWorldAnchor, {
        latitudeDeg: lat,
        longitudeDeg: lon,
      });
      if (!destination) return "destination-unavailable";

      // Preserve the loaded mesh. CameraRig validates that this coordinate is
      // actually sampled by it before starting the fast aircraft movement.
      const started = cameraRig.gotoFlightTo(
        destination.eastM,
        destination.northM,
        0,
        Math.max(100, height + 1.7),
      );
      return started ? "flight-started" : "destination-unavailable";
    },
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
      console.log("MGP: [main.ts] [onSearchSelected]", selection);
      const target = fromSearchResult(selection as any);
      if (target) {
        selectionController.select(target, "search");
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

  const earthPage = new EarthPage({
    onHorizonSettings: (settings) => {
      sceneHost.getHorizonOcclusionState().setEnabled(settings.enabled);
      bridge.sendHorizonSettings(settings);
    },
    onRegenerate: (settings) => {
      sceneHost.getHorizonOcclusionState().setEnabled(settings.enabled);
      bridge.sendHorizonSettings(settings);
      bridge.recalculateHorizon();
    },
    onCancel: () => bridge.cancelHorizon(),
    onSurfaceModeChanged: (mode) => bridge.sendSurfaceMode(mode),
  });
  const earthContainer = shell.getPageContainer("earth");
  if (earthContainer) earthPage.mount(earthContainer);

  const toolsPage = new ToolsPage(() => resourceManagerModal.open());
  const toolsContainer = shell.getPageContainer("tools");
  if (toolsContainer) toolsPage.mount(toolsContainer);

  const starTrailRenderer = new StarTrailLayerRendererImpl(
    sceneHost.getCelestialRoot(),
    sceneHost.getStarFieldRenderer(),
    sceneHost.camera,
    sceneHost.renderer,
  );

  const timeBar = new TimeBar(bridge);
  timeBar.mount(shell.getTimelineContainer());

  const selectionController = new CelestialSelectionController();

  const locationHUD = new LocationHUD({
    onCenter: () => {
       const state = selectionController.getState();
       if (state.selectedTarget) {
         const resolved = trackingResolver.resolve(state.selectedTarget);
         if (resolved) {
           cameraRig.animateTo(resolved.azimuthDeg, resolved.altitudeDeg, cameraRig.pose().horizontalFovDeg, 600);
         }
       }
    },
    onFollow: () => {
       const state = selectionController.getState();
       if (state.selectedTarget) {
         focusTrackingController.startTracking(state.selectedTarget);
       }
    },
    onRelease: () => {
       focusTrackingController.stopTracking();
    },
    onClear: () => {
       selectionController.clearSelection();
    },
  });


  // ─── Picking Initialization (Pas 6) ──────────────────────────────
  const celestialTransformState = new CelestialTransformState();
  sceneHost.setCelestialTransformState(celestialTransformState);
  starTrailRenderer.setTransformState(celestialTransformState);

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
    horizonOcclusionState: sceneHost.getHorizonOcclusionState(),
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
    horizonOcclusionState: sceneHost.getHorizonOcclusionState(),
  });
  const pickProvider = new CelestialPickProvider({
    starPicker: starPickProvider,
    solarSystemPicker: solarSystemPickProvider,
    deepSkyPicker: deepSkyPickProvider,
  });

  const pickingController = new ScenePickingController({
    gestureRouter,
    pickProvider,
    selectionController,
    resolveCallback: (reqId, gen, resId, resVer, catIdx, purpose) => {
      bridge.sendResolveStarPick(reqId, gen, resId, resVer, catIdx, purpose);
    },
  });

  // Tracking (Pas 12)
  const trackingResolver = new TrackingTargetResolver();
  trackingResolver.updateCelestialTransform(celestialTransformState);
  trackingResolver.updateSolarSystemRenderer(sceneHost.getSolarSystemRenderer());
  trackingResolver.updateStarRenderer(sceneHost.getStarFieldRenderer());
  trackingResolver.updateDeepSkyRenderer(sceneHost.getDeepSkyRenderer());
  const focusTrackingController = new FocusTrackingController(cameraRig, trackingResolver);

  cameraRig.onUserInteraction(() => {
    focusTrackingController.stopTracking();
  });

  selectionController.subscribe((state) => {
    const model = buildInspectionModel(state, sceneHost);
    locationHUD.updateInspection(model);
    
    // Auto-track si prové de search o pick
    if (state.selectedTarget) {
        if (state.source === "search" || state.source === "pick") {
           focusTrackingController.startTracking(state.selectedTarget);
        }
    } else {
        focusTrackingController.stopTracking();
    }
  });

  // 2. Mount scene + UI
  const canvasContainer = shell.getCanvasContainer();
  
  // Terrain hover tooltip
  const terrainPickProvider = new TerrainPickProvider({
    camera: sceneHost.camera,
    getViewportRect: () => sceneHost.renderer.domElement.getBoundingClientRect(),
    terrainRenderer: sceneHost.getDemTerrainLayerRenderer(),
  });

  const terrainTooltip = document.createElement("div");
  terrainTooltip.style.position = "absolute";
  terrainTooltip.style.pointerEvents = "none";
  terrainTooltip.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
  terrainTooltip.style.color = "white";
  terrainTooltip.style.padding = "4px 8px";
  terrainTooltip.style.borderRadius = "4px";
  terrainTooltip.style.fontSize = "12px";
  terrainTooltip.style.fontFamily = "'Roboto', sans-serif";
  terrainTooltip.style.display = "none";
  terrainTooltip.style.zIndex = "1000";
  terrainTooltip.style.boxShadow = "0 2px 4px rgba(0,0,0,0.5)";
  document.body.appendChild(terrainTooltip);

  gestureRouter.onHover((x, y) => {
    const terrainHit = terrainPickProvider.hover(x, y);
    if (terrainHit) {
      console.log(`MGP: Terrain hover HIT! classId: ${terrainHit.classId}, label: ${terrainHit.label}`);
      terrainTooltip.style.display = "block";
      terrainTooltip.style.left = `${x + 15}px`;
      terrainTooltip.style.top = `${y + 15}px`;
      terrainTooltip.textContent = `${terrainHit.classId}: ${terrainHit.label}`;
    } else {
      terrainTooltip.style.display = "none";
    }
  });
  
  gestureRouter.onHoverClear(() => {
    terrainTooltip.style.display = "none";
  });

  sceneHost.mount(canvasContainer);
  diagnostics.mount(canvasContainer);
  locationHUD.mount(canvasContainer);
  cameraRig.attach(sceneHost.renderer.domElement);
  const terrainGotoController = new TerrainGotoController({
    canvas: sceneHost.renderer.domElement,
    menuParent: canvasContainer,
    camera: sceneHost.camera,
    getTerrainMeshes: () => sceneHost.getDemTerrainLayerRenderer().getGotoTargetMeshes(),
    getTerrainWorldAnchor: () => terrainWorldAnchor,
    onGoto: (destination) => {
      cameraRig.gotoFlightTo(
        destination.eastM,
        destination.northM,
        destination.terrainUpM,
      );
    },
  });
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
    bridge.sendCameraPoseChanged(pose, motion);
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

  let currentObserverLatitude = 41.38;
  let lastStarTrailsState = "idle";
  const temporalSceneCoordinator = new TemporalSceneCoordinator();

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
    onObserverLocationChanged(lat, lon, elevation, heightOffset, effectiveHeight, elevationSource, navigation) {
      currentObserverLatitude = lat;
      if (!navigation) {
        // A manual relocation rebuilds the terrain and re-anchors its ENU
        // world. Camera GPS updates must retain that persistent anchor.
        terrainWorldAnchor = { latitudeDeg: lat, longitudeDeg: lon };
      }
      if (!navigation) {
        locationPage.updateConfiguredObserverInputs(lat, lon);
        locationPage.notifySuccess();
      }
      locationHUD.updateHUD(lat, lon, elevation, heightOffset, effectiveHeight, elevationSource);
      earthPage.updateObserver(lat, lon, elevation, heightOffset, effectiveHeight, elevationSource);
      // Phase 4: Update observer latitude for celestial equator
      sceneHost.setObserverLatitude(lat);
    },
    onNavigationCoordinatesChanged(lat, lon) {
      currentObserverLatitude = lat;
      locationHUD.updateNavigationCoordinates(lat, lon);
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
      starTrailRenderer.setCurrentSimulationTime(currentTimeIso);
    },
    onStarTrailsSnapshot(snapshot) {
      if (snapshot.state === "running" && lastStarTrailsState !== "running") {
        // Direct the camera view towards the Celestial Pole (Polaris at Az 0°, Alt = lat in North; SCP at Az 180°, Alt = |lat| in South)
        const lat = currentObserverLatitude;
        const az = lat >= 0 ? 0.0 : 180.0;
        const alt = Math.abs(lat);
        const currentPose = cameraRig.pose();
        cameraRig.animateTo(az, alt, currentPose.horizontalFovDeg, 1200);
      }
      lastStarTrailsState = snapshot.state;
      starTrailRenderer.applySnapshot(snapshot);
      const trailMetrics = starTrailRenderer.getMetrics();
      skyPage.updateStarTrailsSnapshot({
        ...snapshot,
        starCount: trailMetrics.starCount,
        segmentCount: trailMetrics.segmentCount,
        gpuBytes: trailMetrics.gpuBytes,
      });
    },
    onStarCatalogStatus(status) {
      skyPage.updateStarCatalogStatus(status);
    },
    onSurfaceProgress(msg) {
      console.info("MGP: main.onSurfaceProgress [INICI]");
      console.debug("[main.ts] onSurfaceProgress rebut:", msg);
      if (msg.cleared === true) {
        sceneHost.getDemTerrainLayerRenderer().landCoverManager.clear();
      } else if (msg.globalBounds && msg.resolution) {
        sceneHost.getDemTerrainLayerRenderer().landCoverManager.initGlobalBuffer(
          msg.globalBounds as [number, number, number, number],
          msg.resolution as number
        );
      }
      earthPage.updateTerrainSurface(msg);
      console.info("MGP: main.onSurfaceProgress [FI]");
    },
    onLandCoverLegend(msg) {
      console.info("MGP: main.onLandCoverLegend [INICI]");
      console.debug("[main.ts] onLandCoverLegend rebut:", msg);
      sceneHost.getDemTerrainLayerRenderer().landCoverManager.updateLegend(msg);
      console.info("MGP: main.onLandCoverLegend [FI]");
    },
    onCelestialFrameTransform(generation, matrix3x3, transitionMs) {
      celestialTransformState.update(generation, matrix3x3 as number[], transitionMs);
    },
    onBinaryResourceReady(metadata, bufferPayload) {
      if (metadata.role === "horizon_profile") {
        const horizonState = sceneHost.getHorizonOcclusionState();
        const applied = horizonState.applyBinaryResource(metadata, bufferPayload);
        if (applied) {
          navigationWorld.setTechnicalPresentationVisible(!horizonState.hasDemBackedProfile);
        }
        return;
      }
      if (metadata.role === "terrain_mesh" || metadata.role === "terrain_stream_chunk") {
        const demTerrain = sceneHost.getDemTerrainLayerRenderer();
        if (demTerrain.applyBinaryResource(metadata, bufferPayload)) {
          navigationWorld.setDemTerrainMesh(
            demTerrain.getNavigationMesh(),
            demTerrain.getNavigationSampling(),
          );
          navigationWorld.setStreamingDemTerrainMeshes(
            demTerrain.getStreamingNavigationLayers(),
          );
        }
        return;
      }
      if (metadata.role === "land_cover_tile") {
        console.info("MGP: main.onBinaryResourceReady.land_cover_tile [INICI]");
        console.debug("[main.ts] onBinaryResourceReady: land_cover_tile rebut!", metadata);
        sceneHost.getDemTerrainLayerRenderer().landCoverManager.addTile({
          ...metadata,
          tileKey: metadata.tileKey || metadata.resourceId || "land_cover_tile",
          data: new Uint16Array(bufferPayload),
        } as any);
        console.info("MGP: main.onBinaryResourceReady.land_cover_tile [FI]");
        return;
      }
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
    onHorizonStatus(status) {
      earthPage.updateHorizonStatus(status);
    },
    onStarPickResolved(msg) {
      if (!msg.star) return;
      pickingController.handleResolveResponse(msg as any);
      // Actualitzar l'Inspector amb la nova info de l'estrella resolta
      const state = selectionController.getState();
      if (state.selectedTarget?.kind === "star" && state.selectedTarget.sourceId === msg.star.sourceId) {
         // Re-render
         const model = buildInspectionModel(state, sceneHost);
         // Empeltem algunes dades que venen de msg.star (ex: BP-RP, magnitut refinada, sourceRole)
         if (model && model.fields) {
            model.fields.magnitude = msg.star.magnitude;
            model.fields.bpRp = msg.star.bpRp;
            model.fields.sourceRole = msg.star.sourceRole;
            model.fields.raDeg = msg.star.raDeg;
            model.fields.decDeg = msg.star.decDeg;
         }
         locationHUD.updateInspection(model);
      }
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
      skyPage.updateSkyEnvironment(snapshot);
    },
    onSolarSystemSnapshot(snapshot) {
      const bridgeBytes = new TextEncoder().encode(JSON.stringify(snapshot)).byteLength;
      sceneHost.getSolarSystemRenderer().updateSnapshot(snapshot, bridgeBytes);
      skyPage.updateSolarSystem(snapshot);
      diagnostics.updateSolarSystem(snapshot, sceneHost.getSolarSystemRenderer().metrics());
      trackingResolver.updateSolarSystemSnapshot(snapshot);
    },
    onTemporalSceneState(state) {
      if (!temporalSceneCoordinator.accept(state)) return;

      const solarRenderer = sceneHost.getSolarSystemRenderer();
      const lighting = sceneHost.getLightingController();
      const sky = state.skyEnvironment;

      // One synchronous transaction: no animation frame can observe mixed
      // positions, sky, eclipse photometry and local lights.
      currentSkyVisibilityState = sky.visibility;
      atmosphereRenderer.updateEnvironment(sky);
      solarRenderer.updateEnvironment(sky);
      sceneHost.getStarFieldRenderer().updateVisibilityUniforms(sky.visibility);
      sceneHost.getDeepSkyRenderer().updateVisibilityUniforms(sky.visibility);
      sceneHost.getGalacticSkyRenderer().updateEnvironment(sky);
      lighting.setEclipseAppearance(state.astronomicalEvent.sceneAppearance);

      if (state.authority === "preview") {
        solarRenderer.updatePreviewSnapshot(state.solarSystem);
      } else {
        const solarBytes = new TextEncoder().encode(JSON.stringify(state.solarSystem)).byteLength;
        solarRenderer.updateSnapshot(state.solarSystem, solarBytes);
        solarRenderer.updateEventSnapshot(state.astronomicalEvent);
      }
      const lightingBytes = state.authority === "authoritative"
        ? new TextEncoder().encode(JSON.stringify(state.lightingEnvironment)).byteLength
        : 0;
      lighting.applySnapshot(
        state.lightingEnvironment,
        lightingBytes,
        performance.now(),
        state.authority,
      );
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
      terrainGotoController.dispose();
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
        bridge.setSatelliteSystems([...enabledSatelliteSystems]);
        diagnostics.updateSession(bridge.sessionId);
      }
    }
  });

  bridge.connect();

  // 6. Render loop with deltaTime for navigation
  let fpsUpdateAccum = 0;
  let performanceUpdateAccum = 0;
  let hudUpdateAccum = 0;
  renderLoop.start((timestampMs: number) => {
    // Phase 3.5: Update navigation physics
    cameraRig.updateNavigation(timestampMs);

    // Avançar les interpolacions visuals (SolarSystem, Stars, DeepSky, StarTrails)
    sceneHost.updateVisualState(timestampMs);
    starTrailRenderer.update(timestampMs);

    // Actualitza el seguiment automàtic de càmera utilitzant l'estat visual ja interpolat
    focusTrackingController.update();

    // Aplica les matrius finals de càmera
    cameraRig.updateMatrices();

    // Renderitza el frame (WebGL)
    sceneHost.renderFrame();

    // Actualitza el marker de selecció sobre la geometria ja calculada
    pickingController.updateMarker(sceneHost.camera, trackingResolver);

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
      const horizon = sceneHost.getHorizonOcclusionState().metrics();
      const horizonLayer = sceneHost.getHorizonLayerRenderer().metrics();
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
        horizonUploadBytes: horizon.horizonUploadBytes,
        horizonTextureBuildCount: horizon.horizonTextureBuildCount,
        horizonGeometryBuildCount: horizonLayer.geometryBuildCount,
        horizonDrawCalls: horizonLayer.activeMeshCount,
        horizonLookupCpuP50: horizon.horizonLookupCpuP50,
        horizonLookupCpuP95: horizon.horizonLookupCpuP95,
      });
    }

    // Project labels only when their camera, viewport, content or scene transform changed.
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
    terrainGotoController.dispose();
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
