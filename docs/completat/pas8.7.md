# Pas 8.7 — Il·luminació física de l’escena: Sol, Lluna, cel i materials PBR

> Estat: **completat**  
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’escena deixa d’utilitzar una il·luminació genèrica o desconnectada de l’estat astronòmic. El terreny tècnic, els objectes locals i qualsevol superfície 3D compatible reaccionen de manera contínua a la posició real del Sol, a la llum lunar i a la contribució difusa del cel.

En moure la timeline:

- el Sol il·lumina el món des de la direcció topocèntrica autoritativa del Pas 8;
- la llum directa solar varia de forma coherent amb l’altura solar i l’estat atmosfèric del Pas 7;
- la Lluna pot aportar llum nocturna des de la seva direcció topocèntrica real;
- la llum lunar queda modulada per fase, distància, altura i qualitat del model disponible;
- el cel aporta una component difusa diferenciada de la llum directa;
- el terreny i els objectes mostren volum, normals, rugositat i ombres coherents;
- dia, crepuscle i nit transicionen sense salts d’intensitat ni canvis artificials de material;
- caminar o volar canvia el punt de vista i les ombres locals, però no recalcula efemèrides, atmosfera o fotometria científica;
- cap geometria, textura o material persistent es recrea per tick.

Aquest pas converteix el sistema d’il·luminació en un consumidor de l’estat científic existent. **Three.js no esdevé l’autoritat astronòmica ni atmosfèrica.**

## Fonts a consultar

### TerraLab3D `main`

Revisar l’estat real del repositori abans d’implementar, especialment:

- `backend/src/terralab3d/domain/sky_background/sky_environment.py`
- implementació final del `SkyEnvironmentSnapshot` o equivalent del Pas 7;
- implementació final del `SolarSystemSnapshot` o equivalent del Pas 8;
- estat final d’orientació i il·luminació lunar del Pas 8.5;
- `backend/src/terralab3d/infrastructure/websocket_bridge.py`
- `frontend/src/contracts/bridge_messages.ts`
- `frontend/src/view/three/ThreeSceneHostImpl.ts`
- `frontend/src/view/three/AtmosphereRenderer.ts`
- renderer del sistema solar;
- renderer lunar;
- materials i geometries del terreny tècnic;
- render loop, lifecycle, diagnòstic i comptadors GPU existents;
- convenció ENU → Three.js real de `main`.

No pressuposis els noms exactes dels símbols creats als Passos 7, 8 i 8.5. Preval sempre el codi real de `main`.

### TerraLab, només com a referència funcional

Consultar només per caracteritzar comportament, fórmules o decisions visuals reutilitzables:

- `TerraLab/render/sky_renderer.py`
- `TerraLab/astro/engine.py`
- `TerraLab/astro/ephemeris_coordinator.py`
- `TerraLab/runtime/offscreen_renderer.py`
- `TerraLab/widgets/physical_math.py`
- proves relacionades amb Sol, Lluna, atmosfera, crepuscle i render si existeixen.

No copiar una il·luminació 2D o una composició QPainter si entra en conflicte amb el model 3D persistent.

### Fonts externes obligatòries

**Three.js — DirectionalLight**

`https://threejs.org/docs/pages/DirectionalLight.html`

S’utilitza com a implementació renderer-side de fonts pràcticament infinites amb raigs paral·lels. És l’adaptació adequada per a la llum directa del Sol i, a l’escala local de TerraLab3D, també per a la llum directa de la Lluna.

**Three.js — Lights manual**

`https://threejs.org/manual/en/lights.html`

Utilitzar-la per caracteritzar les limitacions de `AmbientLight` i `HemisphereLight`. `AmbientLight` no ha de ser el model principal del cel. `HemisphereLight` es pot utilitzar com a implementació inicial o fallback de la component difusa, però no com a model científic.

**Three.js — MeshStandardMaterial**

`https://threejs.org/docs/pages/MeshStandardMaterial.html`

Material PBR base preferent per a terreny i superfícies opaques ordinàries.

**Three.js — MeshPhysicalMaterial**

`https://threejs.org/docs/pages/MeshPhysicalMaterial.html`

Només s’ha d’utilitzar quan una superfície necessiti propietats avançades que justifiquin el seu cost addicional. No convertir-lo en material universal per defecte.

**Three.js — WebGLRenderer**

`https://threejs.org/docs/pages/WebGLRenderer.html`

Consultar configuració actual de color space, tone mapping, shadow maps, capacitats, `renderer.info` i lifecycle.

**Three.js — LightShadow / DirectionalLightShadow**

`https://threejs.org/docs/pages/LightShadow.html`

`https://threejs.org/docs/pages/DirectionalLightShadow.html`

Utilitzar per implementar ombres locals controlades, mesurables i amb lifecycle explícit.

## Objectiu

Crear una vertical d’il·luminació persistent que transformi l’estat científic ja calculat pels Passos 7, 8, 8.5 i 8.6 en paràmetres de renderització Three.js, sense duplicar efemèrides, atmosfera ni geometria científica al frontend.

La separació obligatòria és:

```text
Pas 7 — atmosfera i cel
        │
Pas 8 — Sol i Lluna topocèntrics
        │
Pas 8.5 — geometria Sol–Lluna i orientació lunar
        │
        ▼
Pas 8.6 — textura planetes + satel·lits
        │
        ▼
LightingEnvironmentComposer
        │
        ▼
LightingEnvironmentSnapshot
        │
        ▼
Bridge
        │
        ▼
Three.js Lighting Adapter
├── SunDirectionalLight
├── MoonDirectionalLight
├── DiffuseSkyLighting
├── ShadowController
└── PBRMaterialPolicy
```

