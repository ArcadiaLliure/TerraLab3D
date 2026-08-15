/**
 * Concrete implementation of the CameraRig interface with Phase 3.5
 * translational navigation (walk and flight modes).
 *
 * Architecture:
 *   NavigationInput (WASD) → NavigationController
 *     Walk:   → GroundFollower → PhysicalPose → CameraVisualSmoother → Camera
 *     Flight: → TerrainSampler (clearance only) → PhysicalPose → Camera
 *
 * All camera movement is 100% local to TypeScript — zero round-trips
 * to Python per frame. Only coalesced snapshots are published.
 *
 * World conventions:
 *   Y = up,  North = -Z,  East = +X
 *   Azimuth 0° = North, clockwise (East = 90°)
 *   Altitude 0° = horizon, +90° = zenith
 */

import * as THREE from "three";
import type { CameraPose, CameraRig } from "./CameraRig";
import type { TerrainSampler } from "../../contracts/TerrainSampler";
import type { IGroundFollower } from "../../contracts/GroundFollower";
import type {
  NavigationCameraPose,
  NavigationMode,
  WalkNavigationSettings,
  FlightNavigationSettings,
  MotionState,
} from "../../contracts/navigation";
import {
  DEFAULT_WALK_SETTINGS,
  DEFAULT_FLIGHT_SETTINGS,
  defaultNavigationCameraPose,
} from "../../contracts/navigation";
import { CameraVisualSmoother } from "./CameraVisualSmoother";
import {
  azimuthAltitudeFromThreeDirection,
  setThreeFromAzimuthAltitude,
} from "./celestialCoordinates";

const DEG = Math.PI / 180;
const MIN_FOV = 0.0001;
const MAX_FOV = 120;
const MIN_ALT = -90;
const MAX_ALT = 90;
const ORBIT_SPEED = 0.45;
const KEY_STEP = 4;
const ZOOM_STEP = 1.1;
const THROTTLE_MS = 16;
const NAVIGATION_POSE_THROTTLE_MS = 100;
const MAX_DELTA_TIME = 0.05; // 50ms cap
const FLIGHT_COLLISION_PROBE_SPACING_M = 4;
export const GOTO_FLIGHT_DURATION_S = 10;
const GOTO_ARRIVAL_CLEARANCE_M = 100;

const LOG_PREFIX = "MGP: [CameraRigImpl]";

export type PoseChangedCallback = (pose: CameraPose) => void;
export type NavigationModeChangedCallback = (mode: NavigationMode) => void;
export type NavigationPoseCallback = (pose: NavigationCameraPose, motion: MotionState) => void;

interface FlightGotoTarget {
  readonly eastM: number;
  readonly northM: number;
  readonly upM: number;
  /** Distance-adaptive speed that completes this specific journey in 10 s. */
  readonly speedMps: number;
}

export class CameraRigImpl implements CameraRig {
  // ─── Rotation state (original) ─────────────────────────────────────
  private azimuthDeg = 0;
  private altitudeDeg = 20;
  private hFovDeg = 60;
  private rollDeg = 0;

  // ─── Translation state (Phase 3.5) ─────────────────────────────────
  private positionEastM = 0;
  private positionUpM = 0;
  private positionNorthM = 0;
  private velocityEast = 0;
  private velocityUp = 0;
  private velocityNorth = 0;
  private navigationMode: NavigationMode = "walk";
  private isTrackingTarget = false;
  private gotoTarget: FlightGotoTarget | null = null;

  // ─── Settings ──────────────────────────────────────────────────────
  private walkSettings: WalkNavigationSettings = { ...DEFAULT_WALK_SETTINGS };
  private flightSettings: FlightNavigationSettings = { ...DEFAULT_FLIGHT_SETTINGS };

  // ─── Dependencies (injected, interface-only) ───────────────────────
  private terrainSampler: TerrainSampler | null = null;
  private groundFollower: IGroundFollower | null = null;
  private readonly visualSmoother = new CameraVisualSmoother();

  // ─── Three.js camera ──────────────────────────────────────────────
  private readonly camera: THREE.PerspectiveCamera;
  private container: HTMLElement | null = null;

  // ─── Input state ───────────────────────────────────────────────────
  private readonly keysDown = new Set<string>();
  private dragging = false;
  private lastX = 0;
  private lastY = 0;

  // ─── Smooth transition ─────────────────────────────────────────────
  private animating = false;
  private animStart = 0;
  private animDuration = 0;
  private animFromAz = 0;
  private animFromAlt = 0;
  private animFromFov = 0;
  private animToAz = 0;
  private animToAlt = 0;
  private animToFov = 0;

  // ─── Callbacks ─────────────────────────────────────────────────────
  private poseCallback: PoseChangedCallback | null = null;
  private navigationModeCallback: NavigationModeChangedCallback | null = null;
  private navigationPoseCallback: NavigationPoseCallback | null = null;
  private userInteractionCallback: (() => void) | null = null;
  private throttleTimer: ReturnType<typeof setTimeout> | null = null;
  private navigationPoseTimer: ReturnType<typeof setTimeout> | null = null;
  private dirty = false;
  private navigationPoseDirty = false;

