export interface SkyglowConfiguration {
  readonly mode: "realistic" | "kelvin";
  readonly kelvin: number;
  readonly spectral_family: "CIE_LED_B1_B5";
  readonly normalization: "constant_photopic_flux" | "constant_radiant_power" | "constant_dnb_reference" | "conditional_relative";
  readonly mixture_model: "deterministic_reference_ensemble_v1";
  readonly revision: "black-marble-conditional-v1";
}

export interface SkyglowConfigurationSnapshot {
  readonly type: "skyglow_configuration_snapshot";
  readonly schemaVersion: 1;
  readonly generation: number;
  readonly configuration: SkyglowConfiguration;
  readonly configurationKey: string;
  readonly spectralRevision: string;
  readonly effectiveSpectrum: { readonly spectrumId: string; readonly effectiveCctK: number; readonly distanceUv: number } | null;
  readonly mixtureBasis: "radiant_flux";
  readonly scientificQuality: "conditional_relative";
  readonly calculationStatus: "transport_pending";
  readonly blackMarble: null;
  readonly rsr: null;
  readonly skyRadiance: null;
  readonly error: string | null;
}

export interface ConfigureSkyglowMessage {
  readonly type: "configure_skyglow";
  readonly configuration: SkyglowConfiguration;
}
