# Pla mestre per verticals

## Estat executat — 2026-08-24

- **Vertical 1 completada:** TLST 1.0 versionat, S2GLC i WorldCover, `SampleValidity`, buffers categòrics, picking i tooltip català descriptiu. La clau TLST es conserva al contracte d’auditoria però no es mostra al tooltip ordinari.
- **Vertical 2 completada:** descriptor raster neutral, port únic Rasterio, selecció explícita de banda/subdataset, adaptador TXT/CSV/XYZ regular, importació `managed`/`external`, persistència ordenada a `data_sources.json`, fallback DEM, recàrrega segura del port d’elevació i regeneració de terreny/horitzó.
- **Vertical 3 completada:** importació categòrica enter/paleta/RGB/RGBA sense interpolació, registre versionat, mappings exhaustius S2GLC, WorldCover, Copernicus LCM-10 i CORINE, revisió obligatòria, auditoria de profunditat i activació raster real.
- **Vertical 4 completada:** esquemes d’usuari persistents i reutilitzables, mapping de cada valor a qualsevol node TLST o estat admissible, i revisió immutable identificada per `scheme_key + scheme_version + mapping_revision`.
- **Verticals 5–18 no implementades:** continuen sent context d’extensibilitat i no es documenten com a funcionalitat disponible.

La prova de sortida de la Vertical 2 importa un bundle `mi_dem.asc`, reinicia els repositoris, torna a obrir la font registrada i obté una graella de terreny amb elevació real.

Els fitxers locals no es modelen com a `DownloadJob`.

---

# Principi arquitectònic central

TLST 1.0 és la **taxonomia canònica de TerraLab3D**.

Els estàndards externs no competeixen amb TLST ni es tradueixen entre ells.

```text
S2GLC ───────────────┐
WorldCover ──────────┤
CORINE ──────────────┤
CLC+ ────────────────┤
Dynamic World ───────┤
CGLS-LC100 ──────────┤
ESA CCI ─────────────┤
MODIS ───────────────┤
GlobeLand30 ─────────┤
GLC_FCS30D ──────────┤
NLCD ────────────────┤
Urban Atlas ─────────┤
altres ──────────────┘
                     │
                     ▼
                   TLST
```

Cada classe de cada estàndard es tradueix **directament a TLST** fins al nivell semàntic màxim que la font pot demostrar.

Exemple:

```text
Estàndard A
"cropland"
      ↓
agriculture.cropland
```

Si l’estàndard no diferencia què hi ha sota:

```text
agriculture.cropland
├── ...
├── permanent_crop
│   ├── vineyard
│   ├── orchard
│   └── ...
└── ...
```

la traducció s’atura.

No s’inventa cap fill.

A partir d’aquest punt entra el **refinament**.

```text
estàndard
    ↓
traducció TLST
    ↓
node TLST més profund demostrable
    ↓
queden fills sense resoldre?
    │
 ┌──┴───┐
 NO     SÍ
 │       │
 │       ▼
 │   refinaments
 │       │
 └───┬───┘
     ▼
interpretació final
```

Per tant:

> **Un refinament no serveix per tornar a classificar des de zero. Serveix per intentar resoldre una bifurcació TLST que les evidències anteriors no han pogut resoldre.**

I un refinament també pot quedar-se a mig camí.

```text
tree_cover
    ↓
tree_cover.broadleaf
    ↓
STOP
```

és un resultat completament vàlid si no hi ha evidència per continuar.

---

# Regles invariants

## 1. TLST és l’autoritat semàntica

Cap identificador extern passa al domini procedural com a categoria canònica.

```text
S2GLC 82
WorldCover 10
CLC 311
```

són identificadors de font.

La identitat territorial interna és TLST.

---

## 2. Cada estàndard té un traductor independent

Mai:

```text
S2GLC
↓
WorldCover
↓
CORINE
↓
TLST
```

Sempre:

```text
S2GLC ───────→ TLST
WorldCover ──→ TLST
CORINE ──────→ TLST
```

---

## 3. La traducció arriba només fins on arriba l’estàndard

No es força una fulla TLST.

```text
tree_cover
```

pot ser el resultat final de la traducció.

Igual que:

```text
tree_cover.broadleaf
```

