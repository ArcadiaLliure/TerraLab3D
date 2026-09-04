/**
 * ScenePickingController — orquestrador de picking a l'escena.
 *
 * Responsabilitats:
 * - Connecta PointerGestureRouter amb StarPickProvider
 * - Gestiona hover (debounce, coalescing)
 * - Gestiona selecció (click → resolve backend)
 * - Selection marker reproyectat cada frame
 * - Latest-wins per purpose (hover / select)
 * - Escape neteja selecció
 * - Layer visibility check
 * - Lifecycle complet (start/stop/dispose idempotents)
 */

import type { StarPickRef, ResolvedStar, StarPickResolvedMessage } from "../../../contracts/star_picking_contracts";
import { PointerGestureRouter } from "./PointerGestureRouter";
import { CelestialPickProvider, type CelestialPickHit } from "./CelestialPickProvider";
import { SelectionMarker } from "./SelectionMarker";
import type { SolarSystemPickHit } from "./SolarSystemPickProvider";
import type { DeepSkyPickHit } from "../../../contracts/deep_sky_picking_contracts";
import { setThreeFromAzimuthAltitude } from "../celestialCoordinates";
import type { CelestialSelectionController } from "../../../application/CelestialSelectionController";
import { fromPickHit } from "../../../application/CelestialSelectionController";
import * as THREE from "three";

const LOG_PREFIX = "MGP: [ScenePickingController]";

export type ResolveCallback = (
  requestId: string,
  generation: number,
  resourceId: string,
  resourceVersion: string,
  catalogIndex: number,
  purpose: "select" | "hover",
) => void;

export type SelectedCelestial = ResolvedStar | SolarSystemPickHit | DeepSkyPickHit;
export type SelectionChangedCallback = (selection: SelectedCelestial | null) => void;

export interface ScenePickingControllerDeps {
  gestureRouter: PointerGestureRouter;
  pickProvider: CelestialPickProvider;
  selectionController: CelestialSelectionController;
  resolveCallback: ResolveCallback;
}

const HOVER_DEBOUNCE_MS = 150;

export class ScenePickingController {
  private readonly deps: ScenePickingControllerDeps;
  private readonly selectionMarker: SelectionMarker;

  // ─── Selection state (local tracking for hits) ───────────────
  private selectedHit: CelestialPickHit | null = null;
  private selectedRef: StarPickRef | null = null;
  private unsubscribeSelection: (() => void) | null = null;

  // ─── Hover state ───────────────────────────────────────────────────
  private hoverHit: CelestialPickHit | null = null;
  private hoverRef: StarPickRef | null = null;
  private hoverDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  // ─── Generations (latest-wins) ─────────────────────────────────────
  private selectGeneration = 0;
  private hoverGeneration = 0;

  // ─── Request ID counter ────────────────────────────────────────────
  private requestIdCounter = 0;

  // ─── Lifecycle ─────────────────────────────────────────────────────
  private started = false;
  private disposed = false;

  // ─── Escape handler ────────────────────────────────────────────────
  private readonly onKeyDownBound: (e: KeyboardEvent) => void;

