# Pla d’implementació funcional pas a pas fins a la paritat amb TerraLab

Els noms d'arxius, mètodes, variables i comentaris sempre en català. Els comentaris han d'anar sempre en català. Hi ha variables i classes de "convencions" que sí que han d'estar en anglès, sinó seria estrany. El negoci propi sí que ha d'estar en català, esclareixo.

Reprodueix la mateixa UI i look and feel que E:\Desarrollo\TerraLab. Crec que l'arxiu de la UI és widget_controls_builder.py.

## Finalitat

Aquest pla converteix l’esquelet de TerraLab3D en una aplicació científica tridimensional completa, mantenint una separació estricta entre domini científic, aplicació, infraestructura, escena neutral i adaptador Three.js.

L’ordre està dissenyat perquè **cada pas deixi un avenç palpable, executable i observable**. No hi ha passos dedicats exclusivament a crear carpetes, interfaces, proves o infraestructura sense una funcionalitat connectada al producte.

“Homologable amb TerraLab” significa que cada comportament visible i cada càlcul científic rellevant de TerraLab disposa d’una equivalència implementada, mesurada i acceptada a TerraLab3D. No significa reproduir el pipeline QPainter ni obtenir píxels idèntics.

## Font funcional i norma de consulta

El repositori de referència és:

```text
E:\Desarrollo\TerraLab
```

Aquest repositori s’utilitza **només en mode lectura** per consultar:

- el comportament visible actual;
- els controls i valors per defecte;
- les fórmules i transformacions científiques;
- els catàlegs, manifests i datasets;
- els casos límit i modes de reserva;
- les eines interactives;
- les proves existents;
- les polítiques de cancel·lació, caché i memòria;
- els formats persistents que s’hagin de migrar.

La branca `fromcpu_togpu` de `github.com/ArcadiaLliure/TerraLab` s’ha utilitzat per confeccionar aquest pla. Abans de cada pas, l’agent ha de tornar a inspeccionar el checkout local real de `E:\Desarrollo\TerraLab`; el codi actual preval sobre aquest document quan hi hagi divergències.

No es pot modificar, reformatar, moure ni netejar cap fitxer de `E:\Desarrollo\TerraLab`.

## Regles d’execució

1. Cada pas lliura una vertical funcional executable des de l’entrypoint oficial.
2. Cap pas es considera acabat només perquè compili o perquè els seus tests aïllats passin.
3. Cada capacitat nova ha d’estar connectada a la ruta real Python → bridge → Three.js.
4. La càmera, la projecció a pantalla, la interpolació i el render continu viuen al frontend.
5. La ciència autoritativa, la selecció de dades i les decisions de negoci viuen al domini o a l’aplicació Python.
6. Els recursos grans són persistents, binaris, versionats i amb propietari explícit.
7. No s’envien catàlegs, malles o textures completes per cada frame o canvi de segon.
8. No s’utilitza Base64 per a Gaia, DEM, malles, ortofotos, Via Làctia o Planck.
9. Cada migració parteix d’una caracterització del comportament actual de TerraLab.
10. Les diferències intencionals requereixen justificació, evidència i acceptació.
11. No es creen implementacions falses que retornin dades inventades per fer passar la UI.
12. Els modes de reserva han de ser explícits i visibles per a l’usuari.
13. Cada operació asíncrona utilitza correlació, cancel·lació i descart de resultats obsolets.
14. Cada recurs GPU té un cicle de vida i un `dispose` verificable.
15. Cap càlcul científic pot quedar dins d’un shader, component UI o renderer Three.js.
16. Cap adaptador de dades pot decidir visibilitat científica o comportament de producte.
17. Cada pas manté TerraLab3D arrancable, usable i preparat per al pas següent.
18. No s’anticipa una capacitat posterior excepte quan sigui estrictament necessària per completar la vertical actual.

## Treball transversal obligatori dins de cada pas

Aquestes activitats no són passos separats. S’executen dins de cada vertical funcional:

- [ ] Identificar el comportament equivalent a TerraLab.
- [ ] Localitzar els símbols i fitxers font a `E:\Desarrollo\TerraLab`.
- [ ] Classificar cada element com `REUSE`, `EXTRACT`, `ADAPT`, `REWRITE`, `DISCARD` o `NEW`.
- [ ] Definir els contractes tipats estrictament necessaris per a la vertical.
- [ ] Implementar la ruta executable completa.
- [ ] Afegir proves unitàries del domini.
- [ ] Afegir proves d’integració del bridge i del frontend quan pertoqui.
- [ ] Afegir una comprovació manual reproduïble.
- [ ] Mesurar rendiment, memòria i bytes del bridge quan la vertical afecti render o dades.
- [ ] Documentar errors, fallback i lifecycle.
- [ ] Actualitzar la matriu de paritat.
- [ ] Actualitzar el mapa TerraLab → TerraLab3D.
- [ ] Confirmar que no s’han introduït dependències de capa incorrectes.
- [ ] Confirmar que la funcionalitat no depèn d’una ruta de demo o d’un mock.

## Matriu de cobertura de les 24 funcionalitats agrupades

| # | Funcionalitat agrupada | Passos principals |
| ---: | --- | --- |
| 1 | Ubicació de l’observador | 2 |
| 2 | Data i temps astronòmic | 3 |
| 3 | Navegació per l’escena | 1, 4 |
| 4 | Fons del cel | 6 |
| 5 | Estrelles i Gaia | 5 |
| 6 | Traces circumpolars | 14 |
| 7 | Sistema solar | 8, 9 |
| 8 | Via Làctia i pols Planck | 10 |
| 9 | Cel profund NGC/IC | 11 |
| 10 | Cerca astronòmica | 12 |
| 11 | Contaminació lumínica | 7 |
| 12 | Meteorologia i atmosfera | 6, 18 |
| 13 | Horitzó | 15 |
| 14 | Topografia i relleu | 16 |
| 15 | Superfície del terreny | 17 |
| 16 | Simulació de telescopi i càmera | 19 |
| 17 | Format del camp instrumental | 19 |
| 18 | Simulació fotogràfica | 20 |
| 19 | Selecció i inspecció | 13 |
| 20 | Eines de mesura | 21 |
| 21 | Constel·lacions editables | 22 |
| 22 | Capes i visibilitat | 23 |
| 23 | Gestió de dades i recursos | 23 |
| 24 | Preferències, estat, feedback i recuperació | 23, 24 |

## Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js

### Resultat funcional palpable

En executar `python -m terralab3d`, s’obre una aplicació real amb una escena Three.js 360°, una càmera navegable, un horitzó tècnic, punts cardinals i comunicació bidireccional amb Python.

### Fonts TerraLab a consultar

