# Pas 8.6 — Planetes texturitzats, orientació física, anells i tots els satèl·lits naturals planetaris

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

> **Revisió 2026-08-09:** aquest pas incorpora les consideracions descobertes durant l’anàlisi específica dels anells de Saturn. Les conclusions de l’informe s’han integrat només després de corregir les diferències entre centre planetari i baricentre, B geocèntric/topocèntric, radis PCK, convenció ENU/Three.js i ordre de quaternions.

## Resultat funcional palpable

El Sistema Solar deixa de representar els planetes com a discos o esferes genèriques i passa a disposar d’una representació 3D persistent i físicament orientada dels planetes, els anells de Saturn i els satèl·lits naturals planetaris coneguts amb efemèride disponible.

En completar aquest pas:

- Mercuri, Venus, Mart, Júpiter, Saturn, Urà i Neptú utilitzen les textures planetàries locals ja disponibles;
- la Terra no es representa com a planeta visible des de l’observador terrestre, però continua existint com a cos científic i origen de l’observador;
- Plutó i el seu sistema de satèl·lits s’admeten dins del mateix model genèric de cossos, encara que no es presenti com a planeta;
- cada planeta té radi/forma, eix de rotació, orientació body-fixed i rotació compatibles amb el millor model carregat;
- l’aspecte il·luminat de cada planeta prové de la direcció física cap al Sol, no d’una fase pintada dins de la textura;
- Saturn presenta anells persistents orientats pel seu **pla equatorial real**;
- la inclinació aparent dels anells no es calcula com una rotació visual independent: emergeix de la geometria observador–Saturn–pla equatorial;
- les llunes es posicionen a partir d’efemèrides JPL/NAIF SPK i no d’el·lipses keplerianes simplificades;
- les òrbites planetocèntriques es poden mostrar com a geometries persistents mostrejades de l’efemèride;
- la informació d’orientació, forma, radi, textura i qualitat física és explícita per cos;
- un satèl·lit sense textura o sense model d’orientació continua apareixent a la posició correcta, sense inventar dades;
- el sistema és data-driven: afegir una lluna nova al catàleg o als kernels no requereix crear un renderer específic;
- la càmera local continua sense provocar cap recàlcul científic ni cap round-trip Python per frame.

## Abast exacte de “totes les llunes”

Per al criteri de completitud d’aquest pas, el catàleg canònic mínim és el de **Planetary Satellites** de JPL Solar System Dynamics.

Snapshot de referència a validar en iniciar la implementació:

```text
JPL SSD — 2026-07-09
Planetary Satellites total = 461

Terra      1
Mart       2
Júpiter  115
Saturn   293
Urà       29
Neptú     16
Plutó      5
---------
Total    461
```

Mercuri i Venus no tenen satèl·lits planetaris coneguts.

Aquest nombre **no s’ha de hardcodejar com una constant eterna**. Serveix com a fixture de cobertura del snapshot de dades utilitzat per desenvolupar aquest pas. El catàleg local ha de quedar versionat i actualitzable.

La Lluna terrestre ja queda especialitzada al Pas 8.5 i no s’ha de duplicar. El sistema genèric d’aquest pas, però, l’ha de reconèixer com el mateix concepte de `NaturalSatellite`/satèl·lit natural a nivell de domini.

Els satèl·lits de cossos menors —asteroides, TNO, Eris, Haumea, Makemake i sistemes similars— han de ser compatibles amb el model de domini genèric i amb un futur adaptador JPL Small-Body/Horizons, però **no poden degradar ni bloquejar la cobertura completa dels 461 planetary satellites** d’aquest pas.

## Fonts internes obligatòries

### TerraLab3D `main`

Abans d’implementar, revisar l’estat real de `main` després dels Passos 8 i 8.5. Preval el codi real sobre els noms conceptuals d’aquest document.

Revisar especialment:

- `EphemerisPort` o contracte equivalent creat al Pas 8;
- l’adaptador real d’efemèrides;
- `SolarSystemSnapshot` o estat equivalent;
- model de Sol, Lluna i planetes;
- renderer persistent de la Lluna creat/refinat al Pas 8.5;
- pipeline d’il·luminació Sol → cos;
- conversió ICRF/J2000 → ENU → Three.js;
- convenció d’eixos i quaternions;
- `celestialRoot`;
- bridge binari existent;
- sistema de recursos i manifests;
- UI `Cel → Sistema solar`;
- lifecycle de textures/materials/geometries;
- sistema de picking i labels existent.

No crear una segona autoritat de temps, observador, Sol o efemèrides.

### TerraLab, només com a referència funcional

Consultar en mode lectura:

- `TerraLab/astro/engine.py`;
- `TerraLab/astro/ephemeris_coordinator.py`;
- `TerraLab/runtime/offscreen_renderer.py`;
- `TerraLab/data/layer_manager.py`;
- qualsevol suport real de planetes, satèl·lits, fases, magnituds i textures que existeixi al checkout;
- tests d’efemèrides i sistema solar.

No copiar una representació 2D si entra en conflicte amb el model 3D persistent.

## Textures planetàries locals ja disponibles

La font visual planetària principal ja existeix fora del workspace.

Ruta lògica de runtime:

```text
[data_root]\sky\solar-system\planets
```

Ruta actual de desenvolupament:

```text
I:\TerraLab\data\sky\solar-system\planets
```

Regles obligatòries:

- [ ] Resoldre `data_root` des de `data_location.json`; **no hardcodejar `I:`** dins del codi de producció.
- [ ] Utilitzar `I:\TerraLab\data\sky\solar-system\planets` només com a ruta resolta de l’entorn de desenvolupament actual.
- [ ] Inspeccionar els fitxers reals de la carpeta abans de programar mappings.
- [ ] No assumir noms de fitxer que no existeixin.
- [ ] No redescargar textures que ja són presents.
- [ ] No copiar textures al workspace.
- [ ] No transportar textures pel bridge.
- [ ] No convertir textures a Base64.
- [ ] Preservar i documentar qualsevol fitxer de crèdits, llicència o metadades que ja acompanyi els assets.
- [ ] Generar un manifest local derivat dels fitxers reals, no una llista escrita a cegues.

Manifest conceptual mínim:

```text
bodyId
naifId
bodyName
sourceFile
resolvedPath
sha256
width
height
format
colorSpace
projection
centralMeridianDeg
uvFlipX
uvFlipY
uvRotationDeg
textureQuality
credits
license
```

Qualsevol `uvFlip*`, `uvRotationDeg` o offset fix ha de descriure **la convenció del dataset**, no corregir l’orientació astronòmica d’una data concreta.

## Fonts científiques externes obligatòries

### NASA/JPL NAIF — Generic Kernels

Font arrel:

`https://naif.jpl.nasa.gov/pub/naif/generic_kernels/`

Els tipus de kernel tenen responsabilitats separades:

```text
SPK  → posició i velocitat
PCK  → constants planetàries, forma i orientació IAU
LSK  → UTC ↔ ET/TDB i leap seconds
FK   → frames addicionals quan siguin necessaris
DSK  → forma irregular d’alta fidelitat quan existeixi i s’adopti explícitament
```

No barrejar aquestes responsabilitats dins del renderer.

### Separació obligatòria entre posició, orientació i frame local

Són responsabilitats científiques diferents i no es poden fusionar en un únic càlcul opac:

```text
SPK
→ on és el cos i amb quina velocitat es mou

PCK/FK/BPC
→ com està orientat el cos respecte de l’ICRF/J2000

Earth orientation + ScientificObserver
→ com es transforma l’estat ICRF/J2000 al frame local de l’observador
```

Per tant:

- [ ] la posició no es deriva del PCK;
- [ ] el pol/eix/meridià principal no es deriva de l’SPK;
- [ ] el renderer no pot reconstruir cap d’aquestes dues coses;
- [ ] el frame local de l’observador s’aplica després d’obtenir l’estat inercial coherent;
- [ ] totes tres etapes han de compartir el mateix instant ET/TDB i la mateixa política d’aberració.

No crear una API específica `pck_get_pole()` si SPICE ja pot proporcionar la transformació completa mitjançant `pxform()`; el pol es pot obtenir transformant l’eix +Z del frame body-fixed o extraient-lo de la matriu amb una convenció documentada.

### PCK genèric

Font preferent inicial:

`https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc`

`pck00011.tpc` conté models IAU/WGCCRE de rotació i radi per nombrosos planetes i satèl·lits.

Per a un cos amb model disponible, la informació rellevant és conceptualment:

```text
BODY<id>_POLE_RA
BODY<id>_POLE_DEC
BODY<id>_PM
BODY<id>_NUT_PREC_*
BODY<id>_RADII
```

No reimplementar manualment aquestes fórmules si la llibreria SPICE pot proporcionar directament la transformació del frame body-fixed.

### SPK planetaris i centres planetaris

No assumir que `de*.bsp` conté directament el centre de tots els planetes gegants.

En una efemèride planetària JPL com DE440:

```text
DE440
├── Sun (10)
├── Mercury (199)
├── Venus (299)
├── Earth (399)
├── Moon (301)
├── Jupiter barycenter (5)
├── Saturn barycenter (6)
├── Uranus barycenter (7)
├── Neptune barycenter (8)
└── Pluto barycenter (9)
```

Per Saturn, el centre físic `SATURN (699)` és proporcionat pels SPK del sistema saturnià que el contenen. `sat441.bsp`, per exemple, conté `SATURN (699)` juntament amb múltiples satèl·lits i segments necessaris de DE440.

Això implica que una consulta aparentment simple:

```python
spice.spkezr("SATURN", et, "J2000", aberration, "EARTH")
```

només és vàlida si el `KernelManifest` ha carregat una cadena completa de segments que permeti resoldre:

```text
Earth
→ Saturn barycenter
→ Saturn center (699)
```

Regles:

