type Ownership = "managed" | "external";
type CategoricalEncoding = "integer" | "palette" | "rgb" | "rgba";

interface CategoryRecord {
  readonly categoryKey: string;
  readonly parentKey: string | null;
  readonly categoryLabel: string;
}

interface SchemeClassAudit {
  readonly sourceCode: number;
  readonly sourceValue: number | string;
  readonly sourceLabel: string;
  readonly categoryKey?: string;
  readonly categoryLabel?: string;
  readonly classificationStatus?: "unknown" | "unclassified";
  readonly sampleValidity?: "nodata" | "masked" | "outside_coverage";
  readonly resolvedPath?: readonly string[];
  readonly semanticDepth?: number;
  readonly unresolvedChildren?: readonly string[];
}

interface SchemeAudit {
  readonly schemeKey: string;
  readonly schemeVersion: string;
  readonly mappingRevision: string;
  readonly displayName: string;
  readonly classes: readonly SchemeClassAudit[];
}

interface SchemeCatalog {
  readonly taxonomyKey: "TLST";
  readonly taxonomyVersion: string;
  readonly categories: readonly CategoryRecord[];
  readonly schemes: readonly SchemeAudit[];
}

interface CategoricalValue {
  readonly sourceValue: number | string;
  readonly pixelCount: number;
  readonly colorRgba: [number, number, number, number] | null;
}

interface SchemeCandidate {
  readonly schemeKey: string;
  readonly schemeVersion: string;
  readonly mappingRevision: string;
  readonly displayName: string;
  readonly matchedValues: number;
  readonly totalValues: number;
  readonly exact: boolean;
  readonly valueCodes: Readonly<Record<string, number>>;
}

interface CategoricalAnalysis {
  readonly encoding: CategoricalEncoding;
  readonly bandIndices: readonly number[];
  readonly sourceDtype: string;
  readonly validPixels: number;
  readonly invalidPixels: number;
  readonly values: readonly CategoricalValue[];
  readonly schemeCandidates: readonly SchemeCandidate[];
}

interface RasterInspection {
  readonly driver: string;
  readonly width: number;
  readonly height: number;
  readonly crs: string | null;
  readonly sourceDtype: string | null;
  readonly selectedPath: string;
  readonly subdatasets: readonly string[];
  readonly bands: readonly {
    index: number;
    dtype: string;
    description: string | null;
    colorInterpretation?: string | null;
  }[];
  readonly metadataSuggestions: {
    readonly suggestedEncoding: CategoricalEncoding | null;
    readonly suggestedBandIndices?: readonly number[];
    readonly requiresSubdatasetSelection: boolean;
    readonly requiresCategoricalSelection: boolean;
  };
  readonly categoricalAnalysis?: CategoricalAnalysis;
}

interface CategoricalImportCallbacks {
  readonly onCommitted: () => void;
  readonly onBack: () => void;
  readonly initialCategoryKey?: string;
}

/** Progressive categorical import surface shared by standard and user schemes. */
export class CategoricalImportView {
  public readonly element = document.createElement("div");

  private abortController: AbortController | null = null;
  private busyMessage: string | null = null;
  private importId: string | null = null;
  private files: File[] = [];
  private inspection: RasterInspection | null = null;
  private catalog: SchemeCatalog | null = null;
  private busy = false;
  private name = "";
  private ownership: Ownership = "managed";
  private externalPath = "";
  private subdataset = "";
  private encoding: CategoricalEncoding = "integer";
  private bandIndices = "1";
  private crs = "";
  private transform = "";
  private nodata = "";
  private textLayout = "";
  private textHeader = "";
  private selectedScheme = "custom";
  private customName = "Classificació personalitzada";
  private customVersion = "1.0";
  private mappingConfirmed = false;
  private refinementLicenseId = "CC-BY-4.0";
  private refinementLicenseUrl = refinementLicenseUrl("CC-BY-4.0");
  private refinementAttribution = "";
  private refinementProvider = "";
  private refinementVersion = "1.0";
  private refinementProvenanceUrl = "";
  private refinementCommercialUseConfirmed = false;

  constructor(private readonly callbacks: CategoricalImportCallbacks) {
    this.element.style.cssText = "display:flex;flex-direction:column;gap:10px";
    this.render();
    void this.loadCatalog();
  }

  public async cancel(): Promise<void> {
    if (this.abortController) {
      this.abortController.abort();
    }
    const importId = this.importId;
    this.importId = null;
    if (importId) {
      try { await fetch(`/api/raster-imports/${importId}`, { method: "DELETE" }); } catch { /* staging is recoverable */ }
    }
  }