- `TerraLab/__main__.py` i bootstrap actual
- `TerraLab/runtime/supervisor.py`
- `TerraLab/runtime/render_service.py`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/ui/canvas_mixins/interaction.py`
- `TerraLab/scene/camera.py` i `TerraLab/scene/projection.py`
- `TerraLab/render/threejs/*` i contractes actuals del host

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [x] Definir l’entrypoint oficial `python -m terralab3d` i una única seqüència d’arrencada.
- [x] Escollir i implementar un host d’escriptori concret per al frontend Three.js sense crear dues rutes permanents.
- [x] Arrencar el backend Python, el frontend i el bridge amb ports locals assignats de manera segura.
- [x] Implementar un handshake tipat amb `frontend_ready`, versió de protocol, capacitats i identificador de sessió.
- [x] Crear `ThreeSceneHost` amb `Scene`, `PerspectiveCamera`, `WebGLRenderer` i un únic canvas.
- [x] Definir la convenció de món: eix vertical, nord, est, azimut, altitud i sentit de rotació.
- [x] Mostrar un horitzó tècnic circular, punts N/E/S/O, zenit i una primitiva de diagnòstic.
- [x] Implementar pan/orbit, zoom per FOV, límits verticals, teclat i redimensionament.
- [x] Mantenir el moviment i el render de càmera completament locals a TypeScript.
- [x] Publicar `camera_changed` a Python només al final del gest o amb throttling/coalescing.
- [x] Permetre que Python enviï `set_camera_pose` i `focus_direction` amb transició visual.
- [x] Implementar `viewport_resized`, `bridge_error`, `shutdown_requested` i `shutdown_complete`.
- [x] Gestionar desconnexió, reconexió controlada i missatge d’error visible en comptes d’una pantalla negra.
- [x] Alliberar listeners, timers, sockets, renderer, geometries i materials en tancar.
- [x] Afegir una pantalla de diagnòstic mínima amb estat del bridge, FPS i generació de sessió.

### Criteri de sortida

L’aplicació s’obre des de Python, la càmera es mou i fa zoom amb fluïdesa sense esperar el backend, Python pot reposicionar-la, el resize no deforma la projecció, la pèrdua del bridge es mostra de manera explícita i el tancament no deixa processos, ports ni contextos WebGL vius.

### Evidència obligatòria

- [x] Vídeo o captura de l’arrencada, navegació, focus des de Python, resize i tancament.
- [x] Prova d’integració del handshake i dels missatges de càmera.
- [x] Prova de lifecycle amb arrencada-tancament-arrencada.
- [x] Mètriques de frame P50/P95 en l’escena tècnica.
- [x] Comptador que demostri zero round-trips Python per frame de càmera.

### Fora d’abast del pas

No inclou encara coordenades astronòmiques, estrelles, cel físic, terreny real ni recursos binaris grans.

## Pas 2 — Ubicació geogràfica de l’observador i orientació local

La UI permet introduir latitud, longitud i alçada addicional; l’escena mostra la ubicació activa, orienta correctament els punts cardinals i manté l’estat en canviar la càmera.

### Fonts TerraLab a consultar

- `TerraLab/ui/widget_controls_builder.py` — latitud, longitud, reubicació i alçada addicional
- `TerraLab/terrain/terrain_coordinator.py` — consulta d’elevació
- `TerraLab/application/commands.py` i `controller.py`
- `TerraLab/scene/contracts.py` — `Observer`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [x] Implementar el model immutable d’ubicació geodèsica amb unitats i rangs explícits.
- [x] Implementar la comanda `SetObserverLocation` i el cas d’ús de reubicació.
- [x] Crear un panell funcional amb latitud, longitud, alçada addicional i acció de reubicar.
- [x] Validar latitud [-90, 90], longitud normalitzada i valors finits.
- [x] Mostrar l’altitud del terreny com a pendent fins que existeixi el port DEM, sense inventar-la.
- [x] Calcular l’alçada efectiva com elevació coneguda més offset de l’observador.
- [x] Orientar el marc local Three.js perquè nord, est, sud i oest coincideixin amb la convenció astronòmica.
- [x] Mostrar un HUD discret amb coordenades, alçada efectiva i font de l’elevació.
- [x] Persistir temporalment l’estat de sessió dins del backend, sense afegir encara persistència en disc.
- [x] Fer que canviar ubicació publiqui un delta petit, no una reconstrucció del host.
- [x] Definir un error visible per coordenades invàlides o elevació no disponible.
- [x] Caracteritzar els valors per defecte i el comportament de reubicació de TerraLab.

### Criteri de sortida

L’usuari pot canviar d’ubicació, veure les coordenades i l’alçada efectiva, i comprovar visualment que el sistema local i els punts cardinals s’actualitzen sense reiniciar l’escena.

### Evidència obligatòria

- [x] Proves de validació i normalització geogràfica.
- [x] Prova d’integració UI → Python → delta → escena.
- [x] Comprovació manual amb almenys tres ubicacions i hemisferis diferents.
- [x] Registre del nombre de bytes enviats en una reubicació.

### Fora d’abast del pas

No calcula encara un perfil d’horitzó ni carrega DEM.

## Pas 3 — Rellotge de simulació, temps sideral i moviment visible de la volta celeste

### Resultat funcional palpable

La UI disposa de timeline, data, dia anterior/següent i mode temps real; en moure l’hora, una volta celeste de referència gira correctament al voltant de l’eix polar.

### Fonts TerraLab a consultar

- `TerraLab/ui/time_bar.py`
- `TerraLab/ui/widget_mixins/controls_time.py`
- `TerraLab/astro/engine.py`
- `TerraLab/scene/projection.py`
- `TerraLab/application/controller.py`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [x] Definir `SimulationInstant`, mode pausat/temps real/simulat i factor de velocitat.
- [x] Implementar comandes de data, hora, dia anterior, dia següent, temps real i velocitat.
- [x] Implementar dia julià, segles julians i temps sideral local amb convencions documentades.
- [x] Construir una timeline de 24 hores amb marcador arrossegable i feedback immediat.
- [x] Mostrar data i hora actuals amb selector de calendari.
- [x] Implementar un rellotge autoritatiu Python amb ticks desacoblats del FPS.
- [x] Enviar al frontend només temps autoritatiu, angle sideral i paràmetres derivats necessaris.
- [x] Interpolar la rotació sideral al frontend entre actualitzacions autoritatives.
- [x] Crear una esfera o node de referència amb meridians celestes per visualitzar el moviment.
- [x] Fer que arrossegar la timeline sigui fluid amb política latest-wins.
- [x] Evitar que un canvi d’un segon recreï càmera, escena o recursos persistents.
- [x] Gestionar salts temporals grans sense interpolacions absurdes.
- [x] Comparar valors de temps sideral i orientació amb TerraLab en dates representatives.

### Criteri de sortida

La timeline i el mode temps real funcionen; la volta de referència es mou de manera contínua i correcta; un tick ordinari només actualitza transforms/uniforms i no recrea objectes Three.js.

### Evidència obligatòria

- [ ] Assertions numèriques de JD i LST.
- [ ] Vídeo de timeline, temps real i acceleració.
- [ ] Traça de deltes que demostri que no s’envien recursos grans.
- [ ] Mesura P50/P95 durant arrossegament temporal.

### Fora d’abast del pas

No inclou encara estrelles reals ni efemèrides de cossos.

## Pas 3.5 — Càmera translacional, mode caminar i mode avió

### Resultat funcional palpable

L’usuari pot desplaçar-se físicament per l’escenari tridimensional, no només girar sobre el punt d’origen.

La càmera disposa de dos modes:

- ****Caminar:**** exploració local vinculada a la superfície, amb altura d’ulls i col·lisió amb el terreny.
- ****Avió:**** vol lliure tridimensional amb ascens, descens, pitch, yaw, roll i control de velocitat.

Els objectes pròxims mostren paral·laxi real. El terreny i els objectes locals reaccionen a la translació; el cel astronòmic es manté a distància infinita i no presenta paral·laxi.

Caminar o volar no recalcula automàticament la ubicació astronòmica, el temps sideral, les efemèrides, Gaia, la Via Làctia, NGC, la contaminació lumínica ni els datasets geogràfics.

### Fonts a consultar

#### TerraLab**`main`**, només en mode lectura

- `TerraLab/ui/astro_canvas.py`
- `TerraLab/ui/canvas_mixins/interaction.py`
- `TerraLab/ui/widget_init_helpers.py`
- `TerraLab/scene/camera.py`, si existeix
- `TerraLab/scene/projection.py`, si existeix
- proves de càmera, interacció, projecció i lifecycle

#### TerraLab3D

- controlador de càmera;
- render loop;
- host Three.js;
- arbre de l’escena;
- contractes del bridge;
- HUD;
- listeners de teclat i ratolí;
- resize, focus, `visibilitychange` i shutdown;
- terreny tècnic i proves de les fases 1–3.

### Objectiu

Afegir translació tridimensional real a la càmera mitjançant un sistema local en metres, amb mode caminar i mode avió, sense alterar l’autoritat científica de Python ni introduir recàlculs científics durant la navegació.

La fase ha de preparar l’arquitectura futura de DEM, malles, picking de superfície, col·lisions, LOD, prefetch i reubicació explícita de l’observador.

---

### Separació obligatòria entre observador i càmera

### Observador científic

Determina latitud, longitud, elevació, alçada addicional, zona horària, temps sideral, efemèrides, horitzó, contaminació lumínica i selecció geogràfica de dades.

```ts
interface ScientificObserver {
  latitudeDeg: number;
  longitudeDeg: number;
  terrainElevationM: number | null;
  observerOffsetM: number;
}
```

### Càmera visual

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

### Convenció espacial

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

### Decisions arquitectòniques de navegació i terreny

#### Decisió #6 — `TerrainSampler` és el punt d’extensió crític del terreny

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

#### Decisió #7 — Grounding físic exacte i seguiment d’orografia

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

### Arbre de l’escena

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

### Zona local precarregada

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

### Estats de càrrega

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

### Política inicial de prefetch

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

### Mode caminar

### Comportament

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

### Controls

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

### Seguiment del terreny i grounding

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

## Mode avió---

## Mode avió

### Comportament

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

### Controls recomanats

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

Per a aquesta fase es recomana ****vol lliure****:

- W/S: moviment endavant i enrere;
- A/D: strafe;
- Espai/Ctrl: vertical;
- ratolí: yaw/pitch;
- Q/E: roll visual;
- X: anul·lar velocitat i estabilitzar.

Això deixa preparada una evolució posterior cap a un mode d’avió amb empenta contínua.

### Altura i col·lisions

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

### Roll### Roll

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

### Caminar → avió

- conservar posició, azimut i FOV;
- conservar pitch dins dels límits;
- inicialitzar roll a zero;
- inicialitzar velocitat segura;
- desactivar altura d’ulls;
- no recarregar recursos.

### Avió → caminar

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

### UI

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

### Integració temporal---

### Integració temporal

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

### Cel astronòmic

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

### Autoritat i bridge

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

### HUD

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

### Logging MGP

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

### Caracterització

- [ ] Revisar la càmera actual de TerraLab3D.
- [ ] Revisar el render loop i la convenció d’eixos.
- [ ] Revisar els listeners de teclat i ratolí.
- [ ] Revisar el contracte actual de `camera_pose`.
- [ ] Revisar focus, blur, visibilitychange i shutdown.
- [ ] Documentar les diferències respecte de TerraLab `main`.

### Model d’estat

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

### Arbre Three.js### Arbre Three.js

- [ ] Crear o consolidar `celestialRoot`, `worldRoot` i `overlayRoot`.
- [ ] Crear `cameraRig` amb yaw, pitch i roll.
- [ ] Evitar translació del cel.
- [ ] Aplicar translació al món local.
- [ ] Preservar l’escena persistent.
- [ ] Evitar recrear geometries i materials durant el moviment.

### Zona navegable i superfície

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

### Input### Input

- [ ] Implementar WASD, Shift, Espai, Ctrl, Q/E, X, R i F.
- [ ] Ignorar tecles amb inputs o modals actius.
- [ ] Gestionar blur, visibilitychange, canvi de mode i shutdown.
- [ ] Evitar scroll accidental i tecles enganxades.

### Integració temporal

- [ ] Utilitzar i limitar `deltaTime`.
- [ ] Normalitzar moviment diagonal.
- [ ] Implementar acceleració, frenada i velocitat màxima.
- [ ] Evitar dependència del FPS i salts després de pauses.

### Mode caminar

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

### Canvi de mode

- [ ] Implementar botó SVG únic persona / avió i shortcut F.
- [ ] Sincronitzar icona, `aria-label`, tooltip i estat amb el mode real.
- [ ] Utilitzar SVG locals, sense CDN ni fonts d’icones externes.
- [ ] Conservar posició, azimut i FOV.
- [ ] Netejar velocitats incompatibles.
- [ ] Projectar sobre terreny en entrar a caminar via `TerrainSampler` + `GroundFollower`.
- [ ] Impedir canvi si no hi ha superfície segura.
- [ ] No recarregar recursos ni recalcular ciència.

### Bridge

- [ ] Definir missatges i camps tipats.
- [ ] Afegir correlació i generació.
- [ ] Aplicar coalescing.
- [ ] No enviar missatges per frame.
- [ ] Fer idempotents `set_camera_pose` i `set_navigation_mode`.
- [ ] Preservar pose en reconnectar.

### HUD i UI

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

### Logging i lifecycle

- [ ] Instrumentar preparació, canvi de mode, inici/final, reset, límits i errors.
- [ ] Respectar format MGP i evitar logs per frame.
- [ ] Eliminar listeners, timers i estat de tecles en shutdown.
- [ ] Fer idempotents start, stop i dispose.
- [ ] Verificar arrencada-tancament-arrencada.

## Proves obligatòries

### Proves unitàries

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

### Proves d’integració

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

### Rendiment

- [ ] Moviment equivalent a 30, 60 i 144 FPS.
- [ ] Frame P50 i P95 dins pressupost.
- [ ] Absència de retransferència de recursos.
- [ ] Absència de missatges Python per frame.
- [ ] Absència de reconstrucció de geometries.
- [ ] Absència de creixement continu de memòria.
- [ ] Cost de `sampleGround()` / raycast tècnic dins pressupost.

### Proves visuals

- [ ] Paral·laxi entre objectes pròxims i llunyans.
- [ ] Cel sense paral·laxi.
- [ ] Sobrevol del terreny.
- [ ] Canvi Caminar → Avió → Caminar amb botó SVG persona / avió.
- [ ] Caminada visualment suau sobre terreny irregular sense flotació ni penetració.
- [ ] Roll només en mode avió.
- [ ] HUD llegible.
- [ ] Captures a 1024×768 i 1920×1080.

---

### Criteri de sortida

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

### Evidència obligatòria

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

### Fora d’abast

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

### Instrucció per a l’agent

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
16. No marquis cap checkbox sense evidència.
17. No comencis el Pas 4.

## Pas 4 — Grid celeste, brúixola, etiquetes i HUD astronòmic

### Resultat funcional palpable

L’entorn 3D mostra una quadrícula azimut-altura útil, brúixola, zenit, horitzó, etiquetes legibles i HUD configurable mentre la càmera i el temps es mouen.

### Fonts TerraLab a consultar

- `TerraLab/render/grid_renderer.py`
- `TerraLab/render/overlays_renderer.py`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/scene/projection.py`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [x] Definir geometria renderer-neutral per a grid horitzontal i referències principals.
- [x] Implementar línies d’azimut, cercles d’altitud, horitzó i marca de zenit.
- [x] Implementar etiquetes N/E/S/O i valors angulars amb orientació llegible.
- [x] Aplicar densitat adaptativa segons FOV per evitar soroll visual.
- [x] Evitar regenerar tota la geometria quan només canvia la càmera.
- [x] Implementar culling d’etiquetes i prevenció de solapaments bàsica.
- [x] Afegir toggles per grid, brúixola, labels i HUD.
- [x] Mostrar azimut, altitud i FOV actuals al HUD.
- [x] Fer que les etiquetes mantinguin una mida coherent amb DPR i resize.
- [x] Definir una capa overlay separada dels objectes celestes.
- [x] Afegir mode de colors purs/diagnòstic per verificar geometria i contrast.
- [x] Comparar orientació, densitat i convencions amb TerraLab.

### Criteri de sortida

La navegació ja és espacialment comprensible: l’usuari pot orientar-se, llegir azimut/altitud i activar o desactivar overlays sense canviar l’estat científic.

### Evidència obligatòria

- [x] Captures amb diferents FOV, DPR i orientacions.
- [x] Prova que moure càmera no reconstrueix buffers estàtics del grid.
- [x] Proves de convencions angulars i punts cardinals.

### Fora d’abast del pas

No inclou catàlegs astronòmics.

## Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents

### Resultat funcional palpable

La volta celeste mostra estrelles reals de Gaia o del catàleg fallback, amb posició, magnitud, color, mida, puntes i rotació sideral fluida.

### Fonts TerraLab a consultar

- `TerraLab/data/star_data_coordinator.py`
- `TerraLab/data/star_catalog_store.py`
- `TerraLab/data/tile_manifest.py`
- `TerraLab/data/catalogs/star_catalog.py`
- `TerraLab/scene/plans/stars.py`
- `TerraLab/render/stars_renderer.py`
- `TerraLab/data/layer_manager.py` — `SKY_STARS`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [x] Definir registres i columnes tipades per RA, Dec, magnitud, BP-RP/color i identificador.
- [x] Implementar `StarCatalogPort` amb catàleg general, fallback i consultes de con.
- [x] Preservar la política out-of-core, generacions, cancel·lació i last-request-wins.
- [x] Preservar pressupostos de caché per bytes i eviction de tiles no actius.
- [x] Convertir el catàleg a buffers binaris transferibles sense còpies innecessàries.
- [x] Registrar cada catàleg o tile com a recurs amb ID, versió, owner i mida.
- [x] Construir `BufferGeometry` persistent amb atributs separats de posició, magnitud, color i ID.
- [x] Implementar shader de punt circular o PSF suau; prohibir estrelles quadrades.
- [x] Implementar escala de mida, magnitud límit i llindar de puntes de difracció.
- [x] Mantenir les posicions estel·lars fixes en el marc celeste i rotar un node pare.
- [x] Mostrar estat de Gaia, fallback, extensió i errors de catàleg a la UI.
- [x] Implementar càrrega progressiva sense fer desaparèixer el catàleg general.
- [x] Evitar retransferir buffers quan canvia la càmera, el temps o un uniform visual.
- [x] Caracteritzar recompte, color, ordenació i màxim de magnitud de TerraLab.

### Criteri de sortida

Les estrelles són reals, suaus i fluides; Gaia/fallback és visible; el catàleg es transfereix una sola vegada per versió; canviar un segon o moure càmera només altera transforms o uniforms.

### Evidència obligatòria

- [x] Recompte i hash dels buffers carregats.
- [x] Captures de magnituds i colors representatius.
- [x] Mesures de temps de càrrega, RSS, memòria GPU estimada i bytes del bridge.
- [x] Prova de cancel·lació d’una consulta de con obsoleta.
- [x] Vídeo de navegació i timeline amb el catàleg carregat.

### Fora d’abast del pas

No inclou encara cel físic, contaminació lumínica ni picking final.

## Pas 6 — Sistema de picking estel·lar precís

### Resultat funcional palpable

Es pot fer clic de manera precisa i determinista sobre una estrella del camp cel·lar (Gaia o fallback). El marker de selecció screen-space segueix l'estrella seleccionada encara que la càmera es mogui, i la informació científica (identitat real de catàleg) es recupera al frontend sense readback de GPU, enviant només l'ID als sistemes rellevants.

### Fonts TerraLab a consultar

- `TerraLab/ui/astro_canvas.py` — click vs drag (pointer events), i les diferents generacions de picking.
- `TerraLab/ui/frame_presenter.py` — dispatch de picking.

### Objectiu

Aconseguir identificació estel·lar interactiva totalment desacoblada de l'estructura en GPU, confiant exclusivament en l'índex per recuperar la identitat al backend.

- [x] Crear els contractes tipats de picking (`star_picking_contracts.ts`)
- [x] Definir funcions compartides de mida de punt per calcular hit radius.
- [x] Extreure `CelestialTransformState` per compartir la matriu entre renderer i picker.
- [x] Modificar `StarFieldRenderer` per conservar `Uint32Array` canònic de catalogIndex.
- [x] Implementar `StarSpatialIndex` (cube-sphere hash) per queries de con ràpides.
- [x] Implementar `PointerGestureRouter` per diferenciar netament click vs drag sense capturar ratolí de més.
- [x] Implementar `StarPickProvider` per calcular ray, query, refinament i occlusions.
- [x] Afegir `SelectionMarker` screen-space.
- [x] Orquestrar-ho tot amb `ScenePickingController` incloent el resolving (latest-wins).
- [x] Afegir mètodes al pont WebSocket per `resolve_star_pick` i resposta de resolució.
- [x] Crear `StarPickResolver` al backend (O(1) lookups).
- [x] Modificar `StarCoordinator` al backend per retenir el batch en memòria per al resolutor.
- [x] Posar al HUD la informació bàsica (source_id, ra, dec, mag) de la selecció.
- [x] Preparar tests de Picking.

### Criteri de sortida

Es poden seleccionar estrelles denses del catàleg Gaia i el marker mai es perd en moure la càmera, demostrant un circuit de dades sencer.

### Evidència obligatòria

- [ ] Captura de vídeo fent pan i picking simultani.
- [ ] Tests superats demostrant que els ids en uint32 sobrepassen els problemes de float32 antics.

### Fora d’abast del pas

No inclou menús contextuals de target o GOTO automàtic.

> **Nota**: El "Pas 6" original (Cel diürn, nocturn, crepuscle i atmosfera visual contínua) s'ha mogut a l'annex per poder donar prioritat a aquest sistema de picking a petició de l'usuari.

## Pas 7 — Cel diürn/nocturn, crepuscle, atmosfera visual, contaminació lumínica, Bortle i magnitud límit

> **Nota**: Aquest pas fusiona l'antic annex (Cel diürn, nocturn, crepuscle i atmosfera visual contínua) amb l'antic Pas 7 (Contaminació lumínica, Bortle i magnitud límit). La fusió és intencionada perquè ambdós sistemes convergeixen en el mateix resultat: llum natural del cel + llum artificial + extinció atmosfèrica + magnitud límit = visibilitat astronòmica final.

### Resultat funcional palpable

El cel passa contínuament de dia a nit; existeixen crepuscles civil, nàutic i astronòmic; alba i posta són visuals i direccionals; zenit i horitzó tenen aspecte diferent; hi ha glow al voltant de la direcció solar; no hi ha quadrícules/tiles visibles; Bortle 1 i Bortle 9 són clarament diferents; mode Bortle funciona; mode magnitud manual funciona; mode automàtic funciona només si hi ha font real; les estrelles s'atenuen de manera contínua; les estrelles invisibles deixen de ser pickables; Gaia NO es reenvia; els buffers estel·lars NO es reconstrueixen; la translació local no recalcula atmosfera ni contaminació; camera rotation NO genera bridge calls.

### Fonts TerraLab a consultar

- `TerraLab/render/sky_renderer.py` — `sky_color_phys()` i `draw_background()`
- `TerraLab/light_pollution/bortle.py` — SQM→Bortle
- `TerraLab/light_pollution/mlim.py` — magnitud límit
- `TerraLab/light_pollution/modes.py` — modes automatic/bortle/magnitude
- `TerraLab/light_pollution/processing.py` — pipeline DVNL/SQM (referència, no portar)
- `TerraLab/widgets/visual_magnitude_engine.py` — motor fotomètric
- `TerraLab/widgets/physical_math.py` — math instrumental
- `TerraLab/ui/widget_controls_builder.py` — controls UI
- `TerraLab/ui/time_bar.py` — gradient solar

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Arquitectura

```text
Python domain
├── SolarSkyCalculator
├── LightPollutionModel
├── SkyVisibilityModel
└── SkyEnvironmentComposer
        ↓
SkyEnvironmentSnapshot (typed, generation)
        ↓
Bridge
        ↓
TypeScript
├── SkyEnvironmentState
├── AtmosphereRenderer (fullscreen shader pass)
├── StarVisibilityState (uniforms only)
└── UI/HUD
```

### Tasques

- [x] Implementar posició solar autoritativa (alt, az, ENU) reutilitzable pel futur Sistema Solar.
- [x] Implementar fases twilight categòriques (day/civil/nautical/astronomical/night).
- [x] Implementar twilight factor continu sense salts als boundaries.
- [x] Implementar shader analític continu del cel (zenith, horitzó, glow solar, antisolar, night floor).
- [x] Separar la llum natural del cel de la contaminació lumínica artificial.

- [x] Implementar l’estat tipat dels modes `automatic`, `bortle` i `magnitude`.
- [x] Implementar conversions Bortle ↔ magnitud límit i luminància amb unitats explícites.
- [x] Implementar controls equivalents i labels que canviïn segons el mode.
- [x] Aplicar el límit científic a la selecció o intensitat estel·lar sense reconstruir el catàleg complet.
- [x] Aplicar la brillantor de cel com a uniform de l’atmosfera.
- [x] Preparar els factors de contrast per Via Làctia i NGC.
- [x] Definir un port per a estimació geogràfica automàtica.
- [x] Mostrar clarament si el valor és manual, estimat, raster o fallback.
- [x] Implementar actualització en canviar ubicació o alçada.
- [x] Evitar oscil·lacions visuals quan una estimació remota o raster arriba tard.
- [x] Afegir casos de calibratge i toleràncies de magnitud.
- [x] Comparar classes Bortle i magnituds representatives amb TerraLab.

### Criteri de sortida

Canviar mode o valor produeix un efecte coherent i immediat; l’origen del valor és visible; les fórmules viuen al domini i Three.js només rep paràmetres finals.

### Evidència obligatòria

- [x] Captures Bortle 1, 4, 7 i 9.
- [x] Proves numèriques de conversió.
- [x] Prova de canvi automàtic en reubicar.
- [x] Traça que demostri absència de retransferència de Gaia.

### Fora d’abast del pas

La integració amb raster DVNL/SQM complet s’acaba al pas 23.

## Pas 8 — Sol, Lluna i planetes amb posicions i aparença reals

### Resultat funcional palpable

L’escena mostra Sol, Lluna i planetes en posicions topocèntriques, amb diàmetre aparent, fase, magnitud i toggles equivalents a TerraLab.

### Fonts TerraLab a consultar

- `TerraLab/astro/engine.py`
- `TerraLab/astro/ephemeris_coordinator.py`
- `TerraLab/scene/plans/bodies.py` si existeix al checkout
- `TerraLab/runtime/offscreen_renderer.py` — ruta actual de cossos
- `TerraLab/data/layer_manager.py` — sistema solar i fills

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir IDs i tipus de cos per Sol, Lluna i planetes.
- [ ] Implementar o adaptar un port d’efemèrides autoritatiu.
- [ ] Traslladar posició geocèntrica/topocèntrica, distància i coordenades aparents al domini.
- [ ] Implementar diàmetre angular, fase il·luminada i magnitud aparent.
- [ ] Crear entitats Three.js persistents amb transforms i materials compartits.
- [ ] Representar la Lluna amb terminador o paràmetres de fase coherents.
- [ ] Implementar toggles de sistema solar, Sol/Lluna i planetes.
- [ ] Aplicar oclusió sota l’horitzó pla actual i preparar la futura oclusió DEM.
- [ ] Implementar actualització per tick sense recrear geometria o textures.
- [ ] Mostrar informació bàsica del cos al HUD de diagnòstic.
- [ ] Definir fallback explícit quan falta l’efemèride principal.
- [ ] Verificar si hi ha suport executable de satèl·lits al checkout local; no inventar-lo si només apareix documentat.
- [ ] Comparar posicions, fases, mides i magnituds amb TerraLab.

### Criteri de sortida

Els cossos apareixen i es mouen correctament amb temps i ubicació; les fases i mides són visibles; no hi ha càlculs d’efemèrides al frontend.

### Evidència obligatòria

- [ ] Fixtures per Sol, Lluna i cada planeta.
- [ ] Captures de diverses fases lunars.
- [ ] Comparació angular amb TerraLab dins tolerància.
- [ ] Mesura de deltes per tick.

### Fora d’abast del pas

Eclipsis, contactes i trajectòries detallades arriben al pas següent.

## Pas 8.5 — Superfície lunar LRO/LOLA, orientació física i libració real

### Resultat funcional palpable

La Lluna deixa de ser un disc o una fotografia fixa i es representa com un cos esfèric persistent amb una **textura global neutra de la superfície lunar**, orientada físicament per a l’instant i l’observador actius.

La superfície visible utilitza dades del **NASA CGI Moon Kit** derivades de LRO/LROC i, per al relleu visual, LOLA. La fase i el terminador no estan incorporats a la textura: els genera el renderer a partir de la geometria Sol–Lluna–observador calculada al Pas 8.

En canviar la data, l’hora o la ubicació de l’observador:

- la Lluna manté la posició topocèntrica del Pas 8;
- varia la cara visible segons la libració;
- el nord lunar adopta l’orientació aparent correcta;
- la rotació respecte de l’horitzó local és correcta;
- el terminador manté l’orientació física correcta;
- quart creixent i quart minvant no són simples màscares invertides;
- un observador de l’hemisferi nord i un de l’hemisferi sud no veuen el disc amb la mateixa orientació respecte del seu horitzó;
- caminar, volar o aplicar roll a la càmera no modifica l’efemèride ni la libració científica.

La textura no es transfereix per bridge ni es recrea per tick.

### Fonts a consultar

#### TerraLab3D `main`

Revisar l’estat real del repositori abans d’implementar, especialment:

- `backend/src/terralab3d/__main__.py`
- `backend/src/terralab3d/domain/sky_background/sky_environment.py`
- `backend/src/terralab3d/infrastructure/websocket_bridge.py`
- `frontend/src/main.ts`
- `frontend/src/contracts/bridge_messages.ts`
- `frontend/src/view/three/ThreeSceneHostImpl.ts`
- `frontend/src/view/three/AtmosphereRenderer.ts`
- `frontend/src/view/ui/drawer_pages/SkyPage.ts`
- lifecycle, render loop, convenció ENU → Three.js i gestió actual de recursos persistents.

Després d’haver completat el Pas 8, revisar també els noms reals que finalment s’hagin creat per a:

- `EphemerisPort`;
- `SolarSystemSnapshot`;
- estat lunar;
- `SolarSystemRenderer`;
- renderer de la Lluna;
- contractes del sistema solar;
- missatge `solar_system_snapshot` o equivalent.

No pressuposis que aquests noms coincideixen exactament amb el prompt d’execució del Pas 8: preval el codi real de `main`.

#### TerraLab, només com a referència funcional

Consultar només quan aporti comportament científic o visual reutilitzable:

- `TerraLab/astro/engine.py`
- `TerraLab/astro/ephemeris_coordinator.py`
- `TerraLab/runtime/offscreen_renderer.py`
- tests de fases, orientació lunar o efemèrides que existeixin al checkout real.

No copiar una representació 2D de TerraLab si entra en conflicte amb el model persistent 3D de TerraLab3D.

#### Fonts externes obligatòries

**NASA Scientific Visualization Studio — CGI Moon Kit**

`https://svs.gsfc.nasa.gov/4720/`

Font visual preferent:

```text
lroc_color_16bit_srgb_8k.tif
8192 × 4096
```

És el mapa global de color LROC 2025 centrat a longitud 0°. S’utilitza com a **albedo visual base**, no com una fotografia d’una fase lunar concreta.

Fallback de menor resolució:

```text
lroc_color_16bit_srgb_4k.tif
4096 × 2048
```

Per al relleu visual es poden utilitzar els DEM LOLA distribuïts al mateix CGI Moon Kit, preferentment com a font per generar un normal map o height map runtime:

```text
ldem_16.tif
5760 × 2880
```

o, si el pipeline de generació ho justifica:

```text
ldem_64.tif
23040 × 11520
```

**RECORDATORI IMPORTANT: Caldrà obtenir aquest material mitjançant el gestor de capes, no pot estar guardat dins del workspace. Recorda que tot allò que tenim de capes de dades està emmagatzemat en la carpeta que seleccioni l'usuari la primera vegada que executi l'aplicació (en aquest equip de desenvolupament, de moment pots fer servir I:\TerraLab\data\sky\moon com a destí). Si l'usuari no descarrega aquesta capa, el fallback és el que ja s'ha fet en el Pas 8. Per tant, el que es fa en aquest pas no ha d'esborrar el que ja tenim implementat del Pas 8, simplement substituir la textura sempre i quan l'usuari l'hagi descarregat.**

IMPORTANT PER LA CAPA DE DADES, ELS CRÈDITS.
Crèdits:
NASA's Scientific Visualization Studio

    Visualizer
        Ernie Wright (USRA) ORCID logo. It consists of the text 'id' in lowercase inside of a green circle.
    Scientist
        Noah Petro (NASA/GSFC) ORCID logo. It consists of the text 'id' in lowercase inside of a green circle.

Datasets used

    DEM (Digital Elevation Map) [LRO: LOLA]
    Sensor: LOLA
    See all pages that use this dataset
    LROC WAC Color Mosaic (Natural Color Hapke Normalized WAC Mosaic) [Lunar Reconnaissance Orbiter: LRO Camera]
    Type: Mosaic Sensor: LRO Camera Collected by: Arizona State University

Cal respectar les unitats i el radi de referència documentats per NASA. No interpretar arbitràriament els valors del DEM.

**Skyfield — Planetary Reference Frames**

`https://rhodesmill.org/skyfield/planetary.html`

**NASA/JPL NAIF — Lunar orientation kernels**

`https://naif.jpl.nasa.gov/pub/naif/generic_kernels/`

Si el Pas 8 utilitza DE421, la implementació preferent d’orientació lunar és coherent amb:

```text
moon_080317.tf
moon_pa_de421_1900-2050.bpc
frame: MOON_ME_DE421
```

Si el Pas 8 acaba utilitzant una altra família d’efemèrides, utilitza els kernels d’orientació compatibles amb aquella família.

**No barregis una efemèride DE421 amb una orientació lunar d’una família incompatible sense justificació i validació explícites.**

### Objectiu

Substituir qualsevol representació lunar basada en un bitmap final, una màscara de fase 2D o una rotació manual per una representació separada en tres responsabilitats:

```text
Efemèride i orientació científica
→ determina on és la Lluna i com està orientada

Recurs lunar neutre
→ determina quin aspecte té la superfície

Renderer Three.js
→ aplica orientació + albedo + relleu visual + il·luminació solar
```

La regla central és:

```text
la textura no conté la fase;
la textura no determina la rotació;
la textura no determina la libració;
el shader no calcula efemèrides;
la càmera no modifica l’observador científic.
```

La precisió geomètrica ha de provenir de l’estat científic. El mapa LROC 2025 és un recurs visual i no s’ha de presentar com a producte fotomètric científic.

### Tasques

#### Dependència obligatòria del Pas 8

- [ ] Executar aquest pas només després que el Pas 8 estigui complet i estable.
- [ ] Reutilitzar la mateixa autoritat d’efemèrides del Pas 8.
- [ ] Reutilitzar el mateix Sol científic que governa atmosfera, disc solar i fase lunar.
- [ ] No crear un segon càlcul independent de Sol o Lluna només per al renderer.
- [ ] No modificar la semàntica de `ScientificObserver`.
- [ ] No convertir `CameraPose` en observador astronòmic.
- [ ] Mantenir la Lluna dins de `celestialRoot` perquè no presenti paral·laxi per translació de la càmera local.

#### Recurs lunar neutre i procedència

- [ ] Adoptar el NASA CGI Moon Kit com a font canònica del recurs visual lunar.
- [ ] Utilitzar com a font mestra preferent `lroc_color_16bit_srgb_8k.tif`.
- [ ] Conservar un fallback 4K per a maquinari o configuracions que no admetin 8K.
- [ ] No utilitzar la fotografia lunar aportada manualment com a textura científica de producció.
- [ ] No incorporar ombres, fase o terminador pre-renderitzats al recurs base.
- [ ] Crear un manifest versionat del recurs lunar amb, com a mínim:

```text
source
sourcePage
sourceFile
sourceVersion
acquisitionDate
sha256
projection
centralLongitudeDeg
colorSpace
generatedAsset
generatedAssetSha256
generatorVersion
credits
```

- [ ] Incloure el crèdit requerit a NASA Scientific Visualization Studio i documentar LRO/LROC i LOLA com a fonts.
- [ ] No fer descàrregues silencioses en runtime.
- [ ] No carregar TIFF de centenars de MB directament al navegador si existeix un derivat runtime més eficient.
- [ ] No guardar la textura en Base64 ni transportar-la dins de JSON.

#### Pipeline d’assets

- [ ] Crear un pipeline reproduïble que transformi el TIFF font en un recurs apte per GPU.
- [ ] Preferir KTX2 amb mipmaps per a la textura de producció quan el pipeline ho permeti.
- [ ] Si s’utilitza `KTX2Loader`, empaquetar localment els recursos necessaris del transcoder; no utilitzar CDN.
- [ ] Proporcionar fallback local 4K en un format suportat pel navegador si KTX2 no està disponible.
- [ ] Detectar `renderer.capabilities.maxTextureSize` abans de seleccionar 8K.
- [ ] No fer resize o recompressió costosa en cada arrencada.
- [ ] Generar els derivats una vegada i versionar-los amb hash.
- [ ] Tractar correctament l’albedo sRGB i fer els càlculs d’il·luminació en espai lineal.
- [ ] Si es genera un normal map des de LOLA, documentar resolució font, conversió, escala i versió del generador.
- [ ] No exagerar el relleu per defecte: l’escala visual científica és `1.0`.
- [ ] Si s’ofereix exageració visual, ha de ser opcional, explícita i marcada com a no científica.

#### Mapping cartogràfic i calibració fixa

- [ ] Tractar el mapa LROC com un mapa global equirectangular/cilíndric amb meridià central documentat a `0°`.
- [ ] Verificar amb les metadades de la font el sentit de longitud, orientació nord/sud, seam U i qualsevol flip necessari.
- [ ] No corregir la textura “a ull” amb una rotació dependent de la data.
- [ ] Separar la calibració estàtica del recurs de l’orientació dinàmica de la Lluna.

Estructura recomanada:

```text
moonRoot
└── moonBodyRoot                  ← orientació científica dinàmica
    └── moonSurfaceCalibration    ← transformació fixa del dataset
        └── moonSurfaceMesh       ← esfera + albedo + normal/height
```

- [ ] `moonSurfaceCalibration` només pot corregir la convenció fixa del dataset/UV.
- [ ] `moonBodyRoot` rep exclusivament l’orientació física calculada.
- [ ] Validar el mapping amb diversos accidents lunars identificables repartits per cara propera, vores i cara llunyana.
- [ ] Afegir tests que detectin textura invertida E/O, flip N/S o seam desplaçat 180°.

#### Orientació lunar científica

No implementar l’orientació aparent com una simple fórmula 2D de rotació de pantalla.

La representació 3D autoritativa ha de partir d’un frame lunar body-fixed i produir una transformació completa del cos.

Flux preferent:

```text
UTC
+ ScientificObserver
+ efemèride del Pas 8
+ lunar orientation kernel
→ frame lunar body-fixed
→ orientació body-fixed respecte ICRF
→ transformació ICRF → ENU de l’observador
→ orientació lunar topocèntrica
→ quaternion/matriu renderer-neutral
→ conversió ENU → Three.js
→ moonBodyRoot.quaternion
```

- [ ] Crear o adaptar un port científic d’orientació lunar sense dependències de Three.js.
- [ ] Carregar els kernels d’orientació una sola vegada.
- [ ] Validar el rang temporal del kernel.
- [ ] Fer el lifecycle idempotent.
- [ ] No deixar objectes Skyfield/SPICE fora de l’adapter d’infraestructura.
- [ ] Calcular la transformació completa body-fixed → frame local de l’observador.
- [ ] Incloure la libració física dins d’aquesta transformació.
- [ ] Incloure la component topocèntrica/diürna que depèn de la posició real de l’observador.
- [ ] No limitar-se a libració geocèntrica si això produeix una cara visible incorrecta per a observadors allunyats.
- [ ] No aplicar després un segon `parallacticAngle` si la matriu/quaternion ja està expressada en el frame horitzontal local; evitar doble rotació.
- [ ] El roll de la càmera ha d’afectar la imatge perquè la càmera gira, no perquè es recalculi l’orientació lunar.
- [ ] Caminar o volar amb el temps pausat ha de produir `0` nous càlculs d’orientació lunar.

Estat científic mínim recomanat:

```text
orientationFrame
orientationSource
orientationQuality
bodyToENUQuaternion
librationLongitudeDeg
librationLatitudeDeg
subEarthLongitudeDeg
subEarthLatitudeDeg
subObserverLongitudeDeg
subObserverLatitudeDeg
northPolePositionAngleDeg
brightLimbPositionAngleDeg
moonToSunDirectionENU
```

`subObserver*` és l’estat rellevant per validar la cara realment visible des de l’observador topocèntric.

#### Il·luminació, fase i terminador

La fase no es pinta amb alpha.

El renderer ha de determinar quins fragments estan il·luminats a partir de la normal de superfície i la direcció física cap al Sol.

Flux:

```text
albedo LROC
+ normal geomètrica
+ normal map LOLA opcional
+ Moon → Sun direction
→ il·luminació del fragment
→ terminador
→ disc lunar renderitzat
```

- [ ] Derivar la direcció d’il·luminació de la mateixa efemèride autoritativa del Pas 8.
- [ ] Utilitzar la direcció Sol vista des de la Lluna quan sigui necessari per orientar el terminador amb precisió.
- [ ] No reutilitzar cegament una direcció solar topocèntrica de l’observador si introdueix error geomètric en el terminador lunar.
- [ ] `illuminationFraction` continua sent un valor científic de diagnòstic, no una màscara d’alpha.
- [ ] `phaseAngle` continua sent un valor científic, no una rotació visual.
- [ ] `brightLimbPositionAngleDeg` s’utilitza per validar la geometria, no per substituir-la amb un sprite 2D.
- [ ] La cara nocturna no desapareix per geometria: continua existint però queda sense il·luminació solar directa.
- [ ] No afegir ambient arbitrari que destrueixi el terminador.
- [ ] Si s’afegeix llum de Terra en el futur, ha de ser un terme físic separat i explícit.

No és acceptable:

```text
foto de Lluna plena
× màscara de fase
× rotateZ(...)
```

Tampoc és acceptable:

```text
sprite
+ brightLimbPositionAngle
```

com a substitut permanent de la geometria 3D.

#### Renderer persistent

Crear o consolidar un renderer específic, conceptualment equivalent a:

```text
SolarSystemRenderer
└── MoonSurfaceRenderer
```

El nom concret s’ha d’adaptar al codi real del Pas 8.

- [ ] Crear geometria, material i textures una sola vegada.
- [ ] Reutilitzar el mateix `moonSurfaceMesh` durant timeline, temps real i canvis d’ubicació.
- [ ] Per snapshot només actualitzar:

```text
direction / transform
angular size
body quaternion
Moon → Sun direction
phase diagnostics
visibility
shader uniforms
```

- [ ] No recrear `SphereGeometry`.
- [ ] No recrear `ShaderMaterial`.
- [ ] No recarregar la textura.
- [ ] No re-pujar la textura a GPU per cada tick.
- [ ] No reconstruir mipmaps per cada tick.
- [ ] Mantenir `frustumCulled`, depth i render order coherents amb la resta del sistema solar.
- [ ] Disposar explícitament geometria, material, albedo, normal map i recursos KTX2 en shutdown.

#### Mida angular i geometria d’escena

- [ ] Conservar la mida angular calculada al Pas 8.
- [ ] No posicionar la Lluna a la distància real de centenars de milers de km dins de Three.js si l’arquitectura del Pas 8 utilitza cel aparent.
- [ ] Si s’utilitza un radi celeste arbitrari `D`, escalar l’esfera perquè compleixi:

```text
apparentAngularRadius = atan(renderRadius / D)
```

o una formulació equivalent validada.

- [ ] L’orientació de la superfície no pot dependre del radi celeste artificial escollit.
- [ ] La textura i el relleu visual no poden modificar la magnitud angular científica del disc.
- [ ] El normal map no pot deformar la silueta lunar usada científicament.

#### Bridge

Estendre el missatge lunar del Pas 8 amb un bloc petit d’orientació.

Exemple conceptual:

```text
solar_system_snapshot
└── moon
    ├── ...
    └── orientation
        ├── frame
        ├── source
        ├── quality
        ├── bodyToENUQuaternion
        ├── librationLongitudeDeg
        ├── librationLatitudeDeg
        ├── subEarthLongitudeDeg
        ├── subEarthLatitudeDeg
        ├── subObserverLongitudeDeg
        ├── subObserverLatitudeDeg
        ├── northPolePositionAngleDeg
        ├── brightLimbPositionAngleDeg
        └── moonToSunDirectionENU
```

- [ ] No enviar albedo, normal map, height map, TIFF, KTX2 ni cap asset gran pel bridge.
- [ ] No enviar una matriu i un quaternion redundants si un únic contracte és suficient.
- [ ] Mantenir `generation`, correlació, latest-wins i descart de resultats stale del Pas 8.
- [ ] Per salts temporals grans, aplicar l’estat nou sense una interpolació visual llarga a través d’orientacions incorrectes.
- [ ] Per ticks normals, permetre interpolació curta del quaternion al frontend amb `slerp`.

#### Integració amb l’arquitectura actual

- [ ] Adjuntar la Lluna al `celestialRoot` existent.
- [ ] Respectar la convenció actual:

```text
+X = East
+Y = Up
-Z = North
```

si continua sent la convenció real de `main`.

- [ ] Centralitzar una sola conversió de l’orientació ENU científica a coordenades Three.js.
- [ ] No introduir una segona convenció d’eixos dins del renderer lunar.
- [ ] Reutilitzar el render loop existent.
- [ ] Reutilitzar el lifecycle existent.
- [ ] No crear un segon canvas.
- [ ] No crear una escena Three.js separada només per a la Lluna.
- [ ] No fer polling Python des del frontend.

#### UI

Integrar-se dins de la jerarquia existent del calaix `Cel`:

```text
Sistema solar
├── Sol
├── Lluna
│   └── Superfície LRO/LOLA
└── Planetes
```

- [ ] La superfície LRO/LOLA queda activa per defecte si el recurs està disponible.
- [ ] Mostrar un estat compacte de recurs, per exemple:

```text
LRO 2025 8K
LRO 2025 4K fallback
surface unavailable
```

- [ ] Mostrar en diagnòstic la font d’orientació, per exemple:

```text
MOON_ME_DE421
```

- [ ] No afegir cap control de “rotació manual” de la Lluna.
- [ ] No afegir un panell flotant nou.
- [ ] Si el recurs visual falla, mantenir la Lluna funcional amb la representació geomètrica/fase del Pas 8 i mostrar fallback explícit.

#### Fallback honest

Si falta la textura LRO:

```text
posició lunar         → disponible
mida angular          → disponible
fase/terminador       → disponible si Pas 8 està disponible
orientació científica → disponible si kernels d’orientació estan disponibles
superfície LRO        → unavailable
```

Si falta el kernel d’orientació lunar:

```text
posició/fase Pas 8    → disponible
orientació body-fixed → unavailable
superfície precisa    → no declarar-la precisa
status                → partial
```

No inventar una rotació fixa “aproximada” i marcar-la com a científica.

Si la data queda fora del rang del kernel:

- [ ] detectar-ho explícitament;
- [ ] no extrapolar silenciosament;
- [ ] conservar la resta del sistema solar;
- [ ] informar `orientationQuality = unavailable/out_of_range`.

### Proves obligatòries

#### Ciència i orientació

- [ ] Fixtures d’orientació lunar per diverses UTC dins del rang del kernel.
- [ ] Fixtures independents de libració en longitud i latitud.
- [ ] Fixtures de `subObserverLongitudeDeg` i `subObserverLatitudeDeg`.
- [ ] Validació del position angle del pol nord lunar.
- [ ] Validació del bright limb position angle.
- [ ] Mateixa UTC i ubicacions molt separades → diferència topocèntrica coherent.
- [ ] Mateixa ubicació al llarg de la nit → orientació respecte de l’horitzó evoluciona contínuament.
- [ ] Hemisferi nord vs hemisferi sud → orientació aparent coherent.
- [ ] Camera roll → canvia la imatge a pantalla sense nou càlcul científic.
- [ ] Walk/flight amb temps pausat → `0` requests d’orientació lunar.
- [ ] Canvi de FOV → `0` requests d’orientació lunar.
- [ ] Resize → `0` requests d’orientació lunar.
- [ ] Canvi d’un segon → no recarrega kernels ni assets.
- [ ] Data fora de rang → fallback explícit.

#### Mapping de textura

- [ ] Meridià central correcte.
- [ ] Nord lunar no està invertit.
- [ ] Est/oest no estan invertits.
- [ ] Cara propera correcta.
- [ ] Cara llunyana correcta durant libracions extremes.
- [ ] Seam a ±180° sense discontinuïtat visual greu.
- [ ] Cap flip vertical accidental.
- [ ] Validació amb almenys quatre accidents lunars coneguts en posicions distribuïdes.
- [ ] El mapping no varia amb la data: només varia `moonBodyRoot`.

#### Fase i il·luminació

- [ ] Lluna nova.
- [ ] Creixent fi.
- [ ] Quart creixent.
- [ ] Gibosa creixent.
- [ ] Lluna plena.
- [ ] Gibosa minvant.
- [ ] Quart minvant.
- [ ] Minvant fi.
- [ ] El terminador és continu durant timeline.
- [ ] Creixent i minvant no són una simple inversió de textura.
- [ ] El costat il·luminat coincideix amb la geometria del Sol.
- [ ] L’orientació del terminador es conserva quan la Lluna rota aparentment respecte de l’horitzó.

#### Recursos i rendiment

- [ ] `moon_geometry_build_count` estable després de la inicialització.
- [ ] `moon_material_build_count` estable després de la inicialització.
- [ ] `moon_texture_load_count = 1` per recurs actiu.
- [ ] `moon_texture_upload_bytes` no augmenta per tick.
- [ ] `moon_bridge_texture_bytes = 0`.
- [ ] `moon_kernel_load_count = 1`.
- [ ] P50/P95 de frame abans i després d’activar la superfície lunar.
- [ ] P50/P95 d’actualització d’orientació lunar.
- [ ] Memòria GPU documentada per 8K i fallback 4K.
- [ ] No hi ha creixement continu de memòria durant timeline.
- [ ] Shutdown allibera textures, material, geometria i loaders.
- [ ] Arrencada → tancament → arrencada funciona sense duplicar recursos.

### Criteri de sortida

El Pas 8.5 no es considera complet fins que:

- [ ] la Lluna utilitza un albedo global neutre LRO i no una fotografia d’una fase concreta;
- [ ] la fase no està incorporada a la textura;
- [ ] el terminador prové de la geometria solar;
- [ ] l’orientació del cos prové d’un frame lunar científic;
- [ ] la libració modifica realment la cara visible;
- [ ] la diferència topocèntrica entre observadors està representada;
- [ ] la Lluna es veu correctament orientada respecte de l’horitzó local;
- [ ] no existeix un `textureCalibrationOffset` dependent de la data;
- [ ] qualsevol transformació fixa del dataset està separada de la rotació científica;
- [ ] la càmera local no recalcula la Lluna;
- [ ] el roll de càmera no modifica l’estat científic;
- [ ] no s’envien textures pel bridge;
- [ ] no es recreen geometries, materials ni textures per tick;
- [ ] 8K/4K es seleccionen de manera segura segons capacitats;
- [ ] el fallback és explícit;
- [ ] les proves científiques, visuals, de lifecycle i rendiment passen;
- [ ] els Passos 1–8 continuen funcionant;
- [ ] el Pas 9 encara no s’ha començat.

### Evidència obligatòria

- [ ] Manifest del recurs LRO/LOLA amb URL font, versió i SHA-256.
- [ ] Hash dels assets runtime generats.
- [ ] Documentació de la projecció i convenció UV.
- [ ] Documentació del frame lunar utilitzat i kernels carregats.
- [ ] Rang temporal validat dels kernels.
- [ ] Captura de Lluna plena amb accidents correctament situats.
- [ ] Captures de quart creixent i quart minvant.
- [ ] Captures de la mateixa UTC des de dos hemisferis.
- [ ] Captures de dates amb libracions clarament diferents.
- [ ] Vídeo curt de timeline mostrant fase, terminador i orientació contínues.
- [ ] Prova numèrica de libració i sub-observer point.
- [ ] Prova que caminar/volar no genera requests lunars.
- [ ] Prova que la textura s’ha pujat una sola vegada a GPU.
- [ ] Mètriques P50/P95.
- [ ] Mètriques de memòria GPU 8K/4K.
- [ ] Prova de fallback sense asset LRO.
- [ ] Prova de fallback sense kernel d’orientació.
- [ ] Prova de shutdown i reinici.

### Fora d’abast del pas

Aquest pas no implementa:

- eclipsis solars o lunars;
- contactes d’eclipsi;
- ocultacions;
- separacions angulars i trajectòries del Pas 9;
- silueta lunar deformada per muntanyes per calcular contactes;
- ray tracing o self-shadowing topogràfic complet entre cràters i muntanyes;
- malla lunar d’alta resolució amb milions de triangles;
- streaming de tiles lunars;
- textures locals NAC d’1 m/píxel;
- navegació sobre la superfície lunar;
- landing sites;
- selecció completa de cràters;
- cartografia científica interactiva;
- fotometria Hapke científica completa;
- earthshine físic complet;
- eclipsis projectats sobre la superfície;
- descàrregues de datasets en runtime.

Aquests elements no poden retardar ni contaminar el Pas 9.

La regla final del Pas 8.5 és:

```text
LRO/LOLA defineix la superfície;
JPL/Skyfield defineix l’orientació;
l’efemèride del Pas 8 defineix la geometria Sol–Lluna–observador;
Three.js només representa aquest estat amb recursos persistents.
```

## Pas 9 — Eclipsis, ocultacions, separacions i trajectòries

### Resultat funcional palpable

La simulació identifica i representa eclipsis solars/lunars, separacions angulars i trajectòries temporals dels cossos.

### Fonts TerraLab a consultar

- `TerraLab/astro/engine.py` — geometria d’eclipsi i separacions
- `TerraLab/runtime/offscreen_renderer.py` — fallback o composició actual
- `tests` d’eclipsis, fases i refracció

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Crear un paquet científic específic d’eclipsis i ocultacions.
- [ ] Implementar separació angular i intersecció de discs aparents.
- [ ] Implementar magnitud, obscuració i fase instantània d’eclipsi.
- [ ] Implementar cerca de màxim i contactes dins d’un interval.
- [ ] Representar l’ombra, penombra o superposició amb geometria/materials adequats.
- [ ] Mostrar estat de l’esdeveniment i temps fins al contacte al HUD.
- [ ] Implementar trajectòries opcionals de Sol, Lluna i planetes en un interval.
- [ ] Versionar la geometria de trajectòria i actualitzar-la només quan canvia l’interval.
- [ ] Gestionar esdeveniments no visibles des de la ubicació actual.
- [ ] Afegir toleràncies temporals i angulars explícites.
- [ ] Comparar esdeveniments coneguts amb TerraLab i una font astronòmica de referència.

### Criteri de sortida

Un cas d’eclipsi conegut es pot reproduir des de la UI temporal, els contactes i magnituds són coherents i les trajectòries no es recalculen per cada frame.

### Evidència obligatòria

- [ ] Fixtures d’eclipsi solar i lunar.
- [ ] Vídeo de l’esdeveniment a través de la timeline.
- [ ] Assertions de contactes, separacions i obscuració.
- [ ] Perfil de cost del càlcul i de la representació.

### Fora d’abast del pas

No inclou encara Via Làctia o NGC.

## Pas 10 — Via Làctia i pols galàctica Planck

### Resultat funcional palpable

La volta celeste mostra una Via Làctia orientada correctament i un mapa de pols Planck opcional, amb opacitat afectada pel cel i la contaminació lumínica.

### Fonts TerraLab a consultar

- `TerraLab/render/sky/milkyway_overlay.py`
- `TerraLab/data/layer_manager.py` — `SKY_MILKY_WAY` i `SKY_PLANCK_DUST`
- `TerraLab/data/assets/*` i manifests de recursos

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Identificar i validar els formats FITS/PNG i metadades de coordenades actuals.
- [ ] Definir descriptors versionats per textura de Via Làctia i mapa Planck.
- [ ] Implementar adaptadors de càrrega i conversió fora del domini.
- [ ] Definir orientació galàctica, offset RA, flips i frame de coordenades com a estat tipat.
- [ ] Carregar la textura una sola vegada per versió.
- [ ] Representar la Via Làctia en un skydome persistent.
- [ ] Aplicar opacitat, blend i extinció amb uniforms.
- [ ] Aplicar pols com densitat visual i/o extinció segons la semàntica caracteritzada.
- [ ] Mostrar estat de càrrega, recurs absent, fallback i errors.
- [ ] Implementar toggles independents de Via Làctia i Planck.
- [ ] Evitar qualsevol sampling de pantalla al backend.
- [ ] Comparar orientació i estructura reconeixible amb TerraLab.

### Criteri de sortida

La Via Làctia i Planck apareixen orientats correctament, responen a temps/Bortle sense retransferir textures i fallen de manera explícita si falta el recurs.

### Evidència obligatòria

- [ ] Captures en diverses orientacions i dates.
- [ ] Hash, versió i mida de textures.
- [ ] Mesura de bytes transferits i memòria GPU estimada.
- [ ] Prova de recurs absent i recuperació després d’instal·lar-lo.

### Fora d’abast del pas

No inclou encara els objectes NGC/IC.

## Pas 11 — Cel profund NGC/IC

### Resultat funcional palpable

Galàxies, nebuloses, cúmuls oberts i globulars apareixen amb tipus, dimensions, orientació, magnitud i visibilitat coherents.

### Fonts TerraLab a consultar

- `TerraLab/astro/ngc_catalog.py`
- `TerraLab/runtime/offscreen_renderer.py` — selecció i dibuix NGC
- `TerraLab/data/layer_manager.py` — `SKY_NGC`
- `TerraLab/astro/search_engine.py`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Adaptar el parser OpenNGC a entitats tipades amb ID, àlies, tipus i coordenades.
- [ ] Normalitzar galàxies, nebuloses, cúmuls oberts, globulars i altres tipus.
- [ ] Conservar eixos major/menor, angle de posició i magnitud quan existeixin.
- [ ] Implementar selecció per camp visible, magnitud i extinció.
- [ ] Preparar buffers o instàncies persistents per tipus visual.
- [ ] Definir símbols/materials Three.js diferenciats i escalables.
- [ ] Gestionar objectes sense magnitud o dimensions sense inventar valors científics.
- [ ] Implementar toggle i estat de dataset.
- [ ] Integrar els factors de contaminació lumínica i atmosfera.
- [ ] Fer que un canvi de FOV pugui canviar LOD/labels sense recarregar el catàleg.
- [ ] Comparar recompte, categories, posicions i aparença semàntica amb TerraLab.

### Criteri de sortida

El catàleg NGC és visible i filtrable, els tipus són distingibles, les dades incompletes es gestionen explícitament i el catàleg roman resident.

### Evidència obligatòria

- [ ] Fixtures d’almenys una galàxia, nebulosa i dos tipus de cúmul.
- [ ] Recompte de registres i hash de l’índex.
- [ ] Captures a diferents FOV i Bortle.
- [ ] Mesura de culling i draw calls.

### Fora d’abast del pas

La cerca unificada i el focus es completen al pas següent.

## Pas 12 — Cerca astronòmica, focus i seguiment

### Resultat funcional palpable

L’usuari pot cercar estrelles, planetes, Sol, Lluna, NGC o coordenades i orientar-hi la càmera o el scope.

### Fonts TerraLab a consultar

- `TerraLab/astro/search_engine.py`
- `TerraLab/ui/widget_controls_builder.py` — `txt_search`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/widgets/telescope_scope_mode.py` — RA/Dec

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Construir un índex unificat de noms, àlies i identificadors.
- [ ] Definir una sintaxi explícita per a coordenades RA/Dec.
- [ ] Implementar normalització, ranking i límit de resultats.
- [ ] Retornar resultats tipats amb ID, tipus, nom i coordenada.
- [ ] Crear una UI de resultats navegable amb estat buit i errors.
- [ ] Separar completament `search` de `focus`.
- [ ] Implementar focus suau de càmera a una direcció o coordenada.
- [ ] Implementar seguiment d’un objecte mentre avança el temps.
- [ ] Permetre alliberar el seguiment amb una acció explícita.
- [ ] Fer que la cerca continuï disponible si una capa visual està oculta.
- [ ] Gestionar resultats de datasets no instal·lats amb explicació accionable.
- [ ] Comparar àlies, prioritats i casos de cerca de TerraLab.

### Criteri de sortida

La cerca retorna resultats reals i la càmera pot enfocar o seguir qualsevol objecte suportat sense alterar catàlegs o reconstruir l’escena.

### Evidència obligatòria

- [ ] Proves de noms, àlies, coordenades i consultes ambigües.
- [ ] Vídeo de cerca → focus → seguiment → alliberament.
- [ ] Prova de dataset absent.

### Fora d’abast del pas

El click directe, hover i inspecció es completen al pas següent.

## Pas 13 — Picking real, hover, selecció i inspecció d’objectes

### Resultat funcional palpable

L’usuari pot passar el cursor i clicar estrelles, cossos, NGC i elements compatibles, veure’n informació i centrar-los.

### Fonts TerraLab a consultar

- `TerraLab/core/rendering_contracts/contracts.py` — `PickResult`
- `TerraLab/ui/astro_canvas.py` — gestió de resultats
- `TerraLab/runtime/offscreen_renderer.py` — picking actual
- `TerraLab/render/threejs/*` — picking existent o provisional

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir `PickRequest` i `PickResult` amb ID de petició i generació d’escena.
- [ ] Implementar picking real de Three.js; prohibir resultats sintètics o count-only.
- [ ] Implementar estratègia eficient per punts estel·lars i instàncies.
- [ ] Implementar hover amb throttling i prioritat entre capes.
- [ ] Rebutjar resultats de generacions obsoletes.
- [ ] Mantenir l’estat de selecció autoritatiu a l’aplicació.
- [ ] Mostrar ressaltat, pols o contorn sense recrear l’objecte.
- [ ] Crear un panell d’inspecció amb dades científiques disponibles.
- [ ] Afegir accions de focus, seguiment i neteja de selecció.
- [ ] Gestionar objectes ocults o recursos descarregats durant una selecció.
- [ ] Preparar extensió per terreny, mesures i constel·lacions.
- [ ] Comparar radi de selecció i comportament amb TerraLab.

### Criteri de sortida

Cada objecte visible important es pot seleccionar mitjançant geometria real; els resultats stale no alteren l’estat; la informació i el focus funcionen de punta a punta.

### Evidència obligatòria

- [ ] Proves d’ID/generació i descart stale.
- [ ] Vídeo de hover i selecció de cada tipus.
- [ ] Mesura de latència de picking P50/P95.
- [ ] Prova amb objectes superposats.

### Fora d’abast del pas

El picking de terreny i overlays s’afegirà amb les seves verticals.

## Pas 14 — Traces circumpolars i exposició temporal

### Resultat funcional palpable

L’usuari pot iniciar i aturar una simulació circumpolar, veure el temps acumulat i obtenir traces fluides centrades en el pol celeste corresponent.

### Fonts TerraLab a consultar

- `TerraLab/ui/widget_controls_builder.py` — botó i temps de trace
- `TerraLab/scene/contracts.py` — `TrailState`
- `TerraLab/runtime/offscreen_renderer.py` — acumulació actual
- `TerraLab/render/overlays_renderer.py` o plans equivalents

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir interval, inici, durada, pas temporal i magnitud límit de traces.
- [ ] Calcular la geometria des de coordenades celestes i rotació sideral.
- [ ] Evitar acumular captures raster o textures de pantalla.
- [ ] Crear buffers de línies persistents actualitzables incrementalment.
- [ ] Limitar nombre d’estrelles, segments i memòria.
- [ ] Implementar iniciar, pausar, reprendre, aturar i netejar.
- [ ] Mostrar temps acumulat i estat de l’exposició.
- [ ] Gestionar canvis d’ubicació o data durant una trace.
- [ ] Integrar tracking de muntura quan s’introdueixi la simulació fotogràfica.
- [ ] Aplicar color, opacitat i intensitat derivats de fotometria.
- [ ] Comparar forma i velocitat amb TerraLab.

### Criteri de sortida

Les traces es construeixen incrementalment, es poden controlar, no depenen de la resolució del canvas i no degraden la memòria sense límit.

### Evidència obligatòria

- [ ] Vídeo d’una trace curta i una accelerada.
- [ ] Gràfica de segments i memòria al llarg del temps.
- [ ] Proves de polaritat nord/sud i cancel·lació.

### Fora d’abast del pas

La simulació fotogràfica de llarga exposició completa arriba al pas 20.

## Pas 15 — Elevació real, perfil d’horitzó i oclusió celeste

### Resultat funcional palpable

A partir de DEM reals, TerraLab3D mostra l’altitud del lloc i una silueta d’horitzó 360° que oculta correctament els objectes celestes.

### Fonts TerraLab a consultar

- `TerraLab/terrain/terrain_coordinator.py`
- `TerraLab/terrain/worker.py`
- `TerraLab/terrain/providers/*`
- `TerraLab/terrain/horizon_baker.py` o kernel equivalent
- `TerraLab/render/horizon_renderer.py`
- `TerraLab/data/ray_precision.py` i `visibility_range.py`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir `ElevationPort`, mostres, grids, CRS i errors tipats.
- [ ] Adaptar els proveïdors DEM sense portar GDAL al domini.
- [ ] Implementar consulta d’elevació nua per ubicació.
- [ ] Implementar perfil 360° amb radi visible i pas angular configurables.
- [ ] Conservar vectorització, cancel·lació i pressupostos de memòria dels kernels útils.
- [ ] Exposar profunditat d’1 a 530 km i precisió angular equivalent quan sigui aplicable.
- [ ] Publicar el perfil com a recurs versionat.
- [ ] Representar la silueta i la màscara d’oclusió a Three.js.
- [ ] Ocultar estrelles, cossos i NGC per sota de l’horitzó real.
- [ ] Mostrar progrés, cancel·lació, absència de DEM i horitzó pla fallback.
- [ ] Invalidar i recalcular només quan canvien ubicació, elevació o paràmetres del perfil.
- [ ] Comparar elevació, angles i silueta amb TerraLab.

### Criteri de sortida

Una ubicació amb DEM mostra elevació i perfil reals; els objectes celestes queden ocults coherentment; una ubicació sense dades mostra fallback explícit i no bloqueja la UI.

### Evidència obligatòria

- [ ] Fixtures de perfil pla, muntanyós i amb nodata.
- [ ] Comparació angular amb TerraLab.
- [ ] Captures de cossos entrant i sortint darrere l’horitzó.
- [ ] Temps P50/P95, RSS i cancel·lació.

### Fora d’abast del pas

No inclou encara una malla de terreny plena.

## Pas 16 — Terreny tridimensional retingut, tiles, LOD i picking de superfície

### Resultat funcional palpable

L’escena conté muntanyes, valls i relleu 3D navegable al voltant de l’observador, amb tiles persistents, LOD, llum i picking.

### Fonts TerraLab a consultar

- `TerraLab/terrain/overlay.py`
- `TerraLab/terrain/overlay_mixins/*`
- `TerraLab/terrain/render/*`
- `TerraLab/terrain/raycast.py` i geometria
- `TerraLab/terrain/worker.py`
- `TerraLab/ui/widget_controls_builder.py` — relleu 3D, capes i profunditat

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir tiles, bounds, malles, normals, índexs i versions renderer-neutral.
- [ ] Extreure triangulació i càlcul de normals dels camins QPainter.
- [ ] Definir LOD per error de pantalla, distància i pressupost.
- [ ] Dividir el terreny en recursos persistents substituïbles.
- [ ] Transferir buffers binaris sense Base64.
- [ ] Implementar registre, referències i dispose de tiles GPU.
- [ ] Carregar i descarregar tiles segons visibilitat sense reconstruir tota la malla.
- [ ] Implementar frustum culling i límits de memòria.
- [ ] Implementar il·luminació solar/lunar i boira per distància com a materials/uniforms.
- [ ] Implementar mode relleu 3D i compatibilitat amb silueta per distància.
- [ ] Implementar picking de superfície i coordenada del punt impactat.
- [ ] Gestionar canvi de profunditat, qualitat i precisió amb cancel·lació.
- [ ] Mostrar progrés i estat del terreny.
- [ ] Comparar geometria i visibilitat amb TerraLab.

### Criteri de sortida

La càmera pot navegar sobre un terreny real sense reconstrucció global per frame; tiles, LOD, llum, boira i picking funcionen; la memòria es manté dins pressupost.

### Evidència obligatòria

- [ ] Vídeo de navegació amb càrrega/descàrrega de tiles.
- [ ] Captures de diferents profunditats i LOD.
- [ ] Mètriques de triangles, draw calls, memòria i temps de tile.
- [ ] Prova de cancel·lació en canviar d’ubicació.

### Fora d’abast del pas

Els materials d’ortofoto i cobertura arriben al pas següent.

## Pas 17 — Ortofoto, cobertura categòrica i estils de superfície

### Resultat funcional palpable

El terreny pot alternar entre ortofoto, cobertura categòrica, estil original i vibrant sense reconstruir la geometria.

### Fonts TerraLab a consultar

- `TerraLab/terrain/surface/service.py`
- `TerraLab/terrain/surface/rgb.py`
- `TerraLab/terrain/surface/categorical.py`
- `TerraLab/terrain/surface/geometry.py`
- `TerraLab/land_cover/*`
- `TerraLab/data/layer_manager.py` — superfícies RGB/categòriques

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir ports separats per ortofoto i cobertura categòrica.
- [ ] Adaptar CRS, mostreig, nodata, procedència i resolució.
- [ ] Preservar fallback entre fonts en l’ordre seleccionat.
- [ ] Preservar caché per bytes i caché persistent quan sigui útil.
- [ ] Extreure remostreig, subdivisió adaptativa i LOD renderer-neutral.
- [ ] Publicar textures o atributs categòrics versionats per tile.
- [ ] Implementar materials Three.js separats de la geometria.
- [ ] Implementar estil original i vibrant com a canvi de material/uniforms.
- [ ] Mostrar llegenda de categories quan el mode ho requereixi.
- [ ] Gestionar canvis de font manual/automàtica.
- [ ] Mostrar estat de resolució, CRS, font efectiva i fallback.
- [ ] Evitar tornar a mostrejar quan només canvia l’estil visual.
- [ ] Comparar colors, categories i cobertura amb TerraLab.

### Criteri de sortida

L’usuari pot alternar modes i estils de superfície de manera visible; la geometria roman intacta; nodata i fallback es representen de manera coherent.

### Evidència obligatòria

- [ ] Captures d’ortofoto, categòric original i vibrant.
- [ ] Prova que el canvi d’estil no genera una malla nova.
- [ ] Mesures de sampling, caché, bytes i memòria GPU.
- [ ] Fixtures de nodata i fonts múltiples.

### Fora d’abast del pas

No inclou encara clima dinàmic.

## Pas 18 — Meteorologia real, fallback i efectes atmosfèrics

### Resultat funcional palpable

La capa de clima mostra estat remot o fallback, núvols, boira, precipitació i efectes sobre la transparència del cel.

### Fonts TerraLab a consultar

- `TerraLab/weather/system.py`
- `TerraLab/weather/metno_provider.py`
- `TerraLab/ui/widget_controls_builder.py` — toggle i badge fallback
- `TerraLab/data/layer_manager.py` — `SKY_WEATHER`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir `ClimateState` amb cobertura per capes, humitat, visibilitat, boira i precipitació.
- [ ] Adaptar MET Norway darrere un port amb User-Agent, caché i errors tipats.
- [ ] Reescriure el fallback com a model determinista amb llavor explícita.
- [ ] Eliminar la generació QPixmap/QPainter de núvols del camí nou.
- [ ] Escollir una representació Three.js viable per núvols i estrats.
- [ ] Implementar moviment per vent independent del FPS.
- [ ] Implementar pluja/neu com a efecte visual amb pressupost de partícules.
- [ ] Aplicar transparència, extinció i boira al cel i als objectes.
- [ ] Mostrar font remota/fallback amb anti-flicker equivalent.
- [ ] Gestionar dades parcials i transicions entre slots meteorològics.
- [ ] Fer que desactivar clima alliberi o suspengui recursos costosos.
- [ ] Comparar estats i efectes amb TerraLab.

### Criteri de sortida

La meteorologia modifica visiblement l’escena, informa de la seva font, funciona offline amb fallback determinista i no bloqueja la càmera o la timeline.

### Evidència obligatòria

- [ ] Captures de cel clar, núvols, boira, pluja i neu.
- [ ] Prova de xarxa absent i recuperació remota.
- [ ] Mesura de frame en condicions cobertes.
- [ ] Assertions de normalització del proveïdor.

### Fora d’abast del pas

No inclou encara la simulació òptica/fotogràfica.

## Pas 19 — Telescopi, ocular, sensors i enquadrament instrumental

### Resultat funcional palpable

L’usuari pot activar un scope circular o rectangular, configurar focal, obertura, ocular, sensor, aspecte i moviment, i anar a unes coordenades RA/Dec.

### Fonts TerraLab a consultar

- `TerraLab/widgets/telescope_scope_mode.py`
- `TerraLab/widgets/telescope_runtime.py`
- `TerraLab/widgets/physical_math.py`
- `TerraLab/ui/widget_controls_builder.py` — panell scope complet

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir `OpticalInstrument`, `SensorFormat`, `FieldOfView` i `ScopeState`.
- [ ] Caracteritzar presets 1/2.8, APS-C i full frame.
- [ ] Implementar FOV horitzontal/vertical des de focal i sensor.
- [ ] Implementar mode telescopi amb ocular, augment i pupil·la de sortida.
- [ ] Implementar obertura per diàmetre o nombre f.
- [ ] Implementar formats circular i rectangular.
- [ ] Implementar aspecte automàtic, 1:1, 4:3, 3:2, 16:9, 21:9 i personalitzat.
- [ ] Renderitzar màscara exterior, vora, retícula, centre i HUD al frontend.
- [ ] Implementar selecció inicial del centre per click i arrossegament del scope.
- [ ] Implementar moviment lent i ràpid amb passos i hold rate equivalents.
- [ ] Implementar entrada RA/Dec i acció Go RA/Dec.
- [ ] Fer que el scope sol·liciti consultes de con Gaia cancel·lables quan calgui més profunditat.
- [ ] Mantenir la càmera i el reticle fluids mentre el catàleg profund carrega.
- [ ] Comparar FOV, presets i moviment amb TerraLab.

### Criteri de sortida

El scope és usable de punta a punta, els camps angulars són correctes, la consulta profunda no bloqueja i els controls equivalen funcionalment als de TerraLab.

### Evidència obligatòria

- [ ] Proves numèriques de FOV, augment i aspectes.
- [ ] Vídeo de scope circular/rectangular i Go RA/Dec.
- [ ] Prova de consulta profunda cancel·lada per un nou focus.
- [ ] Mesura de frame en camp estel·lar dens.

### Fora d’abast del pas

ISO i exposició encara no alteren científicament la captura fins al pas 20.

## Pas 20 — Simulació fotogràfica, senyal, soroll i llarga exposició

### Resultat funcional palpable

ISO, exposició, obertura, sensor i tracking produeixen una previsualització fotogràfica coherent amb senyal, soroll, saturació i traces.

### Fonts TerraLab a consultar

- `TerraLab/widgets/visual_magnitude_engine.py`
- `TerraLab/widgets/physical_math.py`
- `TerraLab/widgets/telescope_scope_mode.py`
- `TerraLab/ui/widget_controls_builder.py` — ISO i exposició
- `TerraLab/render/stars_renderer.py` — comportament instrumental actual

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Separar enquadrament òptic de simulació fotomètrica.
- [ ] Definir `ExposureSettings`, guany, senyal, soroll i saturació amb unitats.
- [ ] Implementar relació entre magnitud, flux relatiu, obertura, ISO i exposició.
- [ ] Implementar magnitud límit instrumental.
- [ ] Integrar extinció atmosfèrica i brillantor de fons.
- [ ] Implementar previsualització amb uniforms o postprocessat, no alterant el catàleg científic.
- [ ] Implementar saturació i halo de fonts brillants amb límits visuals.
- [ ] Implementar tracking activat/desactivat i longitud de trace per exposició.
- [ ] Integrar traces circumpolars o curtes segons la configuració.
- [ ] Mostrar paràmetres i estimació de SNR al HUD.
- [ ] Definir metadades reproduïbles de la simulació.
- [ ] Preparar un port d’exportació sense implementar formats no necessaris.
- [ ] Comparar resposta instrumental i magnituds amb TerraLab.

### Criteri de sortida

Modificar ISO, exposició, obertura o sensor produeix un efecte visible i científicament documentat; l’enquadrament i la fotometria són responsabilitats separades.

### Evidència obligatòria

- [ ] Fixtures fotomètriques i proves de monotonicitat.
- [ ] Captures amb exposicions i ISO diferents.
- [ ] Prova de saturació i tracking.
- [ ] Informe de diferències respecte de TerraLab.

### Fora d’abast del pas

L’exportació final d’imatges pot quedar com a extensió posterior si TerraLab no la té homologada.

## Pas 21 — Regla, quadrat, rectangle i cercle amb edició

### Resultat funcional palpable

Les quatre eines de mesura es poden crear sobre el cel, seleccionar, moure, redimensionar, eliminar, desfer i llegir amb valors angulars.

### Fonts TerraLab a consultar

- `TerraLab/widgets/measurement_tools.py`
- `TerraLab/widgets/spherical_math.py` o `scene/spherical_math.py`
- `TerraLab/ui/widget_controls_builder.py` — toolbar d’eines

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir entitats immutables per ruler, square, rectangle i circle.
- [ ] Extreure distància angular, arcs geodèsics i punts de destinació.
- [ ] Implementar construcció esfèrica de cada forma.
- [ ] Implementar labels de distància, amplada/alçada i radi/diàmetre.
- [ ] Implementar gestos de creació amb preview.
- [ ] Implementar picking de forma, vores i handles.
- [ ] Implementar moure i redimensionar mantenint geometria esfèrica.
- [ ] Implementar selecció, eliminar seleccionat i netejar-ho tot.
- [ ] Implementar undo/redo amb límit de memòria.
- [ ] Renderitzar overlays amb batches persistents o geometria actualitzada per entitat.
- [ ] Evitar que la UI contingui la geometria matemàtica.
- [ ] Preparar persistència tipada per al pas 23.
- [ ] Comparar etiquetes i interacció amb TerraLab.

### Criteri de sortida

Totes quatre eines són completes i editables; les mesures són numèricament correctes i continuen coherents en moure càmera o canviar FOV.

### Evidència obligatòria

- [ ] Proves de geometria esfèrica i casos prop de 0/360°.
- [ ] Vídeo de crear, moure, redimensionar, eliminar i undo/redo.
- [ ] Prova de resize i canvi de càmera.

### Fora d’abast del pas

La persistència en disc es connecta al pas 23.

## Pas 22 — Constel·lacions editables amb snapping, grups i persistència

### Resultat funcional palpable

L’usuari pot crear grups de constel·lació, unir estrelles, fer traços discontinus, seleccionar nodes/segments/grups, reanomenar, eliminar i desfer.

### Fonts TerraLab a consultar

- `TerraLab/widgets/constellation_drawing.py`
- `TerraLab/ui/widget_controls_builder.py` — shortcuts Delete, Backspace i Enter
- `TerraLab/scene/spherical_math.py`

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir document, grup, node, segment i semàntica `connect_from_prev`.
- [ ] Implementar snapping a estrelles visibles amb radi en píxels controlat pel frontend.
- [ ] Emmagatzemar RA/Dec i identificador/nom d’estrella, no coordenades de pantalla.
- [ ] Implementar crear grup, afegir node i finalitzar amb Enter.
- [ ] Implementar traços discontinus i reprendre des d’un node.
- [ ] Implementar selecció de node, segment, label, grup i multiselecció.
- [ ] Implementar eliminació granular i de grups múltiples.
- [ ] Implementar rename i labels persistents.
- [ ] Implementar undo/redo de totes les operacions.
- [ ] Implementar geometria d’arcs renderer-neutral i batches Three.js.
- [ ] Implementar repository port amb schema versionat.
- [ ] Migrar i validar el JSON actual de TerraLab quan existeixi.
- [ ] Implementar visibilitat independent del mode d’edició.
- [ ] Comparar workflow i shortcuts amb TerraLab.

### Criteri de sortida

Les constel·lacions es poden crear, editar, reanomenar, eliminar, desfer i restaurar; els documents no depenen de Qt ni de coordenades de pantalla.

### Evidència obligatòria

- [ ] Proves de schema, migració i round-trip.
- [ ] Vídeo de grup continu i discontinu.
- [ ] Prova de snapping, multiselecció i eliminació.
- [ ] Reinici de l’aplicació amb restauració del document.

### Fora d’abast del pas

La gestió unificada de preferències i datasets es tanca al pas 23.

## Pas 23 — Capes, datasets, assistent de dades, preferències i feedback

### Resultat funcional palpable

L’aplicació disposa d’un gestor de capes i recursos equivalent: instal·lació, fonts externes, progrés, cancel·lació, fallback, visibilitat i restauració de preferències.

### Fonts TerraLab a consultar

- `TerraLab/data/layer_manager.py`
- `TerraLab/data/assets_manager.py` i `data/assets/*`
- `TerraLab/data/source_catalog.py`
- `TerraLab/ui/asset_onboarding.py` o assistent equivalent
- `TerraLab/common/utils.py` i configuració
- `TerraLab/ui/widget_controls_builder.py` — badges i progrés

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Definir els IDs de capa i descriptors de cel/terra amb fills del sistema solar.
- [ ] Separar visibilitat de disponibilitat de dades.
- [ ] Definir estats ready, partial, missing, invalid, planned, downloading, paused, extracting i error.
- [ ] Definir manifests amb versió, mida, checksum, llicència, procedència i requisit.
- [ ] Implementar biblioteca de dades configurable i estructura de directoris.
- [ ] Implementar fonts administrades i fonts externes sense assumir-ne propietat.
- [ ] Implementar descàrrega reanudable, pausa, cancel·lació i instal·lació atòmica.
- [ ] Implementar checksum i validació després d’instal·lar.
- [ ] Implementar selecció automàtica/manual de font i fallback.
- [ ] Crear assistent funcional de dades i capes.
- [ ] Mostrar progrés Gaia, terreny, Via Làctia, Planck, NGC i altres recursos.
- [ ] Mostrar badges de fallback amb estabilització anti-flicker.
- [ ] Persistir visibilitat de capes, ubicació, Bortle, terreny, superfície, scope i estils.
- [ ] Versionar l’esquema de preferències i implementar migracions.
- [ ] Restaurar sessió sense iniciar descàrregues automàtiques no sol·licitades.
- [ ] Implementar errors accionables amb opció d’obrir l’assistent.
- [ ] Preservar pressupostos de caché per bytes i neteja segura.
- [ ] Comparar descriptors, defaults i fallbacks amb TerraLab.

### Criteri de sortida

Totes les capes de l’inventari es poden activar o expliquen exactament quin recurs falta; les descàrregues són controlables; les preferències i documents es restauren després de reiniciar.

### Evidència obligatòria

- [ ] Prova de biblioteca buida, parcial i completa.
- [ ] Prova de descàrrega pausada/cancel·lada/reanudada.
- [ ] Prova de checksum incorrecte.
- [ ] Round-trip de preferències i migració d’esquema.
- [ ] Vídeo de l’assistent i dels estats de capa.

### Fora d’abast del pas

El pas final endureix, mesura i homologa el conjunt complet.

## Pas 24 — Homologació integral, recuperació, rendiment i independència de producte

### Resultat funcional palpable

TerraLab3D cobreix totes les funcionalitats acordades, és independent de TerraLab en execució, es recupera de fallades i compleix pressupostos científics i gràfics.

### Fonts TerraLab a consultar

- Tot `E:\Desarrollo\TerraLab` com a referència funcional
- `tests/architecture`, regressions offscreen i benchmarks de TerraLab
- `benchmarks/*` i `tools/dev/*`
- Documentació i fixtures generats durant els passos 1–23

### Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

### Tasques

- [ ] Executar la matriu completa de les 24 funcionalitats amb evidència per fila.
- [ ] Comparar ubicacions, dates, càmeres, capes, datasets i instruments equivalents.
- [ ] Comparar valors científics amb toleràncies explícites.
- [ ] Comparar captures per semàntica visual i llegibilitat, no per píxel idèntic.
- [ ] Executar proves manuals de pan, zoom, timeline, realtime, cerca, picking, scope, terreny, eines i shutdown.
- [ ] Definir pressupostos de frame P50/P95, CPU, GPU, RSS, bridge, draw calls i càrrega.
- [ ] Perfilar càmera, canvi d’un segon, salt temporal, càrrega Gaia, tile DEM, superfície i scope dens.
- [ ] Eliminar reconstruccions, còpies i allocations que superin pressupost.
- [ ] Implementar recuperació després de perdre el context WebGL.
- [ ] Implementar reinici del frontend i resync des d’un snapshot autoritatiu.
- [ ] Fer idempotents start, suspend, resume, restart i close.
- [ ] Verificar dispose de tots els recursos GPU i tancament de workers/handles.
- [ ] Eliminar mocks, adapters temporals, flags de migració i rutes legacy.
- [ ] Eliminar qualsevol dependència executiva de `E:\Desarrollo\TerraLab`.
- [ ] Documentar procedència i llicència dels algoritmes/datasets migrats.
- [ ] Congelar versions de contractes, schemas i formats persistents.
- [ ] Publicar guia d’usuari, guia de dades, guia de desenvolupament i troubleshooting.
- [ ] Documentar diferències intencionals i obtenir acceptació explícita.

### Criteri de sortida

Cap funcionalitat queda sense evidència; la ciència compleix toleràncies; la UI cobreix els workflows de TerraLab; Three.js manté una escena persistent; el producte arrenca, es recupera i es tanca netament; no depèn del renderer QPainter ni del repositori TerraLab.

### Evidència obligatòria

- [ ] Informe final de paritat funcional i científica.
- [ ] Quadre de pressupostos i resultats P50/P95.
- [ ] Captures i vídeos de tots els workflows principals.
- [ ] Informe de recursos GPU, RSS, bytes del bridge i còpies.
- [ ] Prova de pèrdua de context, desconnexió i restart.
- [ ] Llista zero de funcionalitats sense propietari o sense evidència.

### Fora d’abast del pas

No queda cap pas funcional pendent dins de l’abast d’homologació.

# Criteri global d’homologació

TerraLab3D es considera funcionalment homologable quan:

- [ ] Les 24 funcionalitats agrupades tenen implementació executable i evidència.
- [ ] Els càlculs astronòmics, fotomètrics, geoespacials i òptics compleixen toleràncies documentades.
- [ ] La UI permet els mateixos workflows de producte acordats.
- [ ] Els datasets, modes de reserva i estats d’error cobreixen els casos d’ús de TerraLab.
- [ ] La càmera i el render continu no depenen de round-trips Python.
- [ ] Gaia, terreny, textures i catàlegs romanen persistents i versionats.
- [ ] El canvi temporal ordinari només envia deltes petits.
- [ ] El picking és real, tipat i protegit per generació.
- [ ] Les eines editables suporten selecció, modificació, undo i persistència.
- [ ] La recuperació de context, restart i shutdown estan verificats.
- [ ] Els pressupostos P50/P95, memòria, draw calls i bridge estan complerts o justificats.
- [ ] No queda cap ruta QPainter, adapter temporal o dependència executiva de TerraLab.
- [ ] Totes les diferències intencionals estan documentades i acceptades.

# Instrucció per a l’agent

Abans d’executar qualsevol pas:

1. Llegeix aquest document complet.
2. Treballa exclusivament en el pas autoritzat.
3. Consulta `E:\Desarrollo\TerraLab` en mode lectura.
4. Inspecciona el codi real, no només els documents.
5. Publica el mapa origen → transformació → destí.
6. Implementa una vertical funcional connectada a l’entrypoint.
7. No marquis cap checkbox sense evidència.
8. No comencis el pas següent.
9. Utilitza la skill terralab-manel-style per a escriure el codi a implementar, per la propera execució hauries d'utilitzar la skill 'py-dev' per a continuar amb la feina. L'ús d'aquesta darrera es farà de forma intermitent, quan necessiti o quan li indiqui.
10. El rendiment és una prioritat màxima, però sense sacrificar aspecte visual i funcionalitats.
11. Els noms d'arxius, mètodes, variables i comentaris sempre en català. Els comentaris han d'anar sempre en català. Hi ha variables i classes de "convencions" que sí que han d'estar en anglès, sinó seria estrany. El negoci propi sí que ha d'estar en català, esclareixo.
12. La gestió i captura d'errors és important. Error amb informació limitada que no reveli l'estructura interna del projecte o codi font (prohibit stacktrace) per a l'usuari, però sí detallat al log.
13. En cada iteració, és obligatori que marquis a pla-implementacio-pas-a-pas.md els checkbox completats.
14. Cada vegada que s'instal·li una nova dependència, documentar-la a requirements.txt sense duplicar-la i classificant-la amb comentaris de perquè és necessària, en quin apartat s'utilitza.