La regla arquitectònica central és:

```text
Python determina QUINA llum física/astronòmica existeix i d’on prové.
Three.js determina COM aquesta llum es representa eficientment a la GPU.
```

## Frontera obligatòria entre el Pas 8.6 i el Pas 8.7

Aquest pas **no substitueix ni absorbeix** la il·luminació específica dels cossos del Pas 8.6.

La separació és:

```text
Pas 8.6 — il·luminació dels cossos del sistema solar
├── Body → Sun direction per planeta/satèl·lit
├── terminador i fase emergents de normals + direcció solar
├── il·luminació física de Saturn i dels anells
└── materials/geometries persistents dels cossos

Pas 8.7 — il·luminació de l’escena local de TerraLab3D
├── SunDirectionalLight
├── MoonDirectionalLight
├── component difusa del cel
├── materials PBR de worldRoot
└── ombres locals
```

Regles:

- [ ] `SunDirectionalLight` no s’utilitza com a substitut de `bodyToSunDirection` dels planetes, satèl·lits o anells.
- [ ] La il·luminació de cada cos llunyà continua utilitzant la seva pròpia geometria `Body → Sun` definida al Pas 8.6.
- [ ] El Pas 8.7 consumeix la direcció topocèntrica del Sol i de la Lluna per il·luminar `worldRoot` i els objectes locals.
- [ ] Cap `DirectionalLight` global pot imposar un terminador incorrecte als cossos del sistema solar.
- [ ] Els dos sistemes comparteixen fonts científiques, convencions de coordenades, color management i lifecycle, però tenen responsabilitats renderer diferents.
- [ ] Una refactorització futura no pot eliminar el Pas 8.7 perquè el Pas 8.6 ja calculi direccions d’il·luminació dels cossos.

## Regles d’autoritat

- [ ] La direcció del Sol prové exclusivament de l’estat autoritatiu del Pas 8.
- [ ] La direcció de la Lluna prové exclusivament de l’estat autoritatiu del Pas 8.
- [ ] La fase lunar no es recalcula dins del renderer.
- [ ] L’altura solar no es recalcula dins del renderer.
- [ ] L’altura lunar no es recalcula dins del renderer.
- [ ] L’atenuació o transmittància atmosfèrica reutilitza el Pas 7; no es crea un segon model de cel dins del sistema de llums.
- [ ] El frontend pot interpolar valors entre snapshots autoritatius, però no crear una segona efemèride.
- [ ] Els shaders poden avaluar BRDF, normals, ombres i combinació de llum, però no calcular efemèrides ni decisions científiques.
- [ ] Els valors visuals no calibrats físicament s’han de marcar com a `visual` o `approximate`; no s’han de presentar com a lux, irradiància o fotometria científica si no existeix un model validat.
- [ ] La translació de la càmera no modifica l’estat científic de la il·luminació.
- [ ] El roll de càmera no modifica la direcció científica del Sol o la Lluna.

## Estat d’il·luminació neutral

Crear un contracte renderer-neutral equivalent conceptualment a:

```ts
interface DirectionENU {
  east: number;
  up: number;
  north: number;
}

interface DirectLightState {
  enabled: boolean;
  directionToSourceENU: DirectionENU;
  altitudeDeg: number;
  colorLinear: [number, number, number];
  intensity: number;
  intensityKind: "physical" | "relative" | "visual";
  quality: "scientific" | "approximate" | "fallback" | "unavailable";
}

interface DiffuseSkyLightState {
  enabled: boolean;
  zenithColorLinear: [number, number, number];
  horizonColorLinear: [number, number, number];
  groundColorLinear: [number, number, number];
  intensity: number;
  quality: "scientific" | "approximate" | "fallback";
}

interface LightingEnvironmentSnapshot {
  generation: number;
  timestampUtc: string;
  sun: DirectLightState;
  moon: DirectLightState;
  skyDiffuse: DiffuseSkyLightState;
  exposureHint?: number;
  sourceSkyGeneration: number;
  sourceSolarSystemGeneration: number;
}
```

Els noms exactes s’han d’adaptar als contractes reals existents. No crear un segon `SkyEnvironmentSnapshot` o `SolarSystemSnapshot` duplicat.

## Tasques

### Composició de l’estat d’il·luminació

- [ ] Crear una única responsabilitat d’aplicació o domini, conceptualment `LightingEnvironmentComposer`.
- [ ] Consumir l’estat del Pas 7 i el Pas 8 en lloc de recalcular-los.
- [ ] Incorporar del Pas 8.5 només els paràmetres lunars necessaris per a la il·luminació.
- [ ] Produir un snapshot petit, immutable, tipat i versionat.
- [ ] Normalitzar i validar tots els vectors ENU.
- [ ] Rebutjar NaN, infinits, vectors degenerats i intensitats negatives.
- [ ] Propagar `generation` i qualitat de les fonts d’origen.
- [ ] Aplicar latest-wins davant canvis ràpids de timeline.
- [ ] No bloquejar el render si una component de llum queda no disponible.

### Llum directa solar

Implementació Three.js preferent:

