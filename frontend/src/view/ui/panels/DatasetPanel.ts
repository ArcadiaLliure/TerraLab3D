export interface DatasetPanel {
  install(datasetId: string): void;
  cancel(operationId: string): void;
  /** Actualitza el panell a partir d’un model de vista immutable. */
  present(viewModel: Readonly<object>): void;
  /** Desconnecta listeners i recursos de presentació. */
  dispose(): void;
}
