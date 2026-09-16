import type {
  CameraCaptureSnapshot,
  CameraProfileMessage,
  ObservationErrorMessage,
  ObservationSnapshotMessage,
  TelescopeSnapshot,
} from "../../../contracts/observation_contracts";

export interface OpticsPanelCallbacks {
  onCameraChanged(camera: CameraCaptureSnapshot): void;
  onTelescopeChanged(telescope: TelescopeSnapshot): void;
  onProfileMutation(message: Omit<CameraProfileMessage, "type" | "observationRevision">): void;
  onManualGoto(raDeg: number, decDeg: number): void;
  onSelectedGoto(): void;
  onMove(deltaAzimuthDeg: number, deltaAltitudeDeg: number): void;
}

export class OpticsPanelImpl {
  readonly element = document.createElement("section");
  private readonly title = document.createElement("div");
  private readonly cameraSection = document.createElement("div");
  private readonly telescopeSection = document.createElement("div");
  private readonly metrics = document.createElement("div");
  private readonly status = document.createElement("div");
  private readonly profileSelect = document.createElement("select");
  private readonly cameraInputs = new Map<string, HTMLInputElement>();
  private readonly profileInputs = new Map<string, HTMLInputElement>();
  private readonly profileName = document.createElement("input");
  private readonly squarePixelsInput = document.createElement("input");
  private readonly telescopeInputs = new Map<string, HTMLInputElement>();
  private readonly trackingInput = document.createElement("input");
  private selectedGotoButton: HTMLButtonElement | null = null;
  private selectedTargetName: string | null = null;
  private debounceTimer: number | null = null;
  private snapshot: ObservationSnapshotMessage | null = null;
  private fastMovement = false;
  private holdTimer: number | null = null;

  constructor(private readonly callbacks: OpticsPanelCallbacks) {
    this.element.className = "optics-panel";
    this.title.className = "optics-panel-title";
    this.title.textContent = "Instrument òptic";
    this.element.append(this.title, this.cameraSection, this.telescopeSection, this.metrics, this.status);
    this.buildCameraSection();
    this.buildTelescopeSection();
    this.status.className = "optics-status";
    this.metrics.className = "optics-metrics";
    this.element.hidden = true;
  }

  present(snapshot: ObservationSnapshotMessage): void {
    this.snapshot = snapshot;
    this.element.hidden = snapshot.mode === "eye";
    this.cameraSection.hidden = snapshot.mode !== "camera";
    this.telescopeSection.hidden = snapshot.mode !== "telescope";
    if (snapshot.mode === "camera") {
      this.title.textContent = "Instrument: Càmera";
      this.presentCamera(snapshot);
    } else if (snapshot.mode === "telescope") {
      this.title.textContent = "Instrument: Telescopi";
      this.presentTelescope(snapshot);
    } else {
      this.title.textContent = "Instrument òptic";
    }
    this.status.textContent = snapshot.warning ?? this.deepStatus(snapshot);
  }

  updateSelectedTarget(name: string | null): void {
    this.selectedTargetName = name;
    if (this.selectedGotoButton) {
      if (name) {
        this.selectedGotoButton.textContent = `GoTo astre: ${name}`;
        this.selectedGotoButton.title = `Apunta el telescopi directament cap a ${name}`;
        this.selectedGotoButton.classList.add("has-target");
        this.selectedGotoButton.disabled = false;
      } else {
        this.selectedGotoButton.textContent = "GoTo selecció (cap astre)";
        this.selectedGotoButton.title = "Selecciona abans un astre al mapa o al cercador per apuntar-hi el telescopi";
        this.selectedGotoButton.classList.remove("has-target");
        this.selectedGotoButton.disabled = true;
      }
    }
  }

  presentError(error: ObservationErrorMessage): void {
    this.status.textContent = error.message;
    this.status.dataset["state"] = "error";
    for (const input of this.element.querySelectorAll<HTMLInputElement>("[data-field]")) {
      input.classList.toggle("invalid", input.dataset["field"] === error.field);
    }
  }

  mount(container: HTMLElement): void { container.appendChild(this.element); }
  dispose(): void {
    if (this.debounceTimer !== null) window.clearTimeout(this.debounceTimer);
    this.stopHold();
    this.element.remove();
  }

