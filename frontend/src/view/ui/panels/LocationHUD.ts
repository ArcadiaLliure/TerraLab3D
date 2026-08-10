import type { NavigationCameraPose, MotionState, NavigationMode } from "../../../contracts/navigation";
import type { SkyEnvironmentSnapshot } from "../../../contracts/sky_environment_contracts";
import type {
  AstronomicalEventSearchResult,
  AstronomicalEventSnapshot,
  AngularSeparationResult,
} from "../../../contracts/astronomical_event_contracts";
import type { ResolvedStar } from "../../../contracts/star_picking_contracts";
import type { SolarSystemPickHit } from "../../three/picking/SolarSystemPickProvider";
import { formatLocalAndUtcTime } from "../timeFormatting";

const DEG = Math.PI / 180;

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character] ?? character);
}

function solarAppearanceLabel(
  phase: AstronomicalEventSnapshot["totalityAppearance"]["phase"],
): string {
  return ({
    partial: "parcialitat",
    baily_ingress: "Perles de Baily (entrada)",
    diamond_ingress: "anell de diamant (entrada)",
    totality: "totalitat",
    diamond_egress: "anell de diamant (sortida)",
    baily_egress: "Perles de Baily (sortida)",
  })[phase];
}

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
  private skySection: HTMLDivElement;
  private eventSection: HTMLDivElement;
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

    // Separator 3
    this.element.appendChild(this.createSep());

    // Sky section
    this.skySection = document.createElement("div");
    this.element.appendChild(this.skySection);

    this.element.appendChild(this.createSep());
    this.eventSection = document.createElement("div");
    this.eventSection.style.display = "none";
    this.element.appendChild(this.eventSection);

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
    const fovVal = pose.fovDeg;
    const fovText = fovVal >= 10
      ? `${fovVal.toFixed(1)}°`
      : fovVal >= 1
      ? `${fovVal.toFixed(2)}°`
      : fovVal >= 0.01
      ? `${fovVal.toFixed(3)}°`
      : `${fovVal.toFixed(4)}°`;

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

  public setSelectedCelestial(selection: ResolvedStar | SolarSystemPickHit | null): void {
    if (selection === null) {
      this.setSelectedStar(null);
    } else if (selection.kind === "star") {
      this.setSelectedStar(selection);
    } else {
      this.setSelectedSolarBody(selection);
    }
  }

  public setSelectedStar(star: ResolvedStar | null): void {
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

  private setSelectedSolarBody(hit: SolarSystemPickHit): void {
    const labels: Readonly<Record<string, string>> = {
      sun: "Sol",
      moon: "Lluna",
      mercury: "Mercuri",
      venus: "Venus",
      mars: "Mart",
      jupiter: "Júpiter",
      saturn: "Saturn",
      uranus: "Urà",
      neptune: "Neptú",
      pluto: "Plutó",
    };
    const state = hit.state;
    const name = escapeHtml(state.displayName ?? labels[hit.bodyId] ?? hit.bodyId);
    const magnitude = state.apparentMagnitude === null
      ? "no validada"
      : state.apparentMagnitude.toFixed(2);
    const parent = state.parentNaifId === undefined || state.parentNaifId === null
      ? ""
      : ` &nbsp; Pare: ${state.parentNaifId}`;
    const naif = state.naifId === undefined ? "" : `<div>NAIF: ${state.naifId}${parent}</div>`;
    const radii = state.radiiKm === undefined || state.radiiKm === null
      ? "radi no disponible"
      : `radis: ${state.radiiKm.map((value) => value.toFixed(2)).join(" / ")} km`;
    const ring = state.ringDiagnostics === undefined || state.ringDiagnostics === null
      ? ""
      : `<div>B geo/topo: ${state.ringDiagnostics.ringOpeningGeocentricDeg.toFixed(2)}° / ${state.ringDiagnostics.ringOpeningTopocentricDeg.toFixed(2)}°</div>`;
    this.starContainer.style.display = "block";
    this.starContainer.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px; color: #f1cd88;">Cos celeste seleccionat</div>
      <div>${name}</div>
      ${naif}
      <div>Alt: ${state.altitudeDeg.toFixed(2)}° &nbsp; Az: ${state.azimuthDeg.toFixed(2)}°</div>
      <div>Distància: ${state.distanceKm.toLocaleString(undefined, { maximumFractionDigits: 0 })} km</div>
      <div>Diàmetre aparent: ${state.angularDiameterDeg.toFixed(5)}° &nbsp; ${radii}</div>
      <div>Mag: ${magnitude} &nbsp; Il·luminació: ${(state.illuminationFraction * 100).toFixed(0)}%</div>
      <div>Fase: ${state.phaseAngleDeg.toFixed(2)}° &nbsp; Cobertura: ${state.coverageStatus ?? "legacy"}</div>
      <div>Orientació: ${state.orientationQuality ?? state.orientation?.quality ?? "unavailable"} &nbsp; Forma: ${state.shapeQuality ?? "unavailable"}</div>
      <div>Textura: ${state.textureQuality ?? "unavailable"} &nbsp; Kernel: ${escapeHtml(state.ephemerisKernelId ?? "legacy")}</div>
      ${ring}
      <div style="opacity: 0.7; font-size: 11px;">${escapeHtml(state.source)} · ${state.quality}</div>
    `;
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }

  public updateSkyEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    const sunAlt = snapshot.sunAltitudeDeg.toFixed(1);
    
    let lpInfo = "";
    if (snapshot.lightPollutionEnabled) {
      lpInfo = `Bortle ${snapshot.bortleClass?.toFixed(1) || "?"} | Mag lím: ${snapshot.visibility.zenithMagnitudeLimit.toFixed(1)}`;
    } else {
      lpInfo = `Mag lím: ${snapshot.visibility.zenithMagnitudeLimit.toFixed(1)} (sense LP)`;
    }
    
    let atmoInfo = snapshot.atmosphereEnabled ? "Activa" : "Inactiva";
    let phase = snapshot.twilightPhase;
    // Traducció simple
    const phaseCa: any = {
      "day": "Dia",
      "civil": "C. Civil",
      "nautical": "C. Nàutic",
      "astronomical": "C. Astronòmic",
      "night": "Nit"
    };

    this.skySection.innerHTML = `
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--color-text-muted);">Sol (alt):</span>
        <span style="color:var(--color-gold);">${sunAlt}° (${phaseCa[phase] || phase})</span>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--color-text-muted);">Atmosfera:</span>
        <span style="color:var(--color-gold);">${atmoInfo}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-top:2px;">
        <span style="color:var(--color-text-muted);">Cel fosc:</span>
        <span style="color:var(--color-text-bright);">${lpInfo}</span>
      </div>
    `;
  }

  public updateAstronomicalEvent(snapshot: AstronomicalEventSnapshot): void {
    const solar = snapshot.solar;
    const lunar = snapshot.lunar;
    const activeSolar = solar.classification !== "none";
    const activeLunar = lunar.classification !== "none";
    this.eventSection.style.display = activeSolar || activeLunar ? "block" : "none";
    if (!activeSolar && !activeLunar) return;
    this.eventSection.innerHTML = activeSolar ? `
      <div style="font-weight:600;color:#f1cd88">ECLIPSI SOLAR · ${solar.classification.toUpperCase()}</div>
      <div>Magnitud: ${solar.eclipseMagnitude.toFixed(4)}</div>
      <div>Obscuració: ${(solar.obscuration * 100).toFixed(3)}%</div>
      <div>Separació: ${solar.centerSeparation.toFixed(6)}°</div>
      <div>Fase: ${solarAppearanceLabel(snapshot.totalityAppearance.phase)}</div>
      <div style="opacity:.7">${snapshot.geometryQuality} · ${snapshot.limbQuality}</div>
    ` : `
      <div style="font-weight:600;color:#e2a2a2">ECLIPSI LUNAR · ${lunar.classification.toUpperCase()}</div>
      <div>Magnitud umbral: ${lunar.umbralMagnitude.toFixed(4)}</div>
      <div>Magnitud penumbral: ${lunar.penumbralMagnitude.toFixed(4)}</div>
      <div style="opacity:.7">${snapshot.geometryQuality}</div>
    `;
  }

  public updateEventSearchResult(result: AstronomicalEventSearchResult): void {
    const greatest = result.greatestUtc === null
      ? "—"
      : formatLocalAndUtcTime(result.greatestUtc);
    const contacts = result.contacts
      .map((contact) => `${escapeHtml(contact.name)} ${formatLocalAndUtcTime(contact.instantUtc)}`)
      .join(" · ");
    this.eventSection.style.display = "block";
    this.eventSection.insertAdjacentHTML("beforeend", `
      <div style="margin-top:3px">Màxim: ${greatest}</div>
      <div style="opacity:.8">${contacts || "Sense contactes locals"}</div>
    `);
  }

  public updateAngularSeparation(result: AngularSeparationResult): void {
    this.eventSection.style.display = "block";
    this.eventSection.innerHTML = `
      <div style="font-weight:600;color:#88ccff">SEPARACIÓ APARENT</div>
      <div>${escapeHtml(result.bodyA)} ↔ ${escapeHtml(result.bodyB)}</div>
      <div>Centres: ${result.separationDeg.toFixed(6)}°</div>
      <div>Limbe: ${result.limbSeparationDeg.toFixed(6)}°</div>
      <div style="opacity:.7">${result.occultation.classification} · ${result.quality}</div>
    `;
  }

  // ─── Private ──────────────────────────────────────────────────
  private createSep(): HTMLDivElement {
    const sep = document.createElement("div");
    sep.style.cssText = "height: 1px; background: rgba(59, 69, 89, 0.4); margin: 2px 0;";
    return sep;
  }
}
