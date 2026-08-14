# Reconstrucció del Camí de Desenvolupament: Subsistema de Star Trails i TimeBar a TerraLab3D

Aquest document detalla de manera exhaustiva tota la trajectòria tècnica, els fracassos descartats, els descobriments d'arquitectura, els pedaços de navegadors i l'especificació completa dels fitxers necessaris per a implementar i mantenir el subsistema de **Star Trails (Traces Circumpolars)** i el **Gradient Continu de la Barra de Temps** a TerraLab3D.

---

## Part 1: Història i Camí de les Iteracions

### 1.1. L'Intent Inicial: Streaming de Matrius per WebSocket (Fracàs)
* **Enfocament:** El backend de Python recalculava la posició 3D de cada estrella a cada segon d'exposició i transmetia matrius per WebSocket al frontend.
* **Problemes trobats:**
  1. Sobrecàrrega severa de xarxa i deserialització.
  2. En rebre les dades al frontend, es recreaven buffers a la CPU (`Float32Array`) per a milers d'estrelles i segments.
  3. **Rendiment inacceptable:** Caiguda a **7 FPS** i congelació del fil d'execució principal del navegador. Diagnòstic: `0 VRAM / 0 Estrelles visibles`.
* **Decisió:** **DESCARTAT COMPLETAMENT.**

