export type HorizonQuality =
  | "REAL"
  | "PARTIAL_DEM"
  | "FLAT_FALLBACK"
  | "UNAVAILABLE"
  | "ERROR";

export interface HorizonBufferSlice {
  readonly offset: number;
  readonly length: number;
  readonly dtype: "float32" | "uint8";
}

export interface HorizonProfileMetadata {
  readonly role: "horizon_profile";
  readonly resourceId: string;
  readonly version: number;
  readonly contentKey: string;
  readonly sourceIds: readonly string[];
  readonly sourceFingerprint: string;
  readonly observerGeneration: number;
  readonly latitudeDeg: number;
  readonly longitudeDeg: number;
  readonly terrainElevationM: number | null;
  readonly eyeElevationM: number | null;
  readonly visibleRadiusM: number;
  readonly azimuthStartDeg: number;
  readonly angularStepDeg: number;
  readonly sampleCount: number;
  readonly quality: HorizonQuality;
  readonly resolvedFraction: number;
  readonly kernelVersion: string;
  readonly byteLength: number;
  readonly bufferLayout: {
    readonly horizonElevationDeg: HorizonBufferSlice;
    readonly occluderDistanceM: HorizonBufferSlice;
    readonly occluderHeightM: HorizonBufferSlice;
    readonly validMask: HorizonBufferSlice;
  };
}

export interface HorizonStatusMessage {
  readonly type: "horizon_status";
  readonly requestId?: string;
  readonly generation: number;
  readonly observerGeneration: number;
  readonly settingsGeneration: number;
  readonly phase:
    | "queued"
    | "opening_source"
    | "sampling"
    | "reducing"
    | "publishing"
    | "completed"
    | "cancelled"
    | "fallback"
    | "error";
  readonly progress: number | null;
  readonly message?: string | null;
  readonly quality?: HorizonQuality;
  readonly resolvedFraction?: number;
  readonly visibleRadiusM?: number;
  readonly angularStepDeg?: number;
  readonly sourceIds?: readonly string[];
}

export interface HorizonProfileSettingsMessage {
  readonly type: "set_horizon_settings";
  readonly enabled: boolean;
  readonly rangeMode: "auto" | "manual";
  readonly visibleRadiusKm: number;
  readonly angularStepDeg: number;
  readonly atmosphericRefractionEnabled: boolean;
  readonly effectiveEarthRadiusFactor: number;
  readonly maxSamplesPerRay: number;
  readonly memoryBudgetBytes: number;
}
