export interface ObserverPanel {
  setLocation(latitudeDeg: number, longitudeDeg: number): void;
  setHeightOffset(heightM: number): void;
  /** Actualitza el panell a partir d’un model de vista immutable. */
  present(viewModel: Readonly<object>): void;
  /** Desconnecta listeners i recursos de presentació. */
  dispose(): void;
}