  public handleOperationProgress(event: import("../../../contracts/events").OperationProgressedEvent): void {
    if (this.importId !== event.operationId) return;
    this.busyMessage = event.messageKey || "Processant...";
    const track = document.getElementById("categorical-import-progress-track");
    if (track) {
      track.style.display = "block";
    }
    const fill = document.getElementById("categorical-import-progress-fill");
    const percent = Math.floor((event.progressFraction ?? 0) * 100);
    if (fill) {
      fill.style.width = `${percent}%`;
    }
    const msgLabel = document.getElementById("categorical-import-status-msg");
    if (msgLabel) {
      msgLabel.textContent = `${this.busyMessage} (${percent}%)`;
    }
  }

  private async loadCatalog(): Promise<void> {
    try {
      this.catalog = await requestJson("/api/classification-schemes", { method: "GET" }) as SchemeCatalog;
      this.render();
    } catch (error) {
      this.showError(error);
    }
  }

  private render(): void {
    this.element.replaceChildren();
    const title = document.createElement("h3");
    title.textContent = "Importar cobertura categòrica";
    title.style.cssText = "margin:0;font-size:15px;color:#fff";
    this.element.append(
      title,
      note("Els valors font es conservaran intactes. La classificació detectada sempre s'ha de revisar i confirmar."),
    );
    this.element.appendChild(this.renderIdentity());
    if (this.inspection) this.element.appendChild(this.renderInspection());
    else this.element.appendChild(this.renderPreInspection());
    this.element.appendChild(this.renderActions());
  }

  private renderIdentity(): HTMLElement {
    const section = document.createElement("section");
    const name = labelledInput("Nom", "text", "Nom descriptiu de la capa");
    name.input.id = "categorical-import-name";
    name.input.value = this.name;
    name.input.oninput = () => { this.name = name.input.value; };
    const ownership = labelledSelect("Propietat", [
      ["managed", "Gestionada (copiar a la biblioteca)"],
      ["external", "Externa (no copiar ni eliminar)"],
    ]);
    ownership.select.id = "categorical-import-ownership";
    ownership.select.value = this.ownership;
    ownership.select.onchange = () => {
      this.ownership = ownership.select.value as Ownership;
      this.files = [];
      this.inspection = null;
      this.render();
    };
    section.append(name.root, ownership.root);
    if (this.ownership === "external") {
      const path = labelledInput("Ruta absoluta", "text", "C:\\dades\\cobertura.tif");
      path.input.id = "categorical-import-external-path";
      path.input.value = this.externalPath;
      path.input.oninput = () => { this.externalPath = path.input.value; };
      section.appendChild(path.root);
    } else {
      const label = document.createElement("label");
      label.textContent = "Fitxer o bundle";
      label.style.cssText = labelStyle();
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.style.cssText = inputStyle();
      input.onchange = () => { this.files = Array.from(input.files ?? []); };
      const directoryLabel = document.createElement("label");
      directoryLabel.textContent = "o carpeta bundle (preserva sidecars)";
      directoryLabel.style.cssText = labelStyle();
      const directory = document.createElement("input");
      directory.type = "file";
      directory.multiple = true;
      directory.setAttribute("webkitdirectory", "");
      directory.style.cssText = inputStyle();
      directory.onchange = () => { this.files = Array.from(directory.files ?? []); };
      section.append(label, input, directoryLabel, directory);
    }
    return section;
  }

  private renderPreInspection(): HTMLElement {
    const advanced = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Text/CSV i georeferència avançada";
    summary.style.cssText = summaryStyle();
    const layout = labelledSelect("Layout textual", [
      ["", "Confirma el layout…"], ["matrix", "Matriu"], ["xyz", "XYZ regular"],
    ]);
    layout.select.value = this.textLayout;
    layout.select.onchange = () => { this.textLayout = layout.select.value; };
    const header = labelledSelect("Capçalera", [
      ["", "Detectar; confirmar si és ambigu"], ["false", "No"], ["true", "Sí"],
    ]);
    header.select.value = this.textHeader;
    header.select.onchange = () => { this.textHeader = header.select.value; };
    const crs = labelledInput("CRS", "text", "EPSG:25831");
    crs.input.value = this.crs;
    crs.input.oninput = () => { this.crs = crs.input.value; };
    const transform = labelledInput("Transform (a,b,c,d,e,f)", "text", "10,0,0,0,-10,0");
    transform.input.value = this.transform;
    transform.input.oninput = () => { this.transform = transform.input.value; };
    advanced.append(summary, layout.root, header.root, crs.root, transform.root);
    return advanced;
  }