  // ─── Time tracking ─────────────────────────────────────────────────
  private lastTimestampMs = 0;

  // ─── Motion coalescing ─────────────────────────────────────────────
  private wasMoving = false;

  // ─── Bound handlers ────────────────────────────────────────────────
  private readonly onPointerDownBound = this.onPointerDown.bind(this);
  private readonly onPointerMoveBound = this.onPointerMove.bind(this);
  private readonly onPointerUpBound = this.onPointerUp.bind(this);
  private readonly onWheelBound = this.onWheel.bind(this);
  private readonly onKeyDownBound = this.onKeyDown.bind(this);
  private readonly onKeyUpBound = this.onKeyUp.bind(this);
  private readonly onBlurBound = this.onBlur.bind(this);
  private readonly onVisibilityChangeBound = this.onVisibilityChange.bind(this);
  constructor(camera: THREE.PerspectiveCamera) {
    this.camera = camera;
    this.applyToCamera();
  }

  // ─── CameraRig interface ───────────────────────────────────────────

  pose(): CameraPose {
    return {
      azimuthDeg: this.azimuthDeg,
      altitudeDeg: this.altitudeDeg,
      horizontalFovDeg: this.hFovDeg,
      rollDeg: this.rollDeg,
    };
  }

  isAnimating(): boolean {
    return this.animating;
  }

  setPose(p: CameraPose): void {
    this.azimuthDeg = p.azimuthDeg;
    this.altitudeDeg = clamp(p.altitudeDeg, MIN_ALT, MAX_ALT);
    this.hFovDeg = clamp(p.horizontalFovDeg, MIN_FOV, MAX_FOV);
    this.rollDeg = p.rollDeg;
    this.animating = false;
    this.applyToCamera();
  }

  setTrackingState(isTracking: boolean): void {
    this.isTrackingTarget = isTracking;
  }

  orbit(deltaAz: number, deltaAlt: number): void {
    this.azimuthDeg = normalizeAzimuth(this.azimuthDeg + deltaAz);
    this.altitudeDeg = clamp(this.altitudeDeg + deltaAlt, MIN_ALT, MAX_ALT);
    this.applyToCamera();
    this.schedulePosePublish();
  }

  zoomTo(fov: number): void {
    this.hFovDeg = clamp(fov, MIN_FOV, MAX_FOV);
    this.applyToCamera();
    this.schedulePosePublish();
  }

  resize(widthPx: number, heightPx: number): void {
    const aspect = widthPx / heightPx;
    this.camera.aspect = aspect;
    this.camera.fov = hFovToVFov(this.hFovDeg, aspect);
    this.camera.updateProjectionMatrix();
  }

  updateMatrices(): void {
    // Tick any running smooth transition
    if (this.animating) {
      const now = performance.now();
      const t = Math.min(1, (now - this.animStart) / this.animDuration);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

      this.azimuthDeg = lerpAngle(this.animFromAz, this.animToAz, ease);
      this.altitudeDeg = lerp(this.animFromAlt, this.animToAlt, ease);
      this.hFovDeg = lerp(this.animFromFov, this.animToFov, ease);

      this.applyToCamera();

      if (t >= 1) {
        this.animating = false;
        this.publishPoseNow();
      }
    }
  }

  // ─── Navigation API (Phase 3.5) ────────────────────────────────────

  /** Inject terrain dependencies. Called once during main.ts wiring. */
  setTerrainDependencies(
    sampler: TerrainSampler,
    follower: IGroundFollower,
  ): void {
    this.terrainSampler = sampler;
    this.groundFollower = follower;
    console.info(`${LOG_PREFIX} [setTerrainDependencies] [Dependències de terreny connectades]`);
  }

  /** Called each frame from the render loop with timestampMs. */
  updateNavigation(timestampMs: number): void {
    if (this.lastTimestampMs === 0) {
      this.lastTimestampMs = timestampMs;
      return;
    }

    let deltaTime = (timestampMs - this.lastTimestampMs) / 1000;
    this.lastTimestampMs = timestampMs;

    // Cap deltaTime to avoid physics explosions after tab switch
    if (deltaTime <= 0) return;
    if (deltaTime > MAX_DELTA_TIME) deltaTime = MAX_DELTA_TIME;

    // Skip if no terrain
    if (!this.terrainSampler || !this.terrainSampler.isReady()) return;

    const isMoving = this.hasMovementInput() || this.gotoTarget !== null;

    if (this.navigationMode === "walk") {
      this.updateWalkMode(deltaTime);
    } else {
      this.updateFlightMode(deltaTime);
    }

    if (isMoving || this.getMotionState().speedMps > 0.01) {
      this.scheduleNavigationPosePublish();
    }

    // Motion state tracking for coalesced bridge events
    if (isMoving && !this.wasMoving) {
      console.info(`${LOG_PREFIX} [startMotion] [Moviment iniciat mode=${this.navigationMode}]`);
    } else if (!isMoving && this.wasMoving) {
      console.info(
        `${LOG_PREFIX} [stopMotion] [Moviment finalitzat east_m=${this.positionEastM.toFixed(1)} north_m=${this.positionNorthM.toFixed(1)} up_m=${this.positionUpM.toFixed(1)}]`,
      );
      // Publish final snapshot when motion stops
      this.publishNavigationPose();
    }
    this.wasMoving = isMoving;
  }

