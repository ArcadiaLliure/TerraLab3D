# Pas 3.5 — Càmera translacional, mode caminar i mode avió

> Estat: **completat**  
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’usuari pot desplaçar-se físicament per l’escenari tridimensional, no només girar sobre el punt d’origen.

La càmera disposa de dos modes:

- **Caminar:** exploració local vinculada a la superfície, amb altura d’ulls i col·lisió amb el terreny.
- **Avió:** vol lliure tridimensional amb ascens, descens, pitch, yaw, roll i control de velocitat.

Els objectes pròxims mostren paral·laxi real. El terreny i els objectes locals reaccionen a la translació; el cel astronòmic es manté a distància infinita i no presenta paral·laxi.

Caminar o volar no recalcula automàticament la ubicació astronòmica, el temps sideral, les efemèrides, Gaia, la Via Làctia, NGC, la contaminació lumínica ni els datasets geogràfics.

## Fonts a consultar

### TerraLab `main`, només en mode lectura

- `TerraLab/ui/astro_canvas.py`
- `TerraLab/ui/canvas_mixins/interaction.py`
- `TerraLab/ui/widget_init_helpers.py`
- `TerraLab/scene/camera.py`, si existeix
- `TerraLab/scene/projection.py`, si existeix
- proves de càmera, interacció, projecció i lifecycle

### TerraLab3D

- controlador de càmera;
- render loop;
- host Three.js;
- arbre de l’escena;
- contractes del bridge;
- HUD;
- listeners de teclat i ratolí;
- resize, focus, `visibilitychange` i shutdown;
- terreny tècnic i proves de les fases 1–3.

## Objectiu

Afegir translació tridimensional real a la càmera mitjançant un sistema local en metres, amb mode caminar i mode avió, sense alterar l’autoritat científica de Python ni introduir recàlculs científics durant la navegació.

La fase ha de preparar l’arquitectura futura de DEM, malles, picking de superfície, col·lisions, LOD, prefetch i reubicació explícita de l’observador.

---

## Separació obligatòria entre observador i càmera

## Observador científic

Determina latitud, longitud, elevació, alçada addicional, zona horària, temps sideral, efemèrides, horitzó, contaminació lumínica i selecció geogràfica de dades.

```ts
interface ScientificObserver {
  latitudeDeg: number;
  longitudeDeg: number;
  terrainElevationM: number | null;
  observerOffsetM: number;
}
```

## Càmera visual

Determina posició local, orientació, FOV, velocitat, acceleració i mode de navegació.

```ts
type NavigationMode = "walk" | "flight";

interface CameraPose {
  positionEastM: number;
  positionUpM: number;
  positionNorthM: number;
  azimuthDeg: number;
  altitudeDeg: number;
  rollDeg: number;
  fovDeg: number;
  navigationMode: NavigationMode;
}
```

Caminar o volar modifica `CameraPose`. No modifica `ScientificObserver`.

---

## Convenció espacial

Convenció recomanada:

```text
+X = Est
+Y = Amunt
+Z = Nord
Unitat = metres
```

Cal documentar:

- sentit positiu de l’azimut;
- correspondència entre azimut i vectors Three.js;
- convencions `forward`, `right` i `up`;
- orientació inicial;
- origen local;
- semàntica de pitch i roll;
- conversió futura entre ENU i coordenades geodèsiques.

No es poden barrejar metres, graus, radians i coordenades geodèsiques dins del mateix camp.

---

## Decisions arquitectòniques de navegació i terreny

### Decisió #6 — `TerrainSampler` és el punt d’extensió crític del terreny

El controlador de navegació no ha de conèixer la font d’altures ni importar cap implementació concreta de terreny.

Es defineix una abstracció rica de superfície:

```ts
interface GroundSample {
  heightM: number;
  normal: {
    east: number;
    up: number;
    north: number;
  };
  slopeDeg: number;
  valid: boolean;
  surfaceId?: string;
}

interface TerrainSampler {
  sampleGround(
    eastM: number,
    northM: number,
    referenceUpM?: number,
  ): GroundSample | null;
}
```

Responsabilitats de `TerrainSampler`:

- consultar la superfície local;
- retornar altura, normal, pendent i validesa;
- encapsular l’origen de les dades;
- no modificar la càmera;
- no integrar velocitat;
- no aplicar suavitzat;
- no decidir la locomoció.

Implementació actual:

```text
TerrainSampler
    ↑
TechnicalTerrainSampler
    ↑
Raycaster / malla tècnica Three.js
```

Implementació futura:

```text
TerrainSampler
    ↑
DEMTerrainSampler
    ↑
Heightfield / tiles DEM
```

