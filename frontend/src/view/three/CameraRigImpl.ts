/**
 * Concrete implementation of the CameraRig interface.
 *
 * All camera movement is 100% local to TypeScript — zero round-trips
 * to Python.  Only the final resting pose (end of gesture or throttled
 * updates) is published via a callback.
 *
 * World conventions:
 *   Y = up,  North = -Z,  East = +X
 *   Azimuth 0° = North, clockwise (East = 90°)
 *   Altitude 0° = horizon, +90° = zenith
 */

import * as THREE from "three";
import type { CameraPose, CameraRig } from "./CameraRig";

const DEG = Math.PI / 180;
const MIN_FOV = 1;
const MAX_FOV = 120;
const MIN_ALT = -90;
const MAX_ALT = 90;
const ORBIT_SPEED = 0.25; // deg per CSS pixel
const KEY_STEP = 2; // deg per keypress
const ZOOM_STEP = 1.1; // FOV multiplier per wheel tick
const THROTTLE_MS = 16; // ~60 Hz

export type PoseChangedCallback = (pose: CameraPose) => void;

export class CameraRigImpl implements CameraRig {
  private azimuthDeg = 0;
  private altitudeDeg = 20;
  private hFovDeg = 60;
  private rollDeg = 0;

  private readonly camera: THREE.PerspectiveCamera;
  private container: HTMLElement | null = null;

  private dragging = false;
  private lastX = 0;
  private lastY = 0;

  private poseCallback: PoseChangedCallback | null = null;
  private throttleTimer: ReturnType<typeof setTimeout> | null = null;
  private dirty = false;

  // Smooth transition state
  private animating = false;
  private animStart = 0;
  private animDuration = 0;
  private animFromAz = 0;
  private animFromAlt = 0;
  private animFromFov = 0;
  private animToAz = 0;
  private animToAlt = 0;
  private animToFov = 0;

  // Bound handlers for proper removal
  private readonly onPointerDownBound = this.onPointerDown.bind(this);
  private readonly onPointerMoveBound = this.onPointerMove.bind(this);
  private readonly onPointerUpBound = this.onPointerUp.bind(this);
  private readonly onWheelBound = this.onWheel.bind(this);
  private readonly onKeyDownBound = this.onKeyDown.bind(this);
  private readonly onContextMenuBound = (e: Event) => e.preventDefault();

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

  setPose(p: CameraPose): void {
    this.azimuthDeg = p.azimuthDeg;
    this.altitudeDeg = clamp(p.altitudeDeg, MIN_ALT, MAX_ALT);
    this.hFovDeg = clamp(p.horizontalFovDeg, MIN_FOV, MAX_FOV);
    this.rollDeg = p.rollDeg;
    this.animating = false;
    this.applyToCamera();
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

  // ─── Extended API ──────────────────────────────────────────────────

  /**
   * Animate smoothly from the current pose to a target pose.
   * Used by Python's `set_camera_pose` and `focus_direction`.
   */
  animateTo(
    azDeg: number,
    altDeg: number,
    fovDeg: number,
    durationMs: number,
  ): void {
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

  attach(container: HTMLElement): void {
    this.container = container;
    container.addEventListener("pointerdown", this.onPointerDownBound);
    container.addEventListener("pointermove", this.onPointerMoveBound);
    container.addEventListener("pointerup", this.onPointerUpBound);
    container.addEventListener("pointerleave", this.onPointerUpBound);
    container.addEventListener("wheel", this.onWheelBound, { passive: false });
    container.addEventListener("contextmenu", this.onContextMenuBound);
    window.addEventListener("keydown", this.onKeyDownBound);
  }

  detach(): void {
    if (!this.container) return;
    const c = this.container;
    c.removeEventListener("pointerdown", this.onPointerDownBound);
    c.removeEventListener("pointermove", this.onPointerMoveBound);
    c.removeEventListener("pointerup", this.onPointerUpBound);
    c.removeEventListener("pointerleave", this.onPointerUpBound);
    c.removeEventListener("wheel", this.onWheelBound);
    c.removeEventListener("contextmenu", this.onContextMenuBound);
    window.removeEventListener("keydown", this.onKeyDownBound);
    this.container = null;
    if (this.throttleTimer !== null) {
      clearTimeout(this.throttleTimer);
      this.throttleTimer = null;
    }
  }

  // ─── Input handlers ────────────────────────────────────────────────

  private onPointerDown(e: PointerEvent): void {
    if (e.button !== 0 && e.button !== 2) return;
    this.dragging = true;
    this.lastX = e.clientX;
    this.lastY = e.clientY;
    this.animating = false; // cancel any transition on user input
    this.container?.setPointerCapture(e.pointerId);
  }

  private onPointerMove(e: PointerEvent): void {
    if (!this.dragging) return;
    const dx = e.clientX - this.lastX;
    const dy = e.clientY - this.lastY;
    this.lastX = e.clientX;
    this.lastY = e.clientY;

    // Azimuth: dragging right → increasing azimuth (clockwise)
    // Altitude: dragging up → increasing altitude
    this.orbit(-dx * ORBIT_SPEED, dy * ORBIT_SPEED);
  }

  private onPointerUp(e: PointerEvent): void {
    if (!this.dragging) return;
    this.dragging = false;
    this.container?.releasePointerCapture(e.pointerId);
    // Publish final pose at end of gesture
    this.publishPoseNow();
  }

  private onWheel(e: WheelEvent): void {
    e.preventDefault();
    this.animating = false;
    const factor = e.deltaY > 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
    this.zoomTo(this.hFovDeg * factor);
  }

  private onKeyDown(e: KeyboardEvent): void {
    this.animating = false;
    switch (e.key) {
      case "ArrowLeft":
        this.orbit(KEY_STEP, 0);
        break;
      case "ArrowRight":
        this.orbit(-KEY_STEP, 0);
        break;
      case "ArrowUp":
        this.orbit(0, KEY_STEP);
        break;
      case "ArrowDown":
        this.orbit(0, -KEY_STEP);
        break;
      case "+":
      case "=":
        this.zoomTo(this.hFovDeg / ZOOM_STEP);
        break;
      case "-":
        this.zoomTo(this.hFovDeg * ZOOM_STEP);
        break;
      default:
        return;
    }
    e.preventDefault();
  }

  // ─── Camera matrix ─────────────────────────────────────────────────

  private applyToCamera(): void {
    // Convert azimuth/altitude to a look direction.
    // Azimuth 0 = North (-Z), increases clockwise.
    const azRad = this.azimuthDeg * DEG;
    const altRad = this.altitudeDeg * DEG;

    const cosAlt = Math.cos(altRad);
    const dirX = -Math.sin(azRad) * cosAlt; // East component
    const dirY = Math.sin(altRad); // Up component
    const dirZ = -Math.cos(azRad) * cosAlt; // North component

    // Position camera at origin, look towards the computed direction
    this.camera.position.set(0, 0, 0);

    const target = new THREE.Vector3(dirX, dirY, dirZ);
    this.camera.lookAt(target);

    // Update FOV
    const aspect = this.camera.aspect || 1;
    this.camera.fov = hFovToVFov(this.hFovDeg, aspect);
    this.camera.updateProjectionMatrix();
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