  private buildCameraSection(): void {
    this.cameraSection.className = "optics-section";
    this.addLabelled(this.cameraSection, "Sensor", this.profileSelect);
    this.profileSelect.onchange = () => { this.presentProfileDraft(); this.scheduleCamera(); };

    const definitions: Array<[string, string, string]> = [
      ["focalLengthMm", "Focal (mm)", "1"], ["fNumber", "Número f", "0.1"],
      ["iso", "ISO", "1"], ["exposureSeconds", "Exposició (s)", "0.1"],
      ["frameRotationDeg", "Rotació marc (°)", "0.1"],
    ];
    for (const [field, label, step] of definitions) {
      const input = this.numberInput(field, step);
      this.cameraInputs.set(field, input);
      this.addLabelled(this.cameraSection, label, input);
      input.oninput = () => this.scheduleCamera();
    }
    this.trackingInput.type = "checkbox";
    this.trackingInput.onchange = () => this.scheduleCamera();
    this.addLabelled(this.cameraSection, "Seguiment", this.trackingInput);

    // Advanced sensor configuration (collapsible)
    const advanced = document.createElement("details");
    advanced.className = "optics-advanced-details";
    const summary = document.createElement("summary");
    summary.textContent = "Geometria i perfils de sensor…";
    advanced.appendChild(summary);

    const advancedContent = document.createElement("div");
    advancedContent.className = "optics-advanced-content";

    this.profileName.type = "text";
    this.addLabelled(advancedContent, "Nom perfil", this.profileName);

    for (const [field, label] of [
      ["widthMm", "Sensor ample (mm)"], ["heightMm", "Sensor alt (mm)"],
      ["resolutionWidthPx", "Resolució X"], ["resolutionHeightPx", "Resolució Y"],
      ["pixelPitchUm", "Pitch quadrat (µm)"], ["pixelPitchXUm", "Pitch X (µm)"],
      ["pixelPitchYUm", "Pitch Y (µm)"],
    ] as const) {
      const input = this.numberInput(field, "0.01");
      this.profileInputs.set(field, input);
      this.addLabelled(advancedContent, label, input);
    }
    this.squarePixelsInput.type = "checkbox";
    this.squarePixelsInput.checked = true;
    this.addLabelled(advancedContent, "Píxels quadrats", this.squarePixelsInput);

    const transInput = this.numberInput("opticalTransmission", "0.01");
    this.cameraInputs.set("opticalTransmission", transInput);
    this.addLabelled(advancedContent, "Transmissió", transInput);
    transInput.oninput = () => this.scheduleCamera();

    const profileActions = document.createElement("div");
    profileActions.className = "optics-actions";
    profileActions.append(
      this.button("Nou perfil", () => this.createProfile()),
      this.button("Editar", () => this.updateProfile()),
      this.button("Eliminar", () => this.deleteProfile()),
    );
    advancedContent.appendChild(profileActions);

    advanced.appendChild(advancedContent);
    this.cameraSection.appendChild(advanced);
  }

  private buildTelescopeSection(): void {
    this.telescopeSection.className = "optics-section";
    const definitions: Array<[keyof TelescopeSnapshot, string]> = [
      ["focalLengthMm", "Focal tub (mm)"], ["apertureDiameterMm", "Obertura (mm)"],
      ["eyepieceFocalLengthMm", "Ocular (mm)"], ["eyepieceAfovDeg", "AFOV (°)"],
    ];
    for (const [field, label] of definitions) {
      const input = this.numberInput(field, "0.1");
      this.telescopeInputs.set(field, input);
      this.addLabelled(this.telescopeSection, label, input);
      input.oninput = () => this.scheduleTelescope();
    }

    const movementTitle = document.createElement("div");
    movementTitle.className = "optics-subheading";
    movementTitle.textContent = "Control de moviment";
    this.telescopeSection.appendChild(movementTitle);

    const speed = this.button("Moviment: fi", () => {
      this.fastMovement = !this.fastMovement;
      speed.textContent = this.fastMovement ? "Moviment: ràpid" : "Moviment: fi";
    });
    this.telescopeSection.appendChild(speed);
    const pad = document.createElement("div");
    pad.className = "scope-movement-pad";
    pad.append(
      this.movementButton("←", 1, 0), this.movementButton("↑", 0, 1),
      this.movementButton("↓", 0, -1), this.movementButton("→", -1, 0),
    );
    this.telescopeSection.appendChild(pad);

    const gotoContainer = document.createElement("div");
    gotoContainer.className = "optics-goto-container";

    const gotoTitle = document.createElement("div");
    gotoTitle.className = "optics-subheading";
    gotoTitle.textContent = "Alineació GoTo (Apuntat automàtic)";
    gotoContainer.appendChild(gotoTitle);

    // 1. GoTo manual per coordenades RA / Dec
    const gotoRow = document.createElement("div");
    gotoRow.className = "optics-goto-row";

    const raLabel = document.createElement("label");
    raLabel.textContent = "RA:";
    const ra = this.numberInput("raDeg", "0.01");
    ra.placeholder = "0..360°";
    ra.title = "Ascensió Recta (0.0° a 360.0°)";
    raLabel.appendChild(ra);

    const decLabel = document.createElement("label");
    decLabel.textContent = "Dec:";
    const dec = this.numberInput("decDeg", "0.01");
    dec.placeholder = "-90..+90°";
    dec.title = "Declinació (-90.0° a +90.0°)";
    decLabel.appendChild(dec);

    const manualBtn = this.button("GoTo", () => {
      const raDeg = Number(ra.value); const decDeg = Number(dec.value);
      if (Number.isFinite(raDeg) && Number.isFinite(decDeg) && decDeg >= -90 && decDeg <= 90) {
        this.callbacks.onManualGoto(((raDeg % 360) + 360) % 360, decDeg);
      }
    });
    manualBtn.className = "optics-goto-btn";
    manualBtn.title = "Apunta el telescopi a les coordenades astronòmiques introduïdes (RA i Dec)";

    gotoRow.append(raLabel, decLabel, manualBtn);
    gotoContainer.appendChild(gotoRow);

    // 2. GoTo a la selecció actual
    this.selectedGotoButton = this.button(
      this.selectedTargetName ? `GoTo astre: ${this.selectedTargetName}` : "GoTo selecció (cap astre)",
      () => this.callbacks.onSelectedGoto()
    );
    this.selectedGotoButton.className = "optics-goto-target-btn";
    this.selectedGotoButton.title = "Apunta el telescopi automàticament a l'astre actualment seleccionat (planeta, estrella, etc.)";
    if (this.selectedTargetName) {
      this.selectedGotoButton.classList.add("has-target");
      this.selectedGotoButton.disabled = false;
    } else {
      this.selectedGotoButton.disabled = true;
    }
    gotoContainer.appendChild(this.selectedGotoButton);

    this.telescopeSection.appendChild(gotoContainer);
  }