Substituir `TechnicalTerrainSampler` per `DEMTerrainSampler` no ha d’obligar a modificar `NavigationController`, `GroundFollower`, input, HUD, mode caminar ni mode avió.

### Decisió #7 — Grounding físic exacte i seguiment d’orografia

El mode caminar no ha de limitar-se a moure E/N i corregir Y després. La locomoció ha de seguir la superfície real disponible.

Es crea una responsabilitat separada, conceptualment equivalent a:

```ts
interface GroundResolution {
  pose: CameraPose;
  grounded: boolean;
  blocked: boolean;
  reason?: string;
}

interface GroundFollower {
  resolve(
    previousPose: CameraPose,
    proposedPose: CameraPose,
    terrainSampler: TerrainSampler,
    settings: WalkNavigationSettings,
  ): GroundResolution;
}
```

Flux obligatori:

```text
Input WASD
→ moviment proposat
→ TerrainSampler.sampleGround(E, N)
→ GroundFollower
   ├── valida mostra
   ├── comprova desnivell
   ├── comprova pendent
   ├── projecta moviment sobre el pla tangent
   ├── resol grounding
   └── conserva última pose segura si cal
→ PhysicalCameraPose
→ CameraVisualSmoother
→ CameraRig
```

La pose física en mode caminar queda exactament enganxada a la superfície:

```text
physicalUpM = groundHeightM + eyeHeightM
```

No s’ha d’utilitzar un `lerp()` sobre la Y física com a mecanisme de grounding, perquè podria provocar flotació temporal o penetració del terreny.

El suavitzat s’aplica només a la representació visual de la càmera:

```text
GroundFollower
→ PhysicalCameraPose       (exacta)
→ CameraVisualSmoother     (només confort visual)
→ CameraRig
→ Three.js Camera
```

El `CameraVisualSmoother` no pot modificar col·lisions, límits, altura física, càlcul de pendent ni decisions de grounding.

El moviment caminant s’ha de projectar sobre el pla tangent definit per la normal de la superfície, sempre que sigui apropiat, per caminar **sobre** l’orografia en lloc de moure’s horitzontalment i corregir Y posteriorment.

La pendent es calcula a partir de la normal i `UP`. `maximumWalkableSlopeDeg` és configurable i evita escalar parets o superfícies pràcticament verticals.

`maximumStepHeightM` continua sent configurable i diferencia una irregularitat caminable d’un obstacle massa alt.

Si la mostra és `null`, invàlida, NaN, infinita o té una normal degenerada, es conserva `lastSafeGroundedPose` i es bloqueja el moviment cap a la zona insegura. No es teletransporta la càmera a Y=0 ni es permet una caiguda infinita.

El mode avió reutilitza el mateix `TerrainSampler`, però no el `GroundFollower`: utilitza la mostra per calcular clearance, anti-penetració i distància mínima al terreny.

---

## Arbre de l’escena

```text
scene
├── celestialRoot
│   ├── stars
│   ├── milkyWay
│   ├── solarSystem
│   ├── deepSky
│   └── celestialGrid
├── worldRoot
│   ├── terrain
│   ├── horizon
│   ├── surface
│   ├── localReferenceObjects
│   └── navigationBounds
├── overlayRoot
│   ├── HUD
│   ├── labels
│   └── diagnostics
└── cameraRig
    └── yawNode
        └── pitchNode
            └── rollNode
                └── camera
```

Regles:

- `worldRoot` utilitza metres locals.
- `celestialRoot` representa direccions astronòmiques.
- `overlayRoot` no es trasllada ni rota amb el roll.
- el cel no presenta paral·laxi.
- el món local sí que presenta paral·laxi.
- el mode caminar força `rollDeg = 0`.
- el mode avió pot utilitzar roll.

---

## Zona local precarregada

La navegació només s’activa dins d’una zona preparada.

```ts
interface NavigationEnvelope {
  centerEastM: number;
  centerNorthM: number;
  minimumUpM: number;
  maximumUpM: number;
  horizontalRadiusM: number;
  readiness:
    | "empty"
    | "loading"
    | "world_ready"
    | "collision_ready"
    | "navigation_ready"
    | "error";
  generation: number;
}
```

La zona ha de contenir, quan sigui aplicable:

- geometria;
- normals;
- materials;
- superfície detectable;
- informació de col·lisió;
- límits;
- picking;
- metadades de generació.

Si encara no hi ha DEM real, cal utilitzar una escena tècnica persistent amb desnivells, obstacles simples i objectes a distàncies diferents. No s’han d’inventar dades científiques.

