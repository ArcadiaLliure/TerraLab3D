import { ResourceManager } from "../../../application/ResourceManager";
import type { ResourceDescriptor } from "../../../contracts/resource_manager_contracts";

export class ResourceManagerModal {
    private element: HTMLDivElement;
    private contentBox: HTMLDivElement;
    private tabsContainer: HTMLDivElement;
    private listContainer: HTMLDivElement;
    
    private unsubCatalog?: () => void;
    private unsubJobs?: () => void;
    
    private activeDomain: "sky" | "earth" = "sky";
    private activeCategorySky: string = "solar_system";
    private activeCategoryEarth: string = "elevation";
    
    constructor(private manager: ResourceManager) {
        this.element = document.createElement("div");
        this.element.style.cssText = `
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            font-family: var(--font-family-sans, sans-serif);
        `;

        this.contentBox = document.createElement("div");
        this.contentBox.style.cssText = `
            width: 700px;
            max-width: 90vw;
            max-height: 85vh;
            background: var(--color-surface, #1a1a1a);
            border: 1px solid var(--color-border, #333);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            overflow: hidden;
        `;
        
        const header = document.createElement("div");
        header.style.cssText = `
            padding: 16px 20px;
            border-bottom: 1px solid var(--color-border, #333);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--color-surface-raised, #222);
        `;
        
        const title = document.createElement("h2");
        title.textContent = "Gestor de Recursos i Capes";
        title.style.cssText = "margin: 0; font-size: 16px; color: var(--color-text-bright, #fff); font-weight: 500;";
        
        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "&times;";
        closeBtn.style.cssText = `
            background: none; border: none; color: var(--color-text-muted, #888);
            font-size: 24px; cursor: pointer; padding: 0; line-height: 1;
        `;
        closeBtn.onclick = () => this.close();
        
        header.append(title, closeBtn);

        this.tabsContainer = document.createElement("div");
        this.tabsContainer.style.cssText = `
            display: flex;
            flex-direction: column;
            background: var(--color-surface, #1a1a1a);
            border-bottom: 1px solid var(--color-border, #333);
        `;

        this.listContainer = document.createElement("div");
        this.listContainer.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        `;

        this.contentBox.append(header, this.tabsContainer, this.listContainer);
        this.element.appendChild(this.contentBox);

        this.unsubCatalog = this.manager.subscribeCatalog(() => {
            this.renderTabs();
            this.renderList();
        });
        this.unsubJobs = this.manager.subscribeJobs(() => this.renderList());
        
        this.renderTabs();
        
        this.renderList();
    }

    private formatBytes(bytes: number | null | undefined): string {
        if (!bytes) return "Mida desconeguda";
        const mb = bytes / (1024 * 1024);
        if (mb > 1024) return `${(mb / 1024).toFixed(2)} GB`;
        return `${mb.toFixed(1)} MB`;
    }

    private renderTabs(): void {
        this.tabsContainer.innerHTML = "";
        
        // 1. Pestanyes de Domini (Cel / Terra)
        const domainBar = document.createElement("div");
        domainBar.style.cssText = "display: flex; border-bottom: 1px solid var(--color-border, #333);";
        
        const domains = [
            { id: "sky", label: "CEL" },
            { id: "earth", label: "TERRA" }
        ];
        
        for (const dom of domains) {
            const btn = document.createElement("button");
            btn.textContent = dom.label;
            const isActive = this.activeDomain === dom.id;
            btn.style.cssText = `
                flex: 1; padding: 12px 16px; font-size: 13px; font-weight: 500;
                background: ${isActive ? "var(--color-surface-raised, #222)" : "transparent"};
                color: ${isActive ? "var(--color-gold, #facc15)" : "var(--color-text-muted, #888)"};
                border: none;
                border-bottom: 2px solid ${isActive ? "var(--color-gold, #facc15)" : "transparent"};
                cursor: pointer; transition: all 0.2s; outline: none;
            `;
            btn.onclick = () => {
                this.activeDomain = dom.id as "sky" | "earth";
                this.renderTabs();
                this.renderList();
            };
            domainBar.appendChild(btn);
        }
        
        // 2. Subpestanyes de Categoria
        const categoryBar = document.createElement("div");
        categoryBar.style.cssText = "display: flex; background: var(--color-surface-raised, #222); padding: 0 16px;";
        
        let categories: {id: string, label: string}[] = [];
        let activeCat = "";
        
        if (this.activeDomain === "sky") {
            categories = [
                { id: "solar_system", label: "Sistema Solar" },
                { id: "deep_sky", label: "Espai Profund" }
            ];
            activeCat = this.activeCategorySky;
        } else {
            categories = [
                { id: "elevation", label: "Elevació" },
                { id: "land_cover", label: "Raster categòric" },
                { id: "light_pollution", label: "Contaminació lluminosa" }
            ];
            activeCat = this.activeCategoryEarth;
        }
        
        for (const cat of categories) {
            const btn = document.createElement("button");
            btn.textContent = cat.label;
            const isActive = activeCat === cat.id;
            btn.style.cssText = `
                padding: 10px 16px; font-size: 12px;
                background: transparent;
                color: ${isActive ? "var(--color-text-bright, #fff)" : "var(--color-text-dim, #aaa)"};
                border: none;
                border-bottom: 2px solid ${isActive ? "var(--color-text-bright, #fff)" : "transparent"};
                cursor: pointer; transition: all 0.2s; outline: none; margin-right: 8px;
            `;
            btn.onclick = () => {
                if (this.activeDomain === "sky") this.activeCategorySky = cat.id;
                else this.activeCategoryEarth = cat.id;
                this.renderTabs();
                this.renderList();
            };
            categoryBar.appendChild(btn);
        }
        
        this.tabsContainer.append(domainBar, categoryBar);
    }

    private renderList(): void {
        this.listContainer.innerHTML = "";
        
        const descriptors = this.manager.getAllDescriptors();
        if (descriptors.length === 0) {
            const empty = document.createElement("div");
            empty.textContent = "Carregant catàleg...";
            empty.style.cssText = "color: var(--color-text-muted); text-align: center; padding: 40px;";
            this.listContainer.appendChild(empty);
            return;
        }

        const activeCat = this.activeDomain === "sky" ? this.activeCategorySky : this.activeCategoryEarth;
        const filtered = descriptors.filter(d => d.domain === this.activeDomain && d.category === activeCat);

        if (filtered.length === 0) {
            const empty = document.createElement("div");
            empty.textContent = "No hi ha recursos en aquesta categoria.";
            empty.style.cssText = "color: var(--color-text-dim); text-align: center; padding: 40px; font-size: 13px;";
            this.listContainer.appendChild(empty);
            return;
        }

        for (const desc of filtered) {
            const item = document.createElement("div");
            item.style.cssText = `
                border: 1px solid var(--color-border, #333);
                border-radius: 6px;
                padding: 12px;
                background: var(--color-surface-raised, #222);
                margin-bottom: 16px;
            `;

            const topRow = document.createElement("div");
            topRow.style.cssText = "display: flex; justify-content: space-between; margin-bottom: 8px;";
            
            const titleBox = document.createElement("div");
            const title = document.createElement("div");
            title.textContent = desc.name;
            title.style.cssText = "font-weight: 500; font-size: 14px; color: var(--color-text-bright, #fff);";
            
            const provider = document.createElement("div");
            provider.textContent = `${desc.provider} · Categoria: ${desc.category}`;
            provider.style.cssText = "font-size: 11px; color: var(--color-text-muted, #888); margin-top: 2px;";
            
            titleBox.append(title, provider);

            const variantStates = desc.variants.map(v => this.manager.getInstallState(desc.id, v.id));
            let globalStatus = "NOT_INSTALLED";
            if (variantStates.some(s => s.status === "DOWNLOADING")) globalStatus = "DOWNLOADING";
            else if (variantStates.some(s => s.status === "ERROR")) globalStatus = "ERROR";
            else if (variantStates.some(s => s.status === "READY")) globalStatus = "READY";
            
            const statusBadge = document.createElement("div");
            statusBadge.style.cssText = `
                font-size: 10px; padding: 2px 6px; border-radius: 4px;
                background: var(--color-surface-dim, #111);
                color: var(--color-text-muted, #888);
                border: 1px solid var(--color-border, #333);
                align-self: flex-start;
            `;
            statusBadge.textContent = globalStatus;
            if (globalStatus === "READY") {
                statusBadge.style.color = "#4ade80";
                statusBadge.style.borderColor = "#4ade80";
            } else if (globalStatus === "DOWNLOADING") {
                statusBadge.style.color = "var(--color-gold, #facc15)";
                statusBadge.style.borderColor = "var(--color-gold, #facc15)";
            } else if (globalStatus === "ERROR") {
                statusBadge.style.color = "#ff8a80";
                statusBadge.style.borderColor = "#ff8a80";
            }

            topRow.append(titleBox, statusBadge);
            item.appendChild(topRow);

            const infoBox = document.createElement("div");
            infoBox.style.cssText = "margin-bottom: 12px; font-size: 11px; color: var(--color-text-dim, #aaa); border-left: 2px solid var(--color-border); padding-left: 12px;";
            
            const infoTitle = document.createElement("div");
            infoTitle.textContent = "Informació, Citació i Llicència";
            infoTitle.style.cssText = "color: var(--color-text-muted); font-weight: 500; margin-bottom: 6px;";
            infoBox.appendChild(infoTitle);
            
            if (desc.description) {
                const descDiv = document.createElement("div");
                descDiv.style.marginBottom = "4px";
                descDiv.textContent = desc.description;
                infoBox.appendChild(descDiv);
            }
            if (desc.license) {
                const licDiv = document.createElement("div");
                licDiv.style.marginBottom = "4px";
                licDiv.innerHTML = `<strong>Llicència:</strong> ${desc.license}`;
                infoBox.appendChild(licDiv);
            }
            if (desc.citation) {
                const citDiv = document.createElement("div");
                citDiv.style.marginBottom = "4px";
                citDiv.innerHTML = `<strong>Citació:</strong> ${desc.citation}`;
                infoBox.appendChild(citDiv);
            }
            if (desc.credits && desc.credits.length > 0) {
                const creditsDiv = document.createElement("div");
                creditsDiv.style.marginBottom = "4px";
                creditsDiv.textContent = `Crèdits addicionals: ${desc.credits.join(", ")}`;
                infoBox.appendChild(creditsDiv);
            }
            item.appendChild(infoBox);

            const variantsGrid = document.createElement("div");
            variantsGrid.style.cssText = "display: flex; flex-direction: column; gap: 8px;";
            
            for (const variant of desc.variants) {
                const variantRow = document.createElement("div");
                variantRow.style.cssText = `
                    position: relative; overflow: hidden;
                    display: flex; justify-content: space-between; align-items: center;
                    background: var(--color-surface, #1a1a1a);
                    padding: 8px; border-radius: 4px;
                    border: 1px solid var(--color-border, #333);
                `;

                const vInfo = document.createElement("div");
                vInfo.style.cssText = "display: flex; flex-direction: column; font-size: 11px;";
                
                const vTitle = document.createElement("span");
                vTitle.textContent = variant.title;
                vTitle.style.color = "var(--color-text-bright, #fff)";
                
                const vSize = document.createElement("span");
                const details = [
                    variant.format?.toUpperCase(),
                    variant.width && variant.height ? `${variant.width} × ${variant.height}` : null,
                    variant.publishedSizeLabel || this.formatBytes(variant.expectedBytes),
                ].filter((value): value is string => Boolean(value));
                vSize.textContent = details.join(" · ");
                vSize.style.color = "var(--color-text-muted, #888)";
                vSize.style.fontSize = "10px";
                
                vInfo.append(vTitle, vSize);
                
                const btnContainer = document.createElement("div");
                btnContainer.style.cssText = "display: flex; align-items: center; gap: 8px;";
                
                // Variant logic
                const variantState = this.manager.getInstallState(desc.id, variant.id);
                const isThisVariantReady = variantState.status === "READY";
                const isDownloadingThis = variantState.status === "DOWNLOADING" || variantState.status === "PAUSED";
                
                if (isThisVariantReady) {
                    const readyText = document.createElement("span");
                    readyText.textContent = "Instal·lat";
                    readyText.style.cssText = "font-size: 11px; color: #4ade80;";
                    
                    const deleteBtn = document.createElement("button");
                    deleteBtn.textContent = "Eliminar";
                    deleteBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: transparent; color: #ff8a80; margin-left: 8px;";
                    deleteBtn.onpointerdown = () => {
                        if (confirm(`Estàs segur que vols eliminar ${desc.name} (${variant.title})?`)) {
                            this.manager.deleteResource(desc.id, variant.id);
                        }
                    };
                    
                    btnContainer.append(readyText, deleteBtn);
                } else if (isDownloadingThis) {
                    const job = this.manager.getJobState(`${desc.id}_${variant.id}`);
                    if (job) {
                        const hasProgress = job.progress !== null;
                        const progressValue = hasProgress ? job.progress! : 1.0;
                        
                        const pct = document.createElement("span");
                        pct.textContent = hasProgress ? `${Math.floor(job.progress! * 100)}%` : this.formatBytes(job.downloadedBytes);
                        pct.style.cssText = "font-size: 11px; color: var(--color-gold, #facc15); width: 60px; text-align: right; white-space: nowrap;";
                        btnContainer.appendChild(pct);
                        
                        const progressBar = document.createElement("div");
                        if (hasProgress) {
                            progressBar.style.cssText = `
                                position: absolute; bottom: 0; left: 0; height: 3px;
                                background: var(--color-gold, #facc15);
                                width: ${progressValue * 100}%;
                                transition: width 0.2s ease-out;
                            `;
                        } else {
                            progressBar.style.cssText = `
                                position: absolute; bottom: 0; left: 0; height: 3px;
                                background: var(--color-gold, #facc15);
                                width: 100%;
                                animation: pulse-opacity 1.5s infinite;
                            `;
                            // Afegim una animació al document si no existeix
                            if (!document.getElementById("pulse-opacity-style")) {
                                const style = document.createElement("style");
                                style.id = "pulse-opacity-style";
                                style.textContent = `@keyframes pulse-opacity { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }`;
                                document.head.appendChild(style);
                            }
                        }
                        variantRow.appendChild(progressBar);
                    }
                    
                    const actionBtn = document.createElement("button");
                    actionBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-gold);";
                    if (variantState.status === "PAUSED") {
                        actionBtn.textContent = "Reprendre";
                        actionBtn.onpointerdown = () => this.manager.startDownload(desc.id, variant.id);
                    } else {
                        actionBtn.textContent = "Pausar";
                        actionBtn.onpointerdown = () => this.manager.pauseDownload(desc.id, variant.id);
                    }
                    
                    const cancelBtn = document.createElement("button");
                    cancelBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid #ff8a80; background: transparent; color: #ff8a80;";
                    cancelBtn.textContent = "Cancel·lar";
                    cancelBtn.onpointerdown = () => this.manager.cancelDownload(desc.id, variant.id);
                    
                    btnContainer.append(actionBtn, cancelBtn);
                } else if (
                    variantState.status === "VERIFYING" || variantState.status === "PROCESSING"
                ) {
                    const working = document.createElement("span");
                    working.textContent = variantState.status === "VERIFYING" ? "Verificant…" : "Processant…";
                    working.style.cssText = "font-size: 11px; color: var(--color-gold, #facc15);";
                    btnContainer.appendChild(working);
                } else {
                    const autoDownloadSupported = desc.acquisitionKind !== "EXTERNAL_FILE" &&
                        (!(desc.acquisitionKind === "HTTP_BUNDLE" || desc.acquisitionKind === "STATIC_FILE") || !!variant.sourceUrl || (variant.sourceUrls && variant.sourceUrls.length > 0));
                    if (autoDownloadSupported) {
                        const dlBtn = document.createElement("button");
                        dlBtn.textContent = "Descàrrega automàtica";
                        dlBtn.style.cssText = "padding: 4px 12px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-text-bright); margin-right: 8px;";
                        dlBtn.onpointerdown = () => this.manager.startDownload(desc.id, variant.id);
                        btnContainer.appendChild(dlBtn);
                    }
                    if (desc.originalSourceUrl || desc.directUrl) {
                        const sourceBtn = document.createElement("a");
                        sourceBtn.textContent = "Font original";
                        sourceBtn.href = desc.originalSourceUrl || desc.directUrl || "#";
                        sourceBtn.target = "_blank";
                        sourceBtn.style.cssText = "padding: 4px 12px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: transparent; color: var(--color-gold); text-decoration: none; display: inline-block;";
                        btnContainer.appendChild(sourceBtn);
                    }
                }

                variantRow.append(vInfo, btnContainer);
                variantsGrid.appendChild(variantRow);
            }
            
            item.appendChild(variantsGrid);
            this.listContainer.appendChild(item);
        }
    }

    public open(): void {
        document.body.appendChild(this.element);
        this.manager.requestCatalog();
    }

    public close(): void {
        this.element.remove();
    }

    public dispose(): void {
        this.element.remove();
        this.unsubCatalog?.();
        this.unsubJobs?.();
    }
}
