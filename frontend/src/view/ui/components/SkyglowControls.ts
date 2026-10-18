import type { SkyglowConfiguration, SkyglowConfigurationSnapshot } from "../../../contracts/skyglow_contracts";

/** Configuració de fonts; el transport encara no produeix radiància del cel. */
export class SkyglowControls {
  readonly element = document.createElement("div");
  private readonly mode = document.createElement("select");
  private readonly kelvinGroup = document.createElement("div");
  private readonly slider = document.createElement("input");
  private readonly value = document.createElement("output");
  private readonly example = document.createElement("div");
  private readonly normalization = document.createElement("select");
  private readonly status = document.createElement("div");
  private generation = -1;
  private pendingConfiguration: string | null = null;
  private configuration: SkyglowConfiguration = {
    mode: "realistic", kelvin: 3000, spectral_family: "CIE_LED_B1_B5",
    normalization: "constant_photopic_flux", mixture_model: "deterministic_reference_ensemble_v1",
    revision: "black-marble-conditional-v1",
  };

  constructor(private readonly onChange: (configuration: SkyglowConfiguration) => void) {
    this.element.style.cssText = "display:flex;flex-direction:column;gap:6px;font-size:11px;";
    this.mode.style.cssText = "background:var(--color-surface);color:var(--color-text-bright);border:1px solid var(--color-border);border-radius:4px;padding:4px;width:100%;";
    this.normalization.style.cssText = this.mode.style.cssText;
    this.mode.setAttribute("aria-label", "Modalitat de simulació de contaminació lumínica");
    this.mode.add(new Option("Simulació realista", "realistic"));
    this.mode.add(new Option("Simulació per kelvins", "kelvin"));
    this.mode.onchange = () => {
      this.configuration = { ...this.configuration, mode: this.mode.value as SkyglowConfiguration["mode"] };
      this.refresh();
      this.submit();
    };
    const help = document.createElement("p");
    help.textContent = "Observacions Black Marble reals i estimacions espectrals. La simulació realista és una predicció condicionada, no una mesura directa de la brillantor del cel.";
    help.style.cssText = "font-size:10px;color:var(--color-text-muted);margin:0;";
    const label = document.createElement("label");
    label.textContent = "Temperatura de color: ";
    label.htmlFor = "skyglow-kelvin";
    label.appendChild(this.value);
    this.slider.id = "skyglow-kelvin";
    this.slider.type = "range";
    this.slider.min = "2800";
    this.slider.max = "6500";
    this.slider.step = "50";
    this.slider.style.cssText = "width:100%;min-height:28px;accent-color:var(--color-accent);";
    this.slider.oninput = () => {
      this.configuration = { ...this.configuration, kelvin: Number(this.slider.value) };
      this.pendingConfiguration = JSON.stringify(this.configuration);
      this.refresh();
      this.status.textContent = "Configuració pendent d'aplicar…";
    };
    this.slider.onchange = () => this.submit();
    const scale = document.createElement("div");
    scale.style.cssText = "display:flex;justify-content:space-between;";
    const min = document.createElement("span"); min.textContent = "2.800 K";
    const max = document.createElement("span"); max.textContent = "6.500 K";
    scale.append(min, max);
    const family = document.createElement("div");
    family.textContent = "Família SPD estable: LED de fòsfor CIE B1–B5. Font: CIE 015:2018, taules a 1 nm. Interpolació espectral amb CCT comprovada; sense extrapolació.";
    family.style.fontSize = "10px";
    this.kelvinGroup.append(label, this.slider, scale, this.example, family);
    this.normalization.setAttribute("aria-label", "Magnitud conservada en canviar la temperatura");
    for (const [id, text] of [
      ["constant_photopic_flux", "Flux lluminós fotòpic constant"],
      ["constant_radiant_power", "Potència radiant constant"],
      ["constant_dnb_reference", "Resposta DNB de referència constant"],
      ["conditional_relative", "Escala relativa condicionada"],
    ]) this.normalization.add(new Option(text, id));
    this.normalization.onchange = () => {
      this.configuration = { ...this.configuration, normalization: this.normalization.value as SkyglowConfiguration["normalization"] };
      this.submit();
    };
    this.status.setAttribute("role", "status");
    this.status.textContent = "Configuració espectral; transport atmosfèric pendent. Cap efecte físic sobre el cel disponible encara.";
    this.element.append(this.mode, help, this.kelvinGroup, this.normalization, this.status);
    this.refresh();
  }

  update(snapshot: SkyglowConfigurationSnapshot): void {
    if (snapshot.schemaVersion !== 1 || snapshot.generation < this.generation) return;
    if (this.pendingConfiguration !== null && JSON.stringify(snapshot.configuration) !== this.pendingConfiguration && snapshot.error === null) return;
    this.pendingConfiguration = null;
    this.generation = snapshot.generation;
    this.configuration = snapshot.configuration;
    this.refresh();
    const cct = snapshot.effectiveSpectrum?.effectiveCctK;
    this.status.textContent = snapshot.error ?? `${cct ? `CCT efectiva: ${cct.toFixed(1)} K. ` : "Ensemble determinista de mescles hipotètiques; pesos de flux radiant. "}Transport atmosfèric pendent; cap resultat del cel calculat.`;
  }

  private submit(): void {
    this.pendingConfiguration = JSON.stringify(this.configuration);
    this.onChange(this.configuration);
  }

  private refresh(): void {
    this.mode.value = this.configuration.mode;
    this.slider.value = String(this.configuration.kelvin);
    this.value.value = `${this.configuration.kelvin.toLocaleString("ca-ES")} K`;
    this.slider.setAttribute("aria-valuetext", this.value.value);
    this.normalization.value = this.configuration.normalization;
    this.kelvinGroup.hidden = this.configuration.mode !== "kelvin";
    this.normalization.hidden = this.configuration.mode !== "kelvin";
    const k = this.configuration.kelvin;
    this.example.textContent = `Exemple: ${k < 3500 ? "LED blanc càlid" : k < 4500 ? "LED blanc neutre" : k < 5500 ? "LED blanc fred" : "LED tipus llum de dia"}. Orientatiu; no canvia la família SPD.`;
  }
}