- [ ] no documentar `de*.bsp = planetes` i `sat*.bsp = només llunes` com una separació absoluta;
- [ ] distingir `planet/system barycenter` de `planet center`;
- [ ] validar amb `spkobj()`/coverage o mecanisme equivalent quins NAIF IDs conté realment cada kernel;
- [ ] fer que el manifest resolgui la cadena necessària per cos i instant;
- [ ] no dependre del nom del fitxer per inferir els bodies que conté.

### SPK de satèl·lits

Directori canònic:

`https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/`

Inventari i cobertura:

`https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/aa_summaries.txt`

NAIF distribueix un o diversos SPK per sistema planetari. No existeix l’obligació que un únic fitxer contingui totes les llunes d’un planeta.

Famílies a descobrir dinàmicament:

```text
mar*.bsp
jup*.bsp
sat*.bsp
ura*.bsp
nep*.bsp
plu*.bsp
```

Exemples existents en el snapshot 2026, **no llista hardcodejada de producció**:

```text
Mart
  mar099.bsp
  mar099s.bsp

Júpiter
  jup365.bsp
  jup347.bsp
  jup348.bsp
  jup349.bsp

Saturn
  sat393_daphnis.bsp
  sat415.bsp
  sat441.bsp
  sat455.bsp
  sat456.bsp
  sat457.bsp
  sat459.bsp
  sat480.bsp

Urà
  ura184_part-*.bsp
  i altres kernels de cobertura específica quan pertoqui

Neptú
  nep097.bsp
  nep098_part-*.bsp
  nep104.bsp
  nep105.bsp
  i kernels XL quan siguin necessaris per cobertura especial

Plutó
  plu060.bsp
```

La Lluna terrestre és una excepció: la seva efemèride forma part dels SPK planetaris `de*.bsp`, no del directori `spk/satellites`.

### LSK

Utilitzar un leap-seconds kernel compatible amb l’stack SPICE. En el snapshot 2026, `naif0012.tls` continua vigent.

No duplicar la conversió UTC → ET/TDB amb una fórmula casolana si SPICE ja és l’autoritat temporal per als kernels.

### JPL Solar System Dynamics

Catàleg de satèl·lits:

`https://ssd.jpl.nasa.gov/sats/`

Paràmetres físics:

`https://ssd.jpl.nasa.gov/sats/phys_par/`

Circumstàncies i inventari reconegut:

`https://ssd.jpl.nasa.gov/sats/discovery.html`

Els paràmetres físics poden incloure radi, GM, densitat i referències, però **no tots els satèl·lits disposen del mateix nivell de caracterització**.

## Decisió arquitectònica #1 — Una sola autoritat científica

El Pas 8 ja ha creat o adaptat una autoritat d’efemèrides. Aquest pas l’estén; no en crea una de paral·lela.

Si l’adaptador existent és Skyfield i pot carregar de manera robusta els SPK/PCK requerits:

```text
EphemerisPort existent
→ extensió de l’adaptador existent
```

Si la cobertura completa requereix SPICE/SpiceyPy:

```text
EphemerisPort existent
BodyOrientationPort
        ↑
SpiceEphemerisAdapter / SpiceOrientationAdapter
```

Però el domini no pot importar `spiceypy`, Skyfield ni Three.js.

Regla:

```text
una data
+ un observador científic
+ un conjunt de kernels
→ un únic estat científic coherent
```

No és acceptable:

```text
Skyfield calcula planetes
+
SPICE calcula llunes
+
fórmules manuals calculen Saturn
```

si no existeix una capa explícita que garanteixi que temps, frame, aberració i convencions són compatibles.

## Decisió arquitectònica #2 — Model genèric de cos

No crear:

```text
MercuryRenderer
VenusRenderer
MarsRenderer
JupiterRenderer
TitanRenderer
IoRenderer
...
```

Crear un model genèric equivalent conceptualment a:

```python
class TipusCosSistemaSolar(Enum):
    ESTRELLA = ...
    PLANETA = ...
    PLANETA_NAN = ...
    SATELLIT_NATURAL = ...

class QualitatModelFisic(Enum):
    MISSIO_ALTA_PRECISIO = ...
    IAU_PCK = ...
    RADI_MESURAT = ...
    RADI_ESTIMAT = ...
    POSICIO_SOLAMENT = ...
    NO_DISPONIBLE = ...

@dataclass(frozen=True)
class DefinicioCosSistemaSolar:
    id: str
    naif_id: int
    nom: str
    tipus: TipusCosSistemaSolar
    parent_naif_id: int | None
    frame_body_fixed: str | None
    radii_km: tuple[float, float, float] | None
    textura: str | None
    qualitat_textura: str
    qualitat_orientacio: QualitatModelFisic
    qualitat_forma: QualitatModelFisic
```

Els noms definitius han de respectar l’arquitectura real del repositori i la norma general de català del projecte.

## Decisió arquitectònica #3 — Estat científic separat de l’estat visual

Estat científic mínim per cos:

```text
bodyId
naifId
parentNaifId
instantET
referenceFrame
positionICRFKm
velocityICRFKmS
distanceObserverKm
directionENU
angularRadiusRad
phaseAngleRad
illuminatedFraction
bodyFixedFrame
bodyToICRFQuaternion
bodyToENUQuaternion
radiiKm
orientationQuality
shapeQuality
ephemerisQuality
```

Estat visual:

```text
visible
renderScale
textureResourceId
materialVariant
lod
labelVisible
orbitVisible
pickingEnabled
```

El renderer no pot calcular RA/Dec del pol, inclinacions orbitals, elements keplerians o temps SPICE.

## Posicions dels satèl·lits

La font de posició és l’SPK.

Flux científic preferent:

```text
UTC
→ ET/TDB
→ SPK
→ estat del satèl·lit en J2000/ICRF
→ composició amb el sistema planetari
→ correccions observacionals compatibles amb el Pas 8
→ transformació topocèntrica de ScientificObserver
→ ENU
→ direcció celestial
→ estat renderer-neutral
```

La relació pare-fill és científica:

```text
Titan.parent = Saturn
Io.parent = Jupiter
Triton.parent = Neptune
```

però **no obliga** que el node Three.js de la lluna sigui fill directe del node traduït del planeta. Si `celestialRoot` representa direccions a distància virtual, l’arbre de render ha de respectar aquesta convenció i no introduir errors de paral·laxi per una jerarquia inadequada.

## Transformació ICRF/J2000 → frame local de l’observador

La representació correcta respecte de l’horitzó requereix una transformació explícita des del frame inercial a un frame local dependent de `ScientificObserver` i de l’instant.

No és acceptable que el pol de Saturn, el planeta o els anells es transformin només una vegada a un frame fix terrestre: l’orientació respecte de l’horitzó canvia amb la rotació de la Terra i amb la ubicació de l’observador.

Flux preferent d’alta precisió:

```text
ICRF/J2000
→ Earth orientation a l’instant ET
→ ITRF93 / Earth-fixed
→ base local de l’observador
→ ENU canònic (East, North, Up)
→ convenció TerraLab3D (East, Up, North)
→ Three.js
```

Quan s’utilitzi SPICE per a orientació terrestre precisa, preferir un binary Earth PCK d’alta precisió per a `ITRF93` dins del seu coverage. No utilitzar silenciosament `IAU_EARTH` com a equivalent d’alta precisió.

Si el pipeline existent del Pas 3/Pas 8 utilitza LST i fórmules astronòmiques validades, mantenir una única implementació coherent. En aquest cas:

```text
latitud + LST
```

és suficient per a la transformació horitzontal si `LST` ja incorpora la longitud. No passar `longitude` i `LST` com si fossin graus de llibertat independents ni sumar la longitud dues vegades.

Convenció espacial ja establerta a TerraLab3D:

```text
Three.js / celestial local
+X = Est
+Y = Amunt
+Z = Nord
```

Per tant, si una funció científica retorna ENU canònic `(E, N, U)`, l’adaptador a Three.js ha de fer explícitament:

```text
(E, N, U) → (X, Y, Z) = (E, U, N)
```

I l’elevació geomètrica es deriva de la component **Up**, no de `Z`:

```python
geometric_elevation_rad = asin(direction_local_y / norm(direction_local))
```

si el vector ja està expressat en la convenció Three.js/TerraLab3D.

Contracte conceptual recomanat:

```python
class CelestialFrameTransformPort(Protocol):
    def icrf_to_local_enu(
        self,
        vector_icrf: Vector3,
        observer: ScientificObserver,
        instant: SimulationInstant,
    ) -> Vector3:
        ...
```

Requisits:

- [ ] reutilitzar la transformació topocèntrica autoritativa ja existent al Pas 8;
- [ ] no crear una transformació específica només per Saturn;
- [ ] provar latituds i longituds diferents a la mateixa UTC;
- [ ] provar ambdós hemisferis;
- [ ] documentar clarament la convenció d’eixos de cada frontera;
- [ ] normalitzar vectors de direcció després de les transformacions quan pertoqui;
- [ ] no confondre una rotació de frame amb una translació topocèntrica;
- [ ] el `camera roll` només modifica la projecció visual, no el frame científic local.

## Aberració i light-time

La política d’aberració ha de ser única per a planetes i satèl·lits.

- [ ] Caracteritzar què utilitza el Pas 8.
- [ ] Utilitzar la mateixa semàntica per als satèl·lits.
- [ ] Documentar si l’estat és geomètric, `LT`, `LT+S`, `CN` o equivalent.
- [ ] No comparar fixtures generades amb polítiques diferents.
- [ ] No deixar que el frontend apliqui correccions addicionals.

## Orientació física dels planetes i llunes

Per als cossos amb frame IAU/PCK disponible, obtenir la transformació completa body-fixed → J2000/ICRF mitjançant la infraestructura científica.

Flux:

```text
instant ET
+ PCK/FK/BPC carregats
→ IAU_<BODY> o frame body-fixed compatible
→ matriu/quaternion body-fixed → J2000
→ J2000 → ENU observador
→ ENU → Three.js
→ bodyRoot.quaternion
```

Preferir operacions SPICE equivalents a `pxform()`/`sxform()` a reconstruir manualment RA, DEC i W.