  private renderInspection(): HTMLElement {
    const inspection = this.inspection!;
    const section = document.createElement("section");
    section.style.cssText = panelStyle();
    section.appendChild(note(
      `${inspection.driver} · ${inspection.width} × ${inspection.height} · ${inspection.sourceDtype ?? "dtype mixt"} · ${inspection.crs ?? "CRS pendent"}`,
    ));
    if (inspection.subdatasets.length) {
      const dataset = labelledSelect("Dataset", [
        ["", "Selecciona un dataset…"],
        ...inspection.subdatasets.map(value => [value, value] as const),
      ]);
      dataset.select.value = this.subdataset;
      dataset.select.onchange = () => { this.subdataset = dataset.select.value; };
      section.appendChild(dataset.root);
    }
    if (!inspection.categoricalAnalysis) {
      section.appendChild(this.renderEncodingSelection(inspection));
      return section;
    }
    section.appendChild(this.renderAnalysis(inspection.categoricalAnalysis));
    return section;
  }

  private renderEncodingSelection(inspection: RasterInspection): HTMLElement {
    const box = document.createElement("div");
    const encoding = labelledSelect("Codificació", [
      ["integer", "Valors enters"], ["palette", "Índex + paleta"],
      ["rgb", "RGB exacte"], ["rgba", "RGBA exacte"],
    ]);
    encoding.select.value = this.encoding;
    encoding.select.onchange = () => {
      this.encoding = encoding.select.value as CategoricalEncoding;
      this.bandIndices = defaultBands(this.encoding, inspection.bands);
      this.render();
    };
    const bands = labelledInput("Bandes (índexs separats per comes)", "text", "1,2,3");
    bands.input.value = this.bandIndices;
    bands.input.oninput = () => { this.bandIndices = bands.input.value; };
    box.append(encoding.root, bands.root, note("La lectura categòrica sempre usa veí més proper; RGB(A) es compara byte a byte."));
    return box;
  }

  private renderAnalysis(analysis: CategoricalAnalysis): HTMLElement {
    const box = document.createElement("div");
    box.appendChild(note(
      `${analysis.values.length} valors · ${analysis.validPixels.toLocaleString("ca-ES")} píxels vàlids · codificació ${analysis.encoding}`,
    ));
    const exact = analysis.schemeCandidates.filter(value => value.exact);
    const schemes = labelledSelect("Esquema i revisió", [
      ...exact.map(value => [candidateIdentity(value), `${value.displayName} · ${value.schemeVersion}`] as const),
      ["custom", "Crear o reutilitzar una classificació pròpia"],
    ]);
    if (!exact.some(value => candidateIdentity(value) === this.selectedScheme)) {
      this.selectedScheme = exact.length ? candidateIdentity(exact[0]!) : "custom";
    }
    schemes.select.value = this.selectedScheme;
    schemes.select.onchange = () => { this.selectedScheme = schemes.select.value; this.render(); };
    box.appendChild(schemes.root);
    if (this.selectedScheme === "custom") box.appendChild(this.renderCustomMapping(analysis));
    else box.appendChild(this.renderKnownMapping(analysis, exact));
    const confirmation = document.createElement("label");
    confirmation.style.cssText = "display:flex;gap:8px;align-items:flex-start;font-size:12px;color:#fff;margin-top:10px";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = "categorical-mapping-confirmed";
    checkbox.checked = this.mappingConfirmed;
    checkbox.onchange = () => { this.mappingConfirmed = checkbox.checked; };
    confirmation.append(checkbox, document.createTextNode("He revisat els valors, l'esquema, la versió i el mapping TLST i en confirmo l'aplicació."));
    box.appendChild(confirmation);
    if (this.callbacks.initialCategoryKey) box.appendChild(this.renderRefinementLicense());
    const advanced = document.createElement("details");
    advanced.open = !this.inspection?.crs;
    const summary = document.createElement("summary");
    summary.textContent = "Avançat: CRS, transform i NoData";
    summary.style.cssText = summaryStyle();
    const crs = labelledInput("CRS override", "text", "EPSG:25831");
    crs.input.value = this.crs;
    crs.input.oninput = () => { this.crs = crs.input.value; };
    const transform = labelledInput("Transform (a,b,c,d,e,f)", "text", "10,0,0,0,-10,0");
    transform.input.value = this.transform;
    transform.input.oninput = () => { this.transform = transform.input.value; };
    const nodata = labelledInput("NoData override", "number", "255");
    nodata.input.value = this.nodata;
    nodata.input.oninput = () => { this.nodata = nodata.input.value; };
    advanced.append(summary, crs.root, transform.root, nodata.root);
    box.appendChild(advanced);
    return box;
  }

