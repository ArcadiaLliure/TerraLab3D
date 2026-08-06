export interface TerrainPanel {
  setVisibilityRadiusKm(radiusKm: number): void;
  setRayPrecisionDeg(stepDeg: number): void;
  setSurfaceMode(mode: string): void;
  /** Actualitza el panell a partir d’un model de vista immutable. */
  present(viewModel: Readonly<object>): void;
  /** Desconnecta listeners i recursos de presentació. */
  dispose(): void;
}