La representació visual pot reutilitzar la mateixa estructura creada per a la Lluna al Pas 8.5:

```text
bodyRoot
├── orientationRoot
│   ├── surfaceMesh
│   └── ringSystem?     # quan pertoqui
└── label/picking auxiliars fora de la rotació de superfície si cal
```

No duplicar el pipeline lunar; extreure’n la part genèrica.

## Cossos sense model d’orientació

No totes les llunes disposen de model IAU fiable.

Cas de prova obligatori: **Hyperion**. El PCK genèric indica que no disposa d’un model d’orientació predictible a llarg termini perquè la seva rotació és caòtica.

Política:

```text
SPK disponible + orientació absent
→ posició correcta
→ mida coneguda/estimada si existeix
→ superfície neutra
→ orientationQuality = unavailable
→ no inventar rotació síncrona
```

No és acceptable aplicar automàticament “tidal lock” a totes les llunes.

## Forma i mida

Prioritat:

```text
1. shape model/DSK de missió adoptat explícitament
2. radii triaxials PCK
3. radi mesurat JPL
4. radi estimat documentat
5. punt/sprite unresolved si no existeix mida fiable
```

Per a un PCK triaxial:

```text
radii = (a, b, c)
```

Three.js ha de poder representar un el·lipsoide escalant una geometria base persistent.

No forçar una esfera quan `a`, `b` i `c` coneguts són significativament diferents i el cos té mida aparent suficient perquè importi.

## Reutilització del renderer lunar

Extreure del Pas 8.5 només allò que sigui realment genèric:

- [ ] càrrega persistent de textura;
- [ ] manifest i hash;
- [ ] geometria esfèrica/el·lipsoïdal reutilitzable;
- [ ] material il·luminat pel Sol;
- [ ] separació `bodyRoot` / `surfaceMesh`;
- [ ] aplicació de quaternion científic;
- [ ] gestió de LOD;
- [ ] lifecycle i `dispose`;
- [ ] counters de reconstrucció;
- [ ] picking;
- [ ] labels.

Mantenir específic de la Lluna:

- LRO/LOLA;
- libració i mètriques lunars especialitzades;
- `subEarth*`/`subObserver*` lunars si no són generalitzats amb sentit;
- recursos del Moon Kit.

No fer herència artificial només per compartir codi. Preferir composició de recursos i components visuals.

## Textures planetàries

Per cada planeta amb textura disponible:

```text
texture manifest
+ forma física
+ orientació body-fixed
+ direcció al Sol
→ material planetari
```

Requisits:

- [ ] Utilitzar textura global neutra; no una captura amb fase pre-renderitzada.
- [ ] Aplicar `colorSpace` correcte.
- [ ] Generar mipmaps quan pertoqui.
- [ ] No pujar la textura més d’una vegada per versió/recurs.
- [ ] No recrear material per tick.
- [ ] Separar transformació UV fixa del dataset de l’orientació científica.
- [ ] Documentar el meridià central i sentit de longitud del dataset quan es conegui.
- [ ] Validar visualment trets reconeixibles quan sigui possible.
- [ ] No afirmar fidelitat temporal de núvols/taques si la textura és estàtica.

Per Júpiter, Saturn, Urà i Neptú, una textura estàtica representa aparença visual de referència, no meteorologia epoch-correct. Aquesta limitació s’ha de documentar.

## Il·luminació solar direccional comuna

La fase ha de provenir de geometria física i el sistema ha de reutilitzar explícitament el pipeline d’il·luminació direccional introduït per a la Lluna.

```text
normal superfície
+ direcció cos → Sol
+ direcció cos → observador
→ il·luminació solar direccional
→ terminador
→ fase aparent
```

Responsabilitats:

```text
Python / ciència
→ calcula Body → Sun direction en un frame autoritatiu
→ transforma la direcció al frame renderer-neutral necessari

Three.js
→ aplica la direcció rebuda al material/shader
→ calcula N·L i la resposta visual
→ no calcula efemèrides
```

No és obligatori materialitzar el Sol com un únic `THREE.DirectionalLight` global. Per fidelitat geomètrica, cada cos ha de disposar de la seva pròpia `bodyToSunDirection`, perquè la direcció local cap al Sol no és exactament idèntica per a tots els cossos del Sistema Solar.

Implementacions acceptables:

```text
uniform bodyToSunDirection
```

o un mecanisme equivalent basat en llum direccional, sempre que:

- [ ] la direcció provingui de l’efemèride autoritativa;
- [ ] no estigui enganxada a la càmera;
- [ ] el costat nocturn existeixi geomètricament i no sigui una màscara alpha;
- [ ] la textura no contingui fase pre-renderitzada;
- [ ] la il·luminació es calculi en espai lineal;
- [ ] no s’afegeixi una llum ambient arbitrària que destrueixi el terminador;
- [ ] la direcció solar s’actualitzi només quan ho exigeixi el tick científic/tolerància angular, no per frame;
- [ ] el mateix contracte funcioni per planetes i satèl·lits naturals.

No utilitzar:

```text
planetTexture_phase_25.png
planetTexture_phase_50.png
```

No duplicar el Sol ni crear un segon model solar per Saturn. Reutilitzar la mateixa autoritat Sol/efemèrides del Pas 8/8.5.

## Saturn — orientació física, equador i separació de la rotació superficial

Saturn és un cas especial visual, no científicament excepcional.

El PCK defineix el frame body-fixed i els radis/forma del planeta. El pla equatorial queda determinat directament pel pol nord:

```text
p = vector unitari del pol nord
pla equatorial = { v | dot(v, p) = 0 }
normal del pla equatorial = p
pla principal dels anells ≈ pla equatorial
```

No calcular un segon “angle d’inclinació dels anells” per orientar el mesh.

Tanmateix, cal separar dues rotacions que el frame body-fixed complet combina:

```text
orientació de l’eix/pol
→ defineix equador i pla dels anells

W / prime meridian
→ rotació de la superfície de Saturn al voltant del seu eix
```

Els anells **no són solidaris amb la rotació W de la superfície**: les partícules orbiten diferencialment. Geomètricament, aplicar W no canvia el pla dels anells perquè és una rotació al voltant de la seva normal, però no s’ha de fer que una textura/estructura azimutal dels anells giri com si fos enganxada al meridià de Saturn.

Arbre recomanat:

```text
saturnRoot
└── equatorialOrientationRoot      # orienta pol/equador, sense semàntica de spin dels anells
    ├── surfaceSpinRoot            # aplica W al planeta/textura
    │   └── planetSurface
    └── ringSystem                 # comparteix el pla equatorial, no el spin superficial
```

Per obtenir l’orientació:

- [ ] preferir `pxform()`/frame SPICE a reconstruir RA/DEC/W a mà;
- [ ] obtenir el pol transformant l’eix +Z del frame body-fixed o mitjançant una extracció de matriu documentada;
- [ ] derivar una base equatorial estable si el renderer necessita un quaternion complet;
- [ ] si el recurs dels anells és purament radial/axisimètric, només la normal del pla és físicament rellevant;
- [ ] si existeix textura amb estructura azimutal, documentar explícitament quina convenció física/visual en determina l’azimut.

## Saturn — matriu SPICE i quaternion Three.js

SPICE treballa naturalment amb matrius de rotació; Three.js aplica habitualment quaternions.

Exemple conceptual:

```python
body_to_icrf_matrix = spice.pxform("IAU_SATURN", "J2000", et)
body_to_enu_matrix = icrf_to_enu_matrix @ body_to_icrf_matrix
body_to_enu_quaternion = matrix_to_quaternion(body_to_enu_matrix)
```

La conversió ha de preservar handedness i convenció d’eixos. El contracte del bridge ha de fixar **un únic ordre de components**.

Per compatibilitat directa amb `THREE.Quaternion.set(...)`, utilitzar:

```text
[x, y, z, w]
```

No enviar `[w, x, y, z]` i passar-lo directament a `Quaternion.set(x, y, z, w)`.

Provar sempre:

```text
matriu SPICE
→ quaternion backend
→ quaternion Three.js
→ vector base transformat
```

contra la transformació matricial original dins tolerància.

## Saturn — angle d’obertura B: geocèntric vs topocèntric

`B` és útil com a **mètrica diagnòstica**, no com a autoritat de rotació.

Cal distingir dues definicions:

```text
B_geocentric
→ direcció Saturn → centre de la Terra
→ mateix valor per a tots els observadors terrestres a un instant

B_topocentric
→ direcció Saturn → observador real
→ pot variar lleument amb la ubicació per paral·laxi
```

Conceptualment:

```text
B = asin(dot(n_ring_j2000, direction_saturn_to_observer_j2000))
```

No utilitzar la direcció inversa sense documentar el signe.

Per Saturn, la diferència topocèntrica és petita perquè és molt llunyà, però **no és matemàticament zero**. Per tant, no és correcte provar que un únic `B` topocèntric sigui idèntic per a qualsevol latitud/longitud.

Requisits:

- [ ] exposar `ringOpeningGeocentricDeg` si es vol una mètrica comuna comparable amb almanacs;
- [ ] exposar `ringOpeningTopocentricDeg` només si és útil per diagnòstic de la vista real;
- [ ] no utilitzar cap dels dos per rotar `ringSystem`;
- [ ] la inclinació aparent respecte de l’horitzó emergeix de `equatorialOrientationRoot` + frame local de l’observador + càmera;
- [ ] el canvi d’ubicació pot canviar l’orientació aparent respecte de l’horitzó encara que `B_geocentric` es mantingui.

## Saturn — radi i forma des del PCK

No hardcodejar el radi de Saturn com a constant de renderer.

Obtenir-lo de la font PCK activa:

```python
radii = spice.bodvrd("SATURN", "RADII", 3)
```

Amb `pck00011.tpc`, el fixture de referència és:

```text
BODY699_RADII = (60268, 60268, 54364) km
```

