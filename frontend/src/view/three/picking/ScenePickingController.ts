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
  resolveCallback: ResolveCallback;
  selectionChangedCallback?: SelectionChangedCallback;
}

const HOVER_DEBOUNCE_MS = 150;

export class ScenePickingController {
  private readonly deps: ScenePickingControllerDeps;
  private readonly selectionMarker: SelectionMarker;

  // ─── Selection state ───────────────────────────────────────────────
  private selectedHit: CelestialPickHit | null = null;
  private selectedRef: StarPickRef | null = null;
  private resolvedStar: ResolvedStar | null = null;

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

    // Escape handler
    this.onKeyDownBound = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.clearSelection();
        this.clearHover();
      }
    };
  }

  /** Munta el marker al container del canvas. */
  mount(container: HTMLElement): void {
    this.selectionMarker.mount(container);
    window.addEventListener("keydown", this.onKeyDownBound);
    this.started = true;
  }

  private externalTarget: any = null;

  public setExternalTarget(target: any): void {
    console.log(`${LOG_PREFIX} [setExternalTarget] Target:`, target);
    this.externalTarget = target;
    if (!target) {
      this.selectedHit = null;
      this.selectionMarker.hide();
      return;
    }

    if (target.kind === "body" || target.bodyId || target.targetRef) {
      const bodyId = target.bodyId || target.targetRef;
      this.selectedHit = {
        kind: "solar_system_body",
        bodyId,
        state: {} as any,
        screenXCssPx: 0,
        screenYCssPx: 0,
        screenDistanceCssPx: 0,
        hitRadiusCssPx: 20,
        visualRadiusCssPx: 20,
      };
    }
  }

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
        this.selectionMarker.update(pos.x, pos.y, pos.visualRadiusCssPx);
        return;
      }
    }

    if (this.externalTarget && trackingResolver && camera) {
      const resolved = trackingResolver.resolve(this.externalTarget);
      if (resolved) {
        const pos = this.projectDirectionToScreen(resolved.azimuthDeg, resolved.altitudeDeg, camera);
        if (pos) {
          this.selectionMarker.update(pos.x, pos.y, 16);
          return;
        }
      }
    }

    this.selectionMarker.hide();
  }

  private projectDirectionToScreen(azimuthDeg: number, altitudeDeg: number, camera: THREE.Camera): { x: number; y: number } | null {
    const azRad = azimuthDeg * (Math.PI / 180);
    const altRad = altitudeDeg * (Math.PI / 180);
    const cosAlt = Math.cos(altRad);

    const vec = new THREE.Vector3(
      Math.sin(azRad) * cosAlt,
      Math.sin(altRad),
      -Math.cos(azRad) * cosAlt
    ).multiplyScalar(1000000).add(camera.position);

    vec.project(camera);
    if (vec.z > 1.0) return null;

    const width = window.innerWidth;
    const height = window.innerHeight;
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
        console.log(`${LOG_PREFIX} [handleResolveResponse] [${purpose} ${msg.status}]`);
      }
      if (msg.status === "invalid") {
        console.warn(`${LOG_PREFIX} [handleResolveResponse] [${purpose} invalid: requestId=${msg.requestId}]`);
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
      this.resolvedStar = msg.star;
      this.deps.selectionChangedCallback?.(msg.star);
      console.log(
        `${LOG_PREFIX} [handleResolveResponse] [Select resolved: sourceId=${msg.star.sourceId} RA=${msg.star.raDeg.toFixed(4)} Dec=${msg.star.decDeg.toFixed(4)} G=${msg.star.magnitude.toFixed(2)}]`,
      );
    }
    // Hover resolves es podrien usar per tooltip — per ara no fem res extra
  }

  /** Retorna l'estrella resolta seleccionada. */
  getResolvedSelection(): ResolvedStar | null {
    return this.resolvedStar;
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
    if (this.selectedHit || this.selectedRef) {
      this.selectedHit = null;
      this.selectedRef = null;
      this.resolvedStar = null;
      this.selectionMarker.hide();
      this.deps.selectionChangedCallback?.(null);
    }
  }

  /**
   * Notifica que un recurs ha estat evicted o reemplaçat.
   * Si la selecció referencia aquest recurs, es neteja.
   */
  onResourceEvicted(resourceId: string): void {
    if (this.selectedHit?.kind === "star" && this.selectedHit.ref.resourceId === resourceId) {
      console.log(`${LOG_PREFIX} [onResourceEvicted] [Selecció invalidada: ${resourceId}]`);
      this.clearSelection();
    }
    if (this.hoverHit?.kind === "star" && this.hoverHit.ref.resourceId === resourceId) {
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

    this.selectionMarker.dispose();
    this.selectedHit = null;
    this.selectedRef = null;
    this.resolvedStar = null;
    this.hoverHit = null;
    this.hoverRef = null;
  }

  // ─── Private ──────────────────────────────────────────────────────

  private handleTap(clientX: number, clientY: number): void {
    const hit = this.deps.pickProvider.pick(clientX, clientY);

    if (hit) {
      this.selectedHit = hit;
      this.selectedRef = hit.kind === "star" ? hit.ref : null;
      this.resolvedStar = null;

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
        console.log(
          `${LOG_PREFIX} [handleTap] [Star: ${hit.ref.resourceId} idx=${hit.ref.catalogIndex} dist=${hit.screenDistanceCssPx.toFixed(1)}px mag=${hit.magnitude.toFixed(2)}]`,
        );
      } else if (hit.kind === "deep_sky") {
        this.deps.selectionChangedCallback?.(hit);
      } else {
        // Solar-system states already arrive in the scientific snapshot.
        this.deps.selectionChangedCallback?.(hit);
        console.log(
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
