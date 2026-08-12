import { Vector3, MathUtils } from "three";
import type { SolarSystemSnapshot } from "../../../contracts/solar_system_contracts";
import type { SolarSystemRenderer } from "../SolarSystemRenderer";
import type { StarFieldRenderer } from "../StarFieldRenderer";
import type { DeepSkyRenderer } from "../DeepSkyRenderer";
import { threeDirectionToCameraPose } from "../CameraRigImpl";
import type { CelestialTargetRef } from "../../../contracts/celestial_selection_contracts";
import type { CelestialTransformState } from "../CelestialTransformState";

export interface ResolvedTrackingDirection {
  azimuthDeg: number;
  altitudeDeg: number;
}

/**
 * Resol els objectius de seguiment (estrelles, planetes, coordenades fixes)
 * a coordenades topocèntriques actuals (Azimuth/Altitude) basant-se en l'estat
 * científic local, sense necessitat de comunicar-se amb el backend per frame.
 */
export class TrackingTargetResolver {
  private celestialTransform: CelestialTransformState | null = null;
  private latestSnapshot: SolarSystemSnapshot | null = null;
  private solarSystemRenderer: SolarSystemRenderer | null = null;
  private starRenderer: StarFieldRenderer | null = null;
  private deepSkyRenderer: DeepSkyRenderer | null = null;
  
  // Vector temporal per evitar instanciacions
  private readonly _tempVec3 = new Vector3();

  public updateCelestialTransform(transform: CelestialTransformState): void {
    this.celestialTransform = transform;
  }

  public updateSolarSystemSnapshot(snapshot: SolarSystemSnapshot): void {
    this.latestSnapshot = snapshot;
  }

  public updateSolarSystemRenderer(renderer: SolarSystemRenderer): void {
    this.solarSystemRenderer = renderer;
  }

  public updateStarRenderer(renderer: StarFieldRenderer): void {
    this.starRenderer = renderer;
  }

  public updateDeepSkyRenderer(renderer: DeepSkyRenderer): void {
    this.deepSkyRenderer = renderer;
  }

  public resolve(target: CelestialTargetRef | null): ResolvedTrackingDirection | null {
    if (!target) return null;

    if (target.kind === "solar_system") {
      const sol = this.resolveSolarSystem(target.bodyId);
      if (sol) return sol;
    }
    
    // Si el target té coordenades exactes associades, usa-les sempre per evitar el jitter de Float32!
    if ('raDeg' in target && typeof target.raDeg === 'number' && 'decDeg' in target && typeof target.decDeg === 'number') {
      return this.resolveEquatorial(target.raDeg, target.decDeg);
    }
    
    if (target.kind === "coordinate") {
      return this.resolveEquatorial(target.raDeg, target.decDeg);
    }
    if (target.kind === "star") {
      return this.resolveStar(target.resourceId, target.catalogIndex);
    }
    if (target.kind === "deep_sky") {
      return this.resolveDeepSky(target.resourceId, target.catalogIndex);
    }

    return null;
  }

  private resolveEquatorial(raDeg: number, decDeg: number): ResolvedTrackingDirection | null {
    if (!this.celestialTransform) return null;
    
    const ra = MathUtils.degToRad(raDeg);
    const dec = MathUtils.degToRad(decDeg);
    const cosDec = Math.cos(dec);
    
    // Convertir RA/Dec a Vector3 usant la mateixa convenció que backend/domain/stars/calculations.py
    // X = cos(dec) * cos(ra)
    // Y = cos(dec) * sin(ra)
    // Z = sin(dec)
    this._tempVec3.set(
      cosDec * Math.cos(ra),
      cosDec * Math.sin(ra),
      Math.sin(dec)
    );
    
    // Transformació Equatorial (ICRS) -> Topocèntrica ENU
    this._tempVec3.applyMatrix3(this.celestialTransform.equatorialToThree);
    
    // ENU: x=East, y=North, z=Up. Three.js: x=East, y=Up, z=-North
    const e = this._tempVec3.x;
    const n = this._tempVec3.y;
    const u = this._tempVec3.z;
    this._tempVec3.set(e, u, -n);
    
    return threeDirectionToCameraPose(this._tempVec3);
  }

  private resolveStar(resourceId: string, catalogIndex: number): ResolvedTrackingDirection | null {
    if (!this.starRenderer || !this.celestialTransform) return null;
    const resource = this.starRenderer.getResource(resourceId);
    if (!resource || !resource.equatorialPositions) return null;

    const count = resource.starCount;
    if (catalogIndex >= count) return null;

    const eqDirs = resource.equatorialPositions;
    const vx = eqDirs[catalogIndex * 3]!;
    const vy = eqDirs[catalogIndex * 3 + 1]!;
    const vz = eqDirs[catalogIndex * 3 + 2]!;

    this._tempVec3.set(vx, vy, vz);
    this._tempVec3.applyMatrix3(this.celestialTransform.equatorialToThree);
    
    // ENU: x=East, y=North, z=Up. Three.js: x=East, y=Up, z=-North
    const e = this._tempVec3.x;
    const n = this._tempVec3.y;
    const u = this._tempVec3.z;
    this._tempVec3.set(e, u, -n);
    
    return threeDirectionToCameraPose(this._tempVec3);
  }

  private resolveDeepSky(resourceId: string, catalogIndex: number): ResolvedTrackingDirection | null {
    if (!this.deepSkyRenderer || !this.celestialTransform) return null;
    const { metadata, payloadBuffer, catalogIndexToBufferIndex } = this.deepSkyRenderer;
    if (!metadata || !payloadBuffer || metadata.resourceId !== resourceId) return null;

    const idx = catalogIndexToBufferIndex.get(catalogIndex);
    if (idx === undefined) return null;

    const count = metadata.renderableCount ?? metadata.recordCount;
    const layout = metadata.bufferLayout;
    const eqDirs = new Float32Array(payloadBuffer, layout.equatorialDirections.offset, count * 3);
    
    const vx = eqDirs[idx * 3]!;
    const vy = eqDirs[idx * 3 + 1]!;
    const vz = eqDirs[idx * 3 + 2]!;

    this._tempVec3.set(vx, vy, vz);
    this._tempVec3.applyMatrix3(this.celestialTransform.equatorialToThree);
    
    // ENU: x=East, y=North, z=Up. Three.js: x=East, y=Up, z=-North
    const e = this._tempVec3.x;
    const n = this._tempVec3.y;
    const u = this._tempVec3.z;
    this._tempVec3.set(e, u, -n);
    
    return threeDirectionToCameraPose(this._tempVec3);
  }

  private resolveSolarSystem(id: string): ResolvedTrackingDirection | null {
    if (!this.solarSystemRenderer) return null;

    // Usem la posició visual interpolada exacta usada pel render, per evitar jitter
    // i evitar problemes amb vectors no normalitzats que causen clamp de càmera.
    const dir = this.solarSystemRenderer.getDisplayedBodyDirection(id as any);
    if (!dir) return null;

    return threeDirectionToCameraPose(dir);
  }
}
