export type MeasurementKind = "ruler" | "square" | "rectangle" | "circle";

export interface AngularCoordinate {
  readonly altitudeDeg: number;
  readonly azimuthDeg: number;
}

export interface MeasurementGeometrySnapshot {
  readonly paths: readonly (readonly AngularCoordinate[])[];
  readonly label: string;
  readonly anchor: AngularCoordinate;
}

export interface MeasurementSnapshot {
  readonly measurementId: string;
  readonly kind: MeasurementKind;
  readonly start: AngularCoordinate;
  readonly end: AngularCoordinate;
  readonly rotationDeg: number;
  readonly tracking: boolean;
  readonly fixedQuaternion: readonly [number, number, number, number] | null;
  readonly entityVersion: number;
  readonly geometry: MeasurementGeometrySnapshot;
}

export interface MeasurementDocumentSnapshot {
  readonly type: "measurement_snapshot";
  readonly schemaVersion: 1;
  readonly measurementRevision: number;
  readonly trackingEnabled: boolean;
  readonly measurements: readonly MeasurementSnapshot[];
  readonly selectedMeasurementId: string | null;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
  readonly warning: string | null;
}

export interface MeasurementCommandMessage {
  readonly type: "measurement_command";
  readonly measurementRevision: number;
  readonly action: "create" | "update" | "delete" | "select" | "undo" | "redo" | "clear" | "set_tracking";
  readonly measurementId?: string | null;
  readonly kind?: MeasurementKind;
  readonly start?: AngularCoordinate;
  readonly end?: AngularCoordinate;
  readonly rotationDeg?: number;
  readonly tracking?: boolean;
  readonly fixedQuaternion?: readonly [number, number, number, number] | null;
}

export interface MeasurementErrorMessage {
  readonly type: "measurement_error";
  readonly requestedRevision: number;
  readonly field: string | null;
  readonly message: string;
}
