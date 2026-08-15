/**
 * Navigation contracts for Phase 3.5 — Camera translation.
 *
 * Defines the data model for translational camera movement across two modes:
 *   - Walk: surface-bound locomotion with terrain following.
 *   - Flight: free 3D movement with terrain clearance.
 *
 * World conventions (ENU):
 *   +X = East,  +Y = Up,  -Z = North
 *   Azimuth 0° = North, clockwise (East = 90°)
 */

// ─── Navigation Mode ─────────────────────────────────────────────────

export type NavigationMode = "walk" | "flight";

// ─── Camera Pose (Physical) ──────────────────────────────────────────

/** Full camera pose including translational position in ENU metres. */
export interface NavigationCameraPose {
  /** Position east of origin, in metres. */
  positionEastM: number;
  /** Position above local reference plane, in metres. */
  positionUpM: number;
  /** Position north of origin, in metres (mapped to -Z in Three.js). */
  positionNorthM: number;

  /** Azimuth look direction, 0° = North, clockwise. */
  azimuthDeg: number;
  /** Altitude (pitch), 0° = horizon, +90° = zenith. */
  altitudeDeg: number;
  /** Roll, 0° = level. Only non-zero in flight mode. */
  rollDeg: number;
  /** Horizontal field of view, in degrees. */
  fovDeg: number;
  /** Current navigation mode. */
  navigationMode: NavigationMode;
}

/** Creates a default pose at origin, looking north. */
export function defaultNavigationCameraPose(): NavigationCameraPose {
  return {
    positionEastM: 0,
    positionUpM: 0,
    positionNorthM: 0,
    azimuthDeg: 0,
    altitudeDeg: 20,
    rollDeg: 0,
    fovDeg: 60,
    navigationMode: "walk",
  };
}

// ─── Walk Settings ───────────────────────────────────────────────────

export interface WalkNavigationSettings {
  eyeHeightM: number;
  walkSpeedMps: number;
  sprintSpeedMps: number;
  accelerationMps2: number;
  decelerationMps2: number;
  maximumStepHeightM: number;
  maximumWalkableSlopeDeg: number;
  groundProbeDistanceM: number;
  /** Lerp factor for CameraVisualSmoother vertical damping. 0..1 per frame. */
  visualGroundSmoothing: number;
}

export const DEFAULT_WALK_SETTINGS: Readonly<WalkNavigationSettings> = {
  eyeHeightM: 1.70,
  walkSpeedMps: 4.00,
  sprintSpeedMps: 10.00,
  accelerationMps2: 18.00,
  decelerationMps2: 24.00,
  maximumStepHeightM: 0.50,
  maximumWalkableSlopeDeg: 45,
  groundProbeDistanceM: 50.0,
  visualGroundSmoothing: 0.15,
};

// ─── Flight Settings ─────────────────────────────────────────────────

export interface FlightNavigationSettings {
  minimumSpeedMps: number;
  cruiseSpeedMps: number;
  maximumSpeedMps: number;
  accelerationMps2: number;
  brakingMps2: number;
  climbRateMps: number;
  descentRateMps: number;
  maximumPitchDeg: number;
  maximumRollDeg: number;
  minimumClearanceM: number;
  maximumAltitudeM: number;
  autoLevelRoll: boolean;
  autoLevelPitch: boolean;
}

export const DEFAULT_FLIGHT_SETTINGS: Readonly<FlightNavigationSettings> = {
  minimumSpeedMps: 0,
  cruiseSpeedMps: 150,
  maximumSpeedMps: 250,
  accelerationMps2: 90,
  brakingMps2: 120,
  climbRateMps: 60,
  descentRateMps: 60,
  maximumPitchDeg: 80,
  maximumRollDeg: 45,
  minimumClearanceM: 2,
  maximumAltitudeM: 10000,
  autoLevelRoll: true,
  autoLevelPitch: true,
};

// ─── Scientific Observer (separate from camera) ──────────────────────

export interface ScientificObserver {
  latitudeDeg: number;
  longitudeDeg: number;
  terrainElevationM: number | null;
  observerOffsetM: number;
}

// ─── Navigation Envelope ─────────────────────────────────────────────

export type NavigationReadiness =
  | "empty"
  | "loading"
  | "world_ready"
  | "collision_ready"
  | "navigation_ready"
  | "error";

export interface NavigationEnvelope {
  centerEastM: number;
  centerNorthM: number;
  minimumUpM: number;
  maximumUpM: number;
  horizontalRadiusM: number;
  readiness: NavigationReadiness;
  generation: number;
}

// ─── Motion State ────────────────────────────────────────────────────

export interface MotionState {
  moving: boolean;
  sprinting: boolean;
  speedMps: number;
  velocityEast: number;
  velocityUp: number;
  velocityNorth: number;
}

// ─── Bounds feedback ─────────────────────────────────────────────────

export type BoundsDirection = "north" | "south" | "east" | "west" | "up" | "down";

export interface BoundsState {
  atLimit: boolean;
  direction?: BoundsDirection;
}