No confondre aquests radis IAU/PCK amb constants de models dinàmics que poden aparèixer dins dels comentaris d’un SPK saturnià; per exemple, SAT441 documenta un `RADIUS = 60330 km` utilitzat pel seu model dinàmic, que no substitueix `BODY699_RADII` com a forma visual/cartogràfica de Saturn.

## Saturn — aparença dels anells emergeix de la geometria

La geometria 3D és l’autoritat visual:

```text
pol/equador real
+ transformació ICRF → local observador
+ projecció de càmera
→ obertura i angle aparent dels anells
```

No implementar:

```typescript
ringGroup.rotation.x = calculateRingOpening(date);
```

Ni modificar artificialment l’opacitat només perquè `abs(B) < llindar`.

Quan els anells són gairebé de cantell, la geometria ha de col·lapsar naturalment cap a una línia prima. Els artefactes subpíxel s’han de resoldre amb tècniques de rasterització/coverage, no falsificant la física.

Cas límit `B ≈ 0°`:

- [ ] geometria estable sense NaN ni flips;
- [ ] no invertir UV ni normal arbitràriament en canviar el signe;
- [ ] evitar z-fighting;
- [ ] conservar gruix físic/visual documentat si se’n modela un;
- [ ] permetre AA/alpha-to-coverage o estabilització subpíxel si és necessària;
- [ ] qualsevol “visibility aid” que faci els anells més gruixuts/opacs ha de ser opcional i marcat com a no científic.

## Saturn — geometria dels anells

Font de dimensions a documentar:

`https://nssdc.gsfc.nasa.gov/planetary/factsheet/satringfact.html`

La representació mínima fidedigna ha d’incloure:

- anell C;
- anell B;
- divisió de Cassini;
- anell A;
- opcionalment D/F/G/E segons LOD i qualitat visual.

Fixture radial de referència de la NASA Saturnian Rings Fact Sheet:

```text
Saturn equator        60 268 km
C inner edge          74 658 km
C outer / B inner     91 975 km
B outer edge         117 507 km
A inner edge         122 340 km
A outer edge         136 780 km
F ring               139 826 km
```

La divisió de Cassini és la regió principal entre l’outer edge de B i l’inner edge d’A; no reduir-la a un únic radi sense amplada.

Aquests valors són fixtures de font, no literals dispersos pel renderer. Han de viure en dades/versionat/provenance i poder-se substituir per una font millor sense canviar el codi visual.

No és necessari modelar partícules individuals.

Geometria recomanada:

```text
RingGeometry / BufferGeometry annular persistent
+ coordenada radial normalitzada
+ mapa d’opacitat/color radial
+ material de doble cara amb il·luminació/transmissió controlada
```

Si la carpeta de textures planetàries conté una textura o alpha real dels anells:

- [ ] detectar-la al manifest;
- [ ] documentar-ne procedència i mapping;
- [ ] utilitzar-la sense duplicar-la al workspace.

Si no existeix:

- [ ] implementar un fallback radial procedimental clarament identificat com a aproximació visual;
- [ ] conservar dimensions i orientació físiques;
- [ ] representar variació radial d’opacitat/albedo entre C, B, Cassini i A amb paràmetres documentats, no amb un únic color pla;
- [ ] no hardcodejar colors hex com si fossin fotometria científica; qualsevol paleta procedimental ha de quedar marcada com `VISUAL_REFERENCE`;
- [ ] no inventar estructura fina de Cassini/Cassini Division més enllà del model documentat.

El fallback pot utilitzar geometries separades per bandes o una única geometria annular amb coordenada radial. La decisió ha de prioritzar persistència GPU, transicions radials i absència de seams.

## Saturn — oclusió correcta planeta/anells

Requisits visuals:

- [ ] la meitat posterior dels anells queda ocultada pel planeta quan geomètricament correspon;
- [ ] la meitat anterior passa davant del disc;
- [ ] el depth buffer decideix la intersecció, no una màscara 2D manual;
- [ ] utilitzar material de doble cara (`DoubleSide` o shader equivalent) perquè el pla es pugui observar des del nord i des del sud;
- [ ] no aplicar simplement “la cara posterior rep menys llum”: la resposta ha de dependre de la direcció real Ring → Sun, de la normal del pla i, si existeix, del perfil radial d’opacitat/transmissió;
- [ ] calcular com a diagnòstic el signe de l’elevació del Sol sobre el pla dels anells per distingir cara solar i cara oposada;
- [ ] els anells poden mostrar cara il·luminada i transmesa/no il·luminada de manera diferenciada si el material ho suporta;
- [ ] el canvi de signe de `B` no provoca un flip artificial de textura;
- [ ] no hi ha z-fighting al pla equatorial;
- [ ] els anells continuen correctes amb resize, FOV i roll de càmera.

## Saturn — ombres entre planeta i anells

Distingir tres fenòmens:

```text
Saturn → ombra sobre els anells
anells → atenuació/ombra sobre Saturn
self-shadow microscòpic entre partícules dels anells
```

Per una renderització fidedigna, els dos primers són efectes macroscòpics reals i han de quedar previstos pel contracte d’il·luminació. No afirmar que “els anells no tenen ombra”.

Abast d’aquest pas:

- [ ] preparar la geometria/inputs perquè Saturn pugui bloquejar la llum solar que arriba a una regió dels anells;
- [ ] preparar la contribució d’opacitat radial perquè els anells puguin atenuar la llum solar sobre Saturn;
- [ ] preferir una solució analítica en shader basada en Sol–Saturn–pla dels anells si evita shadow maps innecessaris;
- [ ] si aquests dos efectes no s’implementen en aquesta iteració, marcar-los explícitament com a `pending fidelity`, no com a físicament inexistents;
- [ ] deixar fora de l’abast el self-shadow microscòpic/mútua ocultació entre partícules individuals i la dispersió múltiple d’alta fidelitat.

## Altres sistemes d’anells

Júpiter, Urà i Neptú també tenen sistemes d’anells.

Aquest pas ha de deixar el contracte `RingSystem` genèric i evitar que Saturn sigui una excepció arquitectònica.

Abast mínim:

- Saturn: render complet del sistema principal d’anells.
- Júpiter/Urà/Neptú: suport estructural i render opcional si existeixen recursos/dades suficients en el projecte; no inventar una textura.

La manca de recursos visuals dels anells febles no pot impedir l’orientació correcta del planeta.

## Catàleg de satèl·lits

Crear un procés reproduïble de construcció del catàleg, no 461 entrades manuals.

Flux:

```text
JPL satellite catalogue snapshot
+ aa_summaries.txt
+ kernels instal·lats
+ PCK/physical parameters
→ satellite_catalog.json/bin
→ validació de cobertura
```

Camps mínims:

```text
catalogVersion
catalogDate
naifId
name
provisionalDesignation
parentNaifId
parentName
spkKernelIds
spkCoverageStartET
spkCoverageEndET
bodyFixedFrame
hasOrientationModel
orientationSource
radiiKm
meanRadiusKm
physicalParameterSource
textureResourceId
textureQuality
shapeQuality
ephemerisQuality
```

No generar un nom fictici per a satèl·lits que només tenen designació provisional.

## Descobriment i manifest de kernels

Crear un `KernelManifest` versionat.

No confiar en “carrega aquests 10 fitxers per sempre”.

El manifest ha de saber:

```text
kernelId
fileName
kernelType
sourceUrl
sha256
coverage
bodyIds
priority
compatibleEphemerisFamily
installed
```

La selecció de kernels ha de resoldre cobertura per cos i data.

Si dos kernels cobreixen el mateix cos:

- [ ] definir precedència explícita;
- [ ] evitar que l’ordre accidental de `furnsh()` decideixi silenciosament;
- [ ] registrar quin kernel ha guanyat;
- [ ] provar el resultat.

## Gestió de kernels com a dades externes

Els SPK/PCK/LSK grans no han de viure al repositori Git.

Ruta lògica recomanada sota el `data_root`:

```text
[data_root]\sky\solar-system\kernels\
├── lsk\
├── pck\
├── spk\
│   ├── planets\
│   └── satellites\
└── manifests\
```

Ruta de desenvolupament resultant:

```text
I:\TerraLab\data\sky\solar-system\kernels\...
```

Aquest pas ha de reutilitzar el gestor de dades/capes existent per instal·lar i verificar kernels, però no ha de copiar-los al workspace.

Requisits:

- [ ] descàrrega explícita iniciada per l’usuari o pel gestor de dades segons la política existent;
- [ ] checksum;
- [ ] versió;
- [ ] rang temporal;
- [ ] provenance;
- [ ] retry idempotent;
- [ ] no descàrrega silenciosa dins del render loop;
- [ ] no accés a Internet necessari durant una sessió normal si els kernels ja són instal·lats.

## Política de cobertura temporal

Cada SPK té un interval vàlid.

Per cos i instant:

```text
IN_RANGE
OUT_OF_RANGE
NO_KERNEL
AMBIGUOUS_KERNEL
ERROR
```

No extrapolar silenciosament un SPK fora del seu rang.

Fallback:

```text
planetary satellite without valid SPK at instant
→ no inventar posició
→ cos unavailable per aquell instant
→ mostrar estat de cobertura
→ conservar la resta del sistema
```

Si existeix una efemèride alternativa autoritzada, utilitzar-la només si està declarada al manifest i validada.

## Elements orbitals

Els elements orbitals JPL poden conservar-se com a metadades:

```text
a
e
i
Ω
ω
M
period
referencePlane
referenceEpoch
```

Però la posició runtime **no** s’ha de reconstruir a partir d’aquests elements si hi ha SPK.

Regla:

```text
SPK posiciona;
elements orbitals descriuen.
```

Els elements són útils per:

- HUD;
- inspecció;
- classificació;
- estadístiques;
- interval inicial de mostreig d’òrbita;
- fallback només si algun futur requeriment ho autoritza explícitament.

## Òrbites de satèl·lits — semàntica

Aquest pas introdueix **òrbites planetocèntriques de context**, no les trajectòries topocèntriques temporals del Pas 9.