o una fulla més profunda.

---

## 4. El refinament opera sobre una pregunta concreta

No:

```text
refina aquest píxel
```

sinó conceptualment:

```text
actual = tree_cover

pregunta:
quin dels fills de tree_cover
podem demostrar?
```

Després:

```text
actual = tree_cover.broadleaf

pregunta:
podem discriminar algun fill
de broadleaf?
```

---

## 5. No resoldre també és informació

Per cada bifurcació podem tenir:

```text
RESOLVED
UNRESOLVED
NOT_APPLICABLE
```

Això és independent de:

```text
nodata
unknown
unclassified
```

que continuen sent `ObservationState` i no categories TLST.

---

## 6. El raster original mai es modifica

Sempre es conserva:

```text
source
source_version
source_code
source_value
mapping_revision
TLST result
refinement trace
```

La classificació refinada és una interpretació derivada.

---

# Vertical 1 — TLST 1.0 + S2GLC + WorldCover + inspecció científica E2E

## Estat

**COMPLETADA**

És la primera implementació real del sistema canònic TLST.

La precaució continua sent la mateixa:

`uint16`, màscara de 2 bits, `R8UI`, etc. són decisions d’implementació d’aquesta vertical, no propietats universals de TLST.

## Pipeline existent

```text
raster S2GLC / WorldCover
        ↓
codi font intacte
+
SampleValidity
        ↓
mapper versionat
        ↓
TLST 1.0
        ↓
picking
        ↓
tooltip científic auditable
```

Inclou:

- catàleg complet TLST 1.0;
- S2GLC 2017-v1.2;
- WorldCover 2020-v100;
- WorldCover 2021-v200;
- procedència literal;
- `SampleValidity`;
- `SingleSurface`;
- `CompositeSurface`;
- `ObservationState`;
- claus TLST estables;
- JSON versionat;
- tooltip científic.

## Nova consideració arquitectònica

Els mappings S2GLC i WorldCover implementats aquí passen a ser els **dos primers membres del registre general d’equivalències de la Vertical 3**.

No són casos arquitectònicament especials.

---

# Vertical 2 — Lector raster universal + importació d’elevació

## Estat

**COMPLETADA**

Objectiu assolit: separar definitivament:

```text
elevació
```

de:

```text
format de fitxer
```

## Arquitectura

```text
fitxer raster
      ↓
Rasterio
      ↓
RasterDatasetDescriptor
      ↓
semàntica = elevation
      ↓
ElevationSampler
      ↓
pipeline DEM existent
```

Suporta els formats disponibles a la instal·lació GDAL/Rasterio, inclosos GeoTIFF, COG, VRT, AAIGrid, ENVI, BIL/BIP/BSQ, IMG, JP2, NetCDF, HDF, GRIB, SAGA, PCRaster, Idrisi, Surfer, Zarr, etc.

També:

```text
TXT
CSV
XYZ
```

mitjançant adaptador textual quan procedeix.

## UI

```text
TERRA
├── Elevació
├── Categòric
└── Refinament
```

Footer fix:

```text
[ + Importar ]                       [ Tancar ]
```

## Resultat observable

```text
mi_dem.asc
    ↓
importació
    ↓
registre
    ↓
reinici
    ↓
reobertura
    ↓
ElevationSampler
    ↓
terreny real
```

---

# Vertical 3 — Categòric universal + registre d’estàndards + equivalències TLST

## Estat

**COMPLETADA**

El lector universal analitza finestres exactes d'enters, paleta, RGB o RGBA i
materialitza una vista indexada `uint16` reconstruïble només després de la
confirmació. El valor font, el dtype, l'esquema, la versió i la revisió del
mapping continuen sent l'autoritat d'auditoria. Els IDs compactes no són
identitat pública.

El registre inicial conté S2GLC, WorldCover 2020/2021, Copernicus LCM-10 i les
44 classes CORINE, més el seu NoData declarat. La llegenda publicada inclou el
camí resolt, la profunditat semàntica i els fills que una classe genèrica deixa
oberts.

Aquesta vertical passa a ser molt més important del que plantejava el pla inicial.

No consisteix només a poder obrir qualsevol raster categòric.