  private renderRefinementLicense(): HTMLElement {
    const box = document.createElement("fieldset");
    box.style.cssText = `${panelStyle()};margin-top:10px`;
    const legend = document.createElement("legend");
    legend.textContent = "Llicència i procedència del refinament";
    legend.style.cssText = "padding:0 6px;font-size:12px;color:var(--color-gold,#facc15)";
    box.appendChild(legend);
    box.appendChild(note(
      "Només es registrarà cobertura verificada si la llicència permet ús comercial i derivats. La procedència quedarà desada amb el recurs.",
    ));

    const license = labelledSelect("Llicència", [
      ["CC-BY-4.0", "Creative Commons Reconeixement 4.0"],
      ["CC0-1.0", "CC0 1.0"],
      ["public-domain", "Domini públic"],
      ["Copernicus-CLMS", "Política Copernicus CLMS"],
    ]);
    license.select.value = this.refinementLicenseId;
    license.select.onchange = () => {
      this.refinementLicenseId = license.select.value;
      this.refinementLicenseUrl = refinementLicenseUrl(this.refinementLicenseId);
      this.render();
    };
    const officialUrl = labelledInput("URL oficial de la llicència", "url", "https://...");
    officialUrl.input.value = this.refinementLicenseUrl;
    officialUrl.input.oninput = () => { this.refinementLicenseUrl = officialUrl.input.value; };
    const provider = labelledInput("Font o proveïdor", "text", "Organització que publica les dades");
    provider.input.value = this.refinementProvider;
    provider.input.oninput = () => { this.refinementProvider = provider.input.value; };
    const version = labelledInput("Versió del producte", "text", "2024-v1");
    version.input.value = this.refinementVersion;
    version.input.oninput = () => { this.refinementVersion = version.input.value; };
    const provenance = labelledInput("URL de procedència del dataset", "url", "https://...");
    provenance.input.value = this.refinementProvenanceUrl;
    provenance.input.oninput = () => { this.refinementProvenanceUrl = provenance.input.value; };
    const attribution = labelledInput("Text d'atribució o citació", "text", "Font, producte i any");
    attribution.input.value = this.refinementAttribution;
    attribution.input.oninput = () => { this.refinementAttribution = attribution.input.value; };
    box.append(license.root, officialUrl.root, provider.root, version.root, provenance.root, attribution.root);

    const commercial = document.createElement("label");
    commercial.style.cssText = "display:flex;gap:8px;align-items:flex-start;margin-top:10px;font-size:12px;color:#fff";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = this.refinementCommercialUseConfirmed;
    checkbox.onchange = () => { this.refinementCommercialUseConfirmed = checkbox.checked; };
    commercial.append(
      checkbox,
      document.createTextNode("Confirmo que aquesta font permet l'ús comercial, la transformació i la generació de productes derivats."),
    );
    box.appendChild(commercial);
    return box;
  }

  private renderKnownMapping(
    analysis: CategoricalAnalysis,
    candidates: readonly SchemeCandidate[],
  ): HTMLElement {
    const candidate = candidates.find(value => candidateIdentity(value) === this.selectedScheme);
    const scheme = this.catalog?.schemes.find(value => candidate && candidateIdentity(value) === candidateIdentity(candidate));
    if (!candidate || !scheme) return note("Carregant la matriu d'equivalències…");
    const table = mappingTable();
    for (const value of analysis.values) {
      const code = candidate.valueCodes[String(value.sourceValue)];
      const definition = scheme.classes.find(item => item.sourceCode === code);
      appendMappingRow(table, value, definition?.sourceLabel ?? "—", mappingDescription(definition));
    }
    return table;
  }

