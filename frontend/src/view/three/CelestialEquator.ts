/**
 * CelestialEquator — Corba de l'equador celeste projectat.
 *
 * Reimplementa el comportament de `draw_celestial_grid()` de TerraLab:
 * una única corba que representa l'equador celeste projectat en coordenades
 * horitzontals. La posició de la corba depèn de la latitud i el LST.
 *
 * La geometria es construeix una sola vegada. L'actualització amb LST
 * es fa per transformació (rotació del grup), no per reconstrucció.
 *
 * Col·locada a celestialRoot.equatorialReferenceRoot.
 */

import * as THREE from "three";

const LOG_PREFIX = "MGP: [CelestialEquator]";

const SPHERE_RADIUS = 500;
const SEGMENTS = 128;
const DEG = Math.PI / 180;

export class CelestialEquator {
  /** Root group to add to celestialRoot. */
  readonly root: THREE.Group;

  private readonly equatorLine: THREE.Line;
  private readonly positionAttr: THREE.BufferAttribute;
  private currentLatRad = 0;
  private currentLstRad = 0;
  private needsUpdate = true;

  private _geometryBuildCount = 0;
  get geometryBuildCount(): number { return this._geometryBuildCount; }

  constructor() {
    this.root = new THREE.Group();
    this.root.name = "equatorialReferenceRoot";

    // Create buffer geometry — positions will be computed in updateCurve()
    const geo = new THREE.BufferGeometry();
    const verts = new Float32Array((SEGMENTS + 1) * 3);
    this.positionAttr = new THREE.BufferAttribute(verts, 3);
    geo.setAttribute("position", this.positionAttr);

    const mat = new THREE.LineBasicMaterial({
      color: 0x00cccc,
      transparent: true,
      opacity: 0.4,
      depthWrite: false,
    });

    this.equatorLine = new THREE.Line(geo, mat);
    this.equatorLine.name = "celestialEquator";
    this.equatorLine.renderOrder = -800;
    this.root.add(this.equatorLine);

    this._geometryBuildCount++;
    console.info(`${LOG_PREFIX} [constructor] [Geometria de l'equador celeste construïda]`);
  }

  // ─── Public API ─────────────────────────────────────────────

  /**
   * Set observer latitude. Only triggers recalculation when latitude changes.
   * Latitude changes rarely — only on relocation.
   */
  setLatitude(latDeg: number): void {
    const latRad = latDeg * DEG;
    if (Math.abs(latRad - this.currentLatRad) > 1e-6) {
      this.currentLatRad = latRad;
      this.needsUpdate = true;
    }
  }

  /**
   * Set LST (Local Sidereal Time). Triggers recalculation.
   * Called when time changes (timeline drag, realtime tick).
   */
  setLST(lstDeg: number): void {
    const lstRad = lstDeg * DEG;
    if (Math.abs(lstRad - this.currentLstRad) > 1e-6) {
      this.currentLstRad = lstRad;
      this.needsUpdate = true;
    }
  }

  /**
   * Recompute the equator curve if parameters changed.
   * Called from the render loop at a reasonable rate.
   */
  update(): void {
    if (!this.needsUpdate) return;
    this.needsUpdate = false;
    this.computeEquatorCurve();
  }

  setVisible(visible: boolean): void {
    this.root.visible = visible;
  }

  dispose(): void {
    this.equatorLine.geometry.dispose();
    if (Array.isArray(this.equatorLine.material)) {
      this.equatorLine.material.forEach((m) => m.dispose());
    } else {
      this.equatorLine.material.dispose();
    }
    console.info(`${LOG_PREFIX} [dispose] [Recursos alliberats]`);
  }

  // ─── Private ──────────────────────────────────────────────────

  /**
   * Compute the celestial equator as seen from the observer's location.
   *
   * The celestial equator (dec=0°) traces a curve in horizontal coordinates
   * that depends on latitude and LST. This mirrors TerraLab's algorithm:
   *
   * For each RA step:
   *   ha = lst - ra
   *   sin_alt = cos(lat) * cos(ha)
   *   alt = asin(sin_alt)
   *   cos_az = (-sin_alt * sin(lat)) / (cos(alt) * cos(lat))
   *   az = acos(cos_az), flipped if sin(ha) > 0
   */
  private computeEquatorCurve(): void {
    const verts = this.positionAttr.array as Float32Array;
    const cosLat = Math.cos(this.currentLatRad);
    const sinLat = Math.sin(this.currentLatRad);

    for (let i = 0; i <= SEGMENTS; i++) {
      const ra = (i / SEGMENTS) * 360.0;
      const ha = this.currentLstRad - ra * DEG;

      const sinAlt = cosLat * Math.cos(ha);
      const alt = Math.asin(Math.max(-1, Math.min(1, sinAlt)));
      const cosAlt = Math.cos(alt);

      let az = 0;
      if (cosAlt * cosLat > 1e-10) {
        const cosAz = (-sinAlt * sinLat) / (cosAlt * cosLat + 1e-10);
        az = Math.acos(Math.max(-1, Math.min(1, cosAz)));
        if (Math.sin(ha) > 0) {
          az = Math.PI * 2 - az;
        }
      }

      // Convert (az, alt) to Three.js world coords on sphere
      const cosAltF = Math.cos(alt);
      const sinAltF = Math.sin(alt);
      verts[i * 3] = Math.sin(az) * cosAltF * SPHERE_RADIUS;       // X = East
      verts[i * 3 + 1] = sinAltF * SPHERE_RADIUS;                   // Y = Up
      verts[i * 3 + 2] = -Math.cos(az) * cosAltF * SPHERE_RADIUS;  // Z = -North
    }

    this.positionAttr.needsUpdate = true;
    this.equatorLine.geometry.computeBoundingSphere();
  }
}
