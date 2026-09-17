export interface EquatorialPoint {
  readonly raDeg: number;
  readonly decDeg: number;
}

export interface ConstellationVisualComponentSnapshot {
  readonly componentId: string;
  readonly sourceName: string;
  readonly rank: number;
  readonly strokes: readonly (readonly [number, number][])[];
}

export interface ConstellationCatalogEntrySnapshot {
  readonly id: string;
  readonly name: string;
  readonly frame: "ICRS";
  readonly center: readonly [number, number];
  readonly angularRadiusDeg: number;
  readonly visualComponents: readonly ConstellationVisualComponentSnapshot[];
}

export interface ConstellationCatalogSnapshot {
  readonly type: "constellation_catalog";
  readonly schemaVersion: 1;
  readonly catalogVersion: string;
  readonly source: {
    readonly sourceFrame: "FK5_J2000";
    readonly frame: "ICRS";
    readonly maxArcStepDeg: number;
  };
  readonly constellations: readonly ConstellationCatalogEntrySnapshot[];
}

export interface UserConstellationNodeSnapshot extends EquatorialPoint {
  readonly nodeId: string;
  readonly sourceId: string | null;
  readonly starName: string | null;
  readonly startsNewStroke: boolean;
}

export interface UserConstellationSnapshot {
  readonly constellationId: string;
  readonly name: string;
  readonly entityVersion: number;
  readonly nodes: readonly UserConstellationNodeSnapshot[];
  readonly strokes: readonly (readonly EquatorialPoint[])[];
}

export interface ConstellationDocumentSnapshot {
  readonly type: "constellation_document";
  readonly schemaVersion: 1;
  readonly documentRevision: number;
  readonly constellations: readonly UserConstellationSnapshot[];
  readonly selectedConstellationId: string | null;
  readonly editing: boolean;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
  readonly warning: string | null;
}

export interface ConstellationCommandMessage {
  readonly type: "constellation_command";
  readonly requestId: string;
  readonly documentRevision: number;
  readonly action: "create_group" | "append_node" | "finish_group" | "resume_from_node" | "new_stroke" | "select" | "set_editing" | "rename_group" | "delete_selection" | "undo" | "redo" | "clear";
  readonly constellationId?: string | null;
  readonly nodeId?: string;
  readonly name?: string;
  readonly editing?: boolean;
  readonly resourceId?: string;
  readonly resourceVersion?: string;
  readonly catalogIndex?: number;
}

export interface ConstellationErrorMessage {
  readonly type: "constellation_error";
  readonly requestId: string;
  readonly requestedRevision: number;
  readonly authoritativeRevision: number;
  readonly field: string | null;
  readonly message: string;
}
