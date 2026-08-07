import type { NavigationCameraPose, MotionState, NavigationMode } from "../../../contracts/navigation";

const DEG = Math.PI / 180;

/**
 * Compute the cardinal direction suffix for a given azimuth.
 * Returns "N", "NE", "E", "SE", "S", "SO", "O", "NO".
 */
function azimuthToCardinal(azDeg: number): string {
  const az = ((azDeg % 360) + 360) % 360;
  if (az >= 337.5 || az < 22.5) return "N";
  if (az >= 22.5 && az < 67.5) return "NE";
  if (az >= 67.5 && az < 112.5) return "E";
  if (az >= 112.5 && az < 157.5) return "SE";
  if (az >= 157.5 && az < 202.5) return "S";
  if (az >= 202.5 && az < 247.5) return "SO";
  if (az >= 247.5 && az < 292.5) return "O";
  return "NO";
}

/**
 * Compute the view azimuth from the camera pose.
 * Returns null when looking at zenith/nadir (degenerate).
 */
function computeViewAzimuth(azDeg: number, altDeg: number): number | null {
  // When looking nearly straight up or down, the horizontal projection
  // of the forward vector has near-zero length → azimuth is degenerate.
  const cosAlt = Math.cos(altDeg * DEG);
  if (Math.abs(cosAlt) < 0.01) return null;
  return ((azDeg % 360) + 360) % 360;
}

export class LocationHUD {
  private element: HTMLDivElement;
  private observerSection: HTMLDivElement;
  private viewSection: HTMLDivElement;
  private cameraSection: HTMLDivElement;
  private readonly starContainer: HTMLDivElement;
  private hudVisible = true;

  constructor() {
    this.element = document.createElement("div");
    this.element.id = "location-hud";
    this.element.style.cssText = `
      position: absolute;
      bottom: 15px;
      left: 15px;
      background: rgba(13, 17, 28, 0.6);
      border: 1px solid rgba(59, 69, 89, 0.4);
      border-radius: 6px;
      padding: 8px 12px;
      color: #f3f5fa;
      font-family: 'Inter', sans-serif;
      font-size: 11px;
      backdrop-filter: blur(4px);
      display: flex;
      flex-direction: column;
      gap: 6px;
      pointer-events: none;
      z-index: 10;
      min-width: 200px;
    `;

    // Observer section
    this.observerSection = document.createElement("div");
    this.element.appendChild(this.observerSection);

    // Separator 1
    this.element.appendChild(this.createSep());

    // View orientation section (Phase 4)
    this.viewSection = document.createElement("div");
    this.element.appendChild(this.viewSection);

    // Separator 2
    this.element.appendChild(this.createSep());

    // Camera local section
    this.cameraSection = document.createElement("div");
    this.element.appendChild(this.cameraSection);

    this.starContainer = document.createElement("div");
    this.starContainer.style.cssText = `
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid rgba(255,255,255,0.2);
      display: none;
    `;
    this.element.appendChild(this.starContainer);

    this.updateHUD(0, 0, 0, 0, "No disponible");
    this.updateCameraHUD({
      positionEastM: 0,
      positionUpM: 0,
      positionNorthM: 0,
      azimuthDeg: 0,
      altitudeDeg: 0,
      rollDeg: 0,
      fovDeg: 60,
      navigationMode: "walk",
    }, {
      moving: false,
      sprinting: false,
      speedMps: 0,
      velocityEast: 0,
      velocityUp: 0,
      velocityNorth: 0,
    });
  }

  public updateHUD(
    lat: number,
    lon: number,
    elevation: number,
    effectiveHeight: number,
    source: string,
  ): void {
    const latStr = lat.toFixed(4);
    const lonStr = lon.toFixed(4);
    const effStr = effectiveHeight.toFixed(1);

    this.observerSection.innerHTML = `
    <div style="font-weight: 600; color: #d8b26a; margin-bottom: 2px;">
      OBSERVADOR
    </div>
    <div>Lat: ${latStr}° | Lon: ${lonStr}°</div>
    <div>Alçada efectiva: ${effStr} m</div>
    <div style="color: #88bbff; font-size: 10px; margin-top: 2px;">
      Font elev: ${source}
    </div>
  `;
  }

  public updateCameraHUD(
    pose: NavigationCameraPose,
    motion: MotionState,
  ): void {
    // ─── View orientation section (Phase 4) ──────────────────────────
    const viewAz = computeViewAzimuth(pose.azimuthDeg, pose.altitudeDeg);
    const azText = viewAz !== null
      ? `${viewAz.toFixed(1)}° (${azimuthToCardinal(viewAz)})`
      : "—";
    const altText = `${pose.altitudeDeg.toFixed(1)}°`;
    const fovText = `${pose.fovDeg.toFixed(1)}°`;

    let viewHtml = `
    <div style="font-weight: 600; color: #88ccff; margin-bottom: 2px;">
      VISTA
    </div>
    <div>Azimut vista: ${azText}</div>
    <div>Altitud vista: ${altText}</div>
    <div>FOV: ${fovText}</div>
  `;

    // Roll — show only in flight mode
    if (pose.navigationMode === "flight") {
      viewHtml += `<div>Roll: ${pose.rollDeg.toFixed(1)}°</div>`;
    }

    this.viewSection.innerHTML = viewHtml;

    // ─── Camera local section ────────────────────────────────────────
    const modeLabel = pose.navigationMode === "walk" ? "Caminar" : "Avió";
    const distToOrigin = Math.sqrt(
      pose.positionEastM * pose.positionEastM +
      pose.positionNorthM * pose.positionNorthM,
    );

    let html = `
    <div style="font-weight: 600; color: #4fd8c4; margin-bottom: 2px;">
      CÀMERA LOCAL
    </div>
    <div>Mode: ${modeLabel}</div>
    <div>E: ${pose.positionEastM.toFixed(1)} | N: ${pose.positionNorthM.toFixed(1)}</div>
    <div>Cota local: ${pose.positionUpM.toFixed(1)} m</div>
    <div>Vel: ${motion.speedMps.toFixed(1)} m/s</div>
    <div>Dist origen: ${distToOrigin.toFixed(1)} m</div>
  `;

    this.cameraSection.innerHTML = html;
  }

  public setVisible(visible: boolean): void {
    this.hudVisible = visible;
    this.element.style.display = visible ? "flex" : "none";
  }

  public setSelectedStar(star: any | null): void {
    if (!star) {
      this.starContainer.style.display = "none";
      this.starContainer.innerHTML = "";
      return;
    }
    
    this.starContainer.style.display = "block";
    
    let bpRpText = "N/A";
    if (star.bpRp !== null && star.bpRp !== undefined) {
      bpRpText = star.bpRp.toFixed(2);
    }
    
    this.starContainer.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px; color: #f1cd88;">Estrella seleccionada</div>
      <div>ID: ${star.sourceId}</div>
      <div>RA: ${star.raDeg.toFixed(4)}° &nbsp; Dec: ${star.decDeg.toFixed(4)}°</div>
      <div>Mag: ${star.magnitude.toFixed(2)} &nbsp; BP-RP: ${bpRpText}</div>
      <div style="opacity: 0.7; font-size: 11px;">Font: ${star.sourceRole}</div>
    `;
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }

  // ─── Private ──────────────────────────────────────────────────
  private createSep(): HTMLDivElement {
    const sep = document.createElement("div");
    sep.style.cssText = "height: 1px; background: rgba(59, 69, 89, 0.4); margin: 2px 0;";
    return sep;
  }
}