## Estats de càrrega

```text
EMPTY
→ LOADING
→ WORLD_READY
→ COLLISION_READY
→ NAVIGATION_READY
```

En error:

```text
LOADING
→ ERROR
```

Mentre no sigui `NAVIGATION_READY`, la rotació i el FOV poden funcionar, però caminar i volar queden bloquejats.

## Política inicial de prefetch

En aquesta fase no cal streaming infinit:

- carregar una zona local completa;
- impedir sortir-ne;
- frenar o bloquejar al límit;
- mostrar feedback;
- no recalcular ciència en tocar el límit.

Cal deixar preparat el contracte futur:

```text
zona activa
→ corona de prefetch
→ zona no disponible
```

---

## Mode caminar

## Comportament

El mode caminar:

- es desplaça sobre la superfície local real disponible;
- manté una altura d’ulls exacta respecte del terreny;
- segueix pujades i baixades sense separar-se físicament del sòl;
- utilitza `TerrainSampler` per consultar la superfície;
- utilitza `GroundFollower` per resoldre la locomoció;
- no admet roll;
- no admet moviment vertical lliure;
- impedeix travessar la superfície;
- impedeix escalar pendents superiors al límit;
- impedeix superar steps massa alts;
- utilitza velocitat moderada;
- aplica acceleració i frenada suaus;
- separa pose física de suavitzat visual.

```ts
interface WalkNavigationSettings {
  eyeHeightM: number;
  walkSpeedMps: number;
  sprintSpeedMps: number;
  accelerationMps2: number;
  decelerationMps2: number;
  maximumStepHeightM: number;
  maximumWalkableSlopeDeg: number;
  groundProbeDistanceM: number;
  visualGroundSmoothing: number;
}
```

Valors inicials configurables:

```text
eyeHeightM              = 1.70
walkSpeedMps            = 2.50
sprintSpeedMps          = 6.00
accelerationMps2        = 8.00
decelerationMps2        = 10.00
maximumWalkableSlopeDeg = 45
```

## Controls

```text
W       avançar
S       retrocedir
A       esquerra
D       dreta
Shift   córrer
Ratolí  orientar
Roda    modificar FOV
R       tornar a l’origen
F       alternar Caminar / Avió
```

## Seguiment del terreny i grounding

La consulta de terreny es fa exclusivament a través de `TerrainSampler.sampleGround()`.

La implementació actual és `TechnicalTerrainSampler`, basada en raycast contra la malla tècnica. El futur `DEMTerrainSampler` haurà de poder substituir-la sense modificar els consumidors.

El mode caminar resol cada proposta de moviment així:

```text
input
→ moviment E/N proposat
→ sampleGround(E, N)
→ normal + pendent + altura
→ projectar moviment sobre pla tangent
→ comprovar maximumWalkableSlopeDeg
→ comprovar maximumStepHeightM
→ GroundFollower.resolve(...)
→ physicalUpM = groundHeightM + eyeHeightM
→ CameraVisualSmoother
```

Requisits:

- la pose física queda sempre a `groundHeightM + eyeHeightM` quan la mostra és vàlida;
- la Y física no s’interpola amb `lerp()`;
- el suavitzat vertical és exclusivament visual;
- conservar `lastSafeGroundedPose` si falla la consulta;
- rebutjar mostres null, invàlides, NaN, infinites o amb normals degenerades;
- projectar la locomoció sobre la superfície quan sigui apropiat;
- impedir pendents superiors a `maximumWalkableSlopeDeg`;
- impedir steps superiors a `maximumStepHeightM`;
- cap consulta Python per passa ni per frame;
- impedir caigudes infinites;
- impedir travessar la superfície;
- el canvi de sampler no modifica `GroundFollower` ni `NavigationController`.

---

## Mode avió

## Comportament

El mode avió és un mode de navegació 3D inspirat en una aeronau, no una simulació aerodinàmica completa.

Permet:

- avançar i retrocedir;
- ascendir i descendir;
- sobrevolar el terreny;
- controlar pitch i yaw;
- aplicar roll;
- augmentar velocitat;
- estabilitzar la càmera;
- respectar sostre, terreny i límits horitzontals.

```ts
interface FlightNavigationSettings {
  minimumSpeedMps: number;
  cruiseSpeedMps: number;
  maximumSpeedMps: number;
  accelerationMps2: number;
  brakingMps2: number;
  climbRateMps: number;
  descentRateMps: number;
  maximumPitchDeg: number;
  maximumRollDeg: number;
  minimumClearanceM: number;
  maximumAltitudeM: number;
  autoLevelRoll: boolean;
  autoLevelPitch: boolean;
}
```