```text
Scientific Sun direction
        ↓
LightingEnvironmentSnapshot.sun
        ↓
ENU → Three.js
        ↓
THREE.DirectionalLight
```

- [ ] Utilitzar una única `DirectionalLight` solar persistent.
- [ ] No crear ni destruir la llum solar per tick.
- [ ] Actualitzar direcció, color i intensitat sobre l’objecte existent.
- [ ] Recordar que `DirectionalLight` utilitza `position` + `target`; no confiar en `rotation` com a mecanisme de direcció.
- [ ] Centralitzar la conversió `directionToSourceENU` → direcció efectiva del `DirectionalLight`.
- [ ] Fer que la llum solar sigui nul·la o inactiva quan el model autoritatiu determini que no hi ha llum directa sobre el món local.
- [ ] Reutilitzar l’atenuació/color atmosfèrics del Pas 7 quan estiguin disponibles.
- [ ] Evitar un canvi cromàtic manual duplicat per alba o posta si el Pas 7 ja en determina l’estat.
- [ ] Fer transicions contínues durant sortida, posta i crepuscles.
- [ ] Permetre ombres solars segons la política de qualitat definida en aquest pas.

La posició artificial utilitzada internament per orientar `DirectionalLight` no té significat astronòmic. La dada científica és el vector de direcció.

### Llum directa lunar

Implementació Three.js preferent:

```text
Scientific Moon direction + phase + distance
        ↓
LightingEnvironmentSnapshot.moon
        ↓
ENU → Three.js
        ↓
THREE.DirectionalLight
```

- [ ] Utilitzar una única `DirectionalLight` lunar persistent.
- [ ] No representar la llum lunar amb `PointLight`.
- [ ] Reutilitzar posició, fase i distància del Pas 8.
- [ ] Reutilitzar la geometria Sol–Lluna disponible després del Pas 8.5.
- [ ] Atenuar o anul·lar la component directa quan la Lluna no és visible des de l’observador, segons el model definit.
- [ ] Fer que Lluna nova, quart i plena no produeixin la mateixa intensitat.
- [ ] Fer que la variació sigui contínua amb la timeline.
- [ ] No utilitzar una constant arbitrària presentada com a fotometria científica.
- [ ] Si només existeix una aproximació visual, marcar `intensityKind = visual` i `quality = approximate/fallback`.
- [ ] No confondre l’autoil·luminació visual del disc lunar amb la llum que la Lluna aporta al terreny.
- [ ] Permetre desactivar les ombres lunars si el cost no justifica el resultat.

### Component difusa del cel

`AmbientLight` no ha de ser el model principal de la llum del cel perquè no té direcció ni distingeix orientació de les superfícies.

Crear una abstracció renderer-side equivalent a:

```ts
interface DiffuseSkyLightingAdapter {
  apply(state: DiffuseSkyLightState): void;
  setEnabled(enabled: boolean): void;
  dispose(): void;
}
```

Implementació inicial acceptable:

```text
DiffuseSkyLightState
        ↓
HemisphereLight
```

sempre que quedi documentada com una aproximació visual.

- [ ] Utilitzar `HemisphereLight` com a primera implementació si proporciona prou qualitat i rendiment.
- [ ] Reservar la possibilitat de substituir-la per environment lighting, spherical harmonics o una tècnica equivalent sense canviar el domini.
- [ ] Reutilitzar colors i estat atmosfèric del Pas 7.
- [ ] Diferenciar contribució de zenit/hemisferi superior i terra/hemisferi inferior quan el model disponible ho permeti.
- [ ] Evitar que la component difusa mantingui el terreny artificialment brillant durant una nit fosca.
- [ ] Evitar que `AmbientLight` s’utilitzi per “arreglar” materials o ombres mal calibrades.
- [ ] Si s’utilitza `AmbientLight` temporalment en fallback, registrar-ho i mantenir una intensitat explícita i limitada.

### Contaminació lumínica

La contaminació lumínica del Pas 7 **no** s’ha de convertir en milers de `PointLight` o `SpotLight` ficticis.

- [ ] Mantenir Bortle/SQM i skyglow dins del model atmosfèric/visibilitat corresponent.
- [ ] No crear fonts locals artificials sense dades espacials reals que les justifiquin.
- [ ] Reservar `PointLight`, `SpotLight` i `RectAreaLight` per a futurs objectes locals emissius identificables, no per simular globalment la contaminació lumínica.
- [ ] No augmentar la llum del terreny nocturn només perquè augmenti Bortle si no hi ha un model definit que relacioni ambdues magnituds.

### Materials PBR

Definir una política explícita de materials per al món local.

```text
worldRoot
└── renderables
    └── PBRMaterialPolicy
        ├── albedo
        ├── roughness
        ├── metalness
        ├── normal
        ├── ambient occlusion
        └── emissive, només quan sigui realment emissiu
```