Consisteix a construir la **capa universal de traducció entre classificacions externes i TLST 1.0**.

---

## 3.1 Importació categòrica universal

Flux:

```text
TERRA
→ Categòric
→ + Importar
→ raster
→ tipus = categòric
→ lectura de codificació
→ selecció/detecció d’esquema
→ mapping
→ TLST
```

Formats semàntics:

```text
single-band integer
palette/indexed
RGB
RGBA
```

Sense interpolació categòrica.

---

## 3.2 Detecció d’esquema

Només després que l’usuari hagi declarat:

```text
tipus = categòric
```

TerraLab pot intentar reconèixer un esquema.

Per exemple:

```text
Els codis coincideixen amb:
S2GLC Europe 2017 v1.2

[ Utilitzar aquest esquema ]
[ Seleccionar-ne un altre ]
```

Mai:

```text
"sembla vegetació"
"sembla un DEM"
```

---

## 3.3 Registre universal d’estàndards

Cada esquema conegut defineix:

```text
scheme_key
scheme_version
classes
source_semantics
mapping_revision
TLST mappings
```

Exemples progressius:

```text
S2GLC
ESA WorldCover
Copernicus LCM-10
CORINE Land Cover
CLC+
Dynamic World
CGLS-LC100
ESA CCI Land Cover
MODIS MCD12Q1
GlobeLand30
GLC_FCS30D
NLCD
Urban Atlas
...
```

---

# 3.4 Matriu d’equivalències estàndard → TLST

Aquest és el canvi principal.

Per **cada classe de cada estàndard suportat** s’ha de documentar fins on pot arribar dins TLST.

Exemple conceptual:

| Estàndard | Classe externa | TLST màxim justificat |
|---|---|---|
| Estàndard A | Cropland | `agriculture.cropland` |
| Estàndard B | Permanent crops | `agriculture.cropland.permanent_crop` |
| Estàndard C | Vineyards | `agriculture.cropland.permanent_crop.vineyard` |

El sistema no exigeix que tots arribin a la mateixa profunditat.

---

## 3.5 Cobertura jeràrquica

A partir dels mappings es pot derivar una matriu de cobertura.

Exemple:

```text
agriculture
└── cropland
    └── permanent_crop
        ├── vineyard
        ├── orchard
        └── ...
```

Una font podria cobrir:

```text
agriculture                  ✓
cropland                     ✓
permanent_crop               ?
vineyard                     ?
orchard                      ?
```

Una altra:

```text
agriculture                  ✓
cropland                     ✓
permanent_crop               ✓
vineyard                     ?
orchard                      ?
```

I una tercera:

```text
agriculture                  ✓
cropland                     ✓
permanent_crop               ✓
vineyard                     ✓
```

Aquesta informació serà la base directa de la Vertical 5.

---

## 3.6 Tipus de mapping

Es mantenen:

```text
single
composite
observation_state
```

Però el mapping ha d’incloure també la seva profunditat semàntica real.

Exemple:

```text
source class
    ↓
SingleSurface
    ↓
TLST node
    ↓
no afirma res sobre descendents
```

---

## 3.7 Resultat observable

Seleccionar un píxel permet auditar:

```text
Font:
CORINE Land Cover

Codi:
311

Mapping revision:
...

TLST:
tree_cover...

Profunditat resolta:
...

Jerarquia pendent:
...
```

No cal mostrar tota aquesta informació al tooltip ordinari.

Ha d’estar disponible al contracte científic/auditoria.

---

# Vertical 4 — Classificacions personalitzades

## Estat

**COMPLETADA**

Una classificació creada per l'usuari entra al mateix registre que els
estàndards. Es persisteix atòmicament a `classification_schemes.json`, es torna
a carregar en reiniciar i no permet sobreescriure silenciosament una revisió
existent. El selector mostra tota la jerarquia TLST i admet nodes estructurals,
`unknown`, `unclassified` i les valideses no semàntiques declarables.

Les classificacions creades pels usuaris són simplement **un altre esquema extern**.

Exemple:

```text
mapa_manel.tif

1  = bosc
2  = cereal
7  = oliverar
22 = aigua
```

UI:

```text
1  → [node TLST ▼]
2  → [node TLST ▼]
7  → [node TLST ▼]
22 → [node TLST ▼]
```

