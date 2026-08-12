/**
 * celestial_selection_contracts.ts
 *
 * Models tipats que representen la selecció única i autoritària d'objectes celestes.
 * Elimina la dependència de tipus "any" en Tracking i Picking.
 */

export interface StarTargetRef {
  readonly kind: "star";
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
  readonly sourceId?: string; // Només quan està resolt
}

export interface SolarSystemTargetRef {
  readonly kind: "solar_system";
  readonly bodyId: string;
}

export interface DeepSkyTargetRef {
  readonly kind: "deep_sky";
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
}

export interface CoordinateTargetRef {
  readonly kind: "coordinate";
  readonly raDeg: number;
  readonly decDeg: number;
  readonly frame: "J2000";
  readonly displayName?: string;
}

export type CelestialTargetRef =
  | StarTargetRef
  | SolarSystemTargetRef
  | DeepSkyTargetRef
  | CoordinateTargetRef;

export type CelestialAvailability = "available" | "unavailable" | "waiting_for_source";

export type SelectionSource = "pick" | "search" | "external";

export interface CelestialSelectionState {
  readonly generation: number;
  readonly selectedTarget: CelestialTargetRef | null;
  readonly source: SelectionSource | null;
  readonly availability: CelestialAvailability;
}

// Model usat per Inspector / UI
export interface DeepSkyMetadata {
  readonly canonicalName: string | null;
  readonly aliases: readonly string[];
  readonly familyCode: number; // enum code
  readonly raDeg: number;
  readonly decDeg: number;
  readonly magnitude: number | null;
  readonly majorAxisArcmin: number | null;
  readonly minorAxisArcmin: number | null;
  readonly positionAngleDeg: number | null;
  readonly surfaceBrightness: number | null;
  readonly commonName: string | null;
}

export interface CelestialInspectionModel {
  readonly targetRef: CelestialTargetRef;
  readonly displayName: string;
  readonly kind: CelestialTargetRef["kind"];
  readonly availability: CelestialAvailability;
  readonly fields: Record<string, any>; // S'anirà definint de manera més estricta per a cada tipus
}