  getNavigationMode(): NavigationMode {
    return this.navigationMode;
  }

  setNavigationMode(mode: NavigationMode): void {
    if (mode === this.navigationMode) return;
    if (this.gotoTarget) {
      console.info(`${LOG_PREFIX} [setNavigationMode] [Canvi de mode ignorat durant un trajecte Goto actiu]`);
      return;
    }
    const prev = this.navigationMode;
    this.navigationMode = mode;

    // Clear velocities on mode change
    this.velocityEast = 0;
    this.velocityUp = 0;
    this.velocityNorth = 0;
    this.keysDown.clear();
    this.gotoTarget = null;

    if (mode === "walk" && this.terrainSampler && this.groundFollower) {
      // Project onto terrain when entering walk mode
      const sample = this.terrainSampler.sampleGround(
        this.positionEastM,
        this.positionNorthM,
        this.positionUpM,
      );
      if (sample && sample.valid) {
        this.positionUpM = sample.heightM + this.walkSettings.eyeHeightM;
        this.visualSmoother.reset(this.positionUpM);
      }
      this.rollDeg = 0;
    }

    if (mode === "walk") {
      this.visualSmoother.reset(this.positionUpM);
    }

    this.applyToCamera();
    this.navigationModeCallback?.(mode);
    this.publishNavigationPose();
    console.info(`${LOG_PREFIX} [setNavigationMode] [Mode canviat ${prev} → ${mode}]`);
  }

  toggleNavigationMode(): void {
    this.setNavigationMode(this.navigationMode === "walk" ? "flight" : "walk");
  }

  resetToOrigin(): void {
    if (this.gotoTarget) {
      console.info(`${LOG_PREFIX} [resetToOrigin] [Restabliment ignorat durant un trajecte Goto actiu]`);
      return;
    }
    this.positionEastM = 0;
    this.positionNorthM = 0;
    this.velocityEast = 0;
    this.velocityUp = 0;
    this.velocityNorth = 0;
    this.gotoTarget = null;

    // Ground at origin
    if (this.terrainSampler?.isReady()) {
      const sample = this.terrainSampler.sampleGround(0, 0, 100);
      if (sample && sample.valid) {
        this.positionUpM = sample.heightM + this.walkSettings.eyeHeightM;
      } else {
        this.positionUpM = this.walkSettings.eyeHeightM;
      }
    } else {
      this.positionUpM = this.walkSettings.eyeHeightM;
    }

    this.rollDeg = 0;
    this.visualSmoother.reset(this.positionUpM);
    this.applyToCamera();
    this.publishNavigationPose();
    console.info(`${LOG_PREFIX} [resetToOrigin] [Càmera restablerta a l'origen]`);
  }

  getNavigationPose(): NavigationCameraPose {
    return {
      positionEastM: this.positionEastM,
      positionUpM: this.positionUpM,
      positionNorthM: this.positionNorthM,
      azimuthDeg: this.azimuthDeg,
      altitudeDeg: this.altitudeDeg,
      rollDeg: this.rollDeg,
      fovDeg: this.hFovDeg,
      navigationMode: this.navigationMode,
    };
  }

  getMotionState(): MotionState {
    const speed = Math.sqrt(
      this.velocityEast * this.velocityEast +
      this.velocityUp * this.velocityUp +
      this.velocityNorth * this.velocityNorth,
    );
    return {
      moving: speed > 0.01,
      sprinting: this.keysDown.has("ShiftLeft") || this.keysDown.has("ShiftRight"),
      speedMps: speed,
      velocityEast: this.velocityEast,
      velocityUp: this.velocityUp,
      velocityNorth: this.velocityNorth,
    };
  }

  /**
   * Start an explicit high-speed flight to a triangle selected on the DEM.
   * Manual flight remains capped by its user setting; this is a separate,
   * observable navigation command and never changes that cap.
   */
  gotoFlightTo(
    targetEastM: number,
    targetNorthM: number,
    targetTerrainUpM: number,
    requestedArrivalClearanceM = GOTO_ARRIVAL_CLEARANCE_M,
  ): boolean {
    if (
      !this.terrainSampler?.isReady()
      || !Number.isFinite(targetEastM)
      || !Number.isFinite(targetNorthM)
      || !Number.isFinite(targetTerrainUpM)
      || !Number.isFinite(requestedArrivalClearanceM)
    ) return false;
    this.setNavigationMode("flight");
    const currentGround = this.terrainSampler.sampleGround(
      this.positionEastM,
      this.positionNorthM,
      this.positionUpM,
    );
    if (!currentGround?.valid) return false;
    this.positionUpM = Math.max(
      this.positionUpM,
      currentGround.heightM + this.flightSettings.minimumClearanceM,
    );
    const targetGround = this.terrainSampler.sampleGround(targetEastM, targetNorthM, targetTerrainUpM);
    if (!targetGround?.valid) return false;
    this.velocityEast = 0;
    this.velocityNorth = 0;
    this.velocityUp = 0;
    const gotoTarget: FlightGotoTarget = {
      eastM: targetEastM,
      northM: targetNorthM,
      upM: Math.max(
        this.positionUpM,
        targetGround.heightM + Math.max(
          this.flightSettings.minimumClearanceM,
          requestedArrivalClearanceM,
        ),
      ),
      speedMps: 0,
    };
    const distanceM = Math.hypot(
      gotoTarget.eastM - this.positionEastM,
      gotoTarget.northM - this.positionNorthM,
      gotoTarget.upM - this.positionUpM,
    );
    this.gotoTarget = {
      ...gotoTarget,
      speedMps: distanceM / GOTO_FLIGHT_DURATION_S,
    };
    console.info(
      `${LOG_PREFIX} [gotoFlightTo] [Destino DEM east_m=${targetEastM.toFixed(1)} north_m=${targetNorthM.toFixed(1)} duration_s=${GOTO_FLIGHT_DURATION_S} speed_mps=${this.gotoTarget.speedMps.toFixed(1)}]`,
    );
    return true;
  }

