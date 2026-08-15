import "./styles/Shell.css";
import "./styles/design_tokens.css";

const ICONS = {
  location: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-7-5.3-7-10.5a7 7 0 1 1 14 0C19 15.7 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.5"/></svg>`,
  sky: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  earth: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m8 3 4 8 5-5 5 15H2L8 3z"/><path d="M4.14 15.08 7 9.4l3 6"/></svg>`,
  tools: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
};

interface PageSpec {
  id: string;
  title: string;
  iconSvg: string;
  button: HTMLButtonElement;
  container: HTMLDivElement;
}

export interface ShellCallbacks {
  onSetRealtime?: (enabled: boolean) => void;
  onOpenResourceManager?: () => void;
}

export class Shell {
  private readonly root: HTMLElement;
  private readonly canvasContainer: HTMLElement;
  private readonly drawer: HTMLElement;
  private readonly drawerHeaderTitle: HTMLElement;
  private readonly drawerContent: HTMLElement;
  private readonly timeline: HTMLElement;
  private readonly btnToolbarRealtime: HTMLButtonElement;

  private isDrawerOpen = true;
  private activePageId = "location";
  private isRealtimeActive = true;
  private pages: Map<string, PageSpec> = new Map();
  private callbacks: ShellCallbacks;

  constructor(callbacks?: ShellCallbacks) {
    this.callbacks = callbacks || {};
    this.root = document.createElement("div");
    this.root.className = "shell-root";

    // ── 1. Topbar (Quick Toolbar) ──────────────────────────────────
    const topbar = document.createElement("div");
    topbar.className = "shell-topbar";
    
    const title = document.createElement("div");
    title.className = "shell-topbar-title";
    title.textContent = "TERRALAB";
    topbar.appendChild(title);
    
    // Quick Toolbar items
    const quickGroup = document.createElement("div");
    quickGroup.className = "shell-quick-toolbar";
    quickGroup.style.cssText = "display: flex; align-items: center; gap: 6px; margin-left: 10px;";

    this.btnToolbarRealtime = this.createQuickButton("Temps real", () => {
      if (this.callbacks.onSetRealtime) {
        this.callbacks.onSetRealtime(!this.isRealtimeActive);
      }
    });

    const btnSearch = this.createQuickButton("Cercar objecte", () => {
      this.selectPage("sky");
      this.openDrawer();
    });

    const btnLayers = this.createQuickButton("Gestionar capes", () => {
      if (this.callbacks.onOpenResourceManager) {
        this.callbacks.onOpenResourceManager();
      } else {
        this.selectPage("earth");
        this.openDrawer();
      }
    });

    const btnScope = this.createQuickButton("Tub / Telescopi", () => {
      this.selectPage("sky");
      this.openDrawer();
    });

    const btnTools = this.createQuickButton("Eines", () => {
      this.selectPage("tools");
      this.openDrawer();
    });

    quickGroup.appendChild(this.btnToolbarRealtime);
    quickGroup.appendChild(btnSearch);
    quickGroup.appendChild(btnLayers);
    quickGroup.appendChild(btnScope);
    quickGroup.appendChild(btnTools);
    topbar.appendChild(quickGroup);
    
    // ── 2. Viewport (Canvas + Drawer + Rail) ───────────────────────
    const viewport = document.createElement("div");
    viewport.className = "shell-viewport";

    this.canvasContainer = document.createElement("div");
    this.canvasContainer.className = "shell-canvas-container";

    this.drawer = document.createElement("div");
    this.drawer.className = "shell-drawer";
    
    const drawerHeader = document.createElement("div");
    drawerHeader.className = "drawer-header";
    this.drawerHeaderTitle = document.createElement("span");
    this.drawerHeaderTitle.textContent = "Ubicació";
    drawerHeader.appendChild(this.drawerHeaderTitle);
    this.drawer.appendChild(drawerHeader);

    this.drawerContent = document.createElement("div");
    this.drawerContent.className = "drawer-content";
    this.drawer.appendChild(this.drawerContent);

    const rail = document.createElement("div");
    rail.className = "shell-rail";

    // Page specs definition
    const specs = [
      { id: "location", title: "Ubicació", iconSvg: ICONS.location },
      { id: "sky", title: "Cel", iconSvg: ICONS.sky },
      { id: "earth", title: "Topografia", iconSvg: ICONS.earth },
      { id: "tools", title: "Eines", iconSvg: ICONS.tools },
    ];

    specs.forEach((spec, idx) => {
      const btn = this.createRailButton(spec.id, spec.title, spec.iconSvg, idx === 0);
      const pageContainer = document.createElement("div");
      pageContainer.className = `drawer-page-container drawer-page-${spec.id}`;
      pageContainer.style.display = idx === 0 ? "block" : "none";
      this.drawerContent.appendChild(pageContainer);

      btn.addEventListener("click", () => this.onRailButtonClick(spec.id));

      this.pages.set(spec.id, {
        id: spec.id,
        title: spec.title,
        iconSvg: spec.iconSvg,
        button: btn,
        container: pageContainer,
      });

      rail.appendChild(btn);
    });

    viewport.appendChild(this.canvasContainer);
    viewport.appendChild(this.drawer);
    viewport.appendChild(rail);

    // ── 3. Timeline ────────────────────────────────────────────────
    this.timeline = document.createElement("div");
    this.timeline.className = "shell-timeline";

    this.root.appendChild(topbar);
    this.root.appendChild(viewport);
    this.root.appendChild(this.timeline);

    this.updateRealtimeUI(true);
  }

