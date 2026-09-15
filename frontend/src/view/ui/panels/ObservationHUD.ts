import type { ObservationSnapshotMessage } from "../../../contracts/observation_contracts";

/** Retained screen-space summary for the active scientific instrument. */
export class ObservationHUD {
  readonly element = document.createElement("aside");

  constructor() {
    this.element.className = "observation-hud";
    this.element.setAttribute("aria-live", "polite");
    this.element.hidden = true;
  }

  mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  present(snapshot: ObservationSnapshotMessage): void {
    this.element.hidden = snapshot.mode === "eye";
    this.element.dataset["mode"] = snapshot.mode;
    if (snapshot.mode === "camera") {
      const field = snapshot.field;
      const limit = snapshot.photographicPreview?.estimatedLimitMagnitude;
      this.element.textContent = field && limit !== undefined
        ? `CÀMERA  ${field.widthDeg.toFixed(2)}° × ${field.heightDeg.toFixed(2)}°  ·  mlim ${limit.toFixed(2)}`
        : "CÀMERA";
      return;
    }
    if (snapshot.mode === "telescope") {
      const metrics = snapshot.metrics;
      this.element.textContent = `TELESCOPI  ${metrics.magnification?.toFixed(1)}×  ·  pupil·la ${metrics.exitPupilMm?.toFixed(1)} mm  ·  camp ${metrics.trueFovDeg?.toFixed(2)}°`;
    }
  }

  dispose(): void {
    this.element.remove();
  }
}