  cancelGotoFlight(): void {
    if (!this.gotoTarget) return;
    this.gotoTarget = null;
    this.velocityEast = 0;
    this.velocityNorth = 0;
    this.velocityUp = 0;
    console.info(`${LOG_PREFIX} [cancelGotoFlight] [Trajecte Goto cancelÂ·lat]`);
  }

  // ─── Extended API ──────────────────────────────────────────────────

  animateTo(azDeg: number, altDeg: number, fovDeg: number, durationMs: number): void {
    if (durationMs <= 0) {
      this.azimuthDeg = azDeg;
      this.altitudeDeg = clamp(altDeg, MIN_ALT, MAX_ALT);
      this.hFovDeg = clamp(fovDeg, MIN_FOV, MAX_FOV);
      this.applyToCamera();
      this.publishPoseNow();
      return;
    }
    this.animFromAz = this.azimuthDeg;
    this.animFromAlt = this.altitudeDeg;
    this.animFromFov = this.hFovDeg;
    this.animToAz = azDeg;
    this.animToAlt = clamp(altDeg, MIN_ALT, MAX_ALT);
    this.animToFov = clamp(fovDeg, MIN_FOV, MAX_FOV);
    this.animStart = performance.now();
    this.animDuration = durationMs;
    this.animating = true;
  }

  onPoseChanged(cb: PoseChangedCallback): void {
    this.poseCallback = cb;
  }

  onNavigationModeChanged(cb: NavigationModeChangedCallback): void {
    this.navigationModeCallback = cb;
  }

  onNavigationPoseChanged(cb: NavigationPoseCallback): void {
    this.navigationPoseCallback = cb;
  }

  onUserInteraction(cb: () => void): void {
    this.userInteractionCallback = cb;
  }

  attach(container: HTMLElement): void {
    this.container = container;
    container.addEventListener("pointerdown", this.onPointerDownBound);
    container.addEventListener("pointermove", this.onPointerMoveBound);
    container.addEventListener("pointerup", this.onPointerUpBound);
    container.addEventListener("pointerleave", this.onPointerUpBound);
    container.addEventListener("wheel", this.onWheelBound, { passive: false });
    window.addEventListener("keydown", this.onKeyDownBound);
    window.addEventListener("keyup", this.onKeyUpBound);
    window.addEventListener("blur", this.onBlurBound);
    document.addEventListener("visibilitychange", this.onVisibilityChangeBound);
  }

  detach(): void {
    if (!this.container) return;
    const c = this.container;
    c.removeEventListener("pointerdown", this.onPointerDownBound);
    c.removeEventListener("pointermove", this.onPointerMoveBound);
    c.removeEventListener("pointerup", this.onPointerUpBound);
    c.removeEventListener("pointerleave", this.onPointerUpBound);
    c.removeEventListener("wheel", this.onWheelBound);
    window.removeEventListener("keydown", this.onKeyDownBound);
    window.removeEventListener("keyup", this.onKeyUpBound);
    window.removeEventListener("blur", this.onBlurBound);
    document.removeEventListener("visibilitychange", this.onVisibilityChangeBound);
    this.container = null;
    if (this.throttleTimer !== null) {
      clearTimeout(this.throttleTimer);
      this.throttleTimer = null;
    }
    if (this.navigationPoseTimer !== null) {
      clearTimeout(this.navigationPoseTimer);
      this.navigationPoseTimer = null;
    }
  }

  // ─── Walk Mode ─────────────────────────────────────────────────────