Diferència:

```text
Pas 8.6
→ “quina és la geometria de l’òrbita d’aquesta lluna al voltant del seu pare?”

Pas 9
→ “per on es veurà moure aquest cos al cel de l’observador durant un interval?”
```

No barrejar-les.

## Òrbites de satèl·lits — generació

No dibuixar una el·lipse kepleriana ideal com a font principal.

Mostrejar l’SPK:

```text
satellite
+ parent
+ [t0, t1]
+ sampleCount
→ state(t0)...state(tN)
→ vectors planetocèntrics
→ orbit buffer
```

L’interval pot ser:

- un període orbital si existeix un període fiable;
- un interval configurable al voltant de l’època;
- un interval limitat pel coverage de l’SPK.

Per òrbites irregulars/pertorbades, la corba **no té obligació de tancar exactament**.

Metadades de la geometria:

```text
bodyId
parentId
t0ET
t1ET
sampleCount
frame
kernelGeneration
orbitGeneration
```

## Òrbites — persistència i rendiment

Python calcula/mostreja; Three.js conserva.

```text
Python
→ orbit points binaris
→ bridge una vegada per generació
→ THREE.BufferGeometry
→ GPU resident
```

No enviar 461 òrbites a cada tick.

Regenerar només quan canvia alguna dependència real:

```text
kernelGeneration
interval
samplingPolicy
body selection / system selection
```

No regenerar per:

- càmera;
- pan;
- zoom;
- FOV;
- resize;
- walk/flight;
- canvi d’un segon si l’interval de l’òrbita no ha canviat.

## LOD de satèl·lits

“Tots disponibles” no significa “461 meshes d’alta resolució i 461 labels sempre visibles”.

Política de representació:

```text
LOD 0 — unresolved point/sprite
LOD 1 — disc/esfera simple
LOD 2 — esfera/el·lipsoide amb material físic
LOD 3 — textura disponible
LOD 4 — shape model/normal map de missió si existeix
```

La selecció de LOD pot dependre de:

- mida angular;
- FOV;
- cos seleccionat;
- mode d’inspecció;
- pressupost GPU;
- qualitat física disponible.

La ciència no canvia amb el LOD.

## Política de textura dels satèl·lits

No existeix textura global fiable per a totes les llunes.

Prioritat:

```text
1. textura científica/mission-derived local amb llicència/procedència
2. albedo/color de referència documentat
3. material neutre sense textura
4. punt unresolved
```

No utilitzar una textura genèrica “rock.jpg” per a centenars de llunes i presentar-la com a fidel.

Per a satèl·lits majors amb recursos fiables disponibles en el projecte —Io, Europa, Ganimedes, Cal·listo, Tità, Tritó, etc.— el mateix pipeline de recursos ha de permetre incorporar textures posteriorment sense canviar la ciència ni el renderer genèric.

## Qualitat científica explícita

Per cada cos:

```text
ephemerisQuality
orientationQuality
shapeQuality
textureQuality
```

Valors conceptuals:

```text
HIGH_PRECISION
IAU_MODEL
MEASURED
ESTIMATED
VISUAL_REFERENCE
UNAVAILABLE
OUT_OF_RANGE
```

La UI de diagnòstic i els logs han de poder explicar per què un cos es veu com una esfera neutra o no rota.

## Sistema de coordenades i escala

No introduir quilòmetres astronòmics directament a `worldRoot` en metres locals.

Separar:

```text
worldRoot
→ metres locals de terreny/càmera

celestialRoot
→ direccions/escala celestial
```

Els satèl·lits han de conservar la seva separació angular real respecte del planeta vista per `ScientificObserver`.

No utilitzar una escala visual arbitrària que faci que Io aparegui més separat de Júpiter del que correspon sense marcar-ho com a mode ampliat.

Si s’afegeix un mode d’exageració visual per fer visibles llunes minúscules:

- [ ] ha de ser opcional;
- [ ] ha de ser explícit;
- [ ] no ha d’alterar el picking científic;
- [ ] el mode fidedigne 1:1 ha de continuar disponible.

## Mida aparent

Per cossos resolubles:

```text
angularRadius = atan2(physicalRadius, observerDistance)
```

Per el·lipsoides, la silueta pot aproximar-se amb els radii triaxials i l’orientació quan la mida angular ho justifiqui.

No establir un mínim de píxels científicament fals. Si cal un mínim visual per picking, separar:

```text
renderedBodySize
pickingHitArea
```

## Magnitud i visibilitat

Reutilitzar el model del Pas 8 quan existeixi.

Per satèl·lits sense model fotomètric fiable:

- no inventar magnitud;
- utilitzar `magnitude = null`;
- permetre visibilitat per selecció/LOD si l’usuari activa el sistema;
- diferenciar “no visible físicament a simple vista” de “no carregat”.

## Elevació, horitzó i hook de refracció

La visibilitat no és una propietat exclusiva de Saturn; ha de reutilitzar el pipeline d’oclusió/horitzó del Pas 8.

Estat mínim útil:

```text
geometricElevationDeg
horizonElevationDeg
horizonVisible
refractionApplied
```

Amb la convenció TerraLab3D `+Y = Up`, l’elevació es deriva de la component local vertical. No utilitzar `directionENU.z` com a `Up` si el vector ja ha estat adaptat a `(East, Up, North)`.

Política:

- [ ] calcular elevació geomètrica en el frame local;
- [ ] reutilitzar l’horitzó pla existent del Pas 8 fins que el Pas 15 aporti perfil DEM;
- [ ] no posar `mesh.visible = false` amb una regla Saturn-específica si el sistema compartit d’oclusió ja resol el cas;
- [ ] mantenir separat `geometricElevation` de qualsevol futura `apparentElevation` refractada;
- [ ] deixar un hook de correcció atmosfèrica al pipeline observacional, però **no implementar refracció al Pas 8.6**;
- [ ] la futura refracció pot alterar posició/elevació aparent prop de l’horitzó, però no l’orientació body-fixed ni el pla físic dels anells.

## UI

Integrar dins de la jerarquia existent:

```text
Cel
└── Sistema solar
    ├── Sol
    ├── Lluna
    │   └── Superfície LRO/LOLA
    ├── Planetes
    │   ├── Textures
    │   └── Orientació física
    ├── Anells planetaris
    │   └── Saturn
    └── Satèl·lits naturals
        ├── Tots
        ├── Mart
        ├── Júpiter
        ├── Saturn
        ├── Urà
        ├── Neptú
        ├── Plutó
        ├── Òrbites
        └── Etiquetes
```

No crear un panell flotant nou.

Controls mínims:

- [ ] toggle general de satèl·lits;
- [ ] toggle per sistema planetari;
- [ ] toggle d’òrbites;
- [ ] toggle d’etiquetes;
- [ ] toggle d’anells planetaris;
- [ ] selector de nivell de detall `Auto / Fidedigne / Diagnòstic` si l’arquitectura UI ho admet;
- [ ] estat de kernels instal·lats;
- [ ] estat de cobertura de la data seleccionada;
- [ ] recompte `catalogats / amb efemèride / visibles / renderitzats`.

No mostrar 461 caselles individuals per defecte.

## Picking i inspecció

Els planetes i satèl·lits han de ser seleccionables amb el sistema de picking existent.

Informació d’inspecció mínima:

```text
nom
NAIF ID
tipus
pare
RA/Dec o Az/Alt
separació respecte del planeta pare
distància a l’observador
radi/diàmetre
mida angular
fase si aplica
kernel SPK actiu
coverage
frame d’orientació
qualitat d’orientació
qualitat de forma
textura/font visual
```

Si hi ha elements orbitals descriptius:

```text
semieix major
excentricitat
inclinació
període
pla de referència
```

## Bridge

No enviar objectes JSON gegants per tick.

Contractes conceptuals:

```text
solar_system_catalog_manifest
solar_system_resource_manifest
solar_system_state_delta
body_orientation_delta
orbit_geometry_ready
orbit_geometry_binary
kernel_status_changed
```

Separar:

```text
catàleg estàtic       → una vegada per generació
estat dinàmic         → deltes petits
òrbites               → binari per generació
textures              → URL/path local gestionat pel frontend, mai bridge bytes
```

Per tick ordinari, enviar només els cossos que realment necessitin actualització segons la política temporal.

## Política temporal

No totes les propietats s’actualitzen a la mateixa freqüència.

```text
camera frame
→ frontend only

clock interpolation
→ frontend

authoritative celestial state
→ tick científic Python

body axis / pole orientation
→ cache per tolerància angular; evoluciona molt més lentament que la posició orbital

body prime-meridian rotation W
→ tick científic/interpolació quan la textura body-fixed ho exigeixi

ring-plane orientation
→ depèn de l’eix/pol, no de W; no reconstruir geometria

orbit geometry
→ només canvi de generació

texture
→ només canvi de recurs
```

No consultar SPICE 461 × 60 vegades per segon.

## Batch científic

L’adaptador d’efemèrides ha de poder resoldre lots.

Preferir:

```text
get_states(body_ids, et, observer)
```

a:

```text
for body in 461:
    bridge_request(body)
```

SPICE viu a Python i pot fer les consultes necessàries dins d’una operació de domini/aplicació. El frontend mai fa polling per cos.

## Cache

Caches separades:

```text
kernel cache
catalog cache
body constants cache
orientation frame cache
orbit sample cache
texture resource cache
```

Claus mínimes d’òrbita:

```text
bodyId
kernelGeneration
t0ET
t1ET
sampleCount
frame
```

Claus mínimes d’orientació:

```text
bodyId
kernelGeneration
instant bucket/tolerance
```

No cachejar silenciosament fora del rang de cobertura.

## Lifecycle SPICE

La càrrega de kernels ha de ser idempotent.

Requisits:

