export interface ToolsPanel {
  selectMeasurementTool(kind: string): void;
  setConstellationDrawMode(enabled: boolean): void;
  /** Actualitza el panell a partir d’un model de vista immutable. */
  present(viewModel: Readonly<object>): void;
  /** Desconnecta listeners i recursos de presentació. */
  dispose(): void;
}