L’usuari no està obligat a seleccionar una fulla.

Pot indicar honestament:

```text
1 → tree_cover
```

si aquesta és tota la informació que conté el seu raster.

O:

```text
7 → agriculture...olive_grove
```

si el seu esquema realment ho especifica.

## Persistència

```text
scheme_key
scheme_version
mapping_revision
class mappings
```

Exemple:

```text
"Mapa Manel v1"
```

A partir d’aquí funciona exactament igual que qualsevol estàndard oficial.

---

# Vertical 5 — Refinaments com a resolutors de jerarquia TLST

Aquesta vertical canvia conceptualment de manera important.

Un refinament **no pertany simplement a una categoria grossa**.

Pertany a una o més **preguntes de discriminació dins l’arbre TLST**.

---

## Exemple forestal

Situació inicial:

```text
tree_cover
```

Pregunta:

```text
podem discriminar entre els fills de tree_cover?
```

Possible refinament:

```text
Dominant Leaf Type
```

Resultat:

```text
tree_cover.broadleaf
```

Després pot existir una nova pregunta:

```text
podem discriminar els fills de broadleaf?
```

Una altra evidència pot permetre continuar.

O no.

---

## Exemple agrícola

Inicial:

```text
agriculture.cropland
```

Refinament:

```text
EuroCrops
```

Pot arribar a:

```text
agriculture.cropland.permanent_crop.vineyard
```

si la font ho demostra.

---

## Exemple artificial

Inicial:

```text
artificial
```

OSM podria aportar:

```text
building footprint
```

Això pot:

- refinar semàntica;
- aportar geometria autoritativa;
- aportar atributs;

segons el cas.

No totes les evidències han d’alterar la categoria TLST.

---

# Catàleg inicial de refinaments

## Artificial / urbà

```text
OpenStreetMap
imperviousness
Urban Atlas
DEM
clima
```

## Agricultura

```text
EuroCrops
SIGPAC quan procedeixi
HR-VPP
DEM
clima
fenologia
```

## Boscos

```text
Tree Cover Density
Dominant Leaf Type
HR-VPP
DEM
clima
```

## Grassland

```text
Copernicus Grassland
HR-VPP
DEM
clima
```

## Shrub / heath / sclerophyllous

```text
SoilGrids
clima
DEM
cobertura vegetal futura
```

## Wetland

```text
Water & Wetness
DEM
clima
```

## Peat bog

```text
Water & Wetness
SoilGrids
DEM
```

## Mangrove

```text
Water & Wetness
context costaner
clima
DEM
```

## Bare / sparse

```text
SoilGrids
DEM
clima
```

## Water

```text
Water & Wetness
OSM
DEM
```

## Snow / ice

```text
Copernicus Snow
DEM
clima
estació
```

## Context transversal

```text
latitud
longitud
DEM
pendent
orientació
Köppen-Geiger / equivalent
data
estació
```

Tots opcionals.

---

# Vertical 6 — Evidències normalitzades + procedència + capacitat semàntica

Els proveïdors no arriben directament al procedural ni modifiquen directament TLST.

Produiran evidències.

Exemples:

```text
OSM building
→ BuildingFootprintEvidence
```

```text
OSM road
→ RoadGeometryEvidence
```

```text
EuroCrops vineyard
→ CropTypeEvidence
```

```text
Tree Cover Density 76 %
→ TreeCoverDensityEvidence
```

```text
Dominant Leaf Type
→ LeafTypeEvidence
```

```text
SoilGrids
→ SoilEvidence
```

---

## Contracte mínim

Cada evidència conserva:

```text
source
source_version
source_role

spatial_precision
semantic_precision
confidence
temporal_validity

provenance
```

I, quan és semànticament aplicable:

```text
supports_tlst_node
discriminates_from_node
candidate_child
```

No totes les evidències necessiten aquests tres camps.

Per exemple el DEM normalment aporta context, no classificació TLST.

---

## SourceRole

Es mantenen rols com:

```text
AuthoritativeGeometry
AttributeOverride
AttributeRefinement
ContextOnly
FallbackOnly
```

Una mateixa font pot produir evidències amb rols diferents.