  private createQuickButton(text: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = "quick-toolbar-button";
    btn.textContent = text;
    btn.style.cssText = `
      background: var(--button-bg);
      border: 1px solid var(--button-border);
      border-radius: var(--border-radius-sm);
      color: var(--button-text);
      font-size: 10px;
      font-weight: 600;
      padding: 3px 8px;
      cursor: pointer;
      transition: all 0.2s ease;
    `;
    btn.onmouseover = () => btn.style.background = "var(--button-hover)";
    btn.onmouseout = () => {
      if (btn !== this.btnToolbarRealtime || !this.isRealtimeActive) {
        btn.style.background = "var(--button-bg)";
      }
    };
    btn.onclick = onClick;
    return btn;
  }

  private createRailButton(id: string, title: string, iconSvg: string, active: boolean): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = "rail-button";
    btn.setAttribute("title", title);
    btn.setAttribute("aria-label", title);
    if (active) btn.classList.add("active");
    btn.innerHTML = iconSvg;
    return btn;
  }

  private onRailButtonClick(pageId: string) {
    if (this.activePageId === pageId) {
      this.toggleDrawer();
    } else {
      this.selectPage(pageId);
      if (!this.isDrawerOpen) {
        this.openDrawer();
      }
    }
  }

  public selectPage(pageId: string) {
    const spec = this.pages.get(pageId);
    if (!spec) return;

    this.activePageId = pageId;
    this.drawerHeaderTitle.textContent = spec.title;

    this.pages.forEach((p, id) => {
      if (id === pageId) {
        p.button.classList.add("active");
        p.container.style.display = "block";
      } else {
        p.button.classList.remove("active");
        p.container.style.display = "none";
      }
    });
  }

  public updateRealtimeUI(isRealtime: boolean): void {
    this.isRealtimeActive = isRealtime;
    if (isRealtime) {
      this.btnToolbarRealtime.style.background = "var(--button-checked-bg)";
      this.btnToolbarRealtime.style.color = "var(--button-checked-text)";
      this.btnToolbarRealtime.style.borderColor = "var(--button-checked-border)";
    } else {
      this.btnToolbarRealtime.style.background = "var(--button-bg)";
      this.btnToolbarRealtime.style.color = "var(--button-text)";
      this.btnToolbarRealtime.style.borderColor = "var(--button-border)";
    }
  }

  private toggleDrawer() {
    if (this.isDrawerOpen) {
      this.closeDrawer();
    } else {
      this.openDrawer();
    }
  }

  public openDrawer() {
    this.isDrawerOpen = true;
    this.drawer.classList.remove("collapsed");
  }

  public closeDrawer() {
    this.isDrawerOpen = false;
    this.drawer.classList.add("collapsed");
  }

  public getCanvasContainer(): HTMLElement {
    return this.canvasContainer;
  }

  public getPageContainer(pageId: string): HTMLElement | null {
    return this.pages.get(pageId)?.container || null;
  }

  public getTimelineContainer(): HTMLElement {
    return this.timeline;
  }

  public mount(parent: HTMLElement): void {
    parent.appendChild(this.root);
  }
}