- [ ] carregar cada kernel una sola vegada per lifecycle;
- [ ] registrar la generació activa;
- [ ] descarregar/netejar de manera controlada en shutdown si l’adaptador ho requereix;
- [ ] evitar `furnsh()` repetit per tick;
- [ ] evitar estat global no controlat en tests;
- [ ] permetre tests amb un kernel set aïllat;
- [ ] serialitzar l’accés si la llibreria/estratègia triada ho necessita;
- [ ] no fer que Three.js conegui el kernel pool.

## Logging MGP

Format existent:

```text
MGP: [ARXIU] [MÈTODE] [MISSATGE]
```

Exemples:

```text
MGP: [KernelManager.py] [load] [Kernel carregat type=SPK file=sat441.bsp generation=3]
MGP: [SatelliteCatalog.py] [build] [Catàleg validat total=461 covered=461 snapshot=2026-07-09]
MGP: [BodyOrientationService.py] [resolve] [Orientació unavailable body=HYPERION source=pck00011]
MGP: [OrbitSampler.py] [sample] [Òrbita mostrejada body=TITAN samples=512 interval_days=15.945]
MGP: [PlanetTextureRegistry.ts] [load] [Textura carregada body=SATURN resource=...]
MGP: [SaturnRingRenderer.ts] [init] [Anells persistents creats]
```

No registrar:

- cada frame;
- cada satèl·lit a cada tick correcte;
- cada lookup de cache;
- cada actualització de transform;
- cada sample d’òrbita individual.

## Tasques — caracterització prèvia

- [ ] Revisar el resultat real dels Passos 8 i 8.5.
- [ ] Identificar exactament quina llibreria calcula ara les efemèrides.
- [ ] Identificar el frame autoritatiu actual.
- [ ] Identificar la política d’aberració actual.
- [ ] Identificar la conversió topocèntrica actual.
- [ ] Identificar el renderer lunar reutilitzable.
- [ ] Enumerar `I:\TerraLab\data\sky\solar-system\planets`.
- [ ] Generar inventari de textures reals amb hash i dimensions.
- [ ] Detectar si existeix asset d’anells de Saturn.
- [ ] Comprovar l’estat del gestor de dades per kernels.
- [ ] Comparar amb TerraLab només per comportament existent.

## Tasques — infraestructura SPICE/efemèrides

- [ ] Afegir/estendre l’adaptador per carregar SPK de satèl·lits.
- [ ] Afegir PCK `pck00011.tpc` o equivalent compatible.
- [ ] Afegir LSK actual.
- [ ] Definir manifest de kernels.
- [ ] Verificar SHA-256.
- [ ] Parsejar/inventariar `aa_summaries.txt` o generar equivalent local reproduïble.
- [ ] Resoldre cobertura per NAIF ID i instant.
- [ ] Implementar batch de posicions i velocitats.
- [ ] Implementar transformacions body-fixed quan existeixin.
- [ ] Exposar qualitat/fallback sense filtrar tipus SPICE al domini.

## Tasques — catàleg complet

- [ ] Construir snapshot versionat dels 461 planetary satellites.
- [ ] Validar el recompte total.
- [ ] Validar recompte per sistema.
- [ ] Mapar NAIF ID ↔ nom/designació ↔ pare.
- [ ] Mapar cada cos als SPK que el cobreixen.
- [ ] Detectar cos sense SPK i generar report, no ometre’l silenciosament.
- [ ] Incorporar paràmetres físics disponibles.
- [ ] Incorporar frame d’orientació disponible.
- [ ] Marcar orientació absent.
- [ ] No inventar radi, textura ni rotació.

## Tasques — renderer planetari genèric

- [ ] Extreure components reutilitzables del renderer lunar.
- [ ] Crear geometria base compartida o cachejada.
- [ ] Suportar esfera i el·lipsoide.
- [ ] Carregar textura local per manifest.
- [ ] Aplicar quaternion científic.
- [ ] Aplicar il·luminació solar direccional física amb `bodyToSunDirection` per cos.
- [ ] Actualitzar la direcció solar per tick/tolerància científica, mai per frame de càmera.
- [ ] Aplicar LOD.
- [ ] Integrar picking.
- [ ] Integrar labels.
- [ ] Implementar `dispose` idempotent.

## Tasques — planetes

- [ ] Mercuri texturitzat i orientat.
- [ ] Venus texturitzat i orientat.
- [ ] Mart texturitzat i orientat.
- [ ] Júpiter texturitzat i orientat.
- [ ] Saturn texturitzat i orientat.
- [ ] Urà texturitzat i orientat.
- [ ] Neptú texturitzat i orientat.
- [ ] Plutó suportat pel model genèric si existeix recurs visual.
- [ ] Validar sentit de rotació, inclosos cossos retrògrads.
- [ ] No codificar “obliquity = X” al renderer si el frame PCK ja ho resol.

## Tasques — Saturn

- [ ] Separar estrictament posició SPK, orientació PCK i transformació local de l’observador.
- [ ] Validar la cadena SPK necessària per obtenir `SATURN (699)` i no confondre-la amb `SATURN BARYCENTER (6)`.
- [ ] Obtenir orientació de Saturn del frame/PCK.
- [ ] Obtenir `BODY699_RADII` del PCK actiu; no hardcodejar 60330 km com a radi visual.
- [ ] Derivar el pol nord i el pla equatorial de la transformació física.
- [ ] Implementar/validar ICRF/J2000 → frame local de l’observador amb la convenció `(East, Up, North)`.
- [ ] Crear `equatorialOrientationRoot`, `surfaceSpinRoot` i `ringSystem` persistents o una estructura equivalent amb les mateixes responsabilitats.
- [ ] Aplicar W/prime-meridian a la superfície de Saturn sense convertir-lo en spin dels anells.
- [ ] Orientar `ringSystem` pel pla equatorial, no amb un angle visual manual.
- [ ] Convertir matriu SPICE → quaternion renderer-neutral → quaternion Three.js `[x,y,z,w]` i validar equivalència numèrica.
- [ ] Implementar dimensions radials documentades.
- [ ] Implementar A/B/C + Cassini com a mínim.
- [ ] Utilitzar textura/alpha local si existeix i és adequada.
- [ ] Implementar fallback radial si no existeix, amb variació radial documentada d’albedo/opacitat.
- [ ] Implementar material de doble cara amb direcció solar física.
- [ ] Reutilitzar la il·luminació solar direccional comuna `Body → Sun`.
- [ ] Validar depth/oclusió davant/darrere del planeta.
- [ ] Preparar ombra Saturn → anells i anells → Saturn; no confondre-ho amb self-shadow microscòpic.
- [ ] Calcular `B_geocentric` només com a diagnòstic/almanac.
- [ ] Calcular `B_topocentric` només si és útil per validar la vista real; no exigir que sigui idèntic entre observadors.
- [ ] No modificar opacitat arbitràriament quan `B ≈ 0°`; gestionar el cas límit amb geometria/rasterització estable.
- [ ] Calcular elevació geomètrica i reutilitzar el sistema compartit d’horitzó.
- [ ] Deixar hook de refracció futura sense implementar-la al Pas 8.6.
- [ ] Provar dates amb anells molt oberts, propers al cantell i amb canvi de signe de B.

## Tasques — satèl·lits naturals

- [ ] Crear tots els satèl·lits com a entitats data-driven.
- [ ] Resoldre la seva posició SPK.
- [ ] Convertir a topocèntric amb el mateix pipeline del Pas 8.
- [ ] Aplicar mida angular quan el radi és conegut.
- [ ] Aplicar orientació quan el PCK/frame existeix.
- [ ] Marcar `orientationUnavailable` quan no existeix.
- [ ] No assumir rotació síncrona.
- [ ] Implementar material neutre per cossos sense textura.
- [ ] Implementar LOD per satèl·lits unresolved.
- [ ] Fer-los seleccionables.
- [ ] Permetre activar/desactivar per sistema planetari.

## Tasques — òrbites

- [ ] Implementar `OrbitSampler` o equivalent a Python.
- [ ] Mostrejar SPK respecte del pare.
- [ ] Seleccionar interval coherent amb període/cobertura.
- [ ] Fer sample count adaptatiu segons curvatura/període/LOD si és necessari.
- [ ] Generar buffers binaris.
- [ ] Crear `THREE.BufferGeometry` persistent.
- [ ] Versionar per `orbitGeneration`.
- [ ] No regenerar per tick.
- [ ] No confondre òrbita planetocèntrica amb trajectòria topocèntrica del Pas 9.

## Tasques — UI i diagnòstic

- [ ] Integrar controls al calaix `Cel` existent.
- [ ] Afegir recompte de satèl·lits disponibles.
- [ ] Afegir estat de kernels.
- [ ] Afegir estat de coverage temporal.
- [ ] Afegir toggle d’òrbites.
- [ ] Afegir toggle d’anells.
- [ ] Afegir filtre per sistema planetari.
- [ ] Mostrar qualitat científica del cos seleccionat.
- [ ] No crear 461 controls individuals permanents.

## Proves obligatòries — catàleg i kernels

- [ ] Snapshot de catàleg total = 461 per al dataset 2026-07-09.
- [ ] Terra = 1.
- [ ] Mart = 2.
- [ ] Júpiter = 115.
- [ ] Saturn = 293.
- [ ] Urà = 29.
- [ ] Neptú = 16.
- [ ] Plutó = 5.
- [ ] Cap duplicat de NAIF ID.
- [ ] Cap satèl·lit desapareix silenciosament si falta kernel.
- [ ] Tots els kernels del manifest passen checksum.
- [ ] Coverage start/end es respecta.
- [ ] Precedència de kernels duplicats és determinista.

## Proves obligatòries — efemèrides

Fixtures mínimes representatives:

```text
Moon
Phobos
Deimos
Io
Europa
Ganymede
Callisto
Titan
Enceladus
Iapetus
Phoebe
Miranda
Titania
Oberon
Triton
Nereid
Charon
Nix
Hydra
```

Per cada fixture:

- [ ] posició J2000/ICRF dins tolerància;
- [ ] distància respecte del pare;
- [ ] separació angular vista des de l’observador;
- [ ] continuïtat temporal;
- [ ] canvi d’un segon no recrea recursos;
- [ ] data fora de coverage falla explícitament.