- [ ] Utilitzar `MeshStandardMaterial` com a material PBR base preferent per a superfícies opaques ordinàries.
- [ ] Utilitzar `MeshPhysicalMaterial` només quan propietats com clearcoat, transmission, sheen o altres extensions siguin necessàries.
- [ ] No pagar el cost de `MeshPhysicalMaterial` en tot el terreny sense justificació.
- [ ] Per terreny natural, utilitzar `metalness = 0` com a valor base excepte quan una capa real indiqui una altra cosa.
- [ ] Definir `roughness` de manera explícita i no utilitzar el valor només per compensar una llum mal calibrada.
- [ ] Tractar albedo/color com a dada de color i normals/roughness/metalness/AO com a dades no-color.
- [ ] Reutilitzar materials i textures persistents.
- [ ] Actualitzar uniforms o propietats petites; no reconstruir materials quan canvia el Sol.
- [ ] Preparar la política perquè els Passos 16 i 17 puguin connectar DEM, ortofoto i superfície sense reescriure el motor d’il·luminació.
- [ ] No incorporar propietats de material científicament inventades quan el dataset no les proporciona; els defaults visuals han d’estar documentats com a tals.

### Color management i tone mapping

- [ ] Revisar la versió de Three.js real instal·lada abans de tocar configuració de color.
- [ ] Mantenir una única política global de color space.
- [ ] Utilitzar `renderer.outputColorSpace` de manera explícita i coherent amb els assets.
- [ ] Etiquetar correctament textures d’albedo/color i textures de dades.
- [ ] Definir explícitament la política de tone mapping en lloc de dependre accidentalment del default de la versió.
- [ ] Definir una exposició base i documentar qualsevol canvi dinàmic.
- [ ] No implementar autoexposure agressiu que oculti errors de llum o alteri la visibilitat astronòmica sense control.
- [ ] Si s’utilitza exposició dinàmica, separar `exposureHint` científic/ambiental del suavitzat visual renderer-side.
- [ ] Evitar double gamma, textures rentades o normals interpretades en sRGB.
- [ ] Verificar que captures diürnes, crepusculars i nocturnes mantenen rang tonal usable.

### Ombres

Les ombres són una responsabilitat de renderització, no un nou càlcul astronòmic.

Crear una política equivalent a:

```ts
type ShadowQuality = "off" | "low" | "medium" | "high";

interface ShadowPolicy {
  quality: ShadowQuality;
  sunEnabled: boolean;
  moonEnabled: boolean;
  localRadiusM: number;
}
```

- [ ] Activar shadow maps només quan la qualitat ho requereixi.
- [ ] Prioritzar ombres solars.
- [ ] Fer opcionals les ombres lunars.
- [ ] Ajustar la càmera d’ombra a una zona local útil, no a centenars de quilòmetres indiscriminadament.
- [ ] Actualitzar la càmera d’ombra quan la càmera visual es desplaça prou o quan canvia significativament la direcció de la llum.
- [ ] Evitar reconstruir shadow maps, materials o llums per un simple canvi de FOV si no és necessari.
- [ ] Evitar shadow acne i peter-panning amb `bias`/`normalBias` mesurats i documentats, no amb valors enormes.
- [ ] Mesurar el cost de cada qualitat de shadow map.
- [ ] Permetre `shadowMap.autoUpdate = false` o política equivalent quan l’escena i la llum estan estàtiques i sigui segur reutilitzar el mapa.
- [ ] Invalidar explícitament l’ombra quan la direcció solar/lunar o la geometria visible ho requereixi.
- [ ] Evitar shimmering greu durant translació mitjançant estabilització de la càmera d’ombra si és necessària.
- [ ] No intentar resoldre en aquest pas ombres planetàries, eclipsis o self-shadowing topogràfic lunar detallat.

### Arbre de l’escena

Afegir una responsabilitat explícita d’il·luminació sense desfer l’arbre existent:

```text
scene
├── celestialRoot
├── worldRoot
├── lightingRoot
│   ├── sunDirectionalLight
│   ├── moonDirectionalLight
│   └── diffuseSkyLight
├── overlayRoot
└── cameraRig
```

- [ ] `lightingRoot` no conté dades científiques autoritatives; només objectes de render.
- [ ] La translació local de la càmera no altera les direccions astronòmiques.
- [ ] Si cal reposicionar `DirectionalLight.position` i `target` per mantenir precisió o ombres locals, conservar exactament la direcció científica.
- [ ] No adjuntar la llum solar o lunar a la càmera com si fossin un headlight.
- [ ] No crear una escena separada només per a la il·luminació.
- [ ] No crear un segon render loop.

### Renderer persistent i actualització per tick

- [ ] Crear les llums una sola vegada durant inicialització.
- [ ] Crear els materials del terreny tècnic una sola vegada, excepte canvis explícits de recurs o configuració.
- [ ] Aplicar snapshots nous actualitzant valors petits.
- [ ] Interpolar direcció i intensitat al frontend entre ticks normals quan millori la continuïtat visual.
- [ ] Utilitzar interpolació angular robusta; no interpolar vectors degenerats.
- [ ] Davant salts temporals grans, aplicar l’estat nou sense una transició llarga a través d’un cel físicament incorrecte.
- [ ] No interpolar a través del canvi dia/nit de manera que la llum solar continuï activa sota l’horitzó.
- [ ] Fer `dispose()` de materials, textures auxiliars, shadow maps i recursos creats pel sistema en shutdown.
- [ ] Fer idempotents `start`, `apply`, `setQuality` i `dispose`.

### Bridge

Enviar només l’estat compacte necessari.

Exemple conceptual:

```text
lighting_environment_snapshot
├── generation
├── timestamp_utc
├── sun
│   ├── enabled
│   ├── direction_enu
│   ├── color_linear
│   ├── intensity
│   ├── intensity_kind
│   └── quality
├── moon
│   ├── enabled
│   ├── direction_enu
│   ├── color_linear
│   ├── intensity
│   ├── intensity_kind
│   └── quality
└── sky_diffuse
    ├── enabled
    ├── zenith_color_linear
    ├── horizon_color_linear
    ├── ground_color_linear
    ├── intensity
    └── quality
```

