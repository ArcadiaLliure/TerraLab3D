/**
 * HorizontalGrid — Quadrícula azimut-altura persistent amb LODs.
 *
 * Implementa una quadrícula horitzontal fixa en el marc ENU de l'observador.
 * No gira amb el temps sideral. No presenta paral·laxi per translació local.
 *
 * Convenció ENU → Three.js:
 *   +X = Est,  +Y = Amunt,  -Z = Nord
 *   Azimut 0° = Nord, sentit horari (Est = 90°)
 *
 * LOD:
 *   coarse  — FOV > 80°:  azimut cada 30°, altitud cada 30°
 *   medium  — FOV 30-80°: azimut cada 15°, altitud cada 15°
 *   fine    — FOV < 30°:  azimut cada 5°,  altitud cada 5°
 *
 * La geometria es construeix una sola vegada per LOD. El canvi de FOV
 * només activa/desactiva grups. La càmera es mou sense reconstruir buffers.
 */

import * as THREE from "three";

const LOG_PREFIX = "MGP: [HorizontalGrid]";

// ─── Constants ───────────────────────────────────────────────────────

const GRID_RADIUS = 1000000;
const CIRCLE_SEGMENTS = 128;
const DEG = Math.PI / 180;

// LOD thresholds with hysteresis
const LOD_FINE_ENTER = 30;       // Enter fine when FOV < 30
const LOD_FINE_EXIT = 35;        // Exit fine when FOV > 35
const LOD_COARSE_ENTER = 80;     // Enter coarse when FOV > 80
const LOD_COARSE_EXIT = 75;      // Exit coarse when FOV < 75

// Colors
const HORIZON_COLOR = 0x66aacc;
const GRID_COLOR = 0x334466;
const GRID_MINOR_COLOR = 0x223344;
const ZENITH_COLOR = 0xf1cd88;

type GridLODLevel = "coarse" | "medium" | "fine";

interface GridLOD {
  group: THREE.Group;
  azimuthStepDeg: number;
  altitudeStepDeg: number;
  built: boolean;
}

export class HorizontalGrid {
  /** Root group to add to celestialRoot. */
  readonly root: THREE.Group;

  private readonly lods: Map<GridLODLevel, GridLOD> = new Map();
  private currentLOD: GridLODLevel = "medium";

  // Horizon ring — always visible regardless of LOD
  private readonly horizonRing: THREE.LineLoop;
  // Zenith marker — always visible
  private readonly zenithMarker: THREE.Mesh;

  // ─── Metrics ────────────────────────────────────────────────
  private _geometryBuildCount = 0;
  private _lodSwitchCount = 0;
  private _bufferUploadBytes = 0;

  get geometryBuildCount(): number { return this._geometryBuildCount; }
  get lodSwitchCount(): number { return this._lodSwitchCount; }
  get bufferUploadBytes(): number { return this._bufferUploadBytes; }

  constructor() {
    this.root = new THREE.Group();
    this.root.name = "horizontalGridRoot";

    // ─── Horizon ring (alt = 0°, always visible) ─────────────
    const horizonGeo = this.createAltitudeCircle(0);
    const horizonMat = new THREE.LineBasicMaterial({
      color: HORIZON_COLOR,
      transparent: true,
      opacity: 0.7,
    });
    this.horizonRing = new THREE.LineLoop(horizonGeo, horizonMat);
    this.horizonRing.name = "horizonRing_alt0";
    this.root.add(this.horizonRing);

    // ─── Zenith marker ───────────────────────────────────────
    const zenithGeo = new THREE.SphereGeometry(1.5, 12, 8);
    const zenithMat = new THREE.MeshBasicMaterial({ color: ZENITH_COLOR });
    this.zenithMarker = new THREE.Mesh(zenithGeo, zenithMat);
    this.zenithMarker.position.set(0, GRID_RADIUS * 0.98, 0);
    this.zenithMarker.name = "zenithMarker";
    this.root.add(this.zenithMarker);

    // ─── Build all LODs persistently ─────────────────────────
    this.buildLOD("coarse", 30, 30);
    this.buildLOD("medium", 15, 15);
    this.buildLOD("fine", 5, 5);

    // Start with medium visible
    this.setActiveLOD("medium");

    console.info(
      `${LOG_PREFIX} [constructor] [Geometria construïda: ${this._geometryBuildCount} builds, ${this._bufferUploadBytes} bytes]`,
    );
  }

  // ─── Public API ─────────────────────────────────────────────

  /**
   * Update LOD based on current FOV. Called from render loop (not every frame
   * if throttled, but safe to call every frame — only switches when needed).
   */
  updateLOD(hFovDeg: number): void {
    let targetLOD = this.currentLOD;

    if (this.currentLOD === "medium") {
      if (hFovDeg < LOD_FINE_ENTER) targetLOD = "fine";
      else if (hFovDeg > LOD_COARSE_ENTER) targetLOD = "coarse";
    } else if (this.currentLOD === "fine") {
      if (hFovDeg > LOD_FINE_EXIT) targetLOD = "medium";
    } else if (this.currentLOD === "coarse") {
      if (hFovDeg < LOD_COARSE_EXIT) targetLOD = "medium";
    }

    if (targetLOD !== this.currentLOD) {
      this.setActiveLOD(targetLOD);
      this._lodSwitchCount++;
      console.info(
        `${LOG_PREFIX} [updateLOD] [LOD canviat: ${this.currentLOD} fov=${hFovDeg.toFixed(1)}°]`,
      );
    }
  }

  setVisible(visible: boolean): void {
    this.root.visible = visible;
  }

  getActiveLOD(): GridLODLevel {
    return this.currentLOD;
  }

