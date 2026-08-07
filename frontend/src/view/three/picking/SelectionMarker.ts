/**
 * SelectionMarker — overlay HTML screen-space per indicar l'estrella seleccionada.
 *
 * - Anell + creu centrat a la projecció de l'estrella
 * - pointer-events: none
 * - Upright (no rota amb la càmera)
 * - Resize/DPR aware
 * - Hidden si l'estrella surt del viewport o el recurs és evicted
 */

const MARKER_SIZE = 32; // px
const MARKER_COLOR = "#f1cd88"; // color gold de TerraLab3D

export class SelectionMarker {
  private readonly element: HTMLDivElement;
  private container: HTMLElement | null = null;
  private visible = false;

  constructor() {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      position: absolute;
      width: ${MARKER_SIZE}px;
      height: ${MARKER_SIZE}px;
      pointer-events: none;
      z-index: 50;
      display: none;
    `;
    this.element.innerHTML = this.createSvg();
  }

  mount(container: HTMLElement): void {
    this.container = container;
    container.appendChild(this.element);
  }

  /**
   * Actualitza la posició del marker en coordenades CSS relatives al container.
   */
  update(x: number, y: number): void {
    if (!this.container) return;

    const rect = this.container.getBoundingClientRect();
    const localX = x;
    const localY = y;

    // Centrar el marker
    this.element.style.left = `${localX - MARKER_SIZE / 2}px`;
    this.element.style.top = `${localY - MARKER_SIZE / 2}px`;

    if (!this.visible) {
      this.visible = true;
      this.element.style.display = "block";
    }
  }

  hide(): void {
    if (this.visible) {
      this.visible = false;
      this.element.style.display = "none";
    }
  }

  get isVisible(): boolean {
    return this.visible;
  }

  dispose(): void {
    this.element.remove();
    this.container = null;
  }

  private createSvg(): string {
    const r = MARKER_SIZE / 2;
    const baseR = r * 0.4;

    return `<svg width="${MARKER_SIZE}" height="${MARKER_SIZE}" viewBox="0 0 ${MARKER_SIZE} ${MARKER_SIZE}" xmlns="http://www.w3.org/2000/svg">
      <!-- Anell fix central -->
      <circle cx="${r}" cy="${r}" r="${baseR}"
        fill="none" stroke="${MARKER_COLOR}" stroke-width="1.5" opacity="0.9"/>
      
      <!-- Anell expansiu (pulse) mitjançant SVG natiu -->
      <circle cx="${r}" cy="${r}" r="${baseR}" fill="none" stroke="${MARKER_COLOR}">
        <animate attributeName="r" from="${baseR}" to="${r * 0.9}" dur="1.5s" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/>
        <animate attributeName="opacity" from="1" to="0" dur="1.5s" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/>
        <animate attributeName="stroke-width" from="2" to="0.5" dur="1.5s" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/>
      </circle>
    </svg>`;
  }
}
