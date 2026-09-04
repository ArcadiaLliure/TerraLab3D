# Pas 8.5 — Superfície lunar LRO/LOLA, orientació física i libració real

> Estat: **completat**  
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

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

## Fonts a consultar

### TerraLab3D `main`

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

### TerraLab, només com a referència funcional

Consultar només quan aporti comportament científic o visual reutilitzable:

- `TerraLab/astro/engine.py`
- `TerraLab/astro/ephemeris_coordinator.py`
- `TerraLab/runtime/offscreen_renderer.py`
- tests de fases, orientació lunar o efemèrides que existeixin al checkout real.

No copiar una representació 2D de TerraLab si entra en conflicte amb el model persistent 3D de TerraLab3D.

### Fonts externes obligatòries

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

## Objectiu

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

## Tasques

### Dependència obligatòria del Pas 8

- [ ] Executar aquest pas només després que el Pas 8 estigui complet i estable.
- [ ] Reutilitzar la mateixa autoritat d’efemèrides del Pas 8.
- [ ] Reutilitzar el mateix Sol científic que governa atmosfera, disc solar i fase lunar.
- [ ] No crear un segon càlcul independent de Sol o Lluna només per al renderer.
- [ ] No modificar la semàntica de `ScientificObserver`.
- [ ] No convertir `CameraPose` en observador astronòmic.
- [ ] Mantenir la Lluna dins de `celestialRoot` perquè no presenti paral·laxi per translació de la càmera local.

### Recurs lunar neutre i procedència

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

### Pipeline d’assets

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

### Mapping cartogràfic i calibració fixa

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

### Orientació lunar científica

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

### Il·luminació, fase i terminador

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

### Renderer persistent

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

### Mida angular i geometria d’escena

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

### Bridge

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

### Integració amb l’arquitectura actual

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

### UI

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

### Fallback honest

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

## Proves obligatòries

### Ciència i orientació

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

### Mapping de textura

- [ ] Meridià central correcte.
- [ ] Nord lunar no està invertit.
- [ ] Est/oest no estan invertits.
- [ ] Cara propera correcta.
- [ ] Cara llunyana correcta durant libracions extremes.
- [ ] Seam a ±180° sense discontinuïtat visual greu.
- [ ] Cap flip vertical accidental.
- [ ] Validació amb almenys quatre accidents lunars coneguts en posicions distribuïdes.
- [ ] El mapping no varia amb la data: només varia `moonBodyRoot`.

### Fase i il·luminació

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

### Recursos i rendiment

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

## Criteri de sortida

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
- [ ] el Pas 8.6 encara no s’ha començat;
- [ ] el Pas 9 encara no s’ha començat.

## Evidència obligatòria

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