---

# Vertical 7 — Hierarchical InterpretationResolver

Aquesta vertical deixa de ser simplement:

```text
categoria + evidències → categoria millor
```

i passa explícitament a ser un **resolver jeràrquic TLST**.

---

## Pipeline

```text
observació categòrica
      ↓
mapper de l’estàndard
      ↓
node TLST més profund justificat
      ↓
HierarchyResolver
      │
      ├─ evidències
      ├─ refinaments
      ├─ DEM
      └─ context
      ↓
intenta resoldre el següent nivell
      ↓
resolt?
   ┌──┴──┐
  sí    no
  │      │
  ▼      ▼
continua STOP
```

---

## Exemple

Base:

```text
agriculture.cropland
```

EuroCrops:

```text
crop_type = vineyard
```

Resultat:

```text
agriculture.cropland.permanent_crop.vineyard
```

Traça:

```text
S2GLC
→ agriculture.cropland

EuroCrops
→ permanent_crop
→ vineyard
```

La classificació inicial continua intacta i auditable.

---

## Un altre exemple

Base:

```text
tree_cover
```

Dominant Leaf Type:

```text
broadleaf
```

Resultat:

```text
tree_cover.broadleaf
```

No hi ha evidència suficient per continuar:

```text
STOP
```

Resultat final:

```text
tree_cover.broadleaf
```

No:

```text
tree_cover.broadleaf.<fill inventat>
```

---

## ResolutionTrace

Cada resolució ha de conservar conceptualment:

```text
initial_observation
initial_tlst_node

steps:
  - evidence
  - previous_node
  - resolved_node
  - confidence
  - provenance

final_tlst_node
unresolved_children
```

Això serà fonamental per al Mode Científic.

---

# Vertical 8 — SpatialPatch + halo + cache espacial

Un cop resolta la semàntica ja podem deixar de pensar només en samples.

Creem:

```text
SpatialPatch
```

Molts píxels espacialment relacionats:

```text
████████
██████████
  ███████
   █████
```

es converteixen en:

```text
polígon irregular
```

---

## Contracte

Cada patch conté:

```text
category
polygon
area
centroid
neighbours

terrain_stats
evidences
resolution_trace
provenance

seed
```

La categoria és la **interpretació TLST disponible per al patch**, no necessàriament una fulla.

---

## Halo

```text
┌─────────────────┐
│      halo       │
│   ┌─────────┐   │
│   │  patch  │   │
│   └─────────┘   │
└─────────────────┘
```

Permet consultar:

- veïns;
- carreteres pròximes;
- aigua;
- transicions;
- continuïtat paisatgística;
- gradients.

## Regla

```text
tile != patch
```

`Tile`:

```text
transport
cache
IO
```

`Patch`:

```text
semàntica
context
procedural
```

---

# Vertical 9 — Primer generador procedural: agricultura

Agricultura continua sent el millor primer generador complet perquè prova:

- polígons irregulars;
- DEM;
- orientació;
- clipping;
- repetició d’assets;
- refinament;
- determinisme.

Exemple:

```text
TLST:
...vineyard

+
SpatialPatch
+
DEM
+
context

↓
VineyardGenerator
```

Pipeline:

```text
vineyard patch
      ↓
orientació de les files
      ↓
línies paral·leles
      ↓
clip al polígon
      ↓
passadissos
      ↓
distribució de plantes
```

Python calcula:

```text
positions
rotations
scales
rows
polylines
```

Three.js dibuixa.

Si TLST només ha arribat a:

```text
agriculture.cropland
```

no s’executa arbitràriament un generador de vinya.

S’utilitza un generador compatible amb aquesta precisió o un fallback explícit.

---

# Vertical 10 — Boscos, matorral i herbàcies

Aquesta vertical demostra que el contracte procedural no pressuposa files ni agricultura.

## Bosc

```text
TLST
+
Tree Cover Density
+
Leaf Type
+
clima
+
DEM
↓
densitat
clusters
clearings
edge gradients
```

## Shrubland

```text
clusters irregulars
clarianes
densitat variable
```

## Grassland

```text
FAR
→ material

MID
→ geometria simplificada

NEAR
→ instàncies
```