  private renderCustomMapping(analysis: CategoricalAnalysis): HTMLElement {
    const box = document.createElement("div");
    const name = labelledInput("Nom de l'esquema", "text", "La meva classificació");
    name.input.value = this.customName;
    name.input.oninput = () => { this.customName = name.input.value; };
    const version = labelledInput("Versió de l'esquema", "text", "1.0");
    version.input.value = this.customVersion;
    version.input.oninput = () => { this.customVersion = version.input.value; };
    box.append(name.root, version.root);
    const categoryOptions = this.catalog?.categories.map(category => [
      `category:${category.categoryKey}`,
      `${"  ".repeat(Math.max(0, category.categoryKey.split(".").length - 1))}${category.categoryLabel} — ${category.categoryKey}`,
    ] as const) ?? [];
    for (let index = 0; index < analysis.values.length; index++) {
      const value = analysis.values[index]!;
      const row = document.createElement("div");
      row.style.cssText = "display:grid;grid-template-columns:minmax(100px,.7fr) minmax(140px,1fr) minmax(220px,2fr);gap:8px;align-items:end;border-top:1px solid #333;padding:7px 0";
      const identity = note(`${String(value.sourceValue)} · ${value.pixelCount.toLocaleString("ca-ES")} px`);
      const label = labelledInput("Etiqueta font", "text", String(value.sourceValue));
      label.input.id = `categorical-label-${index}`;
      label.input.value = String(value.sourceValue);
      const outcome = labelledSelect("Interpretació", [
        ...categoryOptions,
        ["state:unknown", "Estat: desconegut"],
        ["state:unclassified", "Estat: sense classificar"],
        ["validity:nodata", "Validesa: sense dades"],
        ["validity:masked", "Validesa: emmascarat"],
        ["validity:outside_coverage", "Validesa: fora de cobertura"],
      ], `categorical-outcome-${index}`);
      if (this.callbacks.initialCategoryKey && categoryOptions.some(([optionValue]) => optionValue === `category:${this.callbacks.initialCategoryKey}`)) {
        outcome.select.value = `category:${this.callbacks.initialCategoryKey}`;
      }
      row.append(identity, label.root, outcome.root);
      box.appendChild(row);
    }
    return box;
  }

  private renderActions(): HTMLElement {
    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;justify-content:space-between;margin-top:4px;align-items:center;";
    const back = actionButton("Tornar");
    back.onclick = async () => { await this.cancel(); this.callbacks.onBack(); };

    const rightSide = document.createElement("div");
    rightSide.style.cssText = "display:flex;gap:12px;align-items:center;";

    if (this.busy && this.busyMessage) {
      const container = document.createElement("div");
      container.style.cssText = "display:flex;flex-direction:column;align-items:flex-end;gap:6px;width:250px;";
      
      const msg = document.createElement("div");
      msg.id = "categorical-import-status-msg";
      msg.textContent = this.busyMessage;
      msg.style.cssText = "font-size:12px;color:var(--color-gold,#facc15);";
      
      const progressTrack = document.createElement("div");
      progressTrack.id = "categorical-import-progress-track";
      progressTrack.style.cssText = "width:100%;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;display:none;";
      
      const progressFill = document.createElement("div");
      progressFill.id = "categorical-import-progress-fill";
      progressFill.style.cssText = "width:0%;height:100%;background:var(--color-gold,#facc15);transition:width 0.1s linear;";
      
      progressTrack.appendChild(progressFill);
      container.append(msg, progressTrack);
      rightSide.appendChild(container);

      const cancelOp = actionButton("Cancel·lar procés");
      cancelOp.style.color = "#ff8a80";
      cancelOp.onclick = () => {
        void this.cancel();
      };
      rightSide.appendChild(cancelOp);
    } else {
      const ready = Boolean(this.inspection?.categoricalAnalysis);
      const submit = actionButton(
        ready ? "Importar i activar" : this.inspection ? "Analitzar valors" : "Inspeccionar i continuar",
        true,
      );
      submit.onclick = () => void this.advance();
      rightSide.appendChild(submit);
    }

    actions.append(back, rightSide);
    return actions;
  }