Valors inicials configurables:

```text
minimumSpeedMps   = 0
cruiseSpeedMps    = 20
maximumSpeedMps   = 120
accelerationMps2  = 15
brakingMps2       = 20
climbRateMps      = 15
descentRateMps    = 15
maximumPitchDeg   = 80
maximumRollDeg    = 45
minimumClearanceM = 2
```

## Controls recomanats

```text
W       avançar o augmentar empenta
S       retrocedir o frenar
A       strafe o yaw esquerra
D       strafe o yaw dreta
Espai   pujar
Ctrl    baixar
Shift   impuls ràpid
Ratolí  yaw i pitch
Q       roll esquerra
E       roll dreta
X       aturar o estabilitzar
R       tornar a l’origen
F       tornar a mode caminar
```

Per a aquesta fase es recomana **vol lliure**:

- W/S: moviment endavant i enrere;
- A/D: strafe;
- Espai/Ctrl: vertical;
- ratolí: yaw/pitch;
- Q/E: roll visual;
- X: anul·lar velocitat i estabilitzar.

Això deixa preparada una evolució posterior cap a un mode d’avió amb empenta contínua.

## Altura i col·lisions

El mode avió reutilitza `TerrainSampler` per conèixer el terreny inferior, però no utilitza `GroundFollower` per enganxar-se a la superfície.

```text
clearanceM = physicalUpM - groundHeightM
```

Requisits:

- impedir travessar el terreny;
- mantenir `minimumClearanceM`;
- aplicar sostre màxim;
- frenar o lliscar al contacte amb un límit;
- evitar salts després de frames llargs;
- recuperar posicions invàlides;
- rebutjar NaN i infinits;
- no duplicar la consulta de superfície fora de `TerrainSampler`.

Si `TerrainSampler` no retorna una mostra vàlida:

- conservar l’últim estat segur;
- limitar el descens cap a una zona desconeguda;
- mostrar warning;
- mantenir el render actiu;
- no entrar automàticament en mode caminar.

## Balanceig (`roll`)

- en caminar, roll zero;
- en vol, Q/E modifiquen roll;
- auto-level opcional en deixar les tecles;
- HUD i UI no roten;
- el roll no altera les coordenades astronòmiques.

---

## Canvi de mode

Accions:

```text
set_navigation_mode("walk")
set_navigation_mode("flight")
toggle_navigation_mode()
```

## Caminar → avió

- conservar posició, azimut i FOV;
- conservar pitch dins dels límits;
- inicialitzar roll a zero;
- inicialitzar velocitat segura;
- desactivar altura d’ulls;
- no recarregar recursos.

## Avió → caminar

- trobar una superfície segura sota la càmera;
- aplicar altura d’ulls;
- posar roll a zero;
- anul·lar velocitat vertical;
- anul·lar velocitat de vol;
- conservar azimut;
- limitar pitch;
- no reubicar l’observador.

Si no hi ha superfície segura:

- impedir el canvi;
- mostrar missatge;
- conservar mode avió;
- no teletransportar la càmera.

---

## UI

Afegir la secció `Navegació` dins del calaix `Ubicació`, respectant la UI equivalent a TerraLab.

El canvi de mode s’ha de fer principalment mitjançant un **botó SVG únic d’alternança persona / avió**.

Comportament obligatori del botó:

- en mode `walk`, mostra una icona SVG de persona/caminant;
- en mode `flight`, mostra una icona SVG d’avió;
- un clic alterna el mode;
- la icona canvia immediatament amb l’estat real;
- `F` és una drecera equivalent i queda sincronitzada amb el botó;
- disposa de `hover`, `focus`, `active` i estat disabled;
- disposa d’`aria-label` o tooltip coherent amb el mode actual o l’acció següent;
- les icones són SVG locals, lleugeres i coherents amb el design system;
- no depèn d’una font d’icones externa ni d’un CDN;
- no és un selector textual duplicat si el botó SVG ja cobreix l’acció.

Controls mínims:

- botó SVG persona / avió;
- botó `Tornar a l’origen`;
- indicador textual del mode actual;
- indicador de velocitat;
- posició local;
- altura sobre terreny;
- estat de la zona;
- avís de límit;
- avís de col·lisió.

Shortcut:

```text
F = alternar Caminar / Avió
```

No s’ha d’afegir un panell flotant nou.

---

## Integració temporal

El moviment depèn de `deltaTime`:

```text
input
→ vector d’intenció
→ acceleració
→ velocitat objectiu
→ integració per deltaTime
→ GroundFollower / clearance
→ col·lisió
→ límits
→ pose física
→ suavitzat visual
→ pose renderitzada
```

