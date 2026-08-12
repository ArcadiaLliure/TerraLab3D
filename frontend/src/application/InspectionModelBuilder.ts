import type { CelestialInspectionModel, CelestialSelectionState } from "../contracts/celestial_selection_contracts";
import type { ThreeSceneHostImpl } from "../view/three/ThreeSceneHostImpl";

export function buildInspectionModel(state: CelestialSelectionState, sceneHost: ThreeSceneHostImpl): CelestialInspectionModel | null {
  const target = state.selectedTarget;
  if (!target) return null;

  if (target.kind === "star") {
    // Fetch star fields from backend resolved cache, if available
    // or from renderer directly. Since we don't store the backend resolved cache centrally yet,
    // we can return a basic structure. Wait, ScenePickingController used to hold the ResolvedStar.
    // If the star was resolved by backend, CelestialSelectionController gets the `sourceId`.
    // We can fetch basic fields from StarFieldRenderer directly!
    const renderer = sceneHost.getStarFieldRenderer();
    const resource = renderer.getResource(target.resourceId);
    let raDeg = null, decDeg = null, magnitude = null;
    let sourceRole = "Desconegut";
    let bpRp = null;
    
    if (resource) {
       sourceRole = resource.role;
       const count = resource.starCount;
       if (target.catalogIndex < count) {
         const eqs = resource.equatorialPositions;
         const vx = eqs[target.catalogIndex * 3]!;
         const vy = eqs[target.catalogIndex * 3 + 1]!;
         const vz = eqs[target.catalogIndex * 3 + 2]!;
         decDeg = Math.asin(vz) * (180 / Math.PI);
         raDeg = ((Math.atan2(vy, vx) * (180 / Math.PI)) + 360) % 360;
         
         const mags = resource.magnitudesArray;
         magnitude = mags[target.catalogIndex]!;
       }
    }
    
    return {
      targetRef: target,
      displayName: `Estrella ${target.sourceId || ""}`,
      kind: "star",
      availability: state.availability,
      fields: {
        sourceId: target.sourceId,
        raDeg, decDeg, magnitude, sourceRole, bpRp
      }
    };
  }

  if (target.kind === "deep_sky") {
    const renderer = sceneHost.getDeepSkyRenderer();
    const metadata = renderer.metadata;
    const payloadBuffer = renderer.payloadBuffer;
    let raDeg = null, decDeg = null, magnitude = null, majorAxisArcmin = null, minorAxisArcmin = null, familyCode = null;
    let objectLabel = "NGC";
    
    if (metadata && payloadBuffer) {
      const idx = renderer.catalogIndexToBufferIndex.get(target.catalogIndex);
      if (idx !== undefined) {
         const count = metadata.renderableCount ?? metadata.recordCount;
         const layout = metadata.bufferLayout;
         
         const eqDirs = new Float32Array(payloadBuffer, layout.equatorialDirections.offset, count * 3);
         const vx = eqDirs[idx * 3]!;
         const vy = eqDirs[idx * 3 + 1]!;
         const vz = eqDirs[idx * 3 + 2]!;
         decDeg = Math.asin(vz) * (180 / Math.PI);
         raDeg = ((Math.atan2(vy, vx) * (180 / Math.PI)) + 360) % 360;
         
         const mags = new Float32Array(payloadBuffer, layout.magnitude.offset, count);
         magnitude = mags[idx]! > -1 ? mags[idx]! : null;
         
         const majAx = new Float32Array(payloadBuffer, layout.majorAxisArcmin.offset, count);
         majorAxisArcmin = majAx[idx]! > 0 ? majAx[idx]! : null;
         
         const minAx = new Float32Array(payloadBuffer, layout.minorAxisArcmin.offset, count);
         minorAxisArcmin = minAx[idx]! > 0 ? minAx[idx]! : null;
         
         const fam = new Uint32Array(payloadBuffer, layout.familyCode.offset, count);
         familyCode = fam[idx]!;
         
         const labels = (metadata.objectLabels as string[] | undefined) ?? [];
         objectLabel = labels[idx] || "NGC";
      }
    }
    
    return {
      targetRef: target,
      displayName: objectLabel,
      kind: "deep_sky",
      availability: state.availability,
      fields: {
        raDeg, decDeg, magnitude, majorAxisArcmin, minorAxisArcmin, familyCode
      }
    };
  }

  if (target.kind === "solar_system") {
    const labels: Readonly<Record<string, string>> = {
      sun: "Sol", moon: "Lluna", mercury: "Mercuri", venus: "Venus",
      mars: "Mart", jupiter: "Júpiter", saturn: "Saturn", uranus: "Urà",
      neptune: "Neptú", pluto: "Plutó",
    };
    const renderer = sceneHost.getSolarSystemRenderer();
    let bodyState = null;
    // We could find the specific state from renderer snapshot
    const bodies = renderer.getPickableBodies();
    for (let b of bodies) {
       if (b.id === target.bodyId) {
          bodyState = b.state;
          break;
       }
    }
    
    return {
      targetRef: target,
      displayName: bodyState?.displayName ?? labels[target.bodyId] ?? target.bodyId,
      kind: "solar_system",
      availability: state.availability,
      fields: {
        altitudeDeg: bodyState?.altitudeDeg,
        azimuthDeg: bodyState?.azimuthDeg,
        distanceKm: bodyState?.distanceKm,
        apparentMagnitude: bodyState?.apparentMagnitude,
      }
    };
  }

  if (target.kind === "coordinate") {
    return {
      targetRef: target,
      displayName: target.displayName || "Coordenada",
      kind: "coordinate",
      availability: state.availability,
      fields: {
        raDeg: target.raDeg,
        decDeg: target.decDeg,
      }
    };
  }

  return null;
}