El generador seleccionat depèn de la **profunditat TLST realment resolta**.

---

# Vertical 11 — Built-up + OSM

Vertical procedural especialment complexa.

```text
TLST artificial
+
OSM buildings
+
OSM roads
+
landuse
+
DEM
+
context arquitectònic
        ↓
BuiltUpInterpreter
        ↓
UrbanGenerator
```

Separació obligatòria:

```text
QUÈ ÉS
```

de:

```text
COM ES VEU
```

Exemple:

```text
building_type = industrial
```

pot ser evidència semàntica.

Mentre:

```text
architectural_profile:
    mediterranean = 0.7
    central_european = 0.3
```

és representació/context visual.

Un footprint OSM autoritatiu es conserva.

No es reemplaça per una caixa procedural si tenim geometria millor.

---

# Vertical 12 — Aigua, humedals, neu, gel i bare surfaces

Completa les famílies principals.

## Wetland

```text
aigua
barro
vegetació
transicions
```

## Water

Només es distingeix:

```text
river
canal
reservoir
standing water
...
```

quan TLST + evidències ho permeten.

No pel simple fet que el generador conegui aquests conceptes.

## Snow / Ice

```text
snow
ice
seasonality
DEM
```

## Bare

Principalment:

```text
materials
PBR
masks
procedural variation
```

---

# Vertical 13 — Sistema d’assets i materials

Separar definitivament:

```text
interpretació territorial
```

de:

```text
representació concreta
```

Exemple:

```text
Interpretació:
tree_cover...
climate = mediterranean
density = 0.65
```

Selector:

```text
asset affinity matching
```

Els assets poden tenir múltiples afinitats:

```text
mediterranean = 0.8
mountain = 0.6
rural = 0.9
```

Afegir un asset nou no obliga a recalcular:

```text
mapping
refinement
TLST
patches
```

---

# Vertical 14 — LOD procedural complet

Una única identitat semàntica.

Diverses representacions.

```text
FAR
MID
NEAR
```

## Arbre

```text
FAR  → canopy mass
MID  → impostor
NEAR → mesh
```

## Edifici

```text
FAR  → volum
MID  → footprint + roof
NEAR → façade detail
```

## Cultiu

```text
FAR  → material
MID  → rows
NEAR → instances
```

Canviar de LOD mai modifica TLST.

---

# Vertical 15 — Estacions i estat temporal

No existeixen quatre mons independents.

```text
world seed estable
+
temporal state
```

Pot afectar:

```text
foliage
greenery
crop phase
snow
colors
wetness
```

No modifica arbitràriament:

```text
roads
buildings
tree positions
parcel boundaries
```

I, especialment:

> l’estat temporal visual no pot inventar una classificació TLST més precisa.

---

# Vertical 16 — Refinement Cache automàtic

Aquesta vertical automatitza el sistema construït a V3–V7.

No pregunta simplement:

```text
quines fonts puc descarregar?
```

Pregunta:

```text
quines parts de TLST
queden sense resoldre
en aquesta àrea?
```

---

## Pipeline

```text
AOI
 ↓
classificacions disponibles
 ↓
mappings estàndard → TLST
 ↓
nodes assolits
 ↓
detectar bifurcacions no resoltes
 ↓
buscar refinadors compatibles
 ↓
què tenim?
què falta?
 ↓
descàrrega
 ↓
clip
 ↓
normalització
 ↓
Evidence
 ↓
HierarchyResolver
 ↓
cache
```

Això permet que el sistema digui conceptualment:

```text
Aquí ja sé:
tree_cover.broadleaf

No necessito:
un altre dataset que només distingeixi tree_cover

Sí em pot servir:
un dataset capaç de discriminar
els fills encara no resolts de broadleaf
```

Aquesta és una diferència fonamental respecte a descarregar indiscriminadament totes les fonts disponibles.

---

# Vertical 17 — Mode Científic / Mode Observador complets

## Mode Científic

Mostra:

```text
font original
versió
codi original

mapping
TLST inicial

evidències
refinaments

ResolutionTrace

TLST final
nivells no resolts

procedència
confiança
precisió
```

Representació visual:

```text
OBSERVAT
MAPEJAT
REFINAT
INFERIT
PROCEDURAL
```

