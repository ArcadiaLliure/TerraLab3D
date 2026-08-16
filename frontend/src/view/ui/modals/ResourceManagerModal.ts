import { ResourceManager } from "../../../application/ResourceManager";
import type { ResourceDescriptor } from "../../../contracts/resource_manager_contracts";

type MainDomainTab = "sky" | "earth";
type SkySubCategory = "all" | "solar_system" | "deep_sky";
type EarthSubCategory = "all" | "dem" | "land_cover" | "light_pollution";

export class ResourceManagerModal {
  private element: HTMLDivElement;
  private contentBox: HTMLDivElement;
  private tabsContainer: HTMLDivElement;
  private subFilterContainer: HTMLDivElement;
  private listContainer: HTMLDivElement;

  private activeDomain: MainDomainTab = "sky";
  private activeSkyCategory: SkySubCategory = "all";
  private activeEarthCategory: EarthSubCategory = "all";

  private unsubCatalog?: () => void;
  private unsubJobs?: () => void;

  constructor(private manager: ResourceManager) {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      position: fixed;
      top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
      font-family: var(--font-family-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
    `;

    this.contentBox = document.createElement("div");
    this.contentBox.style.cssText = `
      width: 760px;
      max-width: 92vw;
      max-height: 88vh;
      background: var(--color-surface, #14161d);
      border: 1px solid var(--color-border, #2a2e3d);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.65);
      overflow: hidden;
    `;

    // Modal Header
    const header = document.createElement("div");
    header.style.cssText = `
      padding: 16px 22px;
      border-bottom: 1px solid var(--color-border, #2a2e3d);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--color-surface-raised, #1a1d26);
    `;

    const titleBox = document.createElement("div");
    const title = document.createElement("h2");
    title.textContent = "Gestor de Recursos i Capes";
    title.style.cssText = "margin: 0; font-size: 17px; color: var(--color-text-bright, #fff); font-weight: 600; letter-spacing: -0.01em;";
    const subtitle = document.createElement("div");
    subtitle.textContent = "Gestiona les dades astronòmiques, catàlegs celestes, models d'elevació i cobertures superficials";
    subtitle.style.cssText = "font-size: 11px; color: var(--color-text-muted, #8b92a5); margin-top: 2px;";
    titleBox.append(title, subtitle);

    const closeBtn = document.createElement("button");
    closeBtn.innerHTML = "&times;";
    closeBtn.style.cssText = `
      background: none; border: none; color: var(--color-text-muted, #8b92a5);
      font-size: 26px; cursor: pointer; padding: 0 4px; line-height: 1;
      transition: color 0.15s ease;
    `;
    closeBtn.onmouseenter = () => { closeBtn.style.color = "#fff"; };
    closeBtn.onmouseleave = () => { closeBtn.style.color = "var(--color-text-muted, #8b92a5)"; };
    closeBtn.onclick = () => this.close();

    header.append(titleBox, closeBtn);

    // Primary Domain Tabs (Cel / Terra)
    this.tabsContainer = document.createElement("div");
    this.tabsContainer.style.cssText = `
      display: flex;
      background: var(--color-surface-dim, #11131a);
      border-bottom: 1px solid var(--color-border, #2a2e3d);
      padding: 0 16px;
      gap: 8px;
    `;

    // Sub-category filter pills container
    this.subFilterContainer = document.createElement("div");
    this.subFilterContainer.style.cssText = `
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 10px 20px;
      background: rgba(20, 22, 29, 0.7);
      border-bottom: 1px solid rgba(42, 46, 61, 0.6);
      flex-wrap: wrap;
    `;

    // Resource list container
    this.listContainer = document.createElement("div");
    this.listContainer.style.cssText = `
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    `;

    this.contentBox.append(header, this.tabsContainer, this.subFilterContainer, this.listContainer);
    this.element.appendChild(this.contentBox);

    this.unsubCatalog = this.manager.subscribeCatalog(() => this.render());
    this.unsubJobs = this.manager.subscribeJobs(() => this.render());

    this.render();
  }

  private getDescriptorDomain(desc: ResourceDescriptor): MainDomainTab {
    const metaDomain = String(desc.metadata?.domain || "").toLowerCase();
    if (metaDomain === "earth" || metaDomain === "terra") return "earth";
    if (metaDomain === "sky" || metaDomain === "cel") return "sky";
    if (desc.id.startsWith("earth.")) return "earth";
    return "sky";
  }

  private getDescriptorCategory(desc: ResourceDescriptor): string {
    const metaCat = String(desc.metadata?.category || "").toLowerCase();
    if (metaCat) return metaCat;
    if (desc.id.startsWith("solar.")) return "solar_system";
    if (desc.id.startsWith("sky.")) return "deep_sky";
    if (desc.id.startsWith("earth.dem")) return "dem";
    if (desc.id.startsWith("earth.surface")) return "land_cover";
    if (desc.id.startsWith("earth.light")) return "light_pollution";
    return "other";
  }

  private formatBytes(bytes: number | null | undefined): string {
    if (!bytes) return "Mida desconeguda";
    const mb = bytes / (1024 * 1024);
    if (mb > 1024) return `${(mb / 1024).toFixed(2)} GB`;
    return `${mb.toFixed(1)} MB`;
  }

  private render(): void {
    this.renderTabs();
    this.renderSubFilters();
    this.renderList();
  }

  private renderTabs(): void {
    this.tabsContainer.innerHTML = "";

    const allDesc = this.manager.getAllDescriptors();
    const skyCount = allDesc.filter((d) => this.getDescriptorDomain(d) === "sky").length;
    const earthCount = allDesc.filter((d) => this.getDescriptorDomain(d) === "earth").length;

    const tabs: Array<{ id: MainDomainTab; label: string; icon: string; count: number }> = [
      { id: "sky", label: "Cel", icon: "🌌", count: skyCount },
      { id: "earth", label: "Terra", icon: "🌍", count: earthCount },
    ];

    for (const tab of tabs) {
      const btn = document.createElement("button");
      const isActive = this.activeDomain === tab.id;
      btn.style.cssText = `
        padding: 12px 18px;
        background: none;
        border: none;
        border-bottom: 2px solid ${isActive ? "var(--color-gold, #facc15)" : "transparent"};
        color: ${isActive ? "var(--color-text-bright, #fff)" : "var(--color-text-muted, #8b92a5)"};
        font-size: 14px;
        font-weight: ${isActive ? "600" : "500"};
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.15s ease;
      `;

      btn.innerHTML = `<span>${tab.icon}</span> <span>${tab.label}</span> <span style="font-size: 11px; padding: 1px 6px; border-radius: 10px; background: ${isActive ? "rgba(250, 204, 21, 0.2)" : "rgba(255,255,255,0.06)"}; color: ${isActive ? "#facc15" : "#888"}">${tab.count}</span>`;

      btn.onclick = () => {
        if (this.activeDomain !== tab.id) {
          this.activeDomain = tab.id;
          this.render();
        }
      };

      this.tabsContainer.appendChild(btn);
    }
  }

  private renderSubFilters(): void {
    this.subFilterContainer.innerHTML = "";

    if (this.activeDomain === "sky") {
      const filters: Array<{ id: SkySubCategory; label: string; icon: string }> = [
        { id: "all", label: "Tots els recursos del Cel", icon: "✦" },
        { id: "solar_system", label: "Sistema Solar", icon: "🪐" },
        { id: "deep_sky", label: "Cel Profund", icon: "✨" },
      ];

      for (const filter of filters) {
        const pill = document.createElement("button");
        const isActive = this.activeSkyCategory === filter.id;
        pill.style.cssText = `
          padding: 5px 12px;
          border-radius: 16px;
          font-size: 12px;
          cursor: pointer;
          border: 1px solid ${isActive ? "var(--color-gold, #facc15)" : "rgba(42, 46, 61, 0.8)"};
          background: ${isActive ? "rgba(250, 204, 21, 0.15)" : "rgba(26, 29, 38, 0.6)"};
          color: ${isActive ? "var(--color-gold, #facc15)" : "var(--color-text-muted, #8b92a5)"};
          font-weight: ${isActive ? "600" : "400"};
          display: flex;
          align-items: center;
          gap: 5px;
          transition: all 0.15s ease;
        `;
        pill.innerHTML = `<span>${filter.icon}</span> <span>${filter.label}</span>`;
        pill.onclick = () => {
          this.activeSkyCategory = filter.id;
          this.render();
        };
        this.subFilterContainer.appendChild(pill);
      }
    } else {
      const filters: Array<{ id: EarthSubCategory; label: string; icon: string }> = [
        { id: "all", label: "Totes les capes de la Terra", icon: "✦" },
        { id: "dem", label: "Topografia (DEM)", icon: "⛰️" },
        { id: "land_cover", label: "Cobertura del Sòl", icon: "🌱" },
        { id: "light_pollution", label: "Contaminació Lumínica", icon: "💡" },
      ];

      for (const filter of filters) {
        const pill = document.createElement("button");
        const isActive = this.activeEarthCategory === filter.id;
        pill.style.cssText = `
          padding: 5px 12px;
          border-radius: 16px;
          font-size: 12px;
          cursor: pointer;
          border: 1px solid ${isActive ? "var(--color-gold, #facc15)" : "rgba(42, 46, 61, 0.8)"};
          background: ${isActive ? "rgba(250, 204, 21, 0.15)" : "rgba(26, 29, 38, 0.6)"};
          color: ${isActive ? "var(--color-gold, #facc15)" : "var(--color-text-muted, #8b92a5)"};
          font-weight: ${isActive ? "600" : "400"};
          display: flex;
          align-items: center;
          gap: 5px;
          transition: all 0.15s ease;
        `;
        pill.innerHTML = `<span>${filter.icon}</span> <span>${filter.label}</span>`;
        pill.onclick = () => {
          this.activeEarthCategory = filter.id;
          this.render();
        };
        this.subFilterContainer.appendChild(pill);
      }
    }
  }

  private renderList(): void {
    this.listContainer.innerHTML = "";

    const allDescriptors = this.manager.getAllDescriptors();
    if (allDescriptors.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "Carregant catàleg de recursos...";
      empty.style.cssText = "color: var(--color-text-muted, #888); text-align: center; padding: 40px;";
      this.listContainer.appendChild(empty);
      return;
    }

    // Filter by domain and category
    const filtered = allDescriptors.filter((desc) => {
      const domain = this.getDescriptorDomain(desc);
      if (domain !== this.activeDomain) return false;

      const category = this.getDescriptorCategory(desc);
      if (this.activeDomain === "sky") {
        if (this.activeSkyCategory === "solar_system") return category === "solar_system";
        if (this.activeSkyCategory === "deep_sky") return category === "deep_sky";
      } else {
        if (this.activeEarthCategory === "dem") return category === "dem";
        if (this.activeEarthCategory === "land_cover") return category === "land_cover";
        if (this.activeEarthCategory === "light_pollution") return category === "light_pollution";
      }
      return true;
    });

    if (filtered.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "No hi ha recursos en aquesta categoria.";
      empty.style.cssText = "color: var(--color-text-muted, #888); text-align: center; padding: 30px;";
      this.listContainer.appendChild(empty);
      return;
    }

    for (const desc of filtered) {
      const item = document.createElement("div");
      item.style.cssText = `
        border: 1px solid var(--color-border, #2a2e3d);
        border-radius: 8px;
        padding: 14px 16px;
        background: var(--color-surface-raised, #1a1d26);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      `;

      const topRow = document.createElement("div");
      topRow.style.cssText = "display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;";

      const titleBox = document.createElement("div");
      const title = document.createElement("div");
      title.textContent = desc.title;
      title.style.cssText = "font-weight: 600; font-size: 14px; color: var(--color-gold, #facc15);";

      const provider = document.createElement("div");
      provider.textContent = `${desc.provider} · ${desc.acquisitionKind}`;
      provider.style.cssText = "font-size: 11px; color: var(--color-text-muted, #8b92a5); margin-top: 2px;";

      titleBox.append(title, provider);

      const state = this.manager.getInstallState(desc.id);
      const statusBadge = document.createElement("div");
      statusBadge.style.cssText = `
        font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 4px;
        background: var(--color-surface-dim, #11131a);
        color: var(--color-text-muted, #888);
        border: 1px solid var(--color-border, #2a2e3d);
        align-self: flex-start;
      `;
      statusBadge.textContent = state.status;
      if (state.status === "READY") {
        statusBadge.textContent = "DISPONIBLE";
        statusBadge.style.color = "#4ade80";
        statusBadge.style.borderColor = "rgba(74, 222, 128, 0.4)";
        statusBadge.style.background = "rgba(74, 222, 128, 0.1)";
      } else if (state.status === "DOWNLOADING") {
        statusBadge.textContent = "DESCARREGANT";
        statusBadge.style.color = "var(--color-gold, #facc15)";
        statusBadge.style.borderColor = "rgba(250, 204, 21, 0.4)";
        statusBadge.style.background = "rgba(250, 204, 21, 0.1)";
      } else if (state.status === "ERROR") {
        statusBadge.textContent = "ERROR";
        statusBadge.style.color = "#ff8a80";
        statusBadge.style.borderColor = "rgba(255, 138, 128, 0.4)";
      }

      topRow.append(titleBox, statusBadge);
      item.appendChild(topRow);

      if (desc.credits && desc.credits.length > 0) {
        const credits = document.createElement("div");
        credits.style.cssText = "font-size: 10px; color: var(--color-text-dim, #6e768b); margin-bottom: 10px;";
        credits.textContent = `Crèdits: ${desc.credits.join(", ")}`;
        item.appendChild(credits);
      }

      const variantsGrid = document.createElement("div");
      variantsGrid.style.cssText = "display: flex; flex-direction: column; gap: 6px;";

      for (const variant of desc.variants) {
        const variantRow = document.createElement("div");
        variantRow.style.cssText = `
          display: flex; justify-content: space-between; align-items: center;
          background: var(--color-surface, #14161d);
          padding: 8px 12px; border-radius: 6px;
          border: 1px solid rgba(42, 46, 61, 0.7);
        `;

        const vInfo = document.createElement("div");
        vInfo.style.cssText = "display: flex; flex-direction: column; font-size: 12px;";

        const vTitle = document.createElement("span");
        vTitle.textContent = variant.title;
        vTitle.style.color = "var(--color-text-bright, #fff)";
        vTitle.style.fontWeight = "500";

        const vSize = document.createElement("span");
        const details = [
          variant.format?.toUpperCase(),
          variant.width && variant.height ? `${variant.width} × ${variant.height}` : null,
          variant.publishedSizeLabel || this.formatBytes(variant.expectedBytes),
        ].filter((value): value is string => Boolean(value));
        vSize.textContent = details.join(" · ");
        vSize.style.color = "var(--color-text-muted, #8b92a5)";
        vSize.style.fontSize = "10px";

        vInfo.append(vTitle, vSize);

        const btnContainer = document.createElement("div");
        btnContainer.style.cssText = "display: flex; align-items: center; gap: 8px;";

        const isThisVariantReady = state.status === "READY" && (!state.variantId || state.variantId === variant.id);
        const isDownloadingThis = (state.status === "DOWNLOADING" || state.status === "PAUSED") && state.variantId === variant.id;

        if (isThisVariantReady) {
          const readyText = document.createElement("span");
          readyText.textContent = "Instal·lat";
          readyText.style.cssText = "font-size: 11px; color: #4ade80; font-weight: 500;";

          const deleteBtn = document.createElement("button");
          deleteBtn.textContent = "Eliminar";
          deleteBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid rgba(255, 138, 128, 0.3); background: transparent; color: #ff8a80; margin-left: 6px;";
          deleteBtn.onclick = () => {
            if (confirm(`Estàs segur que vols eliminar ${desc.title} (${variant.title})?`)) {
              this.manager.deleteResource(desc.id, variant.id);
            }
          };

          btnContainer.append(readyText, deleteBtn);
        } else if (isDownloadingThis) {
          const job = this.manager.getJobState(`${desc.id}_${variant.id}`);
          if (job && job.progress !== null) {
            const pct = document.createElement("span");
            pct.textContent = `${Math.floor(job.progress * 100)}%`;
            pct.style.cssText = "font-size: 11px; color: var(--color-gold, #facc15); width: 35px; text-align: right;";
            btnContainer.appendChild(pct);
          }

          const actionBtn = document.createElement("button");
          actionBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-gold);";
          if (state.status === "PAUSED") {
            actionBtn.textContent = "Reprendre";
            actionBtn.onclick = () => this.manager.startDownload(desc.id, variant.id);
          } else {
            actionBtn.textContent = "Pausar";
            actionBtn.onclick = () => this.manager.pauseDownload(desc.id, variant.id);
          }

          const cancelBtn = document.createElement("button");
          cancelBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid #ff8a80; background: transparent; color: #ff8a80;";
          cancelBtn.textContent = "Cancel·lar";
          cancelBtn.onclick = () => this.manager.cancelDownload(desc.id, variant.id);

          btnContainer.append(actionBtn, cancelBtn);
        } else if (
          state.variantId === variant.id &&
          (state.status === "VERIFYING" || state.status === "PROCESSING")
        ) {
          const working = document.createElement("span");
          working.textContent = state.status === "VERIFYING" ? "Verificant…" : "Processant…";
          working.style.cssText = "font-size: 11px; color: var(--color-gold, #facc15);";
          btnContainer.appendChild(working);
        } else {
          const dlBtn = document.createElement("button");
          dlBtn.textContent = variant.sourceUrl ? "Baixar" : "Instal·lar";
          dlBtn.style.cssText = "padding: 4px 12px; font-size: 11px; font-weight: 500; border-radius: 4px; cursor: pointer; border: 1px solid rgba(250, 204, 21, 0.4); background: rgba(250, 204, 21, 0.1); color: var(--color-gold, #facc15);";
          dlBtn.onclick = () => this.manager.startDownload(desc.id, variant.id);
          btnContainer.appendChild(dlBtn);
        }

        variantRow.append(vInfo, btnContainer);
        variantsGrid.appendChild(variantRow);
      }

      item.appendChild(variantsGrid);
      this.listContainer.appendChild(item);
    }
  }

  private onKeyDown = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      this.close();
    }
  };

  private onBackdropClick = (e: MouseEvent): void => {
    if (e.target === this.element) {
      this.close();
    }
  };

  public open(): void {
    if (!this.element.parentElement) {
      document.body.appendChild(this.element);
      this.element.addEventListener("click", this.onBackdropClick);
      window.addEventListener("keydown", this.onKeyDown);
    }
    this.manager.requestCatalog();
    this.render();
  }

  public close(): void {
    this.element.removeEventListener("click", this.onBackdropClick);
    window.removeEventListener("keydown", this.onKeyDown);
    this.element.remove();
  }

  public dispose(): void {
    this.close();
    this.unsubCatalog?.();
    this.unsubJobs?.();
  }
}