Afegir fixtures d’irregulars de Júpiter i Saturn per evitar que només funcioni el cas de les llunes grans.

## Proves obligatòries — orientació

- [ ] Saturn: pol/equador compatible amb PCK.
- [ ] Urà: orientació retrògrada correcta.
- [ ] Io: orientació body-fixed disponible.
- [ ] Europa: orientació body-fixed disponible.
- [ ] Tità: orientació body-fixed disponible.
- [ ] Febe: orientació body-fixed disponible quan el PCK la proporciona.
- [ ] Hiperió: no inventa orientació.
- [ ] `camera roll` no recalcula el cos.
- [ ] walk/flight amb temps pausat = 0 requests científics nous.
- [ ] resize/FOV = 0 requests d’orientació.

## Proves obligatòries — mapping de textures

Per cada textura planetària local:

- [ ] hash estable;
- [ ] càrrega única;
- [ ] absència de Base64;
- [ ] absència de bridge bytes de textura;
- [ ] mapping UV documentat;
- [ ] no hi ha offset dependent de data;
- [ ] orientationRoot rota el cos sense modificar UV;
- [ ] canvi de temps no recarrega textura.

## Proves obligatòries — Saturn i anells

- [ ] `SATURN (699)` es resol amb una cadena SPK vàlida i no es confon amb `SATURN BARYCENTER (6)`.
- [ ] `BODY699_RADII` del PCK actiu coincideix amb el fixture de la versió instal·lada; per `pck00011.tpc`, `(60268, 60268, 54364) km`.
- [ ] Ring plane perpendicular al pol de Saturn dins tolerància numèrica.
- [ ] Transformació ICRF/J2000 → local canvia correctament amb latitud/LST i conserva norma/angles.
- [ ] Mateixa UTC, observadors diferents → orientació respecte de l’horitzó diferent quan correspon.
- [ ] `B_geocentric` és independent de la ubicació concreta de l’observador terrestre.
- [ ] `B_topocentric` pot diferir lleument entre observadors i la diferència és coherent amb la paral·laxi.
- [ ] `B` diagnòstic coincideix amb la geometria i no intervé en el quaternion del ring mesh.
- [ ] Matriu SPICE i quaternion serialitzat `[x,y,z,w]` transformen vectors base de manera equivalent dins tolerància.
- [ ] `surfaceSpinRoot` pot variar W sense alterar el pla de `ringSystem`.
- [ ] Quan `B ≈ 0`, els anells es veuen de cantell sense canvi artificial d’opacitat, NaN ni flip.
- [ ] En canviar de signe `B`, es veu la cara oposada sense flip artificial.
- [ ] Material de doble cara funciona des del nord i sud del pla.
- [ ] Direcció solar del material coincideix amb Saturn → Sol de l’efemèride.
- [ ] A/B/C i Cassini mantenen proporcions radials documentades.
- [ ] Planeta oculta correctament la part posterior.
- [ ] Part anterior oculta correctament el disc quan correspon.
- [ ] Elevació geomètrica utilitza la component `Up` correcta; cos sota l’horitzó és tractat pel pipeline compartit.
- [ ] Sense z-fighting.
- [ ] Textura dels anells carregada una vegada si existeix.
- [ ] `ring_geometry_build_count` estable.
- [ ] `ring_material_build_count` estable.

## Proves obligatòries — òrbites

- [ ] Òrbita de Fobos mostrejada des de SPK.
- [ ] Òrbites galileanes mostrejades des de SPK.
- [ ] Òrbita de Tità mostrejada des de SPK.
- [ ] Òrbita de Tritó reflecteix orientació retrògrada.
- [ ] Òrbita irregular no es força a tancar.
- [ ] Canvi de càmera = 0 regeneracions.
- [ ] Canvi d’un segon = 0 regeneracions si l’interval no canvia.
- [ ] Canvi d’interval = nova `orbitGeneration`.
- [ ] Buffer vell es disposa després de substituir-lo.

## Proves visuals

- [ ] Mercuri, Venus i Mart amb terminador coherent.
- [ ] Júpiter amb orientació de textura coherent.
- [ ] Saturn amb anells físicament inclinats.
- [ ] Urà amb eix extrem correctament representat.
- [ ] Neptú orientat correctament.
- [ ] Io/Europa/Ganimedes/Cal·listo a posicions relatives plausibles i validades.
- [ ] Tità visible al voltant de Saturn quan el FOV ho permet.
- [ ] Llunes petites passen a sprite/punt sense desaparèixer del catàleg.
- [ ] Sistema planetari amb òrbites activades sense saturació de labels.
- [ ] Mateix instant des de dos observadors: diferència topocèntrica coherent.
- [ ] Rotar la càmera no canvia l’estat científic.

## Rendiment

Mesurar amb:

- planetes activats;
- Saturn i anells;
- sistema de Júpiter;
- sistema de Saturn amb totes les llunes disponibles;
- tots els satèl·lits catalogats però amb LOD/culling normal;
- òrbites d’un sistema activades.

Mètriques obligatòries:

```text
solar_body_geometry_build_count
solar_body_material_build_count
planet_texture_load_count
planet_texture_upload_bytes
satellite_catalog_count
satellite_state_count_per_tick
spice_query_duration_ms
orientation_batch_duration_ms
orbit_sampling_duration_ms
orbit_geometry_build_count
orbit_bridge_bytes
solar_system_bridge_bytes_per_tick
GPU memory estimate
frame P50/P95
```

Criteris:

- [ ] 0 textures enviades pel bridge.
- [ ] 0 kernels enviats pel bridge.
- [ ] 0 reconstruccions de geometria planetària per tick.
- [ ] 0 reconstruccions d’anells per tick.
- [ ] 0 regeneracions d’òrbita per frame.
- [ ] 0 calls Python per frame de càmera.
- [ ] memòria estable durant timeline prolongada.
- [ ] cap bucle de 461 cossos a 60 Hz al frontend si els cossos no necessiten actualització visual.

## Criteri de sortida

El Pas 8.6 no es considera complet fins que:

- [ ] les textures existents de `I:\TerraLab\data\sky\solar-system\planets` s’utilitzen a través de `data_location.json`, sense hardcodejar la unitat;
- [ ] els planetes reutilitzen el pipeline genèric extret de la Lluna sempre que sigui aplicable;
- [ ] els planetes tenen orientació física derivada del model científic, no rotations visuals manuals;
- [ ] Saturn té anells persistents alineats amb el seu equador real;
- [ ] la posició de Saturn, la seva orientació i el frame local de l’observador tenen autoritats separades i explícites;
- [ ] `SATURN (699)` no es confon amb `SATURN BARYCENTER (6)`;
- [ ] els radis de Saturn provenen del PCK actiu;
- [ ] la transformació ICRF/J2000 → local depèn correctament de l’observador i respecta `+Y = Up`;
- [ ] els anells comparteixen el pla equatorial però no hereten semànticament el spin W de la superfície;
- [ ] matriu SPICE → quaternion → Three.js conserva la transformació i usa ordre `[x,y,z,w]`;
- [ ] la inclinació aparent dels anells emergeix de la geometria;
- [ ] `B_geocentric` i `B_topocentric` estan diferenciats i cap d’ells controla la rotació del mesh;
- [ ] el cas `B ≈ 0°` és estable sense truc d’opacitat científicament fals;
- [ ] els anells tenen material de doble cara amb il·luminació solar direccional física;
- [ ] planetes i satèl·lits reutilitzen un sistema comú de `Body → Sun direction`, sense llum enganxada a càmera;
- [ ] visibilitat/horitzó reutilitza el pipeline compartit i la refracció queda preparada però no implementada;
- [ ] el catàleg del snapshot cobreix 461 planetary satellites;
- [ ] tots els satèl·lits amb SPK vàlid poden obtenir posició;
- [ ] cap absència de kernel/orientació/textura queda amagada;
- [ ] els satèl·lits sense orientació coneguda no reben rotació inventada;
- [ ] les òrbites es deriven de mostres SPK i no d’el·lipses ideals com a autoritat;
- [ ] les òrbites romanen persistents a GPU;
- [ ] els elements orbitals són metadades, no el motor de posició;
- [ ] la ciència continua íntegrament a Python;
- [ ] Three.js només representa estat científic + recursos visuals;
- [ ] el bridge envia deltes petits i buffers d’òrbita només per generació;
- [ ] la càmera local no recalcula planetes ni llunes;
- [ ] el sistema és data-driven i no conté centenars de classes específiques;
- [ ] lifecycle i `dispose` són idempotents;
- [ ] totes les proves científiques, visuals i de rendiment passen;
- [ ] els Passos 1–8.6 continuen funcionant;
- [ ] el Pas 9 encara no s’ha començat.

## Evidència obligatòria

- [ ] Manifest de textures planetàries real de la carpeta de dades.
- [ ] Hash de totes les textures utilitzades.
- [ ] Manifest de kernels amb URL, hash i coverage.
- [ ] Snapshot versionat del catàleg JPL.
- [ ] Report de cobertura `catalogats / amb SPK / amb orientació / amb radi / amb textura`.
- [ ] Prova numèrica del pol/equador de Saturn.
- [ ] Prova de provenance dels radis de Saturn des del PCK actiu.
- [ ] Prova de cadena SPK Earth → Saturn barycenter → Saturn center.
- [ ] Prova numèrica ICRF/J2000 → local en diversos observadors.
- [ ] Prova d’equivalència matriu SPICE ↔ quaternion Three.js `[x,y,z,w]`.
- [ ] Prova numèrica de `B_geocentric` i `B_topocentric` dels anells en diverses dates.
- [ ] Captures de Saturn amb anells oberts i propers al cantell.
- [ ] Captures dels sistemes de Júpiter, Saturn, Urà i Neptú amb llunes.
- [ ] Captura de Plutó + Caront/Nix/Hidra/Quèrberos/Estix quan el FOV/mode d’inspecció ho permeti.
- [ ] Vídeo de timeline amb moviment continu de llunes sense reconstrucció de recursos.
- [ ] Vídeo activant/desactivant òrbites.
- [ ] Fixture d’Hiperió demostrant fallback honest d’orientació.
- [ ] Prova de data fora de coverage.
- [ ] Prova que canviar FOV/resize/camera roll no fa queries SPICE.
- [ ] Prova que caminar/volar no fa queries SPICE amb temps pausat.
- [ ] Mètriques P50/P95.
- [ ] Mètriques de bytes del bridge.
- [ ] Mètriques de memòria GPU.
- [ ] Prova d’arrencada → tancament → arrencada sense kernels/textures/geometries duplicats.

