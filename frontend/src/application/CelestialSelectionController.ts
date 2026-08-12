import { 
  type CelestialTargetRef, 
  type CelestialSelectionState,
  type SelectionSource
} from "../contracts/celestial_selection_contracts";
import type { CelestialPickHit } from "../view/three/picking/CelestialPickProvider";
import type { AstronomicalSearchResultPayload } from "../contracts/bridge_messages";
import type { ResolvedStar } from "../contracts/star_picking_contracts";

const LOG_PREFIX = "MGP: [CelestialSelectionController]";

export type SelectionChangedCallback = (state: CelestialSelectionState) => void;

export class CelestialSelectionController {
  private state: CelestialSelectionState = {
    generation: 0,
    selectedTarget: null,
    source: null,
    availability: "available"
  };
  
  private listeners: Set<SelectionChangedCallback> = new Set();
  private disposed = false;

  constructor() {}

  public subscribe(callback: SelectionChangedCallback): () => void {
    this.listeners.add(callback);
    callback(this.state);
    return () => {
      this.listeners.delete(callback);
    };
  }

  public getState(): CelestialSelectionState {
    return this.state;
  }

  public select(target: CelestialTargetRef | null, source: SelectionSource): void {
    if (this.disposed) return;
    
    // Si és el mateix target, actualitzem la font (per si de cas) i notifiquem igualment
    // perquè l'usuari podria haver fet pan i voler re-centrar l'objecte fent-hi click de nou.
    
    console.log(`${LOG_PREFIX} Selection changed:`, target, `Source:`, source);
    this.updateState({
      generation: this.state.generation + 1,
      selectedTarget: target,
      source: target ? source : null,
      availability: target ? "available" : "unavailable"
    });
  }

  public clearSelection(): void {
    this.select(null, "external");
  }

  /**
   * Cridat quan una resolució asíncrona de Gaia proporciona el `sourceId` canònic
   * i metadata, que volem adjuntar al target.
   */
  public updateStarTargetWithSourceId(resourceId: string, catalogIndex: number, sourceId: string): void {
    const current = this.state.selectedTarget;
    if (
      current?.kind === "star" && 
      current.resourceId === resourceId && 
      current.catalogIndex === catalogIndex
    ) {
      if (current.sourceId !== sourceId) {
        this.updateState({
          selectedTarget: {
            ...current,
            sourceId
          }
        });
      }
    }
  }

  /**
   * Cridat pel lifecycle quan un recurs s'elimina
   */
  public handleResourceEviction(resourceId: string): void {
    const target = this.state.selectedTarget;
    if (!target) return;
    
    if (
      (target.kind === "star" && target.resourceId === resourceId) ||
      (target.kind === "deep_sky" && target.resourceId === resourceId)
    ) {
      console.log(`${LOG_PREFIX} Selecció invàlida per eviction del recurs ${resourceId}`);
      this.updateState({ availability: "unavailable" });
    }
  }

  private updateState(partial: Partial<CelestialSelectionState>): void {
    this.state = { ...this.state, ...partial };
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }

  private isSameTarget(a: CelestialTargetRef | null, b: CelestialTargetRef | null): boolean {
    if (a === b) return true;
    if (!a || !b) return false;
    if (a.kind !== b.kind) return false;

    if (a.kind === "star" && b.kind === "star") {
      return a.resourceId === b.resourceId && a.catalogIndex === b.catalogIndex && a.resourceVersion === b.resourceVersion;
    }
    if (a.kind === "solar_system" && b.kind === "solar_system") {
      return a.bodyId === b.bodyId;
    }
    if (a.kind === "deep_sky" && b.kind === "deep_sky") {
      return a.resourceId === b.resourceId && a.catalogIndex === b.catalogIndex && a.resourceVersion === b.resourceVersion;
    }
    if (a.kind === "coordinate" && b.kind === "coordinate") {
      // In theory should check frame, but currently J2000 is hardcoded
      return Math.abs(a.raDeg - b.raDeg) < 1e-6 && Math.abs(a.decDeg - b.decDeg) < 1e-6;
    }
    return false;
  }

  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.listeners.clear();
  }
}

// ─── Helpers per conversió ──────────────────────────────────────────────

export function fromPickHit(hit: CelestialPickHit): CelestialTargetRef {
  if (hit.kind === "star") {
    return {
      kind: "star",
      resourceId: hit.ref.resourceId,
      resourceVersion: hit.ref.resourceVersion,
      catalogIndex: hit.ref.catalogIndex,
    };
  } else if (hit.kind === "deep_sky") {
    return {
      kind: "deep_sky",
      resourceId: hit.ref.resourceId,
      resourceVersion: hit.ref.resourceVersion,
      catalogIndex: hit.ref.catalogIndex,
    };
  } else {
    return {
      kind: "solar_system",
      bodyId: hit.bodyId,
    };
  }
}

export function fromSearchResult(result: AstronomicalSearchResultPayload | null): CelestialTargetRef | null {
  if (!result) return null;
  
  if (result.kind === "star") {
    if (result.targetRef) {
      // targetRef here usually contains resourceId, index. We might not have it strictly structured
      const parts = result.targetRef.split(":");
      if (parts.length >= 3) {
        return {
          kind: "star",
          resourceId: parts[0]!,
          resourceVersion: parts[1]!,
          catalogIndex: parseInt(parts[2]!, 10),
          raDeg: result.coordinateSnapshot?.raDeg,
          decDeg: result.coordinateSnapshot?.decDeg,
          // We don't have sourceId directly in search result usually, unless it's in targetRef.
        };
      }
    }
    // Fallback if no full ref, just use coordinates
    if (result.coordinateSnapshot) {
      return {
        kind: "coordinate",
        raDeg: result.coordinateSnapshot.raDeg,
        decDeg: result.coordinateSnapshot.decDeg,
        frame: "J2000",
        displayName: result.displayName
      };
    }
  } else if (result.kind === "deep_sky") {
    if (result.targetRef) {
       const parts = result.targetRef.split(":");
       if (parts.length >= 3) {
         return {
           kind: "deep_sky",
           resourceId: parts[0]!,
           resourceVersion: parts[1]!,
           catalogIndex: parseInt(parts[2]!, 10),
           raDeg: result.coordinateSnapshot?.raDeg,
           decDeg: result.coordinateSnapshot?.decDeg
         };
       }
    }
    if (result.coordinateSnapshot) {
      return {
        kind: "coordinate",
        raDeg: result.coordinateSnapshot.raDeg,
        decDeg: result.coordinateSnapshot.decDeg,
        frame: "J2000",
        displayName: result.displayName
      };
    }
  } else if (result.kind === "body") {
    if (result.targetRef) {
       return {
         kind: "solar_system",
         bodyId: result.targetRef
       };
    }
  }
  
  if (result.coordinateSnapshot) {
    return {
      kind: "coordinate",
      raDeg: result.coordinateSnapshot.raDeg,
      decDeg: result.coordinateSnapshot.decDeg,
      frame: "J2000"
    };
  }
  
  return null;
}