  constructor(deps: ScenePickingControllerDeps) {
    this.deps = deps;
    this.selectionMarker = new SelectionMarker();

    // Wire gesture router
    deps.gestureRouter.onTap((x, y) => this.handleTap(x, y));
    deps.gestureRouter.onHover((x, y) => this.handleHover(x, y));
    deps.gestureRouter.onHoverClear(() => this.clearHover());

    this.unsubscribeSelection = deps.selectionController.subscribe((state) => {
      if (!state.selectedTarget) {
        this.selectedHit = null;
        this.selectedRef = null;
        this.selectionMarker.hide();
      } else if (state.source !== "pick" && state.availability !== "unavailable") {
        // We only clear our internal *hit* cache if the source isn't pick.
        // We keep selectedHit if it was just picked so we can project it.
        // If it was searched, updateMarker will fall back to trackingResolver.
        if (state.source === "search") {
           this.selectedHit = null;
           this.selectedRef = null;
        }
      }
    });

    // Escape handler
    this.onKeyDownBound = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.clearSelection();
        this.clearHover();
      }
    };
  }

  /** Munta el marker al container del canvas. */
  private container: HTMLElement | null = null;
  mount(container: HTMLElement): void {
    this.container = container;
    this.selectionMarker.mount(container);
    window.addEventListener("keydown", this.onKeyDownBound);
    this.started = true;
  }

  // Removed externalTarget and setExternalTarget

  /**
   * Reproyecta el marker de selecció. Cridar des del render loop.
   */
  updateMarker(camera?: THREE.Camera, trackingResolver?: any): void {
    if (!this.started) {
      return;
    }

    if (this.selectedHit) {
      const pos = this.deps.pickProvider.reproject(this.selectedHit);
      if (pos) {
        this.selectionMarker.update(
          pos.x,
          pos.y,
          pos.visualRadiusCssPx,
          horizontalFovDeg(camera),
        );
        return;
      }
    }

    const state = this.deps.selectionController.getState();
    if (state.selectedTarget && state.availability !== "unavailable" && trackingResolver && camera) {
      const resolved = trackingResolver.resolve(state.selectedTarget);
      if (resolved) {
        const pos = this.projectDirectionToScreen(resolved.azimuthDeg, resolved.altitudeDeg, camera);
        if (pos) {
          this.selectionMarker.update(pos.x, pos.y, 16, horizontalFovDeg(camera));
          return;
        }
      }
    }

    this.selectionMarker.hide();
  }

  private projectDirectionToScreen(azimuthDeg: number, altitudeDeg: number, camera: THREE.Camera): { x: number; y: number } | null {
    const vec = setThreeFromAzimuthAltitude(
      new THREE.Vector3(),
      azimuthDeg,
      altitudeDeg,
      1000000,
    ).add(camera.position);

    vec.project(camera);
    if (vec.z > 1.0) return null;

    const rect = this.container ? this.container.getBoundingClientRect() : null;
    const width = rect ? rect.width : window.innerWidth;
    const height = rect ? rect.height : window.innerHeight;
    const x = (vec.x * 0.5 + 0.5) * width;
    const y = (-vec.y * 0.5 + 0.5) * height;

    return { x, y };
  }

  /**
   * Processa una resposta resolve del backend.
   */
  handleResolveResponse(msg: StarPickResolvedMessage): void {
    if (this.disposed) return;

    const purpose = msg.requestId.startsWith("sel:") ? "select" : "hover";
    const expectedGen = purpose === "select"
      ? this.selectGeneration
      : this.hoverGeneration;

    // Latest-wins: descartar stale
    if (msg.generation < expectedGen) {
      return;
    }

    if (msg.status !== "ok" || !msg.star) {
      if (msg.status === "stale" || msg.status === "missing") {
        console.debug(`${LOG_PREFIX} [handleResolveResponse] [${purpose} ${msg.status}]`);
      }
      if (msg.status === "invalid") {
        console.error(`${LOG_PREFIX} [handleResolveResponse] [${purpose} invalid: requestId=${msg.requestId}]`);
      }
      return;
    }

    if (purpose === "select") {
      if (
        this.selectedHit?.kind !== "star"
        || this.selectedRef === null
        || this.selectedRef.resourceId !== msg.star.resourceId
        || this.selectedRef.resourceVersion !== msg.star.resourceVersion
        || this.selectedRef.catalogIndex !== msg.star.catalogIndex
      ) return;
      this.deps.selectionController.updateStarTargetWithSourceId(
         msg.star.resourceId,
         msg.star.catalogIndex,
         msg.star.sourceId
      );
      console.debug(
        `${LOG_PREFIX} [handleResolveResponse] [Select resolved: sourceId=${msg.star.sourceId} RA=${msg.star.raDeg.toFixed(4)} Dec=${msg.star.decDeg.toFixed(4)} G=${msg.star.magnitude.toFixed(2)}]`,
      );
    }
    // Hover resolves es podrien usar per tooltip — per ara no fem res extra
  }

  /** Retorna l'estrella resolta seleccionada. (Obsolet, usar SelectionController) */
  getResolvedSelection(): ResolvedStar | null {
    return null;
  }

  /** Retorna el hit local de la selecció. */
  getSelectedHit(): CelestialPickHit | null {
    return this.selectedHit;
  }

  /** Retorna el hit local del hover. */
  getHoverHit(): CelestialPickHit | null {
    return this.hoverHit;
  }

  /** Neteja la selecció. */
  clearSelection(): void {
    this.deps.selectionController.clearSelection();
  }

  /**
   * Notifica que un recurs ha estat evicted o reemplaçat.
   * Si la selecció referencia aquest recurs, es neteja.
   */
  onResourceEvicted(resourceId: string): void {
    this.deps.selectionController.handleResourceEviction(resourceId);
    if (this.hoverHit?.kind === "star" && this.hoverHit.ref.resourceId === resourceId) {
      this.clearHover();
    }
    if (this.hoverHit?.kind === "deep_sky" && this.hoverHit.ref.resourceId === resourceId) {
      this.clearHover();
    }
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.started = false;

    window.removeEventListener("keydown", this.onKeyDownBound);

    if (this.hoverDebounceTimer) {
      clearTimeout(this.hoverDebounceTimer);
      this.hoverDebounceTimer = null;
    }

    if (this.unsubscribeSelection) {
      this.unsubscribeSelection();
      this.unsubscribeSelection = null;
    }

    this.selectionMarker.dispose();
    this.selectedHit = null;
    this.selectedRef = null;
    this.hoverHit = null;
    this.hoverRef = null;
  }

  // ─── Private ──────────────────────────────────────────────────────

  private handleTap(clientX: number, clientY: number): void {
    const hit = this.deps.pickProvider.pick(clientX, clientY);

    if (hit) {
      this.selectedHit = hit;
      this.selectedRef = hit.kind === "star" ? hit.ref : null;
      
      this.deps.selectionController.select(fromPickHit(hit), "pick");

      // Mostrar marker immediatament
      this.selectionMarker.update(
        hit.screenXCssPx,
        hit.screenYCssPx,
        hit.visualRadiusCssPx,
      );

      if (hit.kind === "star") {
        // Stars need their catalogue data resolved by the backend.
        this.selectGeneration++;
        this.requestIdCounter++;
        const reqId = `sel:${this.requestIdCounter}`;
        this.deps.resolveCallback(
          reqId,
          this.selectGeneration,
          hit.ref.resourceId,
          hit.ref.resourceVersion,
          hit.ref.catalogIndex,
          "select",
        );
        console.debug(
          `${LOG_PREFIX} [handleTap] [Star: ${hit.ref.resourceId} idx=${hit.ref.catalogIndex} dist=${hit.screenDistanceCssPx.toFixed(1)}px mag=${hit.magnitude.toFixed(2)}]`,
        );
      } else if (hit.kind === "deep_sky") {
        console.debug(
          `${LOG_PREFIX} [handleTap] [Deep Sky: ${hit.ref.resourceId} idx=${hit.ref.catalogIndex} dist=${hit.screenDistanceCssPx.toFixed(1)}px]`
        );
      } else {
        console.debug(
          `${LOG_PREFIX} [handleTap] [Solar body: ${hit.bodyId} dist=${hit.screenDistanceCssPx.toFixed(1)}px]`,
        );
      }
    } else {
      // Click a buit → clear selection
      this.clearSelection();
    }
  }

  private handleHover(clientX: number, clientY: number): void {
    const hit = this.deps.pickProvider.pick(clientX, clientY);

    if (!hit) {
      this.clearHover();
      return;
    }

    // Si és el mateix hover que abans, no fer res
    if (
      hit.kind === "star" &&
      this.hoverRef &&
      this.hoverRef.resourceId === hit.ref.resourceId &&
      this.hoverRef.resourceVersion === hit.ref.resourceVersion &&
      this.hoverRef.catalogIndex === hit.ref.catalogIndex
    ) {
      return;
    }

    this.hoverHit = hit;
    this.hoverRef = hit.kind === "star" ? hit.ref : null;

    // Solar-system hover has no asynchronous catalogue resolution.
    if (hit.kind !== "star") return;

    // Debounce la resolució backend del hover
    if (this.hoverDebounceTimer) {
      clearTimeout(this.hoverDebounceTimer);
    }

    this.hoverDebounceTimer = setTimeout(() => {
      this.hoverDebounceTimer = null;

      // Verificar que el hover no ha canviat durant el debounce
      if (
        this.hoverRef &&
        this.hoverRef.resourceId === hit.ref.resourceId &&
        this.hoverRef.catalogIndex === hit.ref.catalogIndex
      ) {
        this.hoverGeneration++;
        this.requestIdCounter++;
        const reqId = `hov:${this.requestIdCounter}`;

        this.deps.resolveCallback(
          reqId,
          this.hoverGeneration,
          hit.ref.resourceId,
          hit.ref.resourceVersion,
          hit.ref.catalogIndex,
          "hover",
        );
      }
    }, HOVER_DEBOUNCE_MS);
  }

  private clearHover(): void {
    this.hoverHit = null;
    this.hoverRef = null;
    if (this.hoverDebounceTimer) {
      clearTimeout(this.hoverDebounceTimer);
      this.hoverDebounceTimer = null;
    }
  }
}

function horizontalFovDeg(camera: THREE.Camera | undefined): number {
  if (!camera || !(camera as THREE.PerspectiveCamera).isPerspectiveCamera) return 60;
  const perspectiveCamera = camera as THREE.PerspectiveCamera;
  const verticalFovRad = THREE.MathUtils.degToRad(perspectiveCamera.fov);
  return THREE.MathUtils.radToDeg(
    2 * Math.atan(Math.tan(verticalFovRad / 2) * perspectiveCamera.aspect),
  );
}
