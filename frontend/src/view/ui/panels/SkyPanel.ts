export interface SkyPanel {
  setLayerVisible(layerId: string, visible: boolean): void;
  setLightPollutionMode(mode: string, value: number): void;
  /** Actualitza el panell a partir d’un model de vista immutable. */
  present(viewModel: Readonly<object>): void;
  /** Desconnecta listeners i recursos de presentació. */
  dispose(): void;
}