  private async advance(): Promise<void> {
    if (this.busy) return;
    this.name = inputValue("categorical-import-name") || this.name;
    this.externalPath = inputValue("categorical-import-external-path") || this.externalPath;
    const currentOwnership = selectValue("categorical-import-ownership");
    if (currentOwnership === "managed" || currentOwnership === "external") {
      this.ownership = currentOwnership;
    }
    this.busy = true;
    this.abortController = new AbortController();
    this.busyMessage = "Iniciant...";
    this.render();
    try {
      if (!this.name.trim()) throw new Error("Cal indicar un nom descriptiu.");
      if (!this.importId) await this.createAndUpload();
      if (!this.inspection) {
        this.busyMessage = "Autodetectant layout GDAL...";
        this.render();
        await this.inspect({ fileOrdinal: findMainRasterOrdinal(this.files), textOptions: this.textOptions() });
      } else if (!this.inspection.categoricalAnalysis) {
        if (this.inspection.subdatasets.length && !this.subdataset) {
          throw new Error("Cal seleccionar explícitament un dataset.");
        }
        this.busyMessage = "Analitzant histograma...";
        this.render();
        await this.inspect({
          fileOrdinal: findMainRasterOrdinal(this.files),
          subdataset: this.subdataset || null,
          categoricalEncoding: this.encoding,
          bandIndices: parseBandIndices(this.bandIndices),
        });
      } else {
        this.busyMessage = "Consolidant fitxers i preparant importació...";
        this.render();
        await this.commit();
        this.importId = null;
        this.callbacks.onCommitted();
      }
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        this.showError(new Error("L'operació ha estat cancel·lada per l'usuari."));
      } else {
        this.showError(error);
      }
    } finally {
      this.busy = false;
      this.abortController = null;
      this.busyMessage = null;
      this.render();
    }
  }

  private async createAndUpload(): Promise<void> {
    if (this.ownership === "managed" && this.files.length === 0) {
      throw new Error("Cal seleccionar almenys un fitxer.");
    }
    if (this.ownership === "external" && !this.externalPath.trim()) {
      throw new Error("Cal indicar una ruta absoluta accessible pel backend.");
    }
    const created = await requestJson("/api/raster-imports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        semanticKind: "categorical",
        ownership: this.ownership,
        name: this.name.trim(),
        externalPath: this.externalPath.trim() || null,
        fileCount: Math.max(1, this.files.length),
      }),
      signal: this.abortController?.signal ?? null,
    }) as { importId: string };
    this.importId = String(created.importId);
    for (let ordinal = 0; ordinal < this.files.length; ordinal++) {
      const file = this.files[ordinal]!;
      this.busyMessage = `Pujant fitxer ${ordinal + 1} de ${this.files.length}...`;
      this.render();
      
      const track = document.getElementById("categorical-import-progress-track");
      if (track) track.style.display = "block";

      await uploadFileWithProgress(
        `/api/raster-imports/${this.importId}/files/${ordinal}`,
        file,
        { "X-TerraLab-Relative-Path": file.webkitRelativePath || file.name },
        this.abortController?.signal,
        (percent) => {
          const msg = document.getElementById("categorical-import-status-msg");
          const fill = document.getElementById("categorical-import-progress-fill");
          if (msg) msg.textContent = `Pujant fitxer ${ordinal + 1} de ${this.files.length}... (${percent}%)`;
          if (fill) fill.style.width = `${percent}%`;
        }
      );

      if (track) track.style.display = "none";
    }
  }

  private async inspect(request: Record<string, unknown>): Promise<void> {
    this.inspection = await requestJson(`/api/raster-imports/${this.importId}/inspect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: this.abortController?.signal ?? null,
      body: JSON.stringify(request),
    }) as RasterInspection;
    const suggestion = this.inspection.metadataSuggestions;
    if (suggestion.suggestedEncoding) this.encoding = suggestion.suggestedEncoding;
    if (suggestion.suggestedBandIndices?.length) {
      this.bandIndices = suggestion.suggestedBandIndices.join(",");
    }
    const exact = this.inspection.categoricalAnalysis?.schemeCandidates.filter(value => value.exact) ?? [];
    this.selectedScheme = exact.length ? candidateIdentity(exact[0]!) : "custom";
  }

  private async commit(): Promise<void> {
    const analysis = this.inspection!.categoricalAnalysis!;
    if (!this.mappingConfirmed) throw new Error("Cal revisar i confirmar explícitament el mapping.");
    const confirmation: Record<string, unknown> = {
      name: this.name.trim(),
      subdataset: this.subdataset || null,
      mappingConfirmed: true,
      overrides: this.metadataOverrides(),
    };
    if (this.selectedScheme === "custom") {
      if (!this.catalog) throw new Error("El catàleg TLST encara no està disponible.");
      confirmation.customScheme = {
        displayName: this.customName.trim(),
        schemeVersion: this.customVersion.trim(),
        classes: analysis.values.map((value, index) => {
          const outcome = selectValue(`categorical-outcome-${index}`);
          const item: Record<string, unknown> = {
            sourceValue: value.sourceValue,
            sourceLabel: inputValue(`categorical-label-${index}`) || String(value.sourceValue),
          };
          const [kind, target] = outcome.split(":", 2);
          if (kind === "category") item.categoryKey = target;
          else if (kind === "state") item.classificationStatus = target;
          else if (kind === "validity") item.sampleValidity = target;
          return item;
        }),
      };
    } else {
      const candidate = analysis.schemeCandidates.find(value => candidateIdentity(value) === this.selectedScheme);
      if (!candidate) throw new Error("L'esquema seleccionat ja no coincideix amb l'anàlisi.");
      Object.assign(confirmation, {
        schemeKey: candidate.schemeKey,
        schemeVersion: candidate.schemeVersion,
        mappingRevision: candidate.mappingRevision,
      });
    }
    if (this.callbacks.initialCategoryKey) {
      if (!this.refinementCommercialUseConfirmed) {
        throw new Error("Cal confirmar els drets d'ús comercial i de generació de derivats.");
      }
      confirmation.refinementContext = {
        categoryKey: this.callbacks.initialCategoryKey,
        licenseId: this.refinementLicenseId,
        officialUrl: this.refinementLicenseUrl.trim(),
        attribution: this.refinementAttribution.trim(),
        citation: this.refinementAttribution.trim(),
        provider: this.refinementProvider.trim(),
        version: this.refinementVersion.trim(),
        provenanceUrl: this.refinementProvenanceUrl.trim(),
        commercialUseConfirmed: true,
      };
    }
    await requestJson(`/api/raster-imports/${this.importId}/commit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: this.abortController?.signal ?? null,
      body: JSON.stringify(confirmation),
    });
  }

  private metadataOverrides(): Record<string, unknown> {
    const overrides: Record<string, unknown> = { provenance: "categorical-import-confirmation" };
    if (this.crs.trim()) overrides.crs = this.crs.trim();
    if (this.transform.trim()) overrides.transform = parseNumbers(this.transform, 6, "transform");
    if (this.nodata.trim()) overrides.nodata = Number(this.nodata);
    return overrides;
  }

  private textOptions(): Record<string, unknown> | undefined {
    const sourceName = this.files[findMainRasterOrdinal(this.files)]?.name ?? this.externalPath;
    if (!/\.(txt|csv|xyz)$/i.test(sourceName)) return undefined;
    return {
      layout: this.textLayout || null,
      hasHeader: this.textHeader === "" ? null : this.textHeader === "true",
      crs: this.crs.trim() || null,
      transform: this.transform.trim() ? parseNumbers(this.transform, 6, "transform") : null,
    };
  }

  private showError(error: unknown): void {
    window.alert(error instanceof Error ? error.message : String(error));
  }
}