## Fora d’abast del pas

Aquest pas no implementa encara:

- eclipsis i contactes;
- ocultacions entre cossos;
- trajectòries topocèntriques temporals del Pas 9;
- atmosfera meteorològica temporal de Júpiter/Saturn;
- núvols 3D volumètrics planetaris;
- self-shadow microscòpic i dispersió múltiple entre partícules individuals dels anells;
- refracció atmosfèrica aparent, que queda com a extensió del pipeline observacional;
- ombres topogràfiques d’alta resolució sobre totes les llunes;
- DSK d’alta resolució per centenars de cossos;
- textures científiques d’alta resolució per a totes les llunes quan no existeixen;
- satèl·lits artificials;
- navegació física sobre altres planetes;
- tots els sistemes binaris de small bodies com a criteri de tancament.

Aquests elements no poden justificar dades inventades dins del Pas 8.6.

## Regla final del Pas 8.6

```text
SPK decideix on és el cos;
PCK/FK/BPC decideix com està orientat quan existeix model;
JPL physical parameters decideixen mida/forma quan existeixen dades;
els recursos locals decideixen l’aspecte visual disponible;
Three.js manté geometria/materials/textures persistents;
la càmera només projecta l’estat resultant.
```

Per Saturn:

```text
SPK complet
→ posició del centre de Saturn (699)

PCK/FK
→ pol nord + frame body-fixed
→ pla equatorial

ScientificObserver + Earth orientation
→ ICRF/J2000 → frame local

pla equatorial
→ ringSystem

W / prime meridian
→ només surfaceSpinRoot de Saturn

Body → Sun direction
→ il·luminació direccional de planeta i anells

frame local + càmera
→ inclinació/aparença aparent correcta
```

Mai:

```text
angle aparent dels anells
→ rotació manual del mesh
```

## Annex: Validació científica, de recursos i de rendiment

Data de preparació: 2026-08-09. Snapshot de catàleg: 2026-07-09.

### Resultat implementat

La ciència del sistema solar té una única autoritat `SpiceEphemerisAdapter` amb
DE440, SPK de satèl·lits, LSK, PCK/FK/BPC i política observacional `LT+S`. La
transformació és J2000/ICRF → `ITRF93` → ENU canònic i el wire conserva l’ordre
històric `(East, Up, North)`. Three.js rep quaternions `[x,y,z,w]`, vectors,
qualitats i recursos validats; no calcula efemèrides.

El renderer manté persistents la geometria planetària compartida, els materials,
les textures, el pla dels anells, un únic batch GPU de satèl·lits i els buffers
d’òrbita versionats. La superfície de Saturn rep W al seu `surfaceSpinRoot`; els
anells són un germà orientat només pel pla equatorial. L’oclusió del semianell
posterior es resol al shader projectant sobre l’el·lipsoide unitari en coordenades
locals de Saturn, sense dependre de la precisió del `depth buffer` a la distància
de l’esfera celeste; el semianell anterior i les zones fora del limbe es conserven.

La UI `Cel → Sistema solar` inclou anells, satèl·lits, òrbites, filtre per sistema,
LOD, etiquetes acotades i estat de catàleg/kernels/coverage. La inspecció mostra
NAIF, pare, distància, diàmetre angular, radis, fase, qualitat i diagnòstics B.

### Recursos i provenance

Els binaris viuen sota el `data_root` resolt per `data_location.json`, actualment:

```text
I:\TerraLab\data\sky\solar-system\planets
I:\TerraLab\data\sky\solar-system\kernels
```

No hi ha textures ni kernels al repositori. Els manifests compactes versionats
són a `backend/src/terralab3d/data/solar_system`; els manifests actius són a
`[data_root]/data/sky/solar-system/kernels/manifests`.

Fonts primàries:

- catàleg: <https://ssd.jpl.nasa.gov/sats/discovery.html>;
- paràmetres físics: <https://ssd.jpl.nasa.gov/sats/phys_par/>;
- kernels i checksums: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/>;
- inventari SPK: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/aa_summaries.txt>;
- vectors de contrast: <https://ssd.jpl.nasa.gov/api/horizons.api>;
- radis dels anells: <https://nssdc.gsfc.nasa.gov/planetary/factsheet/satringfact.html>.

Generació activa de kernels: `97bdf4bf136424a2`, 28 fitxers, 13.913.742.560 B
(12,958 GiB). Tots passen mida, confinament de ruta i SHA-256; quan NAIF publica
MD5 també es valida durant la preparació. Les 9 textures sumen 42.065.271 B i
també passen SHA-256 i validació de dimensions.

### Cobertura del catàleg

| Sistema | Catalogats | Amb SPK al snapshot |
|---|---:|---:|
| Terra | 1 | 1 |
| Mart | 2 | 2 |
| Júpiter | 115 | 115 |
| Saturn | 293 | 292 |
| Urà | 29 | 28 |
| Neptú | 16 | 16 |
| Plutó | 5 | 5 |
| **Total** | **461** | **459** |

Cobertura complementària: 51 orientacions i 71 radis. Els dos casos sense SPK
oficial són `S/2009 S1` i `S/2025 U1`; consten al catàleg com `NO_KERNEL` i no
reben posició inventada. Hiperió té radi però orientació `UNAVAILABLE`.

Decisió de precedència no determinada al pla: `nep104`/`nep105` es carreguen
abans de les tres parts de `nep098`, de manera que la solució global NEP098 de
2026 preval en solapaments. El canvi es va decidir després de contrastar Nereida
amb Horizons; l’error va passar de 317 km a menys de 2 nm al fixture J2000.

### Evidència numèrica

- 21 fixtures Horizons (`Moon`, Fobos, Deimos, galileanes, Himàlia, satèl·lits
  principals i irregulars de Saturn, Urà, Neptú i Plutó) coincideixen amb els
  SPK: error de posició < 0,1 km i velocitat < 1e-5 km/s.
- `SATURN (699)` es resol com a centre físic; el kernel actiu mai és el
  `SATURN BARYCENTER (6)`.
- `BODY699_RADII` del PCK actiu: `(60268, 60268, 54364) km`.
- El pol obtingut amb la matriu ICRF→ENU i el vector rotat pel quaternion
  equatorial coincideixen amb error < 1e-12.
- A 2026-07-09, B geocèntric és `-9,1023432032°` per a Barcelona i Canberra;
  B topocèntric és respectivament `-9,1021807782°` i `-9,1024948174°`.
- Fixtures B: `+9,1816°` (2024-01-01), `+0,0444°` (2025-03-23), `-2,1858°`
  (2025-05-06) i `-26,4934°` (2032-01-01), sense NaN ni flip.
- L’òrbita de Fobos es transmet com 64 mostres Float32: 768 B de payload.
- La prova d’oclusió dels anells verifica els tres casos geomètrics: davant del
  planeta, darrere del planeta i darrere però fora del limbe. El material no
  consulta ni escriu el `depth buffer`: l’oclusió analítica evita els forats
  triangulars del semianell anterior a la distància de l’esfera celeste.
- La regressió lunar recorre els angles de fase enters de `0°` a `180°` en els
  dos sentits del limbe (362 casos) i contrasta la fracció il·luminada amb
  `(1 + cos(phaseAngle)) / 2`, amb tolerància `1e-12`.
- El material lunar conserva `MeshLambertMaterial`, però recupera literalment
  del commit `439b9f6` l’alfa de fase `clamp(directLight + 0.015, 0, 1)`. Això
  deixa que l’atmosfera real del Pas 7 sigui predominant sense afegir cap llum,
  exposició ni segona capa atmosfèrica al renderer lunar. Durant el dia,
  `(1 - twilightFactor) * horizonHaze` comprimeix el contrast de l’albedo cap al
  gris lunar històric `#d8d8d2`; de nit el factor és exactament zero. La llum
  direccional té intensitat `π` per compensar el factor `1/π` del BRDF de
  `MeshLambertMaterial` i recuperar la luminància unitària del shader del Pas 8.

### Validacions executades

```text
python -m pytest backend/tests -q       31 passed
npm run typecheck                       passed
npm test                                187 passed
npm run build                           passed
git diff --check                        passed
```

Prova integrada d’arrencada/bridge/tancament:

- `/` = 200;
- textura externa validada = 200, nom fora de manifest = 404;
- manifests = 9 textures, 461 catalogats, 459 amb SPK;
- snapshot = SPICE/DE440, 8 planetes, kernels `ready`;
- activació del sistema de Mart i òrbita binària de Fobos correctes;
- pool CSPICE netejat i servidor aturat ordenadament.

Mètriques de la passada integrada: efemèrides P50/P95 `7,76/16,49 ms`, batch
d’orientació P50/P95 `1,10/1,48 ms`, òrbita de Fobos `3,69 ms`, snapshot compacte
`17.635 B`, 0 bytes de textures i 0 bytes de kernels pel bridge.

### Evidència visual pendent d’entorn

La sessió d’implementació no exposava cap backend de navegador, per tant no es
van poder produir captures ni vídeos ni mesurar P50/P95 del frame/GPU sobre una
escena WebGL real. La compilació, els tests de geometria/material/lifecycle i la
prova HTTP/WebSocket sí que es van completar. No afecta la ciència ni la
integració, però les captures, vídeos i mètriques de frame/GPU continuen sent
evidència visual pendent.