  private updateWalkMode(dt: number): void {
    if (!this.terrainSampler || !this.groundFollower) return;

    const settings = this.walkSettings;
    const isSprinting = this.keysDown.has("ShiftLeft") || this.keysDown.has("ShiftRight");
    const maxSpeed = isSprinting ? settings.sprintSpeedMps : settings.walkSpeedMps;

    // Build intended direction from azimuth
    const { forwardE, forwardN, rightE, rightN } = this.getMovementBasis();

    // Input vector (normalized if diagonal)
    let inputE = 0;
    let inputN = 0;
    if (this.keysDown.has("KeyW")) { inputE += forwardE; inputN += forwardN; }
    if (this.keysDown.has("KeyS")) { inputE -= forwardE; inputN -= forwardN; }
    if (this.keysDown.has("KeyD")) { inputE += rightE; inputN += rightN; }
    if (this.keysDown.has("KeyA")) { inputE -= rightE; inputN -= rightN; }

    const inputLen = Math.sqrt(inputE * inputE + inputN * inputN);
    if (inputLen > 0.001) {
      inputE /= inputLen;
      inputN /= inputLen;
    }

    // Acceleration / deceleration
    if (inputLen > 0.001) {
      const targetE = inputE * maxSpeed;
      const targetN = inputN * maxSpeed;
      this.velocityEast = approachValue(this.velocityEast, targetE, settings.accelerationMps2 * dt);
      this.velocityNorth = approachValue(this.velocityNorth, targetN, settings.accelerationMps2 * dt);
    } else {
      this.velocityEast = approachValue(this.velocityEast, 0, settings.decelerationMps2 * dt);
      this.velocityNorth = approachValue(this.velocityNorth, 0, settings.decelerationMps2 * dt);
    }

    // Proposed position
    const proposedE = this.positionEastM + this.velocityEast * dt;
    const proposedN = this.positionNorthM + this.velocityNorth * dt;

    const previousPose = this.getNavigationPose();
    const proposedPose: NavigationCameraPose = {
      ...previousPose,
      positionEastM: proposedE,
      positionNorthM: proposedN,
    };

    // GroundFollower resolves grounding
    const resolution = this.groundFollower.resolve(
      previousPose,
      proposedPose,
      this.terrainSampler,
      settings,
    );

    if (resolution.blocked) {
      // Stop velocity in the blocked direction
      this.velocityEast = 0;
      this.velocityNorth = 0;
    }

    // Apply resolved physical pose
    this.positionEastM = resolution.pose.positionEastM;
    this.positionNorthM = resolution.pose.positionNorthM;
    const physicalUpM = resolution.pose.positionUpM;

    // Visual smoother (only affects rendered Y, not physics)
    const visualPose = this.visualSmoother.smooth(
      { ...resolution.pose, positionUpM: physicalUpM },
      settings.visualGroundSmoothing,
    );
    this.positionUpM = visualPose.positionUpM;
    this.rollDeg = 0; // Walk = no roll

    this.applyToCamera();
  }

  // ─── Flight Mode ───────────────────────────────────────────────────

  private updateFlightMode(dt: number): void {
    if (!this.terrainSampler) return;
    if (this.gotoTarget) {
      this.updateGotoFlight(dt);
      return;
    }

    const settings = this.flightSettings;
    const isBoosting = this.keysDown.has("ShiftLeft") || this.keysDown.has("ShiftRight");
    const maxSpeed = isBoosting ? settings.maximumSpeedMps : settings.cruiseSpeedMps;

    // Build full 3D movement basis from azimuth + pitch (altitude)
    const { forwardE, forwardU, forwardN, rightE, rightN } = this.getFlight3DMovementBasis();

    let inputE = 0;
    let inputN = 0;
    let inputU = 0;

    if (this.keysDown.has("KeyW")) {
      inputE += forwardE;
      inputN += forwardN;
      inputU += forwardU;
    }
    if (this.keysDown.has("KeyS")) {
      inputE -= forwardE;
      inputN -= forwardN;
      inputU -= forwardU;
    }
    if (this.keysDown.has("KeyD")) { inputE += rightE; inputN += rightN; }
    if (this.keysDown.has("KeyA")) { inputE -= rightE; inputN -= rightN; }
    if (this.keysDown.has("Space")) { inputU += 1; }
    if (this.keysDown.has("ControlLeft") || this.keysDown.has("ControlRight")) { inputU -= 1; }

    // Normalize 3D vector
    const inputLen = Math.sqrt(inputE * inputE + inputN * inputN + inputU * inputU);
    if (inputLen > 0.001) {
      inputE /= inputLen;
      inputN /= inputLen;
      inputU /= inputLen;
    }

    // Acceleration
    if (inputLen > 0.001) {
      this.velocityEast = approachValue(this.velocityEast, inputE * maxSpeed, settings.accelerationMps2 * dt);
      this.velocityNorth = approachValue(this.velocityNorth, inputN * maxSpeed, settings.accelerationMps2 * dt);
      this.velocityUp = approachValue(this.velocityUp, inputU * maxSpeed, settings.accelerationMps2 * dt);
    } else {
      this.velocityEast = approachValue(this.velocityEast, 0, settings.brakingMps2 * dt);
      this.velocityNorth = approachValue(this.velocityNorth, 0, settings.brakingMps2 * dt);
      this.velocityUp = approachValue(this.velocityUp, 0, settings.brakingMps2 * dt);
    }

    // Stabilize with X
    if (this.keysDown.has("KeyX")) {
      this.velocityEast = approachValue(this.velocityEast, 0, settings.brakingMps2 * dt * 2);
      this.velocityNorth = approachValue(this.velocityNorth, 0, settings.brakingMps2 * dt * 2);
      this.velocityUp = approachValue(this.velocityUp, 0, settings.brakingMps2 * dt * 2);
      if (settings.autoLevelRoll) {
        this.rollDeg = approachValue(this.rollDeg, 0, 90 * dt);
      }
    }

    // Roll
    if (this.keysDown.has("KeyQ")) this.rollDeg -= 90 * dt;
    if (this.keysDown.has("KeyE")) this.rollDeg += 90 * dt;
    this.rollDeg = clamp(this.rollDeg, -settings.maximumRollDeg, settings.maximumRollDeg);

    const swept = this.resolveFlightTerrainSweep(
      this.positionEastM,
      this.positionNorthM,
      this.positionUpM,
      this.positionEastM + this.velocityEast * dt,
      this.positionNorthM + this.velocityNorth * dt,
      this.positionUpM + this.velocityUp * dt,
    );
    if (swept.blocked) {
      this.velocityEast = 0;
      this.velocityNorth = 0;
      this.velocityUp = 0;
    }
    this.applyFlightPosition(swept.eastM, swept.northM, swept.upM);
    this.applyToCamera();
  }