  dispose(): void {
    this.root.traverse((obj) => {
      if (
        obj instanceof THREE.Mesh ||
        obj instanceof THREE.LineSegments ||
        obj instanceof THREE.LineLoop ||
        obj instanceof THREE.Line
      ) {
        obj.geometry.dispose();
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose());
        } else {
          obj.material.dispose();
        }
      }
    });
    console.info(`${LOG_PREFIX} [dispose] [Recursos alliberats]`);
  }

  // ─── Private ───────────────────────────────────────────────

  private buildLOD(level: GridLODLevel, azStep: number, altStep: number): void {
    const group = new THREE.Group();
    group.name = `gridLOD_${level}`;

    // Altitude circles (skip 0° — that's the always-visible horizon ring)
    for (let alt = altStep; alt < 90; alt += altStep) {
      // Positive altitude
      const circGeo = this.createAltitudeCircle(alt);
      const isPrimary = alt % 30 === 0;
      const mat = new THREE.LineBasicMaterial({
        color: isPrimary ? GRID_COLOR : GRID_MINOR_COLOR,
        transparent: true,
        opacity: isPrimary ? 0.4 : 0.2,
      });
      const line = new THREE.LineLoop(circGeo, mat);
      line.name = `altCircle_${alt}`;
      group.add(line);
      this._bufferUploadBytes += circGeo.getAttribute("position").array.byteLength;

      // Negative altitude (below horizon — useful for flight mode)
      const circGeoNeg = this.createAltitudeCircle(-alt);
      const matNeg = new THREE.LineBasicMaterial({
        color: GRID_MINOR_COLOR,
        transparent: true,
        opacity: 0.1,
      });
      const lineNeg = new THREE.LineLoop(circGeoNeg, matNeg);
      lineNeg.name = `altCircle_neg${alt}`;
      group.add(lineNeg);
      this._bufferUploadBytes += circGeoNeg.getAttribute("position").array.byteLength;
    }

    // Azimuth meridians (semicircles from nadir through zenith)
    for (let az = 0; az < 360; az += azStep) {
      const merGeo = this.createAzimuthMeridian(az);
      const isCardinal = az % 90 === 0;
      const isPrimary = az % 30 === 0;
      const mat = new THREE.LineBasicMaterial({
        color: isCardinal ? GRID_COLOR : (isPrimary ? GRID_COLOR : GRID_MINOR_COLOR),
        transparent: true,
        opacity: isCardinal ? 0.5 : (isPrimary ? 0.3 : 0.15),
      });
      const line = new THREE.Line(merGeo, mat);
      line.name = `azMeridian_${az}`;
      group.add(line);
      this._bufferUploadBytes += merGeo.getAttribute("position").array.byteLength;
    }

    this.root.add(group);
    this.lods.set(level, { group, azimuthStepDeg: azStep, altitudeStepDeg: altStep, built: true });
    this._geometryBuildCount++;
  }

  private setActiveLOD(level: GridLODLevel): void {
    for (const [key, lod] of this.lods) {
      lod.group.visible = key === level;
    }
    this.currentLOD = level;
  }

  /**
   * Create a circle at the given altitude on the celestial sphere.
   * alt=0° → horizon (Y=0, radius=GRID_RADIUS)
   * alt=90° → zenith (single point at Y=GRID_RADIUS)
   */
  private createAltitudeCircle(altDeg: number): THREE.BufferGeometry {
    const altRad = altDeg * DEG;
    const r = GRID_RADIUS * Math.cos(altRad);
    const y = GRID_RADIUS * Math.sin(altRad);

    const geo = new THREE.BufferGeometry();
    const verts = new Float32Array((CIRCLE_SEGMENTS + 1) * 3);

    for (let i = 0; i <= CIRCLE_SEGMENTS; i++) {
      // Azimuth angle in Three.js: 0°=North=-Z, clockwise
      const theta = (i / CIRCLE_SEGMENTS) * Math.PI * 2;
      // x = r * sin(theta) → East when theta=90°
      // z = -r * cos(theta) → North when theta=0°
      verts[i * 3] = Math.sin(theta) * r;       // X = East
      verts[i * 3 + 1] = y;                      // Y = Up
      verts[i * 3 + 2] = -Math.cos(theta) * r;  // Z = -North
    }

    geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    return geo;
  }

  /**
   * Create an azimuth meridian — a semicircle from horizon through zenith
   * at the given azimuth angle.
   */
  private createAzimuthMeridian(azDeg: number): THREE.BufferGeometry {
    const azRad = azDeg * DEG;
    const sinAz = Math.sin(azRad);
    const cosAz = Math.cos(azRad);

    const halfSegments = CIRCLE_SEGMENTS;
    const geo = new THREE.BufferGeometry();
    const verts = new Float32Array((halfSegments + 1) * 3);

    for (let i = 0; i <= halfSegments; i++) {
      // Go from alt=-90° (nadir) to alt=+90° (zenith)
      const altRad = ((i / halfSegments) * Math.PI) - Math.PI / 2;
      const cosAlt = Math.cos(altRad);
      const sinAlt = Math.sin(altRad);

      // Direction in Three.js world:
      // East = +X = sin(az) * cos(alt)
      // Up = +Y = sin(alt)
      // North = -Z = cos(az) * cos(alt) → z = -cos(az) * cos(alt)
      verts[i * 3] = sinAz * cosAlt * GRID_RADIUS;     // X
      verts[i * 3 + 1] = sinAlt * GRID_RADIUS;          // Y
      verts[i * 3 + 2] = -cosAz * cosAlt * GRID_RADIUS; // Z
    }

    geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    return geo;
  }
}