## Fora d’abast del pas

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
JPL/NAIF, a través de l’adaptador científic compatible (Skyfield/SPICE), defineix l’orientació;
l’efemèride del Pas 8 defineix la geometria Sol–Lluna–observador;
Three.js només representa aquest estat amb recursos persistents.
```

## Annex: Validació de la superfície i l’orientació lunar

### Resultat implementat

La Lluna és una esfera persistent dins de `celestialRoot`. `MoonSurfaceRenderer`
és propietari de `moonRoot`, `moonBodyRoot`, `moonSurfaceCalibration`, geometria,
material, albedo, normal map i lifecycle. Els snapshots només actualitzen posició,
mida angular, quaternion body-fixed, direcció Moon→Sun, visibilitat i uniforms.

La representació anterior del Pas 8 continua sent el fallback geomètric. L’albedo
LRO només s’activa quan el manifest local és vàlid **i** l’orientació
`MOON_ME_DE421` és precisa. La fase no forma part de l’albedo ni de l’alpha: el
terminador surt del producte entre la normal de superfície i la mateixa geometria
solar autoritativa del Pas 8.

### Fonts i procedència

- NASA SVS CGI Moon Kit: <https://svs.gsfc.nasa.gov/4720/>.
- Albedo mestre: `lroc_color_16bit_srgb_8k.tif`, mapa LROC 2025 sRGB, 8192×4096,
  SHA-256 `db7808e878b6a55eb409bb231eab8deb477f84b5c9d7396d76ff73e5d54992d9`.
- DEM: `ldem_16.tif`, LOLA float en quilòmetres respecte del radi 1737,4 km,
  SHA-256 `1ea42bf44f7e9d694f79c3afa7145f97fbf06cc67372067d9fe73dce43bad796`.
- Frame: `MOON_ME_DE421`, definit per `moon_080317.tf`, SHA-256
  `78732477b96f9863e7b0d65bcee3c22b8707ca5ed0db56d1173319cb2e8c7993`.
- Orientació: `moon_pa_de421_1900-2050.bpc`, SHA-256
  `656f90616403d75a75f0cd6c8830fc5b44f8cb4facb5ccb8915e752b397520cf`.
- Rang validat del PCK: `[1900-01-01, 2051-01-01)` UTC. Fora de rang s’emet
  `orientationQuality = out_of_range` sense extrapolació.

Crèdit mostrat al manifest i a la UI: NASA's Scientific Visualization Studio;
Ernie Wright (USRA); Noah Petro (NASA/GSFC); LROC WAC / Arizona State
University; Lunar Reconnaissance Orbiter Laser Altimeter (LOLA).

El manifest reproduïble és
[`docs/manifests/nasa-cgi-moon-kit-lro-lola-2025.json`](../manifests/nasa-cgi-moon-kit-lro-lola-2025.json)
i el contracte és
[`contracts/schemas/moon-surface-manifest.schema.json`](../../contracts/schemas/moon-surface-manifest.schema.json).

### Instal·lació explícita de la capa

No hi ha descàrregues en runtime. La instal·lació només es produeix amb:

```powershell
python -m pip install -r tools/requirements-moon-assets.txt
python tools/prepare_moon_surface_assets.py --data-root I:\TerraLab
```

El resultat queda a `I:\TerraLab\data\sky\moon` en aquest equip. El catàleg
`ManagedMoonSurfaceAssets` valida noms, mida i SHA-256 una vegada a l’arrencada.
El servidor només exposa els noms acceptats pel manifest sota `/moon-assets/`.
El bridge envia el descriptor i les URLs locals; `moon_bridge_texture_bytes = 0`.

No s’ha adoptat KTX2 perquè el projecte no inclou encara un encoder Basis ni el
transcoder local necessari. El pipeline actual genera JPEG sRGB 8K/4K i PNG
lineal per al normal map, amb mipmaps creats una sola vegada per Three.js.

### Convencions científiques i UV

- El PCK produeix ICRF→body; la transposada produeix body→ICRF.
- `ITRS.rotation_at(t)` i la localització geodèsica produeixen ICRF→ENU.
- `bodyToENUQuaternion` és `(x,y,z,w)` i usa eixos dretans East/North/Up.
- Els vectors del wire conserven l’ordre històric TerraLab3D East/Up/North.
- Una única conversió porta ENU a Three.js: `+X East`, `+Y Up`, `-Z North`.
- El mapa és equirectangular, centrat a longitud 0°, nord a dalt i longitud
  positiva cap a l’est.
- La calibració fixa és `Rx(+90°)` de la malla al body frame: longitud 0°→`+X`,
  nord→`+Z`, est→`+Y`. No depèn de data, observador ni càmera.

Accidents usats per a la inspecció del mapa: Copernicus (9,6°N, 20,1°O), Tycho
(43,3°S, 11,4°O), Aristarchus (23,7°N, 47,5°O) i Mare Crisium (~17°N, 59°E).
La cara propera queda centrada a 0° i el seam queda a ±180°.

### Rendiment i lifecycle

Memòria GPU aproximada per RGBA8 amb mipmaps (la compressió JPEG/PNG només
redueix disc i xarxa local):

| Configuració | Albedo | Normal LOLA | Total aproximat |
|---|---:|---:|---:|
| 8K + normal 4K | 170,67 MiB | 42,67 MiB | 213,33 MiB |
| fallback 4K + normal 4K | 42,67 MiB | 42,67 MiB | 85,33 MiB |

`renderer.capabilities.maxTextureSize` selecciona 8K o 4K. Les mètriques
separen construccions, càrregues d’albedo/normal, bytes estimats pujats i bytes
de textura pel bridge. `dispose()` invalida callbacks tardans, desconnecta el
root i allibera textures, material i geometria.

### Proves automatitzades

- Fixture oficial Skyfield: 2019-12-20 11:05 UTC dona libració `+1,520°` en
  longitud i `−6,749°` en latitud.
- El punt subobservador, transformat pel quaternion, coincideix amb la direcció
  Moon→observador amb error inferior a `3e-6` en vector unitari.
- Observadors en hemisferis diferents comparteixen sub-Earth però tenen
  sub-observer i quaternion local diferents.
- Missing kernel i out-of-range mantenen la Lluna del Pas 8.
- El mapping fixa longitude zero, nord i est sense flips.
- El límit GPU selecciona el fallback 4K; timeline no recarrega ni re-puja.
- Shutdown disposa totes les textures; manifest invàlid conserva fallback.
- El bridge no emet cap payload binari lunar.

Ordres de verificació:

```powershell
python -m pytest backend/tests -q
npm --prefix frontend run typecheck
npm --prefix frontend test
python tools/validate_skeleton.py
```

La inspecció visual dels derivats 4K confirma l’albedo neutre centrat a 0° i un
normal map LOLA coherent, sense ombres ni fase pre-renderitzades. La captura del
canvas i el vídeo de timeline queden com a evidència manual pendent perquè la
sessió d’implementació no disposava de cap navegador controlable; no se simulen
ni se substitueixen per una imatge sintètica.