  private presentCamera(snapshot: ObservationSnapshotMessage): void {
    const active = this.profileSelect.value;
    this.profileSelect.replaceChildren(...snapshot.cameraProfiles.map(profile => {
      const option = document.createElement("option"); option.value = profile.profileId; option.textContent = profile.name; return option;
    }));
    this.profileSelect.value = snapshot.camera.selectedProfileId || active;
    this.presentProfileDraft();
    this.setInputValues(this.cameraInputs, snapshot.camera as unknown as Record<string, unknown>);
    this.trackingInput.checked = snapshot.camera.trackingEnabled;
    const field = snapshot.field;
    const preview = snapshot.photographicPreview;
    this.metrics.textContent = field && preview
      ? `Camp ${field.widthDeg.toFixed(2)}° × ${field.heightDeg.toFixed(2)}° · Ω ${field.solidAngleSr?.toExponential(3)} sr · Magnitud límit estimada ${preview.estimatedLimitMagnitude.toFixed(2)}`
      : "";
  }

  private presentTelescope(snapshot: ObservationSnapshotMessage): void {
    this.setInputValues(this.telescopeInputs, snapshot.telescope as unknown as Record<string, unknown>);
    const value = snapshot.metrics;
    this.metrics.textContent = `${value.magnification?.toFixed(1)}× · pupil·la ${value.exitPupilMm?.toFixed(2)} mm · camp real ${value.trueFovDeg?.toFixed(2)}°`;
  }

  private scheduleCamera(): void {
    this.schedule(() => {
      if (!this.snapshot) return;
      this.callbacks.onCameraChanged({
        selectedProfileId: this.profileSelect.value,
        focalLengthMm: this.value(this.cameraInputs, "focalLengthMm"),
        fNumber: this.value(this.cameraInputs, "fNumber"),
        iso: this.value(this.cameraInputs, "iso"),
        exposureSeconds: this.value(this.cameraInputs, "exposureSeconds"),
        trackingEnabled: this.trackingInput.checked,
        frameRotationDeg: this.value(this.cameraInputs, "frameRotationDeg"),
        opticalTransmission: this.optionalValue(this.cameraInputs, "opticalTransmission"),
      });
    });
  }

  private scheduleTelescope(): void {
    this.schedule(() => this.callbacks.onTelescopeChanged({
      focalLengthMm: this.value(this.telescopeInputs, "focalLengthMm"),
      apertureDiameterMm: this.value(this.telescopeInputs, "apertureDiameterMm"),
      eyepieceFocalLengthMm: this.value(this.telescopeInputs, "eyepieceFocalLengthMm"),
      eyepieceAfovDeg: this.value(this.telescopeInputs, "eyepieceAfovDeg"),
    }));
  }

