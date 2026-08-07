import type { NavigationCameraPose, MotionState, NavigationMode } from "../../../contracts/navigation";

export class LocationHUD {
  private element: HTMLDivElement;
  private observerSection: HTMLDivElement;
  private cameraSection: HTMLDivElement;

  constructor() {
    this.element = document.createElement("div");
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
      min-width: 180px;
    `;

    // Observer section
    this.observerSection = document.createElement("div");
    this.element.appendChild(this.observerSection);

    // Separator
    const sep = document.createElement("div");
    sep.style.cssText = "height: 1px; background: rgba(59, 69, 89, 0.4); margin: 2px 0;";
    this.element.appendChild(sep);

    // Camera local section
    this.cameraSection = document.createElement("div");
    this.element.appendChild(this.cameraSection);

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
    <div>Altura: ${pose.positionUpM.toFixed(1)} m</div>
    <div>Vel: ${motion.speedMps.toFixed(1)} m/s</div>
    <div>Dist origen: ${distToOrigin.toFixed(1)} m</div>
  `;

    // Flight-specific diagnostics
    if (pose.navigationMode === "flight") {
      html += `
    <div style="color: #88bbff; font-size: 10px; margin-top: 2px;">
      Pitch: ${pose.altitudeDeg.toFixed(1)}° | Roll: ${pose.rollDeg.toFixed(1)}°
    </div>
    `;
    }

    this.cameraSection.innerHTML = html;
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }
}