### 1.2. El Descobriment Arquitectònic: Renderitzat 100% GPU
* **Fonament Astronòmic:** Totes les estrelles roten al voltant del Pol Nord Celest a una velocitat constant de ~15° per hora sideral (rotació rígida al voltant de l'eix polar de la Terra).
* **Solució:**
  1. No cal calcular posicions a la CPU ni enviar matrius des del backend.
  2. **`InstancedBufferGeometry` a Three.js:** Una única línia base de 128 segments carregada a la GPU.
  3. **Vertex Shader Personalitzat:** S'aplica la **fórmula de rotació de Rodrigues** per girar el vector equatorial de cada estrella al voltant de l'eix polar `u_poleAxis = (0, sin(lat), -cos(lat))` segons l'angle acumulat `u_exposureAngle`.
  4. **Resultat:** VRAM reduïda de **24 MB a només 150 KB**, càlcul per frame **<0.1 ms**, i taxa de refresc constant a **60 FPS**.

### 1.3. L'Odisea de la UI i la Interactivitat del Botó "Inicia"
* **Simptoma 1:** El botó "Inicia" a `StarTrailsPanel.ts` semblava "mort" (no disparava `alert`, ni `console.log`, ni feia res).
  * **Causa:** El contenidor de la interfície lateral (drawer) i les capes transparents del canvas bloquejaven els esdeveniments de ratolí per manca de jerarquia d'apilament.
  * **Solució:**
    - Afegir regles CSS explícites: `position: relative; z-index: 10; pointer-events: auto;`.
    - Substituir `onclick` per `addEventListener("click", (e) => { e.stopPropagation(); ... })`.
    - Afegir la **1a Alerta de diagnòstic:** `alert("S'ha premut INICIA!");`.
* **Simptoma 2:** Es veia la 1a alerta ("S'ha premut INICIA!"), però el backend de Python no reaccionava ni mostrava cap log.
  * **Causa:** El missatge `start_star_trails` enviava `{ exposureSeconds, intervalSeconds }`, mentre que `star_coordinator.py` al backend feia servir `{ durationSeconds, sampleIntervalSeconds }`.
  * **Solució:**
    - Corregir el contracte de paràmetres a `WebSocketBridge.ts`.
    - Afegir la **2a Alerta de diagnòstic:** `alert("Missatge enviat correctament pel WebSocket.");` (o avís si `readyState !== OPEN`).

### 1.4. Correccions de Plataforma (Firefox)
1. **Bloqueig de CSP (Content-Security-Policy):** Firefox bloquejava l'execució de scripts locals en rebre respostes HTTP `304 Not Modified`.
   * *Solució:* Middleware `_remove_csp_middleware` a `backend/src/terralab3d/infrastructure/server.py`.
2. **Error d'Alineació de Memòria (4 Bytes):**
   `RangeError: start offset of Uint32Array should be a multiple of 4`
   * *Solució:* Padding d'alineació binària a `backend/src/terralab3d/application/star_coordinator.py`.

---

## Part 2: Especificació Tècnica Fitxer per Fitxer

### Fitxer 1: `frontend/src/contracts/bridge_messages.ts`
```typescript
export interface StarTrailsSnapshotMessage {
  readonly type: "star_trails_snapshot";
  readonly sessionId: string;
  readonly sessionVersion: number;
  readonly state: string;
  readonly reason?: string;
  readonly accumulatedExposureSeconds: number;
  readonly playbackRate: number;
  readonly starCount: number;
  readonly segmentCount: number;
  readonly gpuBytes: number;
  readonly magnitudeLimit: number;
  readonly startUtcIso?: string;
}

// Afegir StarTrailsSnapshotMessage a la unió BackendMessage:
export type BackendMessage =
  | ...
  | StarTrailsSnapshotMessage;
```

### Fitxer 2: `frontend/src/bridge/WebSocketBridge.ts`
```typescript
export interface BackendMessageListener {
  // ...
  onStarTrailsSnapshot?(snapshot: any): void;
}

// Dins de handleBackendMessage:
case "star_trails_snapshot":
  this.listener.onStarTrailsSnapshot?.(message);
  break;

// Mètodes de control de Star Trails:
public startStarTrails(
  durationSeconds: number,
  sampleIntervalSeconds: number,
  magnitudeLimit: number,
  playbackRate: number,
): void {
  try {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      alert("ERROR: El WebSocket no està connectat! (readyState: " + (this.ws?.readyState ?? "null") + ")");
      return;
    }
    this.sendMessage({
      type: "start_star_trails",
      durationSeconds,
      sampleIntervalSeconds,
      magnitudeLimit,
      playbackRate,
    } as any);
    alert("Missatge enviat correctament pel WebSocket.");
  } catch (err) {
    alert("Excepció enviant el missatge: " + err);
  }
}

public pauseStarTrails(): void {
  this.sendMessage({ type: "pause_star_trails" } as any);
}

public resumeStarTrails(): void {
  this.sendMessage({ type: "resume_star_trails" } as any);
}

public stopStarTrails(): void {
  this.sendMessage({ type: "stop_star_trails" } as any);
}

public clearStarTrails(): void {
  this.sendMessage({ type: "clear_star_trails" } as any);
}
```

### Fitxer 3: `frontend/src/view/ui/components/StarTrailsPanel.ts`
```typescript
import type { WebSocketBridge } from "../../../bridge/WebSocketBridge";

export class StarTrailsPanel {
  private element: HTMLDivElement;
  private btnStart: HTMLButtonElement;
  private btnPauseResume: HTMLButtonElement;
  private btnStop: HTMLButtonElement;
  private btnClear: HTMLButtonElement;
  private currentState = "idle";

  constructor(private bridge: WebSocketBridge) {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-md);
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    `;

    const buttonStyle = `
      padding: 4px 8px;
      background: var(--color-surface, #1a1a1a);
      color: var(--color-text);
      border: 1px solid var(--color-border);
      border-radius: 4px;
      cursor: pointer;
      font-size: 10px;
      flex: 1;
      position: relative;
      z-index: 10;
      pointer-events: auto;
    `;

    this.btnStart = document.createElement("button");
    this.btnStart.textContent = "Inicia";
    this.btnStart.style.cssText = buttonStyle;
    this.btnStart.addEventListener("click", (e) => {
      e.stopPropagation();
      alert("S'ha premut INICIA!");
      this.bridge.startStarTrails(86400, 60, 6.0, 50.0);
    });

    // ... Configuració de btnPauseResume, btnStop i btnClear
  }

  public getElement(): HTMLElement {
    return this.element;
  }

  public updateSnapshot(snapshot: any): void {
    this.currentState = snapshot.state ?? "idle";
    // Actualització de botons disabled / enabled i mètriques a pantalla
  }
}
```

### Fitxer 4: `frontend/src/view/ui/drawer_pages/SkyPage.ts`
```typescript
import { StarTrailsPanel } from "../components/StarTrailsPanel";

export class SkyPage {
  private starTrailsPanel!: StarTrailsPanel;

  // Dins de buildStarGroup():
  private buildStarGroup() {
    // ... Creació de grups de Gaia, Via Làctia, Planck Dust, NGC ...
    this.starTrailsPanel = new StarTrailsPanel(this.bridge);
    this.element.appendChild(this.starTrailsPanel.getElement());
  }