  private schedule(action: () => void): void {
    if (this.debounceTimer !== null) window.clearTimeout(this.debounceTimer);
    this.debounceTimer = window.setTimeout(() => { this.debounceTimer = null; action(); }, 150);
  }

  private createProfile(): void {
    const name = this.profileName.value.trim();
    if (!name) return;
    this.callbacks.onProfileMutation({ action: "create", name, ...this.profilePayload() });
  }

  private updateProfile(): void {
    const profile = this.snapshot?.cameraProfiles.find(item => item.profileId === this.profileSelect.value);
    if (!profile || profile.builtIn) return;
    const name = this.profileName.value.trim();
    if (!name) return;
    this.callbacks.onProfileMutation({ action: "update", profileId: profile.profileId, name, ...this.profilePayload() });
  }

  private deleteProfile(): void {
    const profile = this.snapshot?.cameraProfiles.find(item => item.profileId === this.profileSelect.value);
    if (!profile || profile.builtIn || !window.confirm(`Eliminar ${profile.name}?`)) return;
    this.callbacks.onProfileMutation({ action: "delete", profileId: profile.profileId });
  }

  private profilePayload() {
    return {
      widthMm: this.value(this.profileInputs, "widthMm"),
      heightMm: this.value(this.profileInputs, "heightMm"),
      resolutionWidthPx: this.optionalValue(this.profileInputs, "resolutionWidthPx"),
      resolutionHeightPx: this.optionalValue(this.profileInputs, "resolutionHeightPx"),
      squarePixels: this.squarePixelsInput.checked,
      pixelPitchUm: this.optionalValue(this.profileInputs, "pixelPitchUm"),
      pixelPitchXUm: this.optionalValue(this.profileInputs, "pixelPitchXUm"),
      pixelPitchYUm: this.optionalValue(this.profileInputs, "pixelPitchYUm"),
    };
  }

  private presentProfileDraft(): void {
    const profile = this.snapshot?.cameraProfiles.find(item => item.profileId === this.profileSelect.value);
    if (!profile) return;
    this.profileName.value = profile.name;
    const sensor = profile.sensor as unknown as Record<string, unknown>;
    this.setInputValues(this.profileInputs, sensor);
    this.squarePixelsInput.checked = profile.sensor.squarePixels;
  }

  private movementButton(label: string, azSign: number, altSign: number): HTMLButtonElement {
    const button = this.button(label, () => undefined);
    const move = (held: boolean) => {
      const step = this.fastMovement ? 0.05 : 0.05 / 60;
      const perSecond = this.fastMovement ? 0.5 : 0.5 / 60;
      this.callbacks.onMove(azSign * (held ? perSecond / 20 : step), altSign * (held ? perSecond / 20 : step));
    };
    button.onpointerdown = event => {
      event.preventDefault(); move(false); this.stopHold();
      this.holdTimer = window.setInterval(() => move(true), 50);
    };
    button.onpointerup = button.onpointerleave = () => this.stopHold();
    return button;
  }

  private stopHold(): void { if (this.holdTimer !== null) window.clearInterval(this.holdTimer); this.holdTimer = null; }
  private numberInput(field: string, step: string): HTMLInputElement {
    const input = document.createElement("input"); input.type = "number"; input.step = step; input.dataset["field"] = field; return input;
  }
  private addLabelled(parent: HTMLElement, text: string, input: HTMLElement): void {
    const label = document.createElement("label"); const span = document.createElement("span"); span.textContent = text; label.append(span, input); parent.appendChild(label);
  }
  private button(text: string, action: () => void): HTMLButtonElement {
    const button = document.createElement("button"); button.type = "button"; button.textContent = text; button.onclick = action; return button;
  }
  private setInputValues(inputs: Map<string, HTMLInputElement>, values: Record<string, unknown>): void {
    for (const [field, input] of inputs) if (document.activeElement !== input) input.value = values[field] == null ? "" : String(values[field]);
  }
  private value(inputs: Map<string, HTMLInputElement>, field: string): number { return Number(inputs.get(field)?.value); }
  private optionalValue(inputs: Map<string, HTMLInputElement>, field: string): number | null {
    const raw = inputs.get(field)?.value ?? ""; return raw.trim() === "" ? null : Number(raw);
  }
  private deepStatus(snapshot: ObservationSnapshotMessage): string {
    const deep = snapshot.deepCatalog;
    if (deep.state === "loading") return "Carregant Gaia profunda…";
    if (deep.state === "ready") return `${deep.selectedStarCount.toLocaleString()} estrelles profundes${deep.truncated ? " (límit de memòria)" : ""}`;
    return deep.message ?? "";
  }
}