  /** Move the automatic Goto flight without weakening DEM collision. */
  private updateGotoFlight(dt: number): void {
    const target = this.gotoTarget;
    if (!target) return;
    const eastDelta = target.eastM - this.positionEastM;
    const northDelta = target.northM - this.positionNorthM;
    const upDelta = target.upM - this.positionUpM;
    const remainingM = Math.hypot(eastDelta, northDelta, upDelta);
    if (remainingM < 0.01) {
      this.finishGotoFlight(target);
      return;
    }
    const travelM = Math.min(target.speedMps * dt, remainingM);
    const fraction = travelM / remainingM;
    this.velocityEast = eastDelta / remainingM * target.speedMps;
    this.velocityNorth = northDelta / remainingM * target.speedMps;
    this.velocityUp = upDelta / remainingM * target.speedMps;
    const swept = this.resolveFlightTerrainSweep(
      this.positionEastM,
      this.positionNorthM,
      this.positionUpM,
      this.positionEastM + eastDelta * fraction,
      this.positionNorthM + northDelta * fraction,
      this.positionUpM + upDelta * fraction,
    );
    if (swept.blocked) {
      this.cancelGotoFlight();
      this.applyFlightPosition(swept.eastM, swept.northM, swept.upM);
      this.applyToCamera();
      return;
    }
    this.applyFlightPosition(swept.eastM, swept.northM, swept.upM);
    if (travelM === remainingM) this.finishGotoFlight(target);
    this.applyToCamera();
  }

  /** Sweep the full flight segment against the same DEM sampler as manual flight. */
  private resolveFlightTerrainSweep(
    previousEastM: number,
    previousNorthM: number,
    previousUpM: number,
    proposedEastM: number,
    proposedNorthM: number,
    proposedUpM: number,
  ): { eastM: number; northM: number; upM: number; blocked: boolean } {
    if (!this.terrainSampler) {
      return { eastM: previousEastM, northM: previousNorthM, upM: previousUpM, blocked: true };
    }
    const horizontalDistance = Math.hypot(proposedEastM - previousEastM, proposedNorthM - previousNorthM);
    const probeCount = Math.max(1, Math.ceil(horizontalDistance / FLIGHT_COLLISION_PROBE_SPACING_M));
    let lastSafeEastM = previousEastM;
    let lastSafeNorthM = previousNorthM;
    let lastSafeUpM = previousUpM;
    for (let probe = 0; probe <= probeCount; probe++) {
      const fraction = probe / probeCount;
      const eastM = previousEastM + (proposedEastM - previousEastM) * fraction;
      const northM = previousNorthM + (proposedNorthM - previousNorthM) * fraction;
      const upM = previousUpM + (proposedUpM - previousUpM) * fraction;
      const sample = this.terrainSampler.sampleGround(eastM, northM, upM);
      if (!sample?.valid) {
        return { eastM: lastSafeEastM, northM: lastSafeNorthM, upM: lastSafeUpM, blocked: true };
      }
      const minimumUpM = sample.heightM + this.flightSettings.minimumClearanceM;
      if (upM < minimumUpM) {
        if (probe === 0) {
          return { eastM: previousEastM, northM: previousNorthM, upM: minimumUpM, blocked: true };
        }
        return { eastM: lastSafeEastM, northM: lastSafeNorthM, upM: lastSafeUpM, blocked: true };
      }
      lastSafeEastM = eastM;
      lastSafeNorthM = northM;
      lastSafeUpM = Math.max(upM, minimumUpM);
    }
    return { eastM: lastSafeEastM, northM: lastSafeNorthM, upM: lastSafeUpM, blocked: false };
  }

  private applyFlightPosition(eastM: number, northM: number, upM: number): void {
    this.positionEastM = eastM;
    this.positionNorthM = northM;
    this.positionUpM = Math.min(upM, this.flightSettings.maximumAltitudeM);
    if (upM > this.flightSettings.maximumAltitudeM && this.velocityUp > 0) this.velocityUp = 0;
  }

