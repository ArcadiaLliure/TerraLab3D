import { ResourceManager } from "../../../application/ResourceManager";
import type { ResourceDescriptor } from "../../../contracts/resource_manager_contracts";

export class ResourceManagerModal {
    private element: HTMLDivElement;
    private contentBox: HTMLDivElement;
    private listContainer: HTMLDivElement;
    
    private unsubCatalog?: () => void;
    private unsubJobs?: () => void;
    
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

        this.listContainer = document.createElement("div");
        this.listContainer.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        `;

        this.contentBox.append(header, this.listContainer);
        this.element.appendChild(this.contentBox);

        this.unsubCatalog = this.manager.subscribeCatalog(() => this.renderList());
        this.unsubJobs = this.manager.subscribeJobs(() => this.renderList());
        
        this.renderList();
    }

    private formatBytes(bytes: number | null | undefined): string {
        if (!bytes) return "Mida desconeguda";
        const mb = bytes / (1024 * 1024);
        if (mb > 1024) return `${(mb / 1024).toFixed(2)} GB`;
        return `${mb.toFixed(1)} MB`;
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

        for (const desc of descriptors) {
            const item = document.createElement("div");
            item.style.cssText = `
                border: 1px solid var(--color-border, #333);
                border-radius: 6px;
                padding: 12px;
                background: var(--color-surface-raised, #222);
            `;

            const topRow = document.createElement("div");
            topRow.style.cssText = "display: flex; justify-content: space-between; margin-bottom: 8px;";
            
            const titleBox = document.createElement("div");
            const title = document.createElement("div");
            title.textContent = desc.title;
            title.style.cssText = "font-weight: 500; font-size: 14px; color: var(--color-gold, #facc15);";
            
            const provider = document.createElement("div");
            provider.textContent = `${desc.provider} · ${desc.acquisitionKind}`;
            provider.style.cssText = "font-size: 11px; color: var(--color-text-muted, #888); margin-top: 2px;";
            
            titleBox.append(title, provider);

            const state = this.manager.getInstallState(desc.id);
            const statusBadge = document.createElement("div");
            statusBadge.style.cssText = `
                font-size: 10px; padding: 2px 6px; border-radius: 4px;
                background: var(--color-surface-dim, #111);
                color: var(--color-text-muted, #888);
                border: 1px solid var(--color-border, #333);
                align-self: flex-start;
            `;
            statusBadge.textContent = state.status;
            if (state.status === "READY") {
                statusBadge.style.color = "#4ade80";
                statusBadge.style.borderColor = "#4ade80";
            } else if (state.status === "DOWNLOADING") {
                statusBadge.style.color = "var(--color-gold, #facc15)";
                statusBadge.style.borderColor = "var(--color-gold, #facc15)";
            } else if (state.status === "ERROR") {
                statusBadge.style.color = "#ff8a80";
                statusBadge.style.borderColor = "#ff8a80";
            }

            topRow.append(titleBox, statusBadge);
            item.appendChild(topRow);

            if (desc.sourcePageUrl || desc.credits.length > 0) {
                const credits = document.createElement("div");
                credits.style.cssText = "font-size: 10px; color: var(--color-text-dim, #aaa); margin-bottom: 12px;";
                credits.textContent = `Crèdits: ${desc.credits.join(", ")}`;
                item.appendChild(credits);
            }

            const variantsGrid = document.createElement("div");
            variantsGrid.style.cssText = "display: flex; flex-direction: column; gap: 8px;";
            
            for (const variant of desc.variants) {
                const variantRow = document.createElement("div");
                variantRow.style.cssText = `
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
                const isThisVariantReady = state.status === "READY" && state.variantId === variant.id;
                const isDownloadingThis = (state.status === "DOWNLOADING" || state.status === "PAUSED") && state.variantId === variant.id;
                
                if (isThisVariantReady) {
                    const readyText = document.createElement("span");
                    readyText.textContent = "Instal·lat";
                    readyText.style.cssText = "font-size: 11px; color: #4ade80;";
                    
                    const deleteBtn = document.createElement("button");
                    deleteBtn.textContent = "Eliminar";
                    deleteBtn.style.cssText = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: transparent; color: #ff8a80; margin-left: 8px;";
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
                    state.variantId === variant.id
                    && (state.status === "VERIFYING" || state.status === "PROCESSING")
                ) {
                    const working = document.createElement("span");
                    working.textContent = state.status === "VERIFYING" ? "Verificant…" : "Processant…";
                    working.style.cssText = "font-size: 11px; color: var(--color-gold, #facc15);";
                    btnContainer.appendChild(working);
                } else {
                    const dlBtn = document.createElement("button");
                    dlBtn.textContent = "Baixar";
                    dlBtn.style.cssText = "padding: 4px 12px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-text-bright);";
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
