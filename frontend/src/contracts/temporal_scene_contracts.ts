import type { AstronomicalEventSnapshot } from "./astronomical_event_contracts";
import type { LightingEnvironmentSnapshot } from "./lighting_environment_contracts";
import type { SkyEnvironmentSnapshot } from "./sky_environment_contracts";
import type {
  SolarSystemPreviewSnapshot,
  SolarSystemSnapshot,
} from "./solar_system_contracts";

export type TemporalAuthority = "preview" | "authoritative";

interface TemporalSceneBase {
  readonly generationId: number;
  readonly simulationTime: string;
  readonly observerGeneration: number;
  readonly skyEnvironment: SkyEnvironmentSnapshot;
  readonly lightingEnvironment: LightingEnvironmentSnapshot;
  readonly astronomicalEvent: AstronomicalEventSnapshot;
}

interface TemporalPreviewSceneState extends TemporalSceneBase {
  readonly authority: "preview";
  readonly solarSystem: SolarSystemPreviewSnapshot;
}

interface TemporalAuthoritativeSceneState extends TemporalSceneBase {
  readonly authority: "authoritative";
  readonly solarSystem: SolarSystemSnapshot;
}

export type TemporalSceneState =
  | TemporalPreviewSceneState
  | TemporalAuthoritativeSceneState;
