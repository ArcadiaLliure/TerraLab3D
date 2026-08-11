export interface CameraPose {
  readonly azimuthDeg: number;
  readonly altitudeDeg: number;
  readonly horizontalFovDeg: number;
  readonly rollDeg: number;
}

export interface CameraRig {
  pose(): CameraPose;
  setPose(pose: CameraPose): void;
  orbit(deltaAzimuthDeg: number, deltaAltitudeDeg: number): void;
  zoomTo(horizontalFovDeg: number): void;
  resize(widthPx: number, heightPx: number): void;
  updateMatrices(): void;
  setTrackingState(isTracking: boolean): void;
}