Requisits:

- distància equivalent a 30, 60 i 144 FPS;
- `deltaTime` limitat després d’una pausa;
- moviment diagonal normalitzat;
- acceleració i frenada suaus;
- cap moviment amb pestanya oculta;
- cap moviment residual després de `blur`;
- cap velocitat residual incompatible després de canviar de mode.

Valor inicial recomanat:

```ts
const cappedDeltaSeconds = Math.min(rawDeltaSeconds, 0.05);
```

---

## Cel astronòmic

- estrelles, Via Làctia i grid no presenten paral·laxi;
- el cel continua rotant amb el temps sideral;
- volar no canvia coordenades celestes;
- volar no modifica Bortle ni magnitud;
- volar no recarrega catàlegs ni textures.

Implementacions acceptables:

- recentrar `celestialRoot`;
- eliminar translació de la matriu;
- skydome;
- escena celeste separada.

Cal documentar la solució escollida.

---

## Autoritat i bridge

TypeScript és responsable de la navegació per frame.

Python pot conservar snapshots, però no participa en cada frame.

No s’ha d’enviar `camera_pose_changed` a 60 Hz.

Política:

- actualització local per frame;
- notificació coalescida durant moviment;
- notificació final en aturar-se;
- snapshot immediat només a petició;
- `set_camera_pose` des de Python;
- confirmació amb generació i correlació.

Missatges mínims:

```text
navigation_world_prepare
navigation_world_ready
navigation_world_failed
set_navigation_mode
navigation_mode_changed
set_camera_pose
camera_pose_changed
camera_motion_started
camera_motion_stopped
camera_reset_requested
camera_reset_completed
camera_bounds_reached
camera_collision_detected
```

Camps:

```text
session_id
trace_id
request_id
generation
timestamp
navigation_mode
position_east_m
position_up_m
position_north_m
azimuth_deg
altitude_deg
roll_deg
fov_deg
velocity_east_m_s
velocity_up_m_s
velocity_north_m_s
speed_m_s
motion_state
bounds_state
collision_state
```

---

## HUD

Distingir:

```text
Observador científic:
  latitud
  longitud
  elevació
  alçada addicional

Càmera local:
  mode
  est
  nord
  altura
  velocitat
  distància a l’origen
  altura sobre terreny
  estat de zona
```

En mode avió, en diagnòstic:

```text
pitch
roll
velocitat vertical
sostre disponible
```

No reconstruir tot el DOM per frame.

---

## Logging MGP

Format obligatori:

```text
MGP: [ARXIU] [MÈTODE] [MISSATGE]
```

Exemples:

```text
MGP: [NavigationWorld.ts] [prepare] [Preparant zona navegable generation=4 radius_m=500]
MGP: [NavigationWorld.ts] [prepare] [Zona preparada generation=4 triangles=12800 duration_ms=42.6]
MGP: [CameraController.ts] [setMode] [Mode canviat previous=walk current=flight]
MGP: [CameraController.ts] [startMotion] [Moviment iniciat mode=flight speed_m_s=20]
MGP: [CameraController.ts] [stopMotion] [Moviment finalitzat east_m=14.2 north_m=-8.7 up_m=32.8]
MGP: [CameraController.ts] [applyBounds] [Límit assolit direction=north]
MGP: [GroundFollower.ts] [resolve] [Pendent rebutjada slope_deg=52.4 limit_deg=45]
MGP: [TechnicalTerrainSampler.ts] [sampleGround] [Mostra invàlida; es conserva lastSafeGroundedPose]
```

No registrar:

- cada frame;
- cada tecla repetida;
- cada `sampleGround()` correcte;
- cada raycast correcte;
- cada actualització de HUD;
- cada canvi submil·limètric.

Canals:

- `camera`;
- `navigation`;
- `scene`;
- `collision`;
- `performance`;
- `bridge`;
- `lifecycle`.

---

## Tasques

## Caracterització

- [ ] Revisar la càmera actual de TerraLab3D.
- [ ] Revisar el render loop i la convenció d’eixos.
- [ ] Revisar els listeners de teclat i ratolí.
- [ ] Revisar el contracte actual de `camera_pose`.
- [ ] Revisar focus, blur, visibilitychange i shutdown.
- [ ] Documentar les diferències respecte de TerraLab `main`.

## Model d’estat

