export interface DeepSkyPickRef {
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
}

export interface DeepSkyPickHit {
  readonly kind: "deep_sky";
  readonly ref: DeepSkyPickRef;
  readonly screenXCssPx: number;
  readonly screenYCssPx: number;
  readonly screenDistanceCssPx: number;
  readonly visualRadiusCssPx: number;
  readonly hitRadiusCssPx: number;
  
  readonly objectLabel: string;
  readonly magnitude: number | null;
  readonly majorAxisArcmin: number | null;
  readonly minorAxisArcmin: number | null;
  readonly positionAngleDeg: number | null;
  readonly surfaceBrightness: number | null;
  readonly familyCode: number;
  readonly raDeg: number;
  readonly decDeg: number;
}
