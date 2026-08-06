export interface OpticsPanel {
  setFocalLengthMm(value: number): void;
  setAperture(value: number, mode: string): void;
  setExposure(iso: number, seconds: number): void;
  /** Actualitza el panell a partir d’un model de vista immutable. */
  present(viewModel: Readonly<object>): void;
  /** Desconnecta listeners i recursos de presentació. */
  dispose(): void;
}
