export type ObservationMode = "eye" | "camera" | "telescope";

export interface SensorFormatSnapshot {
  readonly key: string;
  readonly widthMm: number;
  readonly heightMm: number;
  readonly resolutionWidthPx: number | null;
  readonly resolutionHeightPx: number | null;
  readonly squarePixels: boolean;
  readonly pixelPitchUm: number | null;
  readonly pixelPitchXUm: number | null;
  readonly pixelPitchYUm: number | null;
}

export interface CameraProfileSnapshot {
  readonly profileId: string;
  readonly name: string;
  readonly sensor: SensorFormatSnapshot;
  readonly builtIn: boolean;
}

export interface CameraCaptureSnapshot {
  readonly selectedProfileId: string;
  readonly focalLengthMm: number;
  readonly fNumber: number;
  readonly iso: number;
  readonly exposureSeconds: number;
  readonly trackingEnabled: boolean;
  readonly frameRotationDeg: number;
  readonly opticalTransmission: number | null;
}

export interface TelescopeSnapshot {
  readonly focalLengthMm: number;
  readonly apertureDiameterMm: number;
  readonly eyepieceFocalLengthMm: number;
  readonly eyepieceAfovDeg: number;
}

export interface InstrumentFieldSnapshot {
  readonly widthDeg: number;
  readonly heightDeg: number;
  readonly diagonalDeg: number | null;
  readonly aspectRatio: number | null;
  readonly solidAngleSr: number | null;
  readonly shape: "rectangle" | "circle";
}

export interface OpticalMetricsSnapshot {
  readonly pixelScaleXArcsec: number | null;
  readonly pixelScaleYArcsec: number | null;
  readonly magnification: number | null;
  readonly exitPupilMm: number | null;
  readonly trueFovDeg: number | null;
}

export interface PhotographicPreviewSnapshot {
  readonly modelId: "terralab.photographic-limiting-magnitude.v1";
  readonly estimatedLimitMagnitude: number;
  readonly capturedPhotonIndex: number;
  readonly isoDetectionGainMagnitude: number;
  readonly atmosphericTransmission: number;
  readonly totalTransmission: number;
  readonly shortExposurePenaltyMagnitude: number;
  readonly skyPenaltyMagnitude: number;
}

export interface DeepCatalogStatusSnapshot {
  readonly state: "idle" | "loading" | "ready" | "cancelled" | "unavailable" | "error";
  readonly deepQueryRevision: number;
  readonly residentMagnitudeLimit: number;
  readonly selectedStarCount: number;
  readonly truncated: boolean;
  readonly message: string | null;
}

export interface ObservationSnapshotMessage {
  readonly type: "observation_snapshot";
  readonly schemaVersion: 1;
  readonly observationRevision: number;
  readonly mode: ObservationMode;
  readonly cameraProfiles: readonly CameraProfileSnapshot[];
  readonly camera: CameraCaptureSnapshot;
  readonly telescope: TelescopeSnapshot;
  readonly field: InstrumentFieldSnapshot | null;
  readonly metrics: OpticalMetricsSnapshot;
  readonly photographicPreview: PhotographicPreviewSnapshot | null;
  readonly deepCatalog: DeepCatalogStatusSnapshot;
  readonly warning: string | null;
}

export interface ObservationErrorMessage {
  readonly type: "observation_error";
  readonly requestedRevision: number;
  readonly field: string | null;
  readonly message: string;
}

export interface SetObservationModeMessage {
  readonly type: "set_observation_mode";
  readonly observationRevision: number;
  readonly mode: ObservationMode;
}

export interface ConfigureCameraMessage extends CameraCaptureSnapshot {
  readonly type: "configure_camera";
  readonly observationRevision: number;
}

export interface ConfigureTelescopeMessage extends TelescopeSnapshot {
  readonly type: "configure_telescope";
  readonly observationRevision: number;
}

export interface CameraProfileMessage {
  readonly type: "camera_profile";
  readonly observationRevision: number;
  readonly action: "create" | "update" | "delete";
  readonly profileId?: string;
  readonly name?: string;
  readonly widthMm?: number;
  readonly heightMm?: number;
  readonly resolutionWidthPx?: number | null;
  readonly resolutionHeightPx?: number | null;
  readonly squarePixels?: boolean;
  readonly pixelPitchUm?: number | null;
  readonly pixelPitchXUm?: number | null;
  readonly pixelPitchYUm?: number | null;
}

export interface RequestCameraDepthMessage {
  readonly type: "request_camera_depth";
  readonly observationRevision: number;
  readonly deepQueryRevision: number;
  readonly raDeg: number;
  readonly decDeg: number;
  readonly radiusDeg: number;
  readonly photometricLimit: number;
}

export interface CancelCameraDepthMessage {
  readonly type: "cancel_camera_depth";
  readonly deepQueryRevision: number;
}
