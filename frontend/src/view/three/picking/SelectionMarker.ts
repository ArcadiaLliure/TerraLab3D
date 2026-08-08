/**
 * SelectionMarker — overlay HTML screen-space per indicar l'estrella seleccionada.
 *
 * - Anell + creu centrat a la projecció de l'estrella
 * - pointer-events: none
 * - Upright (no rota amb la càmera)
 * - Resize/DPR aware
 * - Hidden si l'estrella surt del viewport o el recurs és evicted
 */

const MINIMUM_MARKER_SIZE = 32; // CSS px
const MARKER_PADDING = 8; // CSS px outside the rendered object
const MARKER_COLOR = "#f1cd88"; // color gold de TerraLab3D

export class SelectionMarker {
  private readonly element: HTMLDivElement;
  private container: HTMLElement | null = null;
  private visible = false;

  constructor() {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      position: absolute;
      width: ${MINIMUM_MARKER_SIZE}px;
      height: ${MINIMUM_MARKER_SIZE}px;
      pointer-events: none;
      z-index: 50;
      display: none;
      box-sizing: border-box;
      border: 1.5px solid ${MARKER_COLOR};
      border-radius: 50%;
      box-shadow: 0 0 8px rgba(241, 205, 136, 0.75), inset 0 0 8px rgba(241, 205, 136, 0.2);
      transition: width 80ms linear, height 80ms linear;
    `;
  }

  mount(container: HTMLElement): void {
    this.container = container;
    container.appendChild(this.element);
  }

  /**
   * Actualitza la posició del marker en coordenades CSS relatives al container.
   */
  update(x: number, y: number, visualRadiusCssPx = MINIMUM_MARKER_SIZE / 2): void {
    if (!this.container) return;

    const size = Math.max(
      MINIMUM_MARKER_SIZE,
      visualRadiusCssPx * 2 + MARKER_PADDING,
    );

    // The ring follows the apparent disc radius. This makes a zoomed Moon
    // remain enclosed rather than leaving a fixed star-sized cursor behind.
    this.element.style.width = `${size}px`;
    this.element.style.height = `${size}px`;
    this.element.style.left = `${x - size / 2}px`;
    this.element.style.top = `${y - size / 2}px`;

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
    const r = MINIMUM_MARKER_SIZE / 2;
    const baseR = r * 0.4;

    return `<svg width="${MINIMUM_MARKER_SIZE}" height="${MINIMUM_MARKER_SIZE}" viewBox="0 0 ${MINIMUM_MARKER_SIZE} ${MINIMUM_MARKER_SIZE}" xmlns="http://www.w3.org/2000/svg">
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
