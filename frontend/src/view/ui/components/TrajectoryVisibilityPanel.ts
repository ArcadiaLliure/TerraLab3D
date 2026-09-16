import type {
  ApparentTrajectoryMetadata,
  TrajectoryHorizonMode,
  TrajectoryResolution,
} from "../../../contracts/astronomical_event_contracts";
import type { TrajectoryCoverage } from "../../three/ApparentTrajectoryRenderer";

export interface TrajectoryConfiguration {
  readonly enabled: boolean;
  readonly intervalHours: number;
  readonly resolution: TrajectoryResolution;
  readonly horizonMode: TrajectoryHorizonMode;
  readonly showTerrainOccluded: boolean;
  readonly showBelowHorizon: boolean;
}

export interface TrajectoryVisibilityPanelOptions {
  readonly onConfigurationChanged: (configuration: TrajectoryConfiguration) => void;
  readonly onPresentationChanged?: (
    showTerrainOccluded: boolean,
    showBelowHorizon: boolean,
  ) => void;
}

/**
 * Minimalist control for object trajectory and horizon visibility:
 * Single checkbox "Trajectòria de l'objecte" (default checked) + compact live status.
 */
export class TrajectoryVisibilityPanel {
  private readonly root = document.createElement("section");
  private readonly checkbox = document.createElement("input");
  private readonly status = document.createElement("div");
  private enabled = true;
  private intervalHours = 24;
  private resolution: TrajectoryResolution = "detailed";
  private horizonMode: TrajectoryHorizonMode = "real";
  private showTerrainOccluded = true;
  private showBelowHorizon = true;

  constructor(private readonly options: TrajectoryVisibilityPanelOptions) {
    this.root.className = "trajectory-visibility-panel";
    this.root.style.cssText = [
      "background:var(--color-surface-raised)",
      "border:1px solid var(--color-border)",
      "border-radius:var(--border-radius-md)",
      "padding:8px 10px",
      "display:flex",
      "flex-direction:column",
      "gap:4px",
    ].join(";");

    const label = document.createElement("label");
    label.style.cssText = "display:flex;align-items:center;gap:8px;font-size:11px;font-weight:600;color:var(--color-text);cursor:pointer;";
    this.checkbox.type = "checkbox";
    this.checkbox.checked = true;
    this.checkbox.id = "trajectory-object-toggle";
    this.checkbox.addEventListener("change", () => {
      this.enabled = this.checkbox.checked;
      if (!this.enabled) {
        this.status.textContent = "Inactiva.";
        this.status.style.color = "var(--color-text-muted)";
      }
      this.publishConfiguration();
    });

    label.append(this.checkbox, document.createTextNode("Trajectòria de l'objecte"));
    this.root.appendChild(label);

    this.status.style.cssText = "font-size:10px;color:var(--color-text-muted);line-height:1.4;";
    this.status.setAttribute("role", "status");
    this.status.setAttribute("aria-live", "polite");
    this.status.textContent = "Selecciona un astre per veure la seva trajectòria.";
    this.root.appendChild(this.status);
  }

  getElement(): HTMLElement {
    return this.root;
  }

  configuration(): TrajectoryConfiguration {
    return {
      enabled: this.enabled,
      intervalHours: this.intervalHours,
      resolution: this.resolution,
      horizonMode: this.horizonMode,
      showTerrainOccluded: this.showTerrainOccluded,
      showBelowHorizon: this.showBelowHorizon,
    };
  }

  setHorizonMode(mode: TrajectoryHorizonMode): void {
    if (this.horizonMode !== mode) {
      this.horizonMode = mode;
      if (this.enabled) this.publishConfiguration();
    }
  }

  updateCalculating(displayName: string): void {
    this.status.textContent = `Calculant trajectòria · ${displayName}…`;
    this.status.style.color = "var(--color-warning)";
  }

  updateUnavailable(message: string): void {
    this.status.textContent = message;
    this.status.style.color = "var(--color-error)";
  }

  updateCoverage(_coverage: TrajectoryCoverage): void {
    // Dynamic recalculation in main.ts handles interval shifts automatically without user intervention
  }

  updateResult(metadata: ApparentTrajectoryMetadata): void {
    const classification = {
      visible_throughout: "visible tot l'interval",
      never_visible: "mai visible",
      mixed: "visibilitat variable",
      insufficient_data: "dades insuficients",
    }[metadata.intervalClassification ?? "insufficient_data"];
    const circumpolar = metadata.astronomicallyCircumpolar ? " (circumpolar)" : "";
    const eventTexts: string[] = [];
    for (const event of metadata.events ?? []) {
      if (event.kind === "tangent") continue;
      const time = new Date(event.instantUtc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      eventTexts.push(`${event.kind === "rise" ? "↑" : "↓"} ${time}`);
    }
    const eventsSummary = eventTexts.length > 0 ? ` · ${eventTexts.join("  ")}` : "";
    const horizonInfo = metadata.horizonQuality === "REAL" ? " (horitzó DEM)" : "";
    this.status.textContent = `${metadata.displayName ?? metadata.bodyId} · ${classification}${circumpolar}${horizonInfo}${eventsSummary}`;
    this.status.style.color = metadata.intervalClassification === "insufficient_data"
      ? "var(--color-warning)"
      : "var(--color-success)";
  }

  private publishConfiguration(): void {
    this.options.onConfigurationChanged(this.configuration());
  }
}