- [ ] No enviar textures, cubemaps, shadow maps, geometries o materials pel bridge.
- [ ] No duplicar dins del missatge totes les dades del Pas 7 i Pas 8 si només cal un subconjunt derivat.
- [ ] Mantenir `generation`, correlació i descart stale.
- [ ] Coalescing durant arrossegament ràpid de timeline.
- [ ] Zero missatges d’il·luminació per frame.
- [ ] Camera pan/orbit/roll → zero missatges científics d’il·luminació.
- [ ] Walk/flight amb temps pausat → zero missatges científics d’il·luminació.
- [ ] Canvi de qualitat d’ombres → operació local al frontend sempre que no requereixi dades noves.

### Integració amb el terreny tècnic i futurs Passos 16–17

En aquest pas encara no s’ha d’anticipar el DEM final, però la il·luminació ha de quedar demostrada sobre una geometria local amb volum, normals i materials PBR.

- [ ] Aplicar la il·luminació al terreny tècnic persistent disponible.
- [ ] Incloure com a mínim pendents, plans i objectes amb normals diferents per validar la resposta lumínica.
- [ ] Verificar ombres amb desnivells reals de la malla tècnica.
- [ ] No implementar encara el pipeline DEM final.
- [ ] Definir els punts d’extensió perquè el Pas 16 substitueixi la geometria tècnica per topografia real sense canviar `LightingEnvironmentComposer`.
- [ ] Definir els punts d’extensió perquè el Pas 17 connecti albedo/ortofoto/cobertura a `PBRMaterialPolicy` sense canviar l’efemèride ni les llums.
- [ ] No vincular materials PBR a una font concreta de dades.

### UI i diagnòstic

No afegir un panell flotant nou.

Integrar controls només on encaixin amb la UI existent, preferentment a diagnòstic o a la configuració visual:

- [ ] toggle general d’il·luminació física només si és necessari per diagnòstic/comparació;
- [ ] qualitat d’ombres `off/low/medium/high`;
- [ ] indicador de font solar: `scientific/approximate/unavailable`;
- [ ] indicador de font lunar: `scientific/approximate/fallback/unavailable`;
- [ ] indicador de component difusa;
- [ ] mostrar en diagnòstic direcció solar i lunar ENU;
- [ ] mostrar intensitat i `intensityKind` sense etiquetar-la com a lux si no ho és;
- [ ] mostrar recompte de shadow-map updates;
- [ ] mostrar draw calls i memòria només en diagnòstic;
- [ ] no exposar sliders arbitraris de “força del Sol” o “força de la Lluna” en la UI normal si trenquen l’autoritat científica.

### Logging MGP

Respectar el format existent:

```text
MGP: [ARXIU] [MÈTODE] [MISSATGE]
```

Registrar només esdeveniments útils:

```text
MGP: [LightingEnvironmentComposer.py] [compose] [Snapshot generation=42 sun=scientific moon=approximate sky=scientific]
MGP: [SceneLightingController.ts] [apply] [Il·luminació aplicada generation=42]
MGP: [ShadowController.ts] [setQuality] [Qualitat canviada previous=medium current=high]
MGP: [ShadowController.ts] [invalidateSunShadow] [Shadow solar invalidada reason=sun_direction_changed]
MGP: [SceneLightingController.ts] [fallback] [Llum lunar unavailable; es manté cel difús]
```

No registrar:

- cada frame;
- cada interpolació;
- cada canvi subpixel de shadow camera;
- cada material processat;
- cada actualització normal de uniforms.

## Fallback honest

Si el Pas 7 no proporciona component difusa suficient:

```text
llum solar directa  → disponible si Pas 8 està disponible
llum lunar directa  → disponible segons qualitat del model
llum difusa del cel → fallback visual explícit
```

Si falla l’efemèride solar:

```text
sunDirectionalLight → disabled
atmosfera Pas 7      → conservar si pot operar honestament
llum lunar           → conservar si és independent i vàlida
status               → partial
```

Si falla l’estat lunar:

```text
llum solar           → disponible
llum difusa          → disponible
llum lunar directa   → unavailable
```

Si les shadow maps no són suportades o excedeixen el pressupost:

```text
il·luminació PBR → disponible
ombres          → off/fallback
status          → usable
```

No convertir un fallback visual en una dada científica falsa.

## Proves obligatòries

### Autoritat científica i contractes

- [ ] Mateixa UTC + mateixa ubicació → mateixa direcció solar independentment de la càmera.
- [ ] Mateixa UTC + mateixa ubicació → mateixa direcció lunar independentment de la càmera.
- [ ] Pan/orbit → zero recomputacions d’efemèrides.
- [ ] Walk/flight amb temps pausat → zero recomputacions d’efemèrides i atmosfera.
- [ ] Roll de càmera → no modifica vectors ENU del snapshot.
- [ ] Canvi d’un segon → no recrea llums ni materials.
- [ ] Salt temporal gran → no deixa una interpolació llarga entre estats incompatibles.
- [ ] Snapshot rebutja NaN, infinits i vectors degenerats.
- [ ] `generation` stale és descartada.
- [ ] No hi ha càlcul de fase lunar al frontend.
- [ ] No hi ha càlcul de posició solar al shader.