Aquests conceptes no s’han de confondre.

---

## Mode Observador

Mostra principalment:

```text
món procedural
assets
materials
LOD
estat temporal
```

Però qualsevol element pot remetre a la seva traça científica.

---

# Vertical 18 — Procedural Lab independent

Aplicació/laboratori per desenvolupar els generadors sense dependre necessàriament d’una classificació raster externa.

```text
DEM
+
rectangle/polígon dibuixat
+
TLST seed / perfil territorial
+
culture profile
+
seed
        ↓
mateix motor procedural Python
        ↓
Three.js
```

No serà un segon motor.

Utilitzarà els mateixos:

```text
SpatialPatch
SurfaceInterpretation
Generators
Asset selectors
LOD descriptors
```

que TerraLab3D.

---

## Procedural urbà experimental

La mida de l’àrea pot governar:

```text
casa
→ granja
→ aldea
→ poble
→ ciutat
→ metròpoli
```

Pipeline:

```text
terrain cost
→ roads
→ blocks
→ parcels
→ zoning
→ buildings
→ details
```

Això permet desenvolupar i provar generació procedural encara que no existeixin dades reals.

---

# Vista completa revisada

```text
V1  TLST 1.0
    + S2GLC
    + WorldCover
    + auditoria E2E
 │
V2  Raster universal
    + elevació importable
 │
V3  Categòric universal
    + registre d'estàndards
    + equivalències estàndard → TLST
    + cobertura jeràrquica
 │
V4  Esquemes categòrics personalitzats
    + mapping manual → TLST
 │
V5  Refinaments orientats
    a bifurcacions TLST no resoltes
 │
V6  Evidències normalitzades
    + procedència
    + precisió semàntica
 │
V7  Hierarchical InterpretationResolver
    + ResolutionTrace
 │
V8  SpatialPatch
    + halo
    + cache espacial
 │
V9  Procedural agricultura
 │
V10 Boscos
    + shrub
    + grass
 │
V11 Built-up
    + OSM
 │
V12 Aigua
    + wetlands
    + snow/ice
    + bare
 │
V13 Assets
    + materials
 │
V14 LOD procedural
 │
V15 Estat temporal
    + estacions
 │
V16 Refinement Cache automàtic
    guiat pels buits TLST
 │
V17 Mode Científic
    + Mode Observador
 │
V18 Procedural Lab
```

# Flux global final

```text
                    DADES DE COBERTURA
                           │
         ┌─────────────────┼───────────────────┐
         │                 │                   │
       S2GLC           WorldCover            CLC
         │                 │                   │
         ├─────────────────┼───────────────────┤
         │          altres estàndards          │
         └─────────────────┬───────────────────┘
                           │
                           ▼
                SourceSchemeTranslator
                           │
                           ▼
              TLST més profund demostrable
                           │
                           ▼
                Què queda sense resoldre?
                           │
                    ┌──────┴──────┐
                    │             │
                  res          no resolt
                    │             │
                    │             ▼
                    │      RefinementRegistry
                    │             │
                    │             ▼
                    │          Evidence
                    │             │
                    └──────┬──────┘
                           ▼
              HierarchicalInterpretationResolver
                           │
                           ▼
               SurfaceInterpretation TLST
                           │
                           ▼
                     SpatialPatch
                           │
                           ▼
                Procedural Generator
                           │
                           ▼
                  Scene Descriptor
                           │
                           ▼
                     TypeScript
                           │
                           ▼
                      Three.js
```

# Regla final del sistema

La classificació territorial segueix aquesta prioritat conceptual:

```text
1. Observar.
2. Traduir.
3. Determinar fins on sabem.
4. Identificar què no sabem.
5. Buscar evidència específica per resoldre-ho.
6. Refinar només quan l'evidència ho permet.
7. Aturar-se quan deixa d'haver-hi evidència.
8. Generar només amb la precisió realment assolida.
```

Per tant:

> **TLST defineix tot allò que TerraLab3D és capaç d’expressar; els estàndards determinen quina part d’aquesta jerarquia podem observar directament; els refinaments intenten completar únicament els nivells que continuen sense resoldre; i el procedural representa el resultat sense fabricar precisió semàntica inexistent.**
