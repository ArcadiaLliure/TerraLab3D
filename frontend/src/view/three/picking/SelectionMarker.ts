/**
 * SelectionMarker — overlay HTML screen-space per indicar l'estrella seleccionada.
 *
 * - Anell + creu centrat a la projecció de l'estrella
 * - pointer-events: none
 * - Upright (no rota amb la càmera)
 * - Resize/DPR aware
 * - Hidden si l'estrella surt del viewport o el recurs és evicted
 */

const DEFAULT_MARKER_SIZE = 32; // CSS px
const MAXIMUM_MARKER_SIZE = 48; // CSS px
const MINIMUM_ZOOMED_MARKER_SIZE = 16; // CSS px
const FULL_SIZE_FOV_DEG = 1;
const EXTREME_ZOOM_FOV_DEG = 0.0001;
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
      width: ${DEFAULT_MARKER_SIZE}px;
      height: ${DEFAULT_MARKER_SIZE}px;
      pointer-events: none;
      z-index: 50;
      display: none;
      box-sizing: border-box;
      transition: width 80ms linear, height 80ms linear;
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
  update(
    x: number,
    y: number,
    visualRadiusCssPx = DEFAULT_MARKER_SIZE / 2,
    horizontalFovDeg = 60,
  ): void {
    if (!this.container) return;

    const size = selectionMarkerSizeCssPx(visualRadiusCssPx, horizontalFovDeg);

    this.element.style.width = `${size}px`;
    this.element.style.height = `${size}px`;
    this.element.style.left = `${x - size / 2}px`;
    this.element.style.top = `${y - size / 2}px`;

    if (!this.visible) {
      this.visible = true;
      this.element.style.display = "block";
      console.log(`MGP: [SelectionMarker] Marker visible at x=${x.toFixed(1)} y=${y.toFixed(1)} size=${size}px`);
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
    return `<svg width="100%" height="100%" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>
          @keyframes markerPulseRing {
            0% { transform: scale(0.65); opacity: 0.9; stroke-width: 2.5; }
            50% { transform: scale(1.15); opacity: 0.3; stroke-width: 1.0; }
            100% { transform: scale(0.65); opacity: 0.9; stroke-width: 2.5; }
          }
          @keyframes markerPulseInner {
            0% { transform: scale(0.9); opacity: 1.0; }
            50% { transform: scale(1.05); opacity: 0.7; }
            100% { transform: scale(0.9); opacity: 1.0; }
          }
          .pulse-ring {
            transform-origin: 20px 20px;
            animation: markerPulseRing 1.4s ease-in-out infinite;
          }
          .pulse-inner {
            transform-origin: 20px 20px;
            animation: markerPulseInner 1.4s ease-in-out infinite;
          }
        </style>
      </defs>
      <!-- Outer Pulsing Ring -->
      <circle class="pulse-ring" cx="20" cy="20" r="16" fill="none" stroke="${MARKER_COLOR}" />
      <!-- Inner Ring -->
      <circle class="pulse-inner" cx="20" cy="20" r="10" fill="none" stroke="${MARKER_COLOR}" stroke-width="1.8" />
      <!-- Center Dot -->
      <circle cx="20" cy="20" r="2.5" fill="${MARKER_COLOR}" />
    </svg>`;
  }
}

/**
 * Screen-space selection policy.
 *
 * At ordinary FOVs the reticle remains easy to find and may surround a small
 * apparent disc. Below 1 degree it progressively contracts on a logarithmic
 * scale, so telescope zoom never turns the overlay into a screen-sized ring.
 */
export function selectionMarkerSizeCssPx(
  visualRadiusCssPx: number,
  horizontalFovDeg: number,
): number {
  const finiteRadius = Number.isFinite(visualRadiusCssPx)
    ? Math.max(0, visualRadiusCssPx)
    : 0;
  const objectAwareSize = Math.min(
    MAXIMUM_MARKER_SIZE,
    Math.max(DEFAULT_MARKER_SIZE, finiteRadius * 2 + MARKER_PADDING),
  );

  const finiteFov = Number.isFinite(horizontalFovDeg)
    ? Math.max(EXTREME_ZOOM_FOV_DEG, horizontalFovDeg)
    : FULL_SIZE_FOV_DEG;
  const logRange = Math.log10(FULL_SIZE_FOV_DEG / EXTREME_ZOOM_FOV_DEG);
  const zoomProgress = Math.min(
    1,
    Math.max(
      0,
      Math.log10(finiteFov / EXTREME_ZOOM_FOV_DEG) / logRange,
    ),
  );
  const zoomCap = MINIMUM_ZOOMED_MARKER_SIZE
    + (MAXIMUM_MARKER_SIZE - MINIMUM_ZOOMED_MARKER_SIZE) * zoomProgress;
  return Math.min(objectAwareSize, zoomCap);
}