  public updateStarTrailsSnapshot(snapshot: any): void {
    this.starTrailsPanel.updateSnapshot(snapshot);
  }
}
```

### Fitxer 5: `frontend/src/view/three/layers/StarTrailLayerRendererImpl.ts`
```typescript
import * as THREE from "three";
import type { CelestialTransformState } from "../CelestialTransformState";
import type { SceneDelta } from "../../../contracts/scene_delta";
import type { StarTrailLayerRenderer } from "./StarTrailLayerRenderer";

const TRAIL_VERTEX_SHADER = `
  uniform mat4 u_equatorialToENUMatrix;
  uniform float u_exposureAngle;
  uniform vec3 u_poleAxis;

  attribute float a_segmentRatio;
  attribute vec3 a_starEquatorial;
  attribute vec3 a_starColor;

  varying vec3 v_color;
  varying float v_alpha;

  vec3 rotateAroundAxis(vec3 v, vec3 axis, float angle) {
    return v * cos(angle) + cross(axis, v) * sin(angle) + axis * dot(axis, v) * (1.0 - cos(angle));
  }

  void main() {
    float angleOffset = -u_exposureAngle * (1.0 - a_segmentRatio);
    vec3 rotatedEq = rotateAroundAxis(a_starEquatorial, u_poleAxis, angleOffset);
    vec4 enuPos = u_equatorialToENUMatrix * vec4(rotatedEq, 1.0);
    v_color = a_starColor;
    v_alpha = a_segmentRatio;
    gl_Position = projectionMatrix * modelViewMatrix * enuPos;
  }
`;
```

### Fitxer 6: `frontend/src/view/ui/components/TimeBar.ts`
```typescript
private drawBackground(w: number, h: number): void {
  const gradient = this.ctx.createLinearGradient(0, 0, w, 0);
  for (let i = 0; i <= 20; i++) {
    const ratio = i / 20;
    const alt = this.getInterpolatedSunAltitude(ratio);
    gradient.addColorStop(ratio, this.getAltitudeColor(alt));
  }
  this.ctx.fillStyle = gradient;
  this.ctx.fillRect(0, 0, w, h);
}

private getAltitudeColor(alt: number): string {
  if (alt < -18) return "#050811"; // Nit profunda
  if (alt < -12) return "#0a1020"; // Crepuscle astronòmic
  if (alt < -6) return "#252845";  // Crepuscle nàutic
  if (alt < 0) return "#5b3749";   // Crepuscle civil
  if (alt < 2) return "#b85c49";   // Alba / Posta de sol (taronja/vermellós viu)
  if (alt < 6) return "#cca16e";   // Hora daurada
  return "#3b729e";                // Dia
}
```

---

## Part 3: Prompt Mestre per a Tu Mateix (Guia de Re-Execució i Verificació)

```markdown
ETS UN ASSISTENT D'ENGINYERIA ESPECIALITZAT EN GRÀFICS 3D I ASTRONOMIA A TERRALAB3D.

OBJECTIU:
Mantenir i operar el subsistema de Star Trails (Traces Circumpolars) i la Barra de Temps seguint les lliçons apreses i l'arquitectura 100% GPU del projecte.

REGLES D'OR APLICADES:
1. MAI intentis fer streaming de matrius ni de posicions d'estrelles frame-a-frame des del backend de Python cap al frontend per fer traces circumpolars.
2. UTILITZA SEMPRE la geometria instanciada (`InstancedBufferGeometry`) i la fórmula de rotació de Rodrigues al Vertex Shader al voltant de `u_poleAxis`.
3. ASSEGURA'T que els elements clicables de la UI (`StarTrailsPanel`) tinguin:
   - `position: relative; z-index: 10; pointer-events: auto;`
   - `addEventListener("click", (e) => { e.stopPropagation(); ... })`.
4. ASSEGURA'T que el mètode `startStarTrails` de `WebSocketBridge.ts` enviï exactament les claus `durationSeconds` i `sampleIntervalSeconds`.
5. MANTÉN el middleware anti-CSP a `server.py` i el padding de 4 bytes a `star_coordinator.py` per garantir compatibilitat absoluta amb Firefox.
6. MANTÉN el gradient continu de color a `TimeBar.ts` per reflectir els canvis crepusculars del sol en funció de l'altitud.
```