### Llum solar

- [ ] Sol alt → ombres curtes i direcció coherent.
- [ ] Sol baix → ombres llargues i direcció coherent.
- [ ] Sortida de Sol → transició contínua.
- [ ] Posta de Sol → transició contínua.
- [ ] Sol sota horitzó → absència de llum directa solar segons el model.
- [ ] La direcció del `DirectionalLight` coincideix amb el vector científic després de la conversió ENU → Three.js.
- [ ] Canviar la posició local de càmera no canvia la direcció solar.

### Llum lunar

- [ ] Lluna plena sobre l’horitzó → contribució nocturna visible si el model la proporciona.
- [ ] Lluna nova → contribució directa fortament reduïda o nul·la segons el model.
- [ ] Quart → intensitat diferent de plena i nova.
- [ ] Lluna sota horitzó → component directa anul·lada segons el model.
- [ ] La direcció lunar coincideix amb l’efemèride del Pas 8.
- [ ] La llum sobre el terreny i el costat il·luminat del disc lunar són geomètricament compatibles amb el mateix Sol científic.

### Component difusa

- [ ] Dia → superfícies en ombra conserven una contribució difusa coherent.
- [ ] Crepuscle → transició contínua de la component difusa.
- [ ] Nit fosca → no existeix un ambient artificialment elevat.
- [ ] Canvi Bortle no crea automàticament llum directa local fictícia.
- [ ] `AmbientLight` no és necessari per ocultar errors de normals o PBR.
- [ ] Si s’utilitza `HemisphereLight`, la implementació queda marcada com a aproximació renderer-side.

### Materials PBR

- [ ] Pla horitzontal, pendent nord, pendent sud i superfície vertical responen de manera diferent a la mateixa llum.
- [ ] `metalness = 0` per al terreny tècnic base.
- [ ] Roughness produeix resposta especular coherent sense alterar l’albedo.
- [ ] Normal map, si existeix, modifica la resposta local però no la geometria.
- [ ] Textures de dades no s’interpreten com a sRGB.
- [ ] Cap material es reconstrueix per tick.
- [ ] `MeshPhysicalMaterial` no s’utilitza on `MeshStandardMaterial` és suficient.

### Ombres

- [ ] Shadow quality `off` elimina el cost de shadow rendering.
- [ ] `low/medium/high` produeixen costos i resolucions documentats.
- [ ] Shadow solar segueix la direcció del Sol.
- [ ] Translació local actualitza la regió d’ombra sense alterar la direcció científica.
- [ ] No hi ha shadow acne greu en terreny pla o pendent.
- [ ] No hi ha peter-panning greu.
- [ ] No hi ha shimmering inacceptable en moviment continu.
- [ ] Shadow map no s’actualitza si càmera, geometria i llum continuen dins la política de reutilització.
- [ ] Moon shadow off no desactiva la llum lunar.

### Persistència i rendiment

- [ ] `sun_light_build_count = 1` després de la inicialització normal.
- [ ] `moon_light_build_count = 1` després de la inicialització normal.
- [ ] `diffuse_light_build_count = 1` per implementació activa.
- [ ] `pbr_material_build_count` estable durant timeline.
- [ ] `lighting_bridge_asset_bytes = 0`.
- [ ] Zero textures, geometries o materials enviats pel bridge.
- [ ] Zero missatges científics per frame.
- [ ] Mesura P50/P95 amb shadows off.
- [ ] Mesura P50/P95 amb shadows medium.
- [ ] Mesura P50/P95 amb shadows high.
- [ ] Mesura de GPU memory abans i després d’activar shadow maps.
- [ ] Timeline accelerada no produeix creixement continu de memòria.
- [ ] Walk/flight prolongat no produeix reconstrucció de recursos.
- [ ] Shutdown allibera shadow maps i recursos propis.
- [ ] Arrencada → tancament → arrencada no duplica llums ni listeners.

## Criteri de sortida

El Pas 8.7 no es considera complet fins que:

- [ ] existeix una única font autoritativa per a la direcció solar;
- [ ] existeix una única font autoritativa per a la direcció lunar;
- [ ] `DirectionalLight` solar representa el Sol sense recalcular-lo;
- [ ] `DirectionalLight` lunar representa la Lluna sense recalcular-la;
- [ ] la component difusa del cel consumeix l’estat atmosfèric del Pas 7;
- [ ] `AmbientLight` no és la base del sistema d’il·luminació;
- [ ] `HemisphereLight`, si s’utilitza, queda encapsulada com a implementació/fallback substituïble;
- [ ] el terreny tècnic utilitza materials PBR coherents;
- [ ] `MeshStandardMaterial` és el default i `MeshPhysicalMaterial` només s’utilitza quan aporta una propietat necessària;
- [ ] color space i tone mapping són explícits i verificats;
- [ ] la timeline modifica llums mitjançant estat petit, no recreant recursos;
- [ ] caminar, volar, fer pan, zoom o roll no recalcula la ciència de la llum;
- [ ] les ombres solars funcionen segons una política de qualitat mesurada;
- [ ] les ombres lunars són opcionals i no condicionen la disponibilitat de la llum lunar;
- [ ] Bortle/SQM no es simulen amb fonts locals fictícies;
- [ ] els Passos 16 i 17 poden substituir geometria i materials sense reescriure l’autoritat d’il·luminació;
- [ ] no existeixen missatges de bridge per frame;
- [ ] no es recreen llums, materials, geometries o textures per tick;
- [ ] els fallbacks són explícits;
- [ ] lifecycle i `dispose` són verificables;
- [ ] totes les proves passen;
- [ ] els Passos 1–8.6 continuen funcionant;
- [ ] el Pas 9 encara no s’ha començat.