  private finishGotoFlight(target: FlightGotoTarget): void {
    this.positionEastM = target.eastM;
    this.positionNorthM = target.northM;
    this.positionUpM = target.upM;
    this.gotoTarget = null;
    this.velocityEast = 0;
    this.velocityNorth = 0;
    this.velocityUp = 0;
    this.publishNavigationPose();
    console.info(`${LOG_PREFIX} [finishGotoFlight] [Destino Goto alcanzado]`);
  }

  // ─── Input handlers ────────────────────────────────────────────────

  private onPointerDown(e: PointerEvent): void {
    if (e.button !== 0) return;
    this.dragging = true;
    this.lastX = e.clientX;
    this.lastY = e.clientY;
    this.animating = false;
    this.container?.setPointerCapture(e.pointerId);
  }

  private onPointerMove(e: PointerEvent): void {
    if (!this.dragging) return;
    const dx = e.clientX - this.lastX;
    const dy = e.clientY - this.lastY;
    if (dx === 0 && dy === 0) return;

    this.userInteractionCallback?.();
    this.lastX = e.clientX;
    this.lastY = e.clientY;
    const fovScale = this.hFovDeg / 60;
    this.orbit(-dx * ORBIT_SPEED * fovScale, dy * ORBIT_SPEED * fovScale);
  }

  private onPointerUp(e: PointerEvent): void {
    if (!this.dragging) return;
    this.dragging = false;
    this.container?.releasePointerCapture(e.pointerId);
    this.publishPoseNow();
  }

  private onWheel(e: WheelEvent): void {
    e.preventDefault();
    // No cridem this.userInteractionCallback?.(); perquè volem 
    // permetre fer zoom mentre segueix trackejant l'objectiu
    this.animating = false;
    const factor = e.deltaY > 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
    const oldHFov = this.hFovDeg;
    const newHFov = clamp(this.hFovDeg * factor, MIN_FOV, MAX_FOV);

    if (newHFov === oldHFov || !this.container) return;

    const rect = this.container.getBoundingClientRect();
    const dx = e.clientX - rect.left - rect.width / 2;
    const dy = rect.top + rect.height / 2 - e.clientY;

    const aspect = this.camera.aspect || 1;
    const oldVFov = hFovToVFov(oldHFov, aspect);
    const newVFov = hFovToVFov(newHFov, aspect);

    const deltaAz = -(dx / rect.width) * (oldHFov - newHFov);
    const deltaAlt = (dy / rect.height) * (oldVFov - newVFov);

    if (!this.isTrackingTarget) {
      this.orbit(deltaAz, deltaAlt);
    }
    this.zoomTo(newHFov);
  }

  private onKeyDown(e: KeyboardEvent): void {
    if (e.code === "Escape") {
      if (this.gotoTarget) {
        e.preventDefault();
        this.cancelGotoFlight();
      }
      return;
    }

    // Ignore when input/textarea is focused
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    this.animating = false;

    // Navigation keys (WASD, Shift, Space, Ctrl, Q, E, X)
    const navKeys = [
      "KeyW", "KeyA", "KeyS", "KeyD",
      "ShiftLeft", "ShiftRight",
      "Space", "ControlLeft", "ControlRight",
      "KeyQ", "KeyE", "KeyX",
    ];
    if (navKeys.includes(e.code)) {
      this.userInteractionCallback?.();
      e.preventDefault();
      this.keysDown.add(e.code);
      return;
    }

    // Mode toggle
    if (e.code === "KeyF") {
      e.preventDefault();
      this.toggleNavigationMode();
      return;
    }

    // Reset
    if (e.code === "KeyR") {
      e.preventDefault();
      this.resetToOrigin();
      return;
    }

    // Original arrow/zoom keys
    const fovScale = this.hFovDeg / 60;

    let handled = true;
    switch (e.key) {
      case "ArrowLeft": this.orbit(KEY_STEP * fovScale, 0); break;
      case "ArrowRight": this.orbit(-KEY_STEP * fovScale, 0); break;
      case "ArrowUp": this.orbit(0, KEY_STEP * fovScale); break;
      case "ArrowDown": this.orbit(0, -KEY_STEP * fovScale); break;
      case "+": case "=": this.zoomTo(this.hFovDeg / ZOOM_STEP); break;
      case "-": this.zoomTo(this.hFovDeg * ZOOM_STEP); break;
      default: handled = false; break;
    }

    if (handled) {
      this.userInteractionCallback?.();
      e.preventDefault();
    }
  }

  private onKeyUp(e: KeyboardEvent): void {
    this.keysDown.delete(e.code);
  }

  private onBlur(): void {
    this.keysDown.clear();
    this.dragging = false;
  }

  private onVisibilityChange(): void {
    if (document.hidden) {
      this.keysDown.clear();
      this.dragging = false;
    }
  }

  // ─── Movement helpers ──────────────────────────────────────────────

