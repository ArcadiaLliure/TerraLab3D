/**
 * TerrainSampler — surface query abstraction.
 *
 * This interface is the SOLE extension point for terrain data.
 * Today it is implemented by TechnicalTerrainSampler (raycaster).
 * In the future, DEMTerrainSampler will replace it without modifying
 * any consumer (GroundFollower, NavigationController, HUD, etc.).
 *
 * TerrainSampler is ONLY responsible for answering:
 *   "What navigable surface exists at this location?"
 *
 * It is NOT responsible for:
 *   - acceleration, movement, velocity
 *   - camera positioning or smoothing
 *   - collision resolution
 *   - mode changes
 */

// ─── Ground Sample ───────────────────────────────────────────────────

/** Result of querying the terrain at a specific horizontal position. */
export interface GroundSample {
  /** Height of the surface above the local reference plane, in metres. */
  heightM: number;

  /** Surface normal in ENU coordinates (+X=East, +Y=Up, -Z=North). */
  normal: {
    east: number;
    up: number;
    north: number;
  };

  /** Slope angle of the surface in degrees (0 = flat, 90 = vertical wall). */
  slopeDeg: number;

  /** Whether this sample represents valid, navigable terrain. */
  valid: boolean;

  /** Optional identifier for the surface type (e.g. "terrain", "platform"). */
  surfaceId?: string;
}

// ─── TerrainSampler Interface ────────────────────────────────────────

/**
 * Abstract terrain query contract.
 *
 * All navigation code depends on this interface, never on concrete
 * implementations (TechnicalTerrainSampler, DEMTerrainSampler, etc.).
 */
export interface TerrainSampler {
  /**
   * Query the ground surface at a horizontal position.
   *
   * @param eastM    East coordinate in metres from origin.
   * @param northM   North coordinate in metres from origin.
   * @param referenceUpM  Optional hint: approximate height of the querier,
   *                      useful for implementations that cast rays downward.
   * @returns  GroundSample if terrain exists at this position, or null
   *           if the position is outside the prepared zone or invalid.
   */
  sampleGround(
    eastM: number,
    northM: number,
    referenceUpM?: number,
  ): GroundSample | null;

  /** Whether the sampler is initialized and ready to answer queries. */
  isReady(): boolean;
}
