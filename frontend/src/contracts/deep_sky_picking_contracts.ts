export interface DeepSkyPickRef {
  readonly resourceId: string;
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
  
  // Directly resolved properties (no backend roundtrip needed)
  readonly objectLabel: string;
  readonly magnitude: number;
  readonly majorAxisArcmin: number;
  readonly minorAxisArcmin: number;
  readonly familyCode: number;
}