function refinementLicenseUrl(licenseId: string): string {
  const urls: Readonly<Record<string, string>> = {
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "public-domain": "https://creativecommons.org/publicdomain/mark/1.0/",
    "Copernicus-CLMS": "https://land.copernicus.eu/en/faq/data-use-terms-and-conditions",
  };
  return urls[licenseId] ?? "";
}

function candidateIdentity(value: Pick<SchemeCandidate | SchemeAudit, "schemeKey" | "schemeVersion" | "mappingRevision">): string {
  return `${value.schemeKey}\u001f${value.schemeVersion}\u001f${value.mappingRevision}`;
}

function mappingDescription(value: SchemeClassAudit | undefined): string {
  if (!value) return "Sense equivalència";
  if (value.categoryKey) {
    const remaining = value.unresolvedChildren?.length
      ? ` · genèric; fills no resolts: ${value.unresolvedChildren.join(", ")}`
      : " · directe";
    return `${value.categoryLabel ?? value.categoryKey}${remaining}`;
  }
  if (value.classificationStatus) return `Estat: ${value.classificationStatus}`;
  if (value.sampleValidity) return `Validesa: ${value.sampleValidity}`;
  return "Sense classificar";
}

function mappingTable(): HTMLDivElement {
  const table = document.createElement("div");
  table.style.cssText = "margin-top:8px;border:1px solid #333;border-radius:4px;overflow:hidden";
  return table;
}

function appendMappingRow(
  table: HTMLElement,
  value: CategoricalValue,
  sourceLabel: string,
  interpretation: string,
): void {
  const row = document.createElement("div");
  row.style.cssText = "display:grid;grid-template-columns:.65fr 1fr 1.6fr;gap:8px;padding:6px 8px;border-bottom:1px solid #333;font-size:11px;color:#ddd";
  const source = document.createElement("span");
  source.textContent = `${String(value.sourceValue)} (${value.pixelCount.toLocaleString("ca-ES")})`;
  const label = document.createElement("span");
  label.textContent = sourceLabel;
  const target = document.createElement("span");
  target.textContent = interpretation;
  row.append(source, label, target);
  table.appendChild(row);
}