- [ ] Separar `ScientificObserver` de `CameraPose`.
- [ ] Afegir `NavigationMode`.
- [ ] Afegir posició i velocitat locals en metres.
- [ ] Afegir roll, estat de moviment, límits i col·lisió.
- [ ] Afegir `CameraHomePose` i `NavigationEnvelope`.
- [ ] Definir `GroundSample` i `TerrainSampler`.
- [ ] Definir `GroundFollower` i `GroundResolution`.
- [ ] Separar `PhysicalCameraPose` de la pose visual suavitzada.
- [ ] Afegir `lastSafeGroundedPose`.
- [ ] Validar finits i rebutjar NaN o infinits.
- [ ] Validar normals de superfície.
- [ ] Normalitzar azimut i limitar pitch i roll.
- [ ] Versionar contractes.

## Arbre Three.js

- [ ] Crear o consolidar `celestialRoot`, `worldRoot` i `overlayRoot`.
- [ ] Crear `cameraRig` amb yaw, pitch i roll.
- [ ] Evitar translació del cel.
- [ ] Aplicar translació al món local.
- [ ] Preservar l’escena persistent.
- [ ] Evitar recrear geometries i materials durant el moviment.

## Zona navegable i superfície

- [ ] Implementar els estats de preparació.
- [ ] Crear escena tècnica persistent.
- [ ] Afegir superfície detectable, desnivells i objectes de referència.
- [ ] Implementar `TechnicalTerrainSampler` darrere `TerrainSampler`.
- [ ] Fer que `TechnicalTerrainSampler` retorni altura, normal i pendent.
- [ ] Verificar que cap consumidor importa directament el raycaster.
- [ ] Deixar preparada la substitució futura per `DEMTerrainSampler` sense implementar DEM real.
- [ ] Afegir límits horitzontals i verticals.
- [ ] Implementar error i retry idempotent.
- [ ] Rebutjar generacions antigues.
- [ ] No activar navegació abans de `NAVIGATION_READY`.

## Entrada

- [ ] Implementar WASD, Shift, Espai, Ctrl, Q/E, X, R i F.
- [ ] Ignorar tecles amb inputs o modals actius.
- [ ] Gestionar blur, visibilitychange, canvi de mode i shutdown.
- [ ] Evitar scroll accidental i tecles enganxades.

## Integració temporal

- [ ] Utilitzar i limitar `deltaTime`.
- [ ] Normalitzar moviment diagonal.
- [ ] Implementar acceleració, frenada i velocitat màxima.
- [ ] Evitar dependència del FPS i salts després de pauses.

## Mode caminar

- [ ] Implementar velocitat normal i sprint.
- [ ] Implementar altura d’ulls.
- [ ] Implementar `GroundFollower` desacoblat de la font de terreny.
- [ ] Consultar la superfície exclusivament via `TerrainSampler`.
- [ ] Mantenir la pose física exactament a `groundHeightM + eyeHeightM`.
- [ ] Projectar el moviment sobre el pla tangent de la superfície.
- [ ] Implementar `maximumWalkableSlopeDeg` configurable.
- [ ] Rebutjar pendents no caminables.
- [ ] Implementar `maximumStepHeightM` i rebutjar obstacles massa alts.
- [ ] Implementar `CameraVisualSmoother` separat del grounding físic.
- [ ] Impedir que el smoothing visual modifiqui col·lisions o pose física.
- [ ] Impedir travessar el terreny.
- [ ] Conservar `lastSafeGroundedPose` davant mostres invàlides.
- [ ] Posar roll a zero i impedir moviment vertical lliure.

## Mode avió

- [ ] Implementar moviment tridimensional lliure.
- [ ] Implementar ascens, descens i impuls ràpid.
- [ ] Implementar pitch, yaw i roll.
- [ ] Implementar estabilització amb X.
- [ ] Reutilitzar `TerrainSampler` per clearance i anti-penetració.
- [ ] No utilitzar `GroundFollower` per enganxar el mode avió al terreny.
- [ ] Implementar sostre i distància mínima al terreny.
- [ ] Impedir sortir del volum.
- [ ] Recuperar posicions invàlides.
- [ ] No implementar aerodinàmica completa.

## Canvi de mode

- [ ] Implementar botó SVG únic persona / avió i shortcut F.
- [ ] Sincronitzar icona, `aria-label`, tooltip i estat amb el mode real.
- [ ] Utilitzar SVG locals, sense CDN ni fonts d’icones externes.
- [ ] Conservar posició, azimut i FOV.
- [ ] Netejar velocitats incompatibles.
- [ ] Projectar sobre terreny en entrar a caminar via `TerrainSampler` + `GroundFollower`.
- [ ] Impedir canvi si no hi ha superfície segura.
- [ ] No recarregar recursos ni recalcular ciència.

## Bridge