  private hasMovementInput(): boolean {
    return (
      this.keysDown.has("KeyW") ||
      this.keysDown.has("KeyA") ||
      this.keysDown.has("KeyS") ||
      this.keysDown.has("KeyD") ||
      this.keysDown.has("Space") ||
      this.keysDown.has("ControlLeft") ||
      this.keysDown.has("ControlRight")
    );
  }

  /** Get forward and right vectors on the horizontal plane from current azimuth. */
  private getMovementBasis(): {
    forwardE: number; forwardN: number;
    rightE: number; rightN: number;
  } {
    const azRad = this.azimuthDeg * DEG;
    // Forward in ENU: North is azimuth 0
    const forwardE = Math.sin(azRad);
    const forwardN = Math.cos(azRad); // Corrected: cos(0) = 1 → north
    // Right is 90° clockwise from forward
    const rightE = Math.cos(azRad);
    const rightN = -Math.sin(azRad);
    return { forwardE, forwardN, rightE, rightN };
  }

  /** Get full 3D forward and right vectors including pitch (altitudeDeg). */
  private getFlight3DMovementBasis(): {
    forwardE: number; forwardU: number; forwardN: number;
    rightE: number; rightN: number;
  } {
    const azRad = this.azimuthDeg * DEG;
    const altRad = this.altitudeDeg * DEG;
    const cosAlt = Math.cos(altRad);

    // Forward vector in ENU coordinates (+X=East, +Y=Up, +Z=North)
    const forwardE = Math.sin(azRad) * cosAlt;
    const forwardU = Math.sin(altRad);
    const forwardN = Math.cos(azRad) * cosAlt;

    // Right vector on horizontal plane
    const rightE = Math.cos(azRad);
    const rightN = -Math.sin(azRad);

    return { forwardE, forwardU, forwardN, rightE, rightN };
  }

  // ─── Camera matrix ─────────────────────────────────────────────────

  private applyToCamera(): void {
    // Position: ENU → Three.js (East=+X, Up=+Y, North=-Z)
    this.camera.position.set(
      this.positionEastM,
      this.positionUpM,
      -this.positionNorthM,
    );

    const target = setThreeFromAzimuthAltitude(
      new THREE.Vector3(),
      this.azimuthDeg,
      this.altitudeDeg,
    ).add(this.camera.position);
    this.camera.lookAt(target);

    // Apply roll if in flight mode
    if (this.rollDeg !== 0) {
      const rollRad = this.rollDeg * DEG;
      this.camera.rotateZ(-rollRad);
    }

    // Updating a projection matrix per movement frame is avoidable work: the
    // view matrix changes with camera navigation, projection only with FOV or
    // viewport changes.
    const aspect = this.camera.aspect || 1;
    const verticalFov = hFovToVFov(this.hFovDeg, aspect);
    if (Math.abs(this.camera.fov - verticalFov) > 1e-10) {
      this.camera.fov = verticalFov;
      this.camera.updateProjectionMatrix();
    }
  }

  // ─── Throttled pose publishing ─────────────────────────────────────

  private schedulePosePublish(): void {
    this.dirty = true;
    if (this.throttleTimer !== null) return;
    this.throttleTimer = setTimeout(() => {
      this.throttleTimer = null;
      if (this.dirty) {
        this.dirty = false;
        this.publishPoseNow();
      }
    }, THROTTLE_MS);
  }

  private publishPoseNow(): void {
    this.dirty = false;
    this.poseCallback?.(this.pose());
  }

  private scheduleNavigationPosePublish(): void {
    this.navigationPoseDirty = true;
    if (this.navigationPoseTimer !== null) return;
    this.navigationPoseTimer = setTimeout(() => {
      this.navigationPoseTimer = null;
      if (!this.navigationPoseDirty) return;
      this.navigationPoseDirty = false;
      this.publishNavigationPose();
    }, NAVIGATION_POSE_THROTTLE_MS);
  }

  private publishNavigationPose(): void {
    this.navigationPoseCallback?.(this.getNavigationPose(), this.getMotionState());
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function normalizeAzimuth(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

function hFovToVFov(hFovDeg: number, aspect: number): number {
  const hRad = hFovDeg * DEG;
  const vRad = 2 * Math.atan(Math.tan(hRad / 2) / aspect);
  return vRad / DEG;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpAngle(a: number, b: number, t: number): number {
  let diff = ((b - a + 180) % 360) - 180;
  if (diff < -180) diff += 360;
  return normalizeAzimuth(a + diff * t);
}

function approachValue(current: number, target: number, maxDelta: number): number {
  const diff = target - current;
  if (Math.abs(diff) <= maxDelta) return target;
  return current + Math.sign(diff) * maxDelta;
}

/**
 * Converts a Three.js direction vector (ENU: +X=East, +Y=Up, -Z=North)
 * to CameraRig pose (Azimuth/Altitude) using the CameraRig conventions:
 * Azimuth: 0=North, 90=East, 180=South, 270=West
 */
export function threeDirectionToCameraPose(dir: THREE.Vector3): { azimuthDeg: number; altitudeDeg: number } {
  return azimuthAltitudeFromThreeDirection(dir) ?? { azimuthDeg: 0, altitudeDeg: 0 };
}
