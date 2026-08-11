import type { WebSocketBridge } from "../../../bridge/WebSocketBridge";
import type { AstronomicalSearchResultPayload } from "../../../contracts/bridge_messages";

export interface SearchWidgetOptions {
  onSelect: (result: AstronomicalSearchResultPayload) => void;
}

export class SearchWidget {
  private element: HTMLDivElement;
  private input: HTMLInputElement;
  private resultsContainer: HTMLDivElement;
  private loadingIndicator: HTMLDivElement;
  
  private currentRequestId = "";
  private currentGeneration = 0;
  private searchTimeout: ReturnType<typeof setTimeout> | null = null;
  private lastQuery = "";

  constructor(private bridge: WebSocketBridge, private options: SearchWidgetOptions) {
    this.element = document.createElement("div");
    this.element.className = "search-widget";
    this.element.style.cssText = `
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
    `;

    const searchBar = document.createElement("div");
    searchBar.style.cssText = `
      display: flex;
      align-items: center;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-md);
      padding: 4px 8px;
    `;

    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.placeholder = "Cercar objecte (ex: Lluna, M42)...";
    this.input.style.cssText = `
      flex: 1;
      background: transparent;
      border: none;
      color: var(--color-text-bright);
      outline: none;
      font-size: 11px;
    `;
    this.input.addEventListener("input", () => this.onInput());

    const searchIcon = document.createElement("div");
    searchIcon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`;
    searchIcon.style.color = "var(--color-text-muted)";
    
    searchBar.appendChild(searchIcon);
    searchBar.appendChild(this.input);
    
    this.loadingIndicator = document.createElement("div");
    this.loadingIndicator.style.cssText = "font-size: 10px; color: var(--color-text-muted); display: none; padding-left: 4px;";
    this.loadingIndicator.textContent = "Cercant...";
    
    this.resultsContainer = document.createElement("div");
    this.resultsContainer.style.cssText = `
      display: flex;
      flex-direction: column;
      gap: 2px;
      max-height: 200px;
      overflow-y: auto;
    `;

    this.element.appendChild(searchBar);
    this.element.appendChild(this.loadingIndicator);
    this.element.appendChild(this.resultsContainer);

    this.bridge.addMessageListener({
      onAstronomicalSearchResult: (msg) => {
        if (msg.requestId === this.currentRequestId && msg.generation === this.currentGeneration) {
          this.renderResults(msg.results);
        }
      }
    });
  }

  private onInput() {
    const query = this.input.value.trim();
    if (query === this.lastQuery) return;
    this.lastQuery = query;

    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    if (query.length === 0) {
      this.resultsContainer.innerHTML = "";
      this.loadingIndicator.style.display = "none";
      return;
    }

    this.searchTimeout = setTimeout(() => {
      this.loadingIndicator.style.display = "block";
      this.currentRequestId = `search-${Date.now()}`;
      this.currentGeneration++;
      this.bridge.requestAstronomicalSearch(this.currentRequestId, this.currentGeneration, query, 15);
    }, 300);
  }

  private renderResults(results: AstronomicalSearchResultPayload[]) {
    this.loadingIndicator.style.display = "none";
    this.resultsContainer.innerHTML = "";

    if (results.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "Cap resultat.";
      empty.style.cssText = "font-size: 10px; color: var(--color-text-muted); padding: 4px;";
      this.resultsContainer.appendChild(empty);
      return;
    }

    for (const res of results) {
      const item = document.createElement("div");
      item.style.cssText = `
        display: flex;
        flex-direction: column;
        padding: 6px;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--border-radius-sm);
        cursor: pointer;
        transition: background 0.1s ease;
      `;
      item.onmouseover = () => item.style.background = "var(--color-surface-hover)";
      item.onmouseout = () => item.style.background = "var(--color-surface)";
      item.onclick = () => {
        this.input.value = res.displayName;
        this.resultsContainer.innerHTML = "";
        this.options.onSelect(res);
      };

      const title = document.createElement("div");
      title.style.cssText = "font-weight: 600; font-size: 11px; color: var(--color-text-bright);";
      title.textContent = res.displayName;

      const details = document.createElement("div");
      details.style.cssText = "font-size: 9px; color: var(--color-text-muted); display: flex; justify-content: space-between;";
      
      let typeText = "Objecte";
      if (res.kind === "body") typeText = "Planeta / Satèl·lit";
      else if (res.kind === "star") typeText = "Estrella";
      else if (res.kind === "deep_sky") typeText = "Cel profund";
      else if (res.kind === "coordinate") typeText = "Coordenada";
      
      const typeSpan = document.createElement("span");
      typeSpan.textContent = typeText;
      
      const posSpan = document.createElement("span");
      if (res.coordinateSnapshot) {
        posSpan.textContent = `RA: ${res.coordinateSnapshot.raDeg.toFixed(1)}° Dec: ${res.coordinateSnapshot.decDeg.toFixed(1)}°`;
      }

      details.appendChild(typeSpan);
      details.appendChild(posSpan);

      item.appendChild(title);
      if (res.matchedAlias) {
        const aliasSpan = document.createElement("div");
        aliasSpan.style.cssText = "font-size: 9px; color: var(--color-text-dim); margin-top: 2px;";
        aliasSpan.textContent = `Alias: ${res.matchedAlias}`;
        item.appendChild(aliasSpan);
      }
      item.appendChild(details);

      this.resultsContainer.appendChild(item);
    }
  }

  public getElement(): HTMLDivElement {
    return this.element;
  }
}