- [ ] Definir missatges i camps tipats.
- [ ] Afegir correlació i generació.
- [ ] Aplicar coalescing.
- [ ] No enviar missatges per frame.
- [ ] Fer idempotents `set_camera_pose` i `set_navigation_mode`.
- [ ] Preservar pose en reconnectar.

## HUD i UI

- [ ] Afegir secció Navegació al calaix Ubicació.
- [ ] Afegir botó SVG d’alternança persona / avió.
- [ ] Afegir icona SVG de persona per `walk` i d’avió per `flight`.
- [ ] Sincronitzar el botó SVG amb la drecera F.
- [ ] Afegir reset.
- [ ] Mostrar posició, velocitat, altura i estat.
- [ ] Mostrar altura física sobre terreny i mode actual.
- [ ] Mostrar pitch i roll només en diagnòstic.
- [ ] No reconstruir tot el DOM per frame.
- [ ] No afegir panells flotants.

## Logging i lifecycle

- [ ] Instrumentar preparació, canvi de mode, inici/final, reset, límits i errors.
- [ ] Respectar format MGP i evitar logs per frame.
- [ ] Eliminar listeners, timers i estat de tecles en shutdown.
- [ ] Fer idempotents start, stop i dispose.
- [ ] Verificar arrencada-tancament-arrencada.

## Proves obligatòries

## Proves unitàries

- [ ] Conversió de yaw/pitch/roll a vectors.
- [ ] Normalització de moviment diagonal.
- [ ] Integració per `deltaTime`.
- [ ] Acceleració i frenada.
- [ ] Límits horitzontals i verticals.
- [ ] `TechnicalTerrainSampler` retorna altura correcta.
- [ ] `TechnicalTerrainSampler` retorna normal correcta.
- [ ] `TechnicalTerrainSampler` retorna pendent correcta.
- [ ] `TerrainSampler` rebutja mostres invàlides, NaN i infinits.
- [ ] `GroundFollower` manté exactament `eyeHeightM` sobre un pla.
- [ ] `GroundFollower` segueix una pujada.
- [ ] `GroundFollower` segueix una baixada sense flotació.
- [ ] `GroundFollower` no penetra després d’una pujada.
- [ ] `GroundFollower` accepta pendent caminable.
- [ ] `GroundFollower` rebutja pendent excessiva.
- [ ] `GroundFollower` accepta un step petit.
- [ ] `GroundFollower` rebutja un step excessiu.
- [ ] `GroundFollower` conserva `lastSafeGroundedPose` si falla el sampler.
- [ ] Projectar moviment sobre el pla tangent conserva direcció i velocitat esperades.
- [ ] `CameraVisualSmoother` no modifica la pose física.
- [ ] El smoothing visual redueix microoscil·lacions sense alterar grounding.
- [ ] Mode avió utilitza `TerrainSampler` per clearance i no `GroundFollower`.
- [ ] Canvi walk → flight.
- [ ] Canvi flight → walk.
- [ ] Reset.
- [ ] Coalescing i descart de generacions antigues.
- [ ] `NavigationController` depèn de `TerrainSampler`, no del raycaster concret.
- [ ] `GroundFollower` no importa `TechnicalTerrainSampler`.

## Proves d’integració

- [ ] Caminar endavant, lateralment i amb sprint seguint pujades i baixades.
- [ ] Verificar grounding exacte sobre terreny irregular.
- [ ] Verificar bloqueig davant pendent excessiva i step massa alt.
- [ ] Volar endavant, pujar i baixar.
- [ ] Aplicar roll i estabilitzar.
- [ ] Canviar de mode durant una sessió amb el botó SVG.
- [ ] Canviar de mode amb F i verificar sincronització de la icona.
- [ ] Impedir entrar a caminar sense superfície.
- [ ] Impedir travessar el terreny.
- [ ] Impedir sortir del volum.
- [ ] Reset en tots dos modes.
- [ ] Blur i visibilitychange amb tecles premudes.
- [ ] Reconnectar el bridge.
- [ ] Obrir i tancar calaixos durant el moviment.
- [ ] Canviar timeline, resize i shutdown durant el moviment.

## Rendiment

- [ ] Moviment equivalent a 30, 60 i 144 FPS.
- [ ] Frame P50 i P95 dins pressupost.
- [ ] Absència de retransferència de recursos.
- [ ] Absència de missatges Python per frame.
- [ ] Absència de reconstrucció de geometries.
- [ ] Absència de creixement continu de memòria.
- [ ] Cost de `sampleGround()` / raycast tècnic dins pressupost.

## Proves visuals

