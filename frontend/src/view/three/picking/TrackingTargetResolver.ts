import { Vector3, MathUtils } from "three";
import type { SelectedCelestial } from "./ScenePickingController";
import type { AstronomicalSearchResultPayload } from "../../../contracts/bridge_messages";
import type { CelestialTransformState } from "../CelestialTransformState";
import type { SolarSystemSnapshot } from "../../../contracts/solar_system_contracts";
import type { SolarSystemRenderer } from "../SolarSystemRenderer";
import { threeDirectionToCameraPose } from "../CameraRigImpl";

export interface ResolvedTrackingDirection {
  azimuthDeg: number;
  altitudeDeg: number;
}

export type TrackingTarget = any;

/**
 * Resol els objectius de seguiment (estrelles, planetes, coordenades fixes)
 * a coordenades topocèntriques actuals (Azimuth/Altitude) basant-se en l'estat
 * científic local, sense necessitat de comunicar-se amb el backend per frame.
 */
export class TrackingTargetResolver {
  private celestialTransform: CelestialTransformState | null = null;
  private latestSnapshot: SolarSystemSnapshot | null = null;
  private solarSystemRenderer: SolarSystemRenderer | null = null;
  
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

  public resolve(target: TrackingTarget): ResolvedTrackingDirection | null {
    if (!target) return null;

    const t = target as any;

    const bodyId = t.bodyId || (t.kind === "body" ? t.targetRef : null);
    if (bodyId) {
      const sol = this.resolveSolarSystem(bodyId);
      if (sol) return sol;
    }
    if (t.raDeg !== undefined && t.decDeg !== undefined) {
      return this.resolveEquatorial(t.raDeg, t.decDeg);
    }
    if (t.coordinateSnapshot) {
      return this.resolveEquatorial(t.coordinateSnapshot.raDeg, t.coordinateSnapshot.decDeg);
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
    
    // Transformació Equatorial (ICRS) -> Topocèntrica Three.js (ENU: +X=East, +Y=Up, -Z=North)
    // NOTA: La matriu equatorialToThree ja fa tota la transformació.
    this._tempVec3.applyMatrix3(this.celestialTransform.equatorialToThree);
    
    // Centralitzat amb la mateixa matemàtica de CameraRigImpl
    return threeDirectionToCameraPose(this._tempVec3);
  }

  private resolveSolarSystem(bodyId: string): ResolvedTrackingDirection | null {
    if (!this.solarSystemRenderer) return null;
    
    // Usem la posició visual interpolada exacta usada pel render, per evitar jitter
    const dir = this.solarSystemRenderer.getDisplayedBodyDirection(bodyId as any);
    if (!dir) return null;
    
    // Centralitzat amb la mateixa matemàtica de CameraRigImpl
    return threeDirectionToCameraPose(dir);
  }
}
