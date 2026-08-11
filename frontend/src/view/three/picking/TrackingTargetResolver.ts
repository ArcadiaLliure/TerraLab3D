import { Vector3, MathUtils } from "three";
import type { SelectedCelestial } from "./ScenePickingController";
import type { AstronomicalSearchResultPayload } from "../../../contracts/bridge_messages";
import type { CelestialTransformState } from "../CelestialTransformState";
import type { SolarSystemSnapshot } from "../../../contracts/solar_system_contracts";

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
  
  // Vector temporal per evitar instanciacions
  private readonly _tempVec3 = new Vector3();

  public updateCelestialTransform(transform: CelestialTransformState): void {
    this.celestialTransform = transform;
  }

  public updateSolarSystemSnapshot(snapshot: SolarSystemSnapshot): void {
    this.latestSnapshot = snapshot;
  }

  public resolve(target: TrackingTarget): ResolvedTrackingDirection | null {
    if (!target) return null;

    const t = target as any;

    if (t.bodyId) {
      return this.resolveSolarSystem(t.bodyId);
    }
    if (t.targetRef && t.kind === "body") {
      return this.resolveSolarSystem(t.targetRef);
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
    
    // Convertir RA/Dec a Vector3 i aplicar matriu de transformació
    const phi = MathUtils.degToRad(90 - decDeg);
    const theta = MathUtils.degToRad(raDeg);
    
    this._tempVec3.setFromSphericalCoords(1.0, phi, theta);
    
    // Transformació Equatorial (ICRS) -> Topocèntrica (ENU)
    this._tempVec3.applyMatrix3(this.celestialTransform.equatorialToThree);
    
    // Convertir de nou a esfèriques per obtenir Az/Alt
    // En el nostre sistema ENU (ThreeJS): x=Est, y=Amunt, z=-Nord
    // l'Azimuth 0 és Nord, creix cap a l'Est.
    const altDeg = MathUtils.radToDeg(Math.asin(this._tempVec3.y));
    const azDeg = MathUtils.radToDeg(Math.atan2(this._tempVec3.x, -this._tempVec3.z));
    
    // En CameraRigImpl: 0=Nord, 90=Oest, 180=Sud, 270=Est
    // atan2 dóna 90 per a Est (+X). Ho hem de mapejar a 270.
    const rigAz = 360 - azDeg;
    
    return {
      azimuthDeg: rigAz >= 360 ? rigAz - 360 : rigAz,
      altitudeDeg: altDeg
    };
  }

  private resolveSolarSystem(bodyId: string): ResolvedTrackingDirection | null {
    if (!this.latestSnapshot) return null;
    
    let state = null;
    if (bodyId === "sun") {
      state = this.latestSnapshot.sun;
    } else if (bodyId === "moon") {
      state = this.latestSnapshot.moon;
    } else {
      state = this.latestSnapshot.planets.find(b => b.id === bodyId) ||
              (this.latestSnapshot.satellites || []).find(b => b.id === bodyId);
    }
    
    if (!state) return null;
    
    // El snapshot ja conté la posició aparent respecte l'observador.
    // L'Azimuth ja és Topocèntric i Altitude també.
    return {
      azimuthDeg: (360 - state.azimuthDeg) % 360,
      altitudeDeg: state.altitudeDeg
    };
  }
}