function defaultBands(encoding: CategoricalEncoding, bands: readonly { index: number }[]): string {
  const count = encoding === "rgba" ? 4 : encoding === "rgb" ? 3 : 1;
  return bands.slice(0, count).map(value => value.index).join(",");
}

function parseBandIndices(value: string): number[] {
  const values = parseNumbers(value, null, "bandes");
  if (!values.length || values.some(item => !Number.isSafeInteger(item) || item < 1)) {
    throw new Error("Els índexs de banda han de ser enters positius.");
  }
  return values;
}

function parseNumbers(value: string, count: number | null, label: string): number[] {
  const values = value.split(",").map(item => Number(item.trim()));
  if ((count !== null && values.length !== count) || values.some(item => !Number.isFinite(item))) {
    throw new Error(`El camp ${label} no té el nombre o el format esperat.`);
  }
  return values;
}

function note(text: string): HTMLDivElement {
  const value = document.createElement("div");
  value.textContent = text;
  value.style.cssText = "font-size:12px;color:var(--color-text-dim,#aaa)";
  return value;
}

function labelledInput(labelText: string, type: string, placeholder: string): { root: HTMLDivElement; input: HTMLInputElement } {
  const root = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  label.style.cssText = labelStyle();
  const input = document.createElement("input");
  input.type = type;
  input.placeholder = placeholder;
  input.style.cssText = inputStyle();
  root.append(label, input);
  return { root, input };
}

function labelledSelect(
  labelText: string,
  options: readonly (readonly [string, string])[],
  id?: string,
): { root: HTMLDivElement; select: HTMLSelectElement } {
  const root = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  label.style.cssText = labelStyle();
  const select = document.createElement("select");
  if (id) select.id = id;
  select.style.cssText = inputStyle();
  for (const [value, text] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.appendChild(option);
  }
  root.append(label, select);
  return { root, select };
}

function actionButton(text: string, primary = false): HTMLButtonElement {
  const button = document.createElement("button");
  button.textContent = text;
  button.style.cssText = `padding:7px 14px;border-radius:4px;cursor:pointer;border:1px solid ${primary ? "var(--color-gold,#facc15)" : "var(--color-border,#333)"};background:${primary ? "var(--color-gold,#facc15)" : "transparent"};color:${primary ? "#111" : "#fff"};font-size:12px`;
  return button;
}

function labelStyle(): string {
  return "display:block;font-size:11px;color:var(--color-text-dim,#aaa);margin:8px 0 4px";
}

function inputStyle(): string {
  return "box-sizing:border-box;width:100%;padding:7px 8px;border-radius:4px;border:1px solid var(--color-border,#333);background:var(--color-surface,#1a1a1a);color:#fff;font-size:12px";
}

function panelStyle(): string {
  return "border:1px solid var(--color-border,#333);border-radius:6px;padding:12px";
}

function summaryStyle(): string {
  return "cursor:pointer;font-size:12px;color:#aaa;margin-top:8px";
}

function inputValue(id: string): string {
  return (document.getElementById(id) as HTMLInputElement | null)?.value.trim() ?? "";
}

function selectValue(id: string): string {
  return (document.getElementById(id) as HTMLSelectElement | null)?.value ?? "";
}

async function requestJson(url: string, init: RequestInit): Promise<unknown> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
  return response.json();
}

function uploadFileWithProgress(
  url: string,
  file: File,
  headers: Record<string, string>,
  signal: AbortSignal | undefined | null,
  onProgress: (percent: number) => void
): Promise<any> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    for (const [key, value] of Object.entries(headers)) xhr.setRequestHeader(key, value);

    if (signal) {
      signal.addEventListener("abort", () => {
        xhr.abort();
        reject(new DOMException("Aborted", "AbortError"));
      });
    }

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.floor((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response ? JSON.parse(xhr.response) : null);
      } else {
        reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error("Network error"));
    xhr.send(file);
  });
}


function findMainRasterOrdinal(files: File[]): number {
  if (files.length <= 1) return 0;
  const rasterExts = ['.tif', '.tiff', '.vrt', '.nc', '.hgt', '.asc', '.dt0', '.dt1', '.dt2', '.dem', '.img', '.jp2'];
  const exactMatches = files.findIndex(f => rasterExts.some(ext => f.name.toLowerCase().endsWith(ext)));
  if (exactMatches !== -1) return exactMatches;
  const textExts = ['.txt', '.csv', '.xyz'];
  const textMatches = files.findIndex(f => textExts.some(ext => f.name.toLowerCase().endsWith(ext)));
  if (textMatches !== -1) return textMatches;
  return 0;
}
