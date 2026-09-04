import { ResourceManager } from "../../../application/ResourceManager";
export interface ResourceBackedLayerOptions {
    label: string;
    resourceId: string;
    variantId?: string; // Tries to select this variant, defaults to first if undefined
    initialVisible?: boolean;
    onVisibilityChanged?: (visible: boolean) => void | Promise<void>;
}

export class ResourceBackedLayerRow {
    private element: HTMLDivElement;
    private checkbox: HTMLInputElement;
    private statusText: HTMLSpanElement;
    private actionBtn: HTMLButtonElement;
    private progressBarContainer: HTMLDivElement;
    private progressBarFill: HTMLDivElement;
    
    private resourceId: string;
    private variantId: string | undefined;
    private manager: ResourceManager;
    private unsubJobs?: () => void;
    private unsubCatalog?: () => void;
    private _isDestroyed = false;
    private _onVisibilityChanged: ((visible: boolean) => void | Promise<void>) | undefined;

    constructor(manager: ResourceManager, options: ResourceBackedLayerOptions) {
        this.manager = manager;
        this.resourceId = options.resourceId;
        this.variantId = options.variantId;
        this._onVisibilityChanged = options.onVisibilityChanged;

        this.element = document.createElement("div");
        this.element.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 10px;
            padding-left: 12px;
        `;

        const row = document.createElement("div");
        row.style.cssText = "display: flex; justify-content: space-between; align-items: center;";

        const labelContainer = document.createElement("label");
        labelContainer.style.cssText = "display: flex; align-items: center; gap: 4px; cursor: pointer;";
        
        this.checkbox = document.createElement("input");
        this.checkbox.type = "checkbox";
        this.checkbox.checked = options.initialVisible ?? false;
        this.checkbox.disabled = true; // Disabled until READY
        this.checkbox.onchange = () => void this.applyVisibility(this.checkbox.checked);
        
        labelContainer.append(this.checkbox, document.createTextNode(options.label));
        
        const controlsContainer = document.createElement("div");
        controlsContainer.style.cssText = "display: flex; align-items: center; gap: 6px;";

        this.statusText = document.createElement("span");
        this.statusText.style.cssText = "font-size: 9px; color: var(--color-text-muted);";
        this.statusText.textContent = "Desconegut";

        this.actionBtn = document.createElement("button");
        this.actionBtn.style.cssText = `
            padding: 2px 6px;
            font-size: 9px;
            border-radius: 3px;
            border: 1px solid var(--color-border);
            background: var(--color-surface);
            color: var(--color-gold);
            cursor: pointer;
            display: none;
        `;

        controlsContainer.append(this.statusText, this.actionBtn);
        row.append(labelContainer, controlsContainer);

        this.progressBarContainer = document.createElement("div");
        this.progressBarContainer.style.cssText = `
            width: 100%;
            height: 2px;
            background: var(--color-surface-dim);
            border-radius: 1px;
            overflow: hidden;
            display: none;
        `;
        this.progressBarFill = document.createElement("div");
        this.progressBarFill.style.cssText = `
            height: 100%;
            width: 0%;
            background: var(--color-gold);
            transition: width 0.2s ease-out;
        `;
        this.progressBarContainer.appendChild(this.progressBarFill);

        this.element.append(row, this.progressBarContainer);

        this.unsubCatalog = this.manager.subscribeCatalog(() => this.updateUI());
        this.unsubJobs = this.manager.subscribeJobs(() => this.updateUI());
        
        this.updateUI();
    }

    public getElement(): HTMLElement {
        return this.element;
    }
    
    public setCheckboxVisible(visible: boolean) {
        this.checkbox.checked = visible;
        void this.applyVisibility(visible);
    }

    public destroy(): void {
        this._isDestroyed = true;
        this.unsubJobs?.();
        this.unsubCatalog?.();
    }

    private updateUI(): void {
        if (this._isDestroyed) return;
        
        const descriptor = this.manager.getDescriptor(this.resourceId);
        if (!descriptor) {
            this.statusText.textContent = "Carregant catàleg...";
            return;
        }

        // Auto-select variant if none provided
        let targetVariantId = this.variantId || descriptor.variants.find(variant =>
            this.manager.getInstallState(this.resourceId, variant.id).status !== "NOT_INSTALLED"
        )?.id;
        if (!targetVariantId && descriptor.variants.length > 0) {
            targetVariantId = descriptor.variants[0]!.id;
        }
        const state = this.manager.getInstallState(this.resourceId, targetVariantId ?? "");

        if (state.status !== "READY" && this.checkbox.checked) {
            this.checkbox.checked = false;
            void this.applyVisibility(false);
        }

        if (state.status === "READY") {
            this.statusText.textContent = "";
            this.actionBtn.style.display = "none";
            this.progressBarContainer.style.display = "none";
            
            // Just became ready, maybe auto-enable?
            const wasDisabled = this.checkbox.disabled;
            this.checkbox.disabled = false;
            
            // If the user checked it while it was downloading (we don't allow it yet, but just in case)
            if (wasDisabled && this.checkbox.checked) {
                void this.applyVisibility(true);
            }
        } 
        else if (state.status === "NOT_INSTALLED" || state.status === "PARTIAL" || state.status === "ERROR") {
            this.checkbox.disabled = true;
            this.progressBarContainer.style.display = "none";
            
            if (state.status === "ERROR") {
                const msg = (state as any).errorMessage || "Error desconegut";
                this.statusText.textContent = `Error: ${msg}`;
                this.statusText.title = msg;
                console.error(`MGP: [ResourceLayer] Error de descàrrega per a ${this.resourceId}: ${msg}`);
                this.statusText.style.color = "var(--color-error, #ff5555)";
                this.actionBtn.textContent = "Reintentar";
            } else {
                this.statusText.textContent = "";
                this.statusText.title = "";
                this.statusText.style.color = "var(--color-text-muted)";
                this.actionBtn.textContent = "Baixar";
            }
            
            this.actionBtn.style.display = "block";
            this.actionBtn.onclick = () => {
                if (targetVariantId) {
                    this.manager.startDownload(this.resourceId, targetVariantId);
                }
            };
        }
        else if (state.status === "DOWNLOADING" || state.status === "PAUSED") {
            this.checkbox.disabled = true;
            this.actionBtn.style.display = "block";
            this.progressBarContainer.style.display = "block";
            
            if (state.status === "PAUSED") {
                this.statusText.textContent = "Pausat";
                this.actionBtn.textContent = "Reprendre";
                this.actionBtn.onclick = () => {
                    if (targetVariantId) {
                        this.manager.startDownload(this.resourceId, targetVariantId);
                    }
                };
            } else {
                // Determine progress
                const job = this.manager.getJobState(`${this.resourceId}_${targetVariantId}`);
                if (job && job.progress !== null) {
                    const percent = Math.floor(job.progress * 100);
                    this.statusText.textContent = `${percent}%`;
                    this.progressBarFill.style.width = `${percent}%`;
                } else {
                    this.statusText.textContent = "Baixant...";
                    this.progressBarFill.style.width = "0%";
                }
                
                this.actionBtn.textContent = "Pausar";
                this.actionBtn.onclick = () => {
                    if (targetVariantId) {
                        this.manager.pauseDownload(this.resourceId, targetVariantId);
                    }
                };
            }
        }
        else if (state.status === "VERIFYING" || state.status === "PROCESSING") {
            this.checkbox.disabled = true;
            this.statusText.textContent = state.status === "VERIFYING"
                ? "Verificant..."
                : "Processant...";
            this.actionBtn.style.display = "none";
            this.progressBarContainer.style.display = "block";
            this.progressBarFill.style.width = "100%";
            this.progressBarFill.style.background = "var(--color-success, #55ff55)";
        }
    }

    private async applyVisibility(visible: boolean): Promise<void> {
        if (!this._onVisibilityChanged) return;
        this.checkbox.disabled = true;
        try {
            await this._onVisibilityChanged(visible);
            this.statusText.style.color = "var(--color-text-muted)";
        } catch (error) {
            this.checkbox.checked = !visible;
            this.statusText.textContent = error instanceof Error ? error.message : "Error de capa";
            this.statusText.style.color = "var(--color-error, #ff5555)";
        } finally {
            const state = this.manager.getEffectiveInstallState(this.resourceId, this.variantId);
            this.checkbox.disabled = state.status !== "READY";
        }
    }
}