- [ ] Paral·laxi entre objectes pròxims i llunyans.
- [ ] Cel sense paral·laxi.
- [ ] Sobrevol del terreny.
- [ ] Canvi Caminar → Avió → Caminar amb botó SVG persona / avió.
- [ ] Caminada visualment suau sobre terreny irregular sense flotació ni penetració.
- [ ] Roll només en mode avió.
- [ ] HUD llegible.
- [ ] Captures a 1024×768 i 1920×1080.

---

## Criteri de sortida

- [ ] La càmera presenta translació real.
- [ ] El mode caminar funciona.
- [ ] El mode avió funciona.
- [ ] El canvi de mode és estable.
- [ ] El món local mostra paral·laxi i el cel no.
- [ ] El moviment és consistent entre FPS.
- [ ] La càmera no surt de la zona carregada.
- [ ] La càmera no travessa el terreny.
- [ ] Caminar manté físicament `groundHeightM + eyeHeightM` sobre qualsevol superfície vàlida.
- [ ] Caminar segueix pujades i baixades sense flotació ni penetració.
- [ ] El moviment caminant respecta pendent màxim i step màxim.
- [ ] El smoothing és exclusivament visual i no altera la pose física.
- [ ] `TerrainSampler` es pot substituir sense modificar `GroundFollower` ni `NavigationController`.
- [ ] El mode avió reutilitza `TerrainSampler` només per clearance / anti-penetració.
- [ ] El botó SVG persona / avió i la drecera F romanen sincronitzats.
- [ ] Volar permet ascens, descens i roll.
- [ ] El reset és exacte i segur.
- [ ] La navegació no recalcula ciència.
- [ ] La navegació no reenvia catàlegs.
- [ ] Python no rep missatges per frame.
- [ ] No es recrea l’escena ni la càmera.
- [ ] No hi ha tecles, timers o listeners pendents.
- [ ] Els logs MGP són útils i no excessius.
- [ ] Totes les proves passen.

---

## Evidència obligatòria

- [ ] Vídeo caminant i corrent sobre pujades i baixades.
- [ ] Vídeo demostrant grounding sense flotació ni penetració.
- [ ] Vídeo mostrant bloqueig per pendent excessiva o obstacle massa alt.
- [ ] Vídeo canviant a mode avió amb el botó SVG persona / avió i amb F.
- [ ] Vídeo sobrevolant, pujant, baixant i aplicant roll.
- [ ] Vídeo tornant a caminar sobre superfície segura.
- [ ] Vídeo movent-se amb la timeline activa.
- [ ] Prova que els recursos celestes no es retransferixen.
- [ ] Prova que Python no rep missatges a 60 Hz.
- [ ] Prova equivalent a 30, 60 i 144 FPS.
- [ ] Prova de blur, visibilitychange, límits, sostre i col·lisió.
- [ ] Mesures P50/P95.
- [ ] Prova d’arquitectura que substitueix un `TerrainSampler` fake sense canviar `GroundFollower`.
- [ ] Traça MGP de preparació, canvi de mode, inici i final.
- [ ] Captures del HUD en tots dos modes.

---

## Fora d’abast

- streaming infinit de terreny;
- reubicació geodèsica automàtica;
- aerodinàmica realista;
- gravetat física completa;
- vent, turbulència o combustible;
- col·lisions detallades amb edificis o vegetació;
- navmesh;
- DEM, ortofoto i cobertura finals;
- sistema complet de LOD i prefetch.

---

## Instrucció per a l’agent

1. Executa exclusivament el Pas 3.5.
2. Conserva íntegrament els Passos 1–3.
3. Utilitza TerraLab `main` només com a referència en mode lectura.
4. No converteixis el moviment local en reubicació científica.
5. No enviïs la càmera a Python per cada frame.
6. No facis polling de terreny a Python mentre l’usuari es mou.
7. No introdueixis streaming de tiles si no és necessari.
8. No implementis una simulació aeronàutica completa.
9. Mantén la UI equivalent a TerraLab.
10. No afegeixis controls visuals desconnectats.
11. Implementa el canvi de mode amb un botó SVG persona / avió; `F` és només la drecera equivalent.
12. No facis que `NavigationController` depengui de `TechnicalTerrainSampler` ni del raycaster concret.
13. No suavitzis la Y física per resoldre el grounding; la pose física queda exactament enganxada al terreny i el smoothing és només visual.
14. Reutilitza `TerrainSampler` tant en caminar com en vol, amb semàntiques diferents.
15. No implementis encara `DEMTerrainSampler`; deixa el contracte preparat.
16. No marquis cap casella sense evidència.
17. No comencis el Pas 4.