## Evidència obligatòria

- [ ] Captura amb Sol alt mostrant volum i ombres del terreny tècnic.
- [ ] Captura amb Sol baix mostrant ombres llargues coherents.
- [ ] Vídeo curt de posta o sortida mitjançant timeline sense salts lumínics.
- [ ] Captura nocturna amb Lluna plena i contribució lunar visible quan el model ho permeti.
- [ ] Captura equivalent amb Lluna nova demostrant la diferència.
- [ ] Captura de nit fosca sense ambient artificial excessiu.
- [ ] Comparació `shadows off/medium/high`.
- [ ] Prova que pan/orbit/walk/flight no genera requests científics d’il·luminació.
- [ ] Prova que `sun_light_build_count` i `moon_light_build_count` es mantenen estables.
- [ ] Prova que els materials no es reconstrueixen durant timeline.
- [ ] Traça de bridge demostrant zero assets i zero missatges per frame.
- [ ] Mètriques P50/P95 per cada qualitat d’ombres suportada.
- [ ] Mètriques de memòria GPU.
- [ ] Traça MGP d’inicialització, canvi de qualitat, fallback i shutdown.
- [ ] Prova de color management amb albedo i normal map.
- [ ] Prova de shutdown i reinici.

## Fora d’abast del pas

Aquest pas no implementa:

- DEM final dels Passos 15–16;
- ortofoto o superfície final del Pas 17;
- global illumination completa;
- path tracing;
- ray tracing físic complet;
- scattering atmosfèric volumètric nou si el Pas 7 ja proporciona el model necessari;
- autoexposure fotogràfic complet del Pas 20;
- HDR fotogràfic del pipeline instrumental;
- milers de llums urbanes artificials;
- dades GIS de fanals;
- eclipsis solars o lunars;
- ombres d’eclipsi;
- self-shadowing topogràfic lunar d’alta resolució;
- ombres de cràters calculades científicament a escala lunar;
- reflexions especulars avançades de masses d’aigua finals;
- meteorologia volumètrica del Pas 18.

Aquests elements no poden retardar ni contaminar el Pas 9.

La regla final del Pas 8.7 és:

```text
Pas 7 defineix l’entorn atmosfèric;
Pas 8 defineix on són el Sol i la Lluna;
Pas 8.5 manté coherent la geometria i orientació lunar;
Pas 8.6 manté la il·luminació específica Body → Sun dels planetes, satèl·lits i anells;
LightingEnvironmentComposer deriva l’estat d’il·luminació local de l’escena;
Three.js el representa amb llums direccionals persistents, component difusa, materials PBR i ombres;
la càmera només observa el resultat.
```

## Annex: Validació de la il·luminació física de l’escena

Data de validació: 2026-08-10

### Estat

La capacitat vertical del Pas 8.7 està implementada i supera la regressió
automàtica completa. El bridge i el lifecycle també s'han provat amb una
instància real en un port aïllat. Queda pendent l'evidència visual comparativa
i la mesura GPU en navegador real; per tant, aquest document no presenta com a
observades captures o mètriques que aquesta sessió no ha pogut obtenir.

El Pas 9 no s'ha començat. L'únic punt preparat per al pas següent és
`directSolarVisibilityFactor`, publicat amb valor `1.0`.

### Invariant lunar prioritari

La fase i l'aparença lunar continuen sota el camí específic Lluna→Sol del Pas
8/8.5, independent de les llums globals de l'escena:

- el subarbre lunar no conté cap `Light`;
- el shader lunar elimina completament l'acumulació de llums globals;
- el vector Lluna→Sol existent continua governant fase i terminador;
- la normal map LRO continua afectant la resposta superficial;
- la cara no il·luminada conserva exactament el terme atmosfèric d'opacitat
  `0.015`, de manera que l'atmosfera predomina i no apareix una pilota negra;
- el vel diürn neutre, l'orientació, la libració, els fallbacks i el lifecycle
  existents es mantenen;
- canviar el vector Lluna→Sol no pot mutar ni il·luminar el terreny local.

La Lluna sí aporta ara llum direccional al món local segons magnitud aparent,
altitud i extinció. És una escala visual PBR explícita, no lux. La referència de
Lluna plena alta dona `0.1118816576`: prou visible sobre el terreny tècnic fosc,
però molt inferior a la referència solar `3.0`. No s'ha afegit cap halo lunar.

### Halo solar

L'halo sol·licitat s'ha integrat en el shader atmosfèric del Pas 7, no com una
textura, un sprite o un lens flare:

- comparteix la direcció solar autoritativa;
- combina un nucli Mie compacte i una aurèola exterior suau;
- la terbolesa controla l'amplada angular;
- el color s'escalfa amb el Sol baix;
- desapareix quan el Sol és físicament sota l'horitzó;
- no afegeix cap dada, llum o efecte a la Lluna.

La prova numèrica comprova que la intensitat cau de forma monòtona entre
`0°`, `2°` i `8°`, que és zero a `-2°` d'altitud solar i que una terbolesa més
alta eixampla l'aurèola a `5°`.

