/**
 * PointerGestureRouter — separa click de drag sense acoblar CameraRig i StarPicker.
 *
 * Responsabilitats:
 * - Detectar tap (pointerdown→pointerup sense drag significant)
 * - Detectar hover (pointermove sense botó premut)
 * - Emetre callbacks sense importar CameraRig ni picking
 * - Coalescing de hover: màxim 1 per requestAnimationFrame
 *
 * PROHIBIT:
 * - CameraRig imports PointerGestureRouter
 * - PointerGestureRouter imports CameraRig o StarPicker
 * - Doble pointer capture
 *
 * NOTA: CameraRig ja gestiona pointerdown/pointermove/pointerup per orbit/drag.
 *       Aquest router observa els mateixos events sense capturar el pointer,
 *       i només emet tap/hover basant-se en la distància del gest.
 */

const LOG_PREFIX = "MGP: [PointerGestureRouter]";

export type TapCallback = (xCssPx: number, yCssPx: number) => void;
export type HoverCallback = (xCssPx: number, yCssPx: number) => void;
export type HoverClearCallback = () => void;

export interface PointerGestureRouterConfig {
  /** Llindar en CSS px per diferenciar click de drag. */
  clickDragThresholdCssPx: number;
}

const DEFAULT_CONFIG: PointerGestureRouterConfig = {
  clickDragThresholdCssPx: 15,
};

export class PointerGestureRouter {
  private config: PointerGestureRouterConfig;
  private container: HTMLElement | null = null;

  // ─── Tap detection ─────────────────────────────────────────────────
  private pointerDownX = 0;
  private pointerDownY = 0;
  private pointerDownButton = -1;
  private isPointerDown = false;

  // ─── Hover coalescing ──────────────────────────────────────────────
  private pendingHoverX = 0;
  private pendingHoverY = 0;
  private hasPendingHover = false;
  private hoverRafId = 0;

  // ─── Callbacks ─────────────────────────────────────────────────────
  private tapCallbacks: TapCallback[] = [];
  private hoverCallbacks: HoverCallback[] = [];
  private hoverClearCallbacks: HoverClearCallback[] = [];

  // ─── Bound handlers ────────────────────────────────────────────────
  private readonly onPointerDownBound: (e: PointerEvent) => void;
  private readonly onPointerMoveBound: (e: PointerEvent) => void;
  private readonly onPointerUpBound: (e: PointerEvent) => void;
  private readonly onPointerLeaveBound: (e: PointerEvent) => void;

  constructor(config: Partial<PointerGestureRouterConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.onPointerDownBound = this.onPointerDown.bind(this);
    this.onPointerMoveBound = this.onPointerMove.bind(this);
    this.onPointerUpBound = this.onPointerUp.bind(this);
    this.onPointerLeaveBound = this.onPointerLeave.bind(this);
  }

  onTap(cb: TapCallback): void {
    this.tapCallbacks.push(cb);
  }

  onHover(cb: HoverCallback): void {
    this.hoverCallbacks.push(cb);
  }

  onHoverClear(cb: HoverClearCallback): void {
    this.hoverClearCallbacks.push(cb);
  }

  attach(container: HTMLElement): void {
    this.container = container;
    // Observe in capture phase before CameraRig takes pointer capture. The
    // router still never prevents or stops the navigation gesture.
    container.addEventListener("pointerdown", this.onPointerDownBound, true);
    container.addEventListener("pointermove", this.onPointerMoveBound, true);
    container.addEventListener("pointerup", this.onPointerUpBound, true);
    container.addEventListener("pointerleave", this.onPointerLeaveBound, true);
  }

  detach(): void {
    if (!this.container) return;
    this.container.removeEventListener("pointerdown", this.onPointerDownBound, true);
    this.container.removeEventListener("pointermove", this.onPointerMoveBound, true);
    this.container.removeEventListener("pointerup", this.onPointerUpBound, true);
    this.container.removeEventListener("pointerleave", this.onPointerLeaveBound, true);
    this.container = null;
    this.cancelHoverRaf();
  }

  dispose(): void {
    this.detach();
    this.tapCallbacks = [];
    this.hoverCallbacks = [];
    this.hoverClearCallbacks = [];
  }

  // ─── Private handlers ──────────────────────────────────────────────

  private onPointerDown(e: PointerEvent): void {
    if (e.button !== 0) return; // Només botó esquerre
    this.isPointerDown = true;
    this.pointerDownX = e.clientX;
    this.pointerDownY = e.clientY;
    this.pointerDownButton = e.button;
  }

  private onPointerMove(e: PointerEvent): void {
    if (this.isPointerDown) {
      // Si estem en pointerdown, no emetem hover
      return;
    }

    // Coalescing: guardar última posició, processar al següent RAF
    this.pendingHoverX = e.clientX;
    this.pendingHoverY = e.clientY;
    if (!this.hasPendingHover) {
      this.hasPendingHover = true;
      this.hoverRafId = requestAnimationFrame(() => {
        this.hasPendingHover = false;
        for (const cb of this.hoverCallbacks) cb(this.pendingHoverX, this.pendingHoverY);
      });
    }
  }

  private onPointerUp(e: PointerEvent): void {
    if (!this.isPointerDown || this.pointerDownButton !== 0) {
      this.isPointerDown = false;
      return;
    }

    this.isPointerDown = false;

    // Verificar si és un tap (distància < threshold)
    const dx = e.clientX - this.pointerDownX;
    const dy = e.clientY - this.pointerDownY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance <= this.config.clickDragThresholdCssPx) {
      // És un tap
      for (const cb of this.tapCallbacks) cb(e.clientX, e.clientY);
    }
    // Si distance > threshold, era drag — CameraRig ja l'ha gestionat
  }

  private onPointerLeave(_e: PointerEvent): void {
    this.isPointerDown = false;
    this.cancelHoverRaf();
    for (const cb of this.hoverClearCallbacks) cb();
  }

  private cancelHoverRaf(): void {
    if (this.hasPendingHover) {
      cancelAnimationFrame(this.hoverRafId);
      this.hasPendingHover = false;
    }
  }
}