### Arquitectura implementada

#### Domini i bridge

- `LightingEnvironmentComposer` deriva un DTO renderer-neutral dels snapshots
  existents de cel i sistema solar, sense recalcular efemèrides.
- La direcció de cada llum és ENU `[East, Up, North]`, normalitzada i validada.
- La magnitud aparent lunar no es torna a multiplicar per fase i distància; el
  fallback només usa aquests factors quan la magnitud no existeix.
- La paleta lineal de cel és compartida per atmosfera i llum difusa.
- Bortle/SQM no crea cap llum local fictícia.
- El missatge `lighting_environment_snapshot` és JSON compacte i no transporta
  textures, geometries ni recursos Gaia.

#### Escena persistent

- Existeix un únic `lightingRoot` persistent.
- Conté un `DirectionalLight` solar, un `DirectionalLight` lunar i un
  `HemisphereLight` difús encapsulat com a aproximació renderer-side.
- No s'utilitza `AmbientLight`.
- Els snapshots obsolets es descarten i els canvis normals s'interpolen durant
  un segon; els salts temporals grans i els canvis d'activació fan snap.
- La càmera només mou la regió local d'ombres i mai altera el vector científic.
- `dispose()` retira les llums i allibera els shadow maps de forma idempotent.

#### PBR, color i ombres

- El terreny tècnic i només els objectes locals explícits utilitzen
  `MeshStandardMaterial`; no hi ha conversió indiscriminada de l'escena.
- Terreny: `metalness=0`, `roughness=0.92`.
- Les textures d'albedo es marquen sRGB i les normal/roughness/metalness/AO
  queden en `NoColorSpace`.
- El renderer usa color management explícit, sortida sRGB, `NoToneMapping` i
  exposició estàtica `1.0`, evitant una regressió de la capa celeste existent.
- Les qualitats d'ombra són `off`, `low=512`, `medium=1024` i `high=2048`.
- Les ombres solars tenen prioritat; les lunars queden opcionals/desactivades
  sense desactivar la llum lunar.
- La shadow camera local es recentra per texels i només s'invalida per direcció,
  canvi de regió, geometria o qualitat.

### Evidència automàtica

Execució final:

```text
backend:  40 passed
frontend typecheck: passed
frontend grid: 69 passed
frontend navigation: 18 passed
frontend solar system: 71 passed
frontend Step 8.6: 29 passed
frontend Step 8.7: 41 passed
frontend build: passed
```

Cobertura específica del Pas 8.7:

- Sol/Lluna alts, baixos i sota l'horitzó;
- Lluna plena, quart i nova, inclòs fallback sense magnitud;
- absència de doble aplicació de fase/distància lunar;
- hook acotat del Pas 9 amb valor base `1.0`;
- rebuig de NaN, infinits i vectors degenerats;
- coherència exacta de la paleta cel/difusa;
- direcció `DirectionalLight` coherent amb ENU→Three.js;
- 100 actualitzacions de timeline sense reconstruir llums ni materials;
- zero snapshots científics durant 120 moviments de càmera;
- descarte de generacions stale;
- PBR diferent per pla, pendent nord, pendent sud i vertical;
- qualitat i lifecycle d'ombres;
- color management i etiquetatge de textures;
- independència lunar respecte de les llums globals;
- independència del terreny respecte del vector Lluna→Sol;
- cara fosca lunar atmosfèrica amb opacitat base `0.015`;
- perfil físic-visual de l'halo solar.

### Prova integrada del bridge

Es va arrencar l'aplicació actual en `127.0.0.1:14408`, sense interferir amb la
instància de l'usuari de `14398`, i es va tancar amb `shutdown_complete`.

Resultat:

```text
lighting_environment_snapshot: 964 bytes
assets dins el snapshot: false
missatges lighting després de camera_changed amb temps pausat: 0
bytes binaris després de camera_changed amb temps pausat: 0
shutdown: net
```

Els `1,650,244` bytes binaris observats durant el handshake corresponen als
catàlegs inicials d'estrelles (`fallback` i `general`), no al snapshot ni a una
actualització d'il·luminació.

### Evidència visual i GPU pendent

No s'han pogut generar honestament des d'aquesta sessió:

- captures amb Sol alt i baix;
- captures Lluna plena/nova i nit fosca;
- comparació visual `shadows off/medium/high`;
- vídeo de sortida o posta;
- P50/P95 i memòria GPU mesurats en les quatre qualitats.

El navegador integrat no estava disponible per a automatització. Els comptadors
i la instrumentació necessaris sí que han quedat implementats al diagnòstic i al
missatge `frontend_performance_metrics`, però cal una passada visual/GPU en una
sessió WebGL real per completar aquesta part de l'evidència obligatòria.

### Fallbacks i límits

- Sense Sol vàlid: llum solar directa desactivada; cel/difusa continuen segons
  el snapshot disponible.
- Sense Lluna: llum lunar `unavailable`; la resta de l'entorn continua usable.
- Sense atmosfera: component difusa i halo atmosfèric desactivats.
- Sense shadow maps o amb pressupost insuficient: qualitat `off`, PBR disponible.
- `HemisphereLight` és una aproximació substituïble, no una dada científica.
- No hi ha autoexposure, HDR fotogràfic, scattering volumètric nou ni eclipsis.
