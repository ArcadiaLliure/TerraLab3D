# Pla mestre per verticals

## Estat executat — 2026-08-31

En preparar aquesta revisió, el HEAD observat de `gestor_capes` és:

```text
418006ba5c0339ca10d61784542590df8caf06ea
Avenç de Pas 23: Gestor de capes. Parcialment funcional
```

Si existeixen commits posteriors, preval sempre el codi real.

- **Vertical 1 completada:** TLST 1.0 versionat, S2GLC i WorldCover, `SampleValidity`, buffers categòrics, picking i tooltip català descriptiu. La clau TLST es conserva al contracte d'auditoria però no es mostra al tooltip ordinari.
- **Vertical 2 completada:** descriptor raster neutral, port únic Rasterio per a fonts raster externes, selecció explícita de banda/subdataset, adaptador TXT/CSV/XYZ regular, importació `managed`/`external`, persistència ordenada a `data_sources.json`, fallback DEM, recàrrega segura del port d'elevació i regeneració de terreny/horitzó.
- **Vertical 3 completada:** importació categòrica enter/paleta/RGB/RGBA sense interpolació, registre versionat, mappings exhaustius S2GLC, WorldCover, Copernicus LCM-10 i CORINE, revisió obligatòria, auditoria de profunditat i activació raster real.
- **Vertical 4 completada:** esquemes d'usuari persistents i reutilitzables, mapping de cada valor a qualsevol node TLST o estat admissible, i revisió immutable identificada per `scheme_key + scheme_version + mapping_revision`.
- **Gestor d'adquisició de refinaments implementat / WIP:** AOI, jerarquia, descoberta multiproveïdor, llicències fail-closed, plans congelats, descàrrega, cancel·lació, autenticació CDSE, harmonització TLST, mosaic incremental de les instal·lacions, cobertura verificada, importació manual i UI. La matriu exacta és a [tlst-refinement-manager.md](tlst-refinement-manager.md).
- **Governador, resolver global, caché TLST canònica, SpatialPatch i procedural no implementats:** són les següents verticals d'aquest pla i no s'han de documentar com a funcionalitat disponible.

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
LCM-10 ──────────────┤
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

Si l'estàndard no diferencia què hi ha sota:

```text
agriculture.cropland
├── ...
├── permanent_crop
│   ├── vineyard
│   ├── orchard
│   └── ...
└── ...
```

la traducció s'atura.

No s'inventa cap fill.

A partir d'aquí cal distingir dues decisions:

```text
QUINA FONT BASE DESCRIU AQUESTA POSICIÓ?
→ governador espacial

FINS A QUIN DESCENDENT TLST PODEM ARRIBAR?
→ refinament semàntic
```

La cadena revisada és:

```text
categòrics generals actius
        ↓
governador per posició
        ↓
node TLST base
        ↓
refinaments compatibles
        ↓
resolver determinista
        ↓
TLST final
        ↓
caché TLST canònica
        ↓
SpatialPatch
        ↓
procedural
```

---

# Regles invariants

## 1. TLST és l'autoritat semàntica

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

## 3. La traducció arriba només fins on arriba l'estàndard

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

## 4. Sense categòric general actiu no hi ha refinament

El categòric general sol continua sent una interpretació vàlida.

Els refinaments són opcionals, però necessiten una base.

```text
TERRA
├── Elevació
├── Categòric
│   └── almenys una font general activa
└── Refinament
    └── disponible després de tenir base
```

---

## 5. El governador és una decisió espacial

Per cada posició:

```text
fonts BASE_CATEGORICAL actives
→ ordenar per menor mida de cel·la
→ primera amb dada semàntica vàlida
→ TLST base
```

En empat de resolució s'utilitza la prioritat persistent.

`NoData`, `unknown` i `unclassified` activen fallback a la següent font.

---

## 6. El refinament no pot contradir el governador

Un refinament només pot mantenir o aprofundir la branca TLST del node actual.

```text
candidate == current
```

o:

```text
candidate descendant_of current
```

Una altra branca és `NOT_APPLICABLE`.

---

## 7. L'ordre entre refinaments és determinista

Entre refinaments compatibles:

```text
1. major profunditat TLST
2. major precisió espacial
3. prioritat persistent
4. stable ID només com a últim tie-break tècnic
```

TerraLab3D no calcula un `trust score` o una puntuació subjectiva de fiabilitat dels datasets.

---

## 8. Ignorar no és eliminar

Una font pot estar:

```text
ACTIVA
IGNORADA
```

sense perdre els fitxers, la llicència ni la procedència.

L'estat ha de persistir i la reactivació no ha d'obligar a redescàrrega.

---

## 9. No resoldre també és informació

Per una bifurcació podem tenir:

```text
RESOLVED
UNRESOLVED
NOT_APPLICABLE
```

Això és diferent de:

```text
nodata
unknown
unclassified
```

que continuen sent `ObservationState` i no categories TLST.

---

## 10. El raster original mai es modifica

Sempre es conserva:

```text
source
source_version
source_code
source_value
mapping_revision
TLST result
resolution trace
```

La classificació resolta és una interpretació derivada.

---

# Vertical 1 — TLST 1.0 + S2GLC + WorldCover + inspecció científica E2E

## Estat

**COMPLETADA**

És la primera implementació real del sistema canònic TLST.

La precaució continua sent la mateixa:

`uint16`, màscara de 2 bits, `R8UI`, etc. són decisions d'implementació d'aquesta vertical, no propietats universals de TLST.

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

Els mappings S2GLC i WorldCover implementats aquí són membres del registre general d'equivalències de la Vertical 3. No són casos arquitectònicament especials.

---

# Vertical 2 — Lector raster universal + importació d'elevació

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
fitxer raster extern
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

Suporta els formats disponibles a la instal·lació GDAL/Rasterio, inclosos GeoTIFF, COG, VRT, AAIGrid, ENVI, BIL/BIP/BSQ, IMG, JP2, NetCDF, HDF, GRIB, SAGA, PCRaster, Idrisi, Surfer, Zarr quan Rasterio/GDAL l'ofereixi, etc.

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

No reobrir aquesta vertical per implementar la caché TLST. La caché interna Zarr és una responsabilitat diferent de la façana Rasterio d'entrada.

---

# Vertical 3 — Categòric universal + registre d'estàndards + equivalències TLST

## Estat

**COMPLETADA**

El lector universal analitza finestres exactes d'enters, paleta, RGB o RGBA i materialitza una vista indexada reconstruïble només després de la confirmació. El valor font, dtype, esquema, versió i revisió del mapping continuen sent l'autoritat d'auditoria. Els IDs compactes no són identitat pública.

El registre inicial conté S2GLC, WorldCover 2020/2021, Copernicus LCM-10 i les 44 classes CORINE, més els seus NoData declarats.

Aquesta vertical construeix la capa universal de traducció entre classificacions externes i TLST 1.0.

## 3.1 Importació categòrica universal

```text
TERRA
→ Categòric
→ + Importar
→ raster
→ lectura de codificació
→ selecció/detecció d'esquema
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

## 3.2 Detecció d'esquema

Només després que l'usuari hagi declarat:

```text
tipus = categòric
```

TerraLab3D pot intentar reconèixer l'esquema a partir de dades objectives.

Mai intenta deduir si el raster "sembla bosc" o "sembla un DEM".

## 3.3 Registre universal

Cada esquema conegut defineix:

```text
scheme_key
scheme_version
classes
source_semantics
mapping_revision
TLST mappings
```

## 3.4 Matriu estàndard → TLST

Per cada classe externa es documenta el node TLST màxim justificat.

| Estàndard | Classe externa | TLST màxim justificat |
|---|---|---|
| Estàndard A | Cropland | `agriculture.cropland` |
| Estàndard B | Permanent crops | `agriculture.cropland.permanent_crop` |
| Estàndard C | Vineyards | `agriculture.cropland.permanent_crop.vineyard` |

No s'obliga totes les fonts a arribar a la mateixa profunditat.

## 3.5 Cobertura jeràrquica

A partir dels mappings es pot derivar quins nodes resol directament cada esquema i quines bifurcacions deixa obertes. Aquesta informació serà consumida pel futur resolver i pel futur planificador automàtic de refinaments.

## 3.6 Tipus de mapping

Es mantenen:

```text
single
composite
observation_state
```

Un mapping a un node pare no afirma res sobre els descendents.

---

# Vertical 4 — Classificacions personalitzades

## Estat

**COMPLETADA**

Una classificació creada per l'usuari entra al mateix registre que els estàndards. Es persisteix atòmicament a `classification_schemes.json`, es torna a carregar en reiniciar i no permet sobreescriure silenciosament una revisió existent.

L'usuari pot mapar honestament a un node intermedi.

Exemple:

```text
mapa_manel.tif

1  = bosc
2  = cereal
7  = oliverar
22 = aigua
```

```text
1  → tree_cover
2  → [node agrícola justificat]
7  → ...olive_grove
22 → water...
```

Persistència:

```text
scheme_key
scheme_version
mapping_revision
class mappings
```

A partir d'aquí funciona igual que qualsevol altre esquema extern.

---

# Gestor d'adquisició de refinaments — infraestructura existent

## Estat

**IMPLEMENTAT / PARCIALMENT FUNCIONAL**

Aquesta peça no és una nova vertical pendent de crear.

Ja existeixen:

- AOI;
- arbre TLST;
- descoberta multiproveïdor;
- filtre comercial fail-closed;
- plans immutables;
- descàrrega;
- cancel·lació;
- autenticació CDSE;
- traducció source → TLST;
- postprocessat;
- mosaic de la instal·lació;
- cobertura verificada;
- importació manual;
- persistència;
- UI.

El seu paper és proporcionar fonts locals normalitzades al sistema de resolució que es construeix a V5–V7.

Els artefactes actuals `refinement_mosaic.tif`, `refinement_source.tif`, `refinement_quality.tif`, `refinement_conflict.tif` i manifest es conserven com a derivats de les instal·lacions/planes actuals.

No són encara la caché territorial global definitiva.

---

# Vertical 5 — Ràster governador + `Actiu/Ignorat` + prioritat persistent

## Estat

**PENDENT — pròxima vertical recomanada**

## Objectiu

Formalitzar quin categòric general governa cada posició i separar:

```text
BASE_CATEGORICAL
```

de:

```text
SEMANTIC_REFINEMENT
```

## Dependència funcional

No s'apliquen refinaments si no existeix almenys un categòric general actiu.

## Activació

Reutilitzar el concepte `enabled` ja existent on sigui possible.

Una font pot quedar:

```text
ACTIVA
IGNORADA
```

sense ser eliminada.

Persistir també l'ordre de prioritat necessari per desempatar fonts equivalents.

## Algoritme del governador

Per cada posició:

```text
1. BASE_CATEGORICAL actius que cobreixen la posició
2. resolution ASC
3. priority DESC en empat
4. sample
5. si NoData/unknown/unclassified → següent
6. primera dada semàntica vàlida → governador
```

## Exemple

```text
Categòric A 1 m → artificial.built
Categòric B 10 m → agriculture.cropland

→ A governa
```

```text
Categòric A 1 m → NoData
Categòric B 10 m → agriculture.cropland

→ B governa
```

## Reutilitzar

- `data_sources.json`;
- `enabled` categòric actual;
- `ConfiguredSurfaceSampler` o contracte equivalent real;
- registry TLST;
- mappings;
- `RefinementInstallation`;
- repositoris de recursos;
- footprints verificats;
- UI existent.

## No fer

- nou sistema de descàrrega;
- nous providers només per aquesta vertical;
- nova taxonomia;
- quality/trust score;
- caché global encara;
- SpatialPatch.

## Proves mínimes

```text
1 m vàlid + 10 m vàlid → 1 m governa
1 m NoData + 10 m vàlid → 10 m governa
1 m ignored + 10 m actiu → 10 m governa
empat resolució → prioritat
reinici → enabled/priority persisteixen
```

---

# Vertical 6 — Resolver TLST determinista + ResolutionTrace

## Estat

**PENDENT**

## Objectiu

Aplicar refinaments actius sense permetre que contradiguin la branca establerta pel governador.

## Contribució normalitzada mínima

El resolver ha de rebre un descriptor equivalent a:

```text
source_id
source_version
source_role
coverage
spatial_resolution
mapping_revision
source_value
candidate_tlst
provenance
temporal_validity?      # quan aplica
source_confidence?      # només si la font el publica
```

No és necessari crear una subclasse `Evidence` distinta per cada proveïdor si un contracte data-driven resol el problema.

## Compatibilitat

Un refinament només participa si:

```text
candidate_tlst == current_tlst
```

o:

```text
candidate_tlst descendant_of current_tlst
```

Una altra branca s'ignora per aquella posició.

## Ordre

```text
compatibilitat
→ profunditat TLST DESC
→ resolució espacial ASC
→ prioritat DESC
→ stable ID
```

TerraLab3D no calcula una confiança pròpia.

## Exemple compatible

```text
base:
agriculture.cropland

Crop Types:
vineyard

→ aprofundir fins a vineyard segons el mapping TLST real
```

## Exemple incompatible

```text
base 1 m:
artificial.built

Crop Types 10 m:
vineyard

→ ignorar Crop Types
```

## ResolutionTrace

```text
governing_source
governing_source_value
governing_mapping_revision
initial_tlst_node

steps:
  - source_id
  - source_value
  - mapped_tlst
  - previous_tlst
  - resulting_tlst
  - spatial_resolution
  - priority

final_tlst_node
```

## Resultat observable

El mode d'auditoria ha de poder explicar per què un refinament s'ha aplicat o s'ha descartat sense exposar complexitat innecessària al tooltip ordinari.

---

# Vertical 7 — Caché TLST canònica progressiva i multiresolució

## Estat

**PENDENT — crítica abans de SpatialPatch**

## Objectiu

Materialitzar el resultat del governador + resolver en una representació ràpida i regenerable que el runtime pugui consultar sense reinterpretar totes les fonts en cada accés.

```text
sources
→ governor
→ resolver
→ canonical TLST cache
→ surface runtime
```

## Format lògic

```text
<cache-id>.tlstcache/
├── manifest.json
└── data.zarr/
```

Zarr és un backend intern darrere un port propi. Rasterio continua sent la façana de fonts raster externes.

L'exportació a GeoTIFF/COG queda fora d'aquesta vertical.

## Multiresolució

No existeix una sola matriu amb píxels de mida variable.

```text
resolution_1m/
resolution_10m/
resolution_100m/
...
```

Cada array té resolució fixa.

Només es generen els chunks necessaris.

## Contingut dens mínim

```text
tlst_code
validity
```

`categoryKey` continua sent la identitat pública.

`uint16` pot ser l'encoding intern actual mentre TLST hi càpiga.

Traçabilitat preferent:

```text
diccionari de traces per chunk
trace_id opcional
metadata de procedència
```

No duplicar automàticament `source_id`, `quality` o `confidence` a cada cel·la si no és necessari.

## Chunking i compressió

Benchmarkar com a mínim:

```text
512 × 512
1024 × 1024
```

amb:

```text
Zstd
Blosc + Zstd
```

No hardcodejar el guanyador sense mesura.

## Invalidació

Fingerprint mínim:

```text
TLST version
resolver version
active sources
source roles
enabled/ignored
priority
source fingerprints
scheme/version/mapping_revision
CRS/grid/resolution
cache schema version
```

Canvis semàntics invaliden la caché.

Quan existeix footprint fiable, invalidar només chunks solapats.

Si la invalidació parcial no és demostrablement segura, invalidació completa.

## Estimació d'espai

Mida bruta:

```text
cells × bytes obligatoris
```

Mida comprimida estimada:

```text
sample chunks
→ compressor
→ ratio mesurada
→ extrapolació
```

La UI pot informar brut, comprimit estimat i espai lliure, indicant que la mida final pot variar.

## Integració

El consumer de superfície evoluciona de:

```text
esquema concret
```

a:

```text
TLST cache
```

sense reconstruir la geometria DEM.

---

# Vertical 8 — SpatialPatch + halo

## Estat

**PENDENT**

La caché TLST és raster/IO. `SpatialPatch` és una unitat semàntica i procedural.

```text
caché TLST
→ regions espacialment coherents
→ SpatialPatch
```

## Contracte conceptual

```text
category
polygon
area
centroid
neighbours
terrain_stats
provenance
resolution_trace_ref
seed
```

La traça completa es pot referenciar; no cal duplicar-la íntegrament dins de cada patch.

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

Un patch pot travessar tiles.

---

# Vertical 9 — Primer generador procedural: agricultura

## Estat

**PENDENT**

Agricultura continua sent el millor primer generador complet perquè prova:

- polígons irregulars;
- DEM;
- orientació;
- clipping;
- repetició d'assets;
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
→ orientació de files
→ línies paral·leles
→ clip al polígon
→ passadissos
→ distribució de plantes
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

no s'executa arbitràriament un generador de vinya. S'utilitza un generador compatible amb aquella profunditat o un fallback explícit.

---

# Vertical 10 — Boscos, matorral i herbàcies

## Estat

**PENDENT**

Demostra que el contracte procedural no pressuposa files ni agricultura.

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
FAR  → material
MID  → geometria simplificada
NEAR → instàncies
```

El generador depèn de la profunditat TLST realment resolta.

---

# Vertical 11 — Built-up i geometria vectorial

## Estat

**PENDENT**

Vertical procedural complexa.

La necessitat arquitectònica és:

```text
TLST artificial
+
geometries vectorials autoritzades
+
atributs
+
DEM
+
context arquitectònic
        ↓
BuiltUpInterpreter
        ↓
UrbanGenerator
```

No assumir OSM com a font oficial ja integrada: la política comercial actual exclou ODbL/llinatge OSM del catàleg oficial. El motor pot ser compatible amb dades importades externament amb llicència/procedència separades, però això no converteix OSM en dependència oficial.

Separació obligatòria:

```text
QUÈ ÉS
```

de:

```text
COM ES VEU
```

Una geometria autoritativa disponible es conserva; no es reemplaça per una caixa procedural si existeix una geometria millor.

---

# Vertical 12 — Aigua, humedals, neu, gel i bare surfaces

## Estat

**PENDENT**

Completa les famílies principals.

## Wetland

```text
aigua
fang
vegetació
transicions
```

## Water

Només es distingeix river/canal/reservoir/standing water quan TLST + refinaments ho permeten.

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

# Vertical 13 — Sistema d'assets i materials

## Estat

**PENDENT**

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

Afegir un asset nou no obliga a recalcular mappings, TLST, caché ni patches si la semàntica territorial no ha canviat.

---

# Vertical 14 — LOD procedural complet

## Estat

**PENDENT**

Una única identitat semàntica, diverses representacions:

```text
FAR
MID
NEAR
```

Arbre:

```text
FAR  → canopy mass
MID  → impostor
NEAR → mesh
```

Edifici:

```text
FAR  → volum
MID  → footprint + roof
NEAR → façade detail
```

Cultiu:

```text
FAR  → material
MID  → rows
NEAR → instances
```

Canviar de LOD mai modifica TLST.

---

# Vertical 15 — Estacions i estat temporal

## Estat

**PENDENT**

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

No modifica arbitràriament carreteres, edificis, posicions estructurals o parcel·les.

L'estat temporal visual no inventa una classificació TLST més precisa.

Si en el futur un dataset temporal real canvia semàntica territorial, aquesta dependència haurà d'entrar explícitament al fingerprint del resolver/cache corresponent; no es dedueix d'una simple animació estacional.

---

# Vertical 16 — Planificador automàtic de refinaments guiat pels buits TLST

## Estat

**PENDENT**

Aquesta vertical substitueix l'antic concepte de "Refinement Cache automàtic".

La caché TLST canònica ja existeix des de V7.

V16 automatitza la selecció de refinaments útils.

No pregunta simplement:

```text
quines fonts puc descarregar?
```

Pregunta:

```text
quines parts de TLST
continuen massa genèriques
en aquesta àrea?
```

## Pipeline

```text
TLST cache
+
ResolutionTrace
 ↓
detectar nodes encara genèrics
 ↓
quins refinadors poden aportar profunditat nova?
 ↓
reutilitzar discovery del gestor existent
 ↓
filtre de llicència
 ↓
pla
 ↓
descàrrega/importació
 ↓
instal·lació
 ↓
invalidar chunks afectats
 ↓
reconstruir cache
```

Exemple:

```text
Aquí ja sé:
tree_cover.broadleaf

No necessito:
un altre producte que només distingeixi tree_cover

Sí em pot servir:
un producte capaç de discriminar descendents encara oberts
```

La descoberta, llicències, plans i downloads no es tornen a implementar: es reutilitza el gestor existent.

---

# Vertical 17 — Mode Científic / Mode Observador complets

## Estat

**PENDENT**

## Mode Científic

Mostra o permet auditar:

```text
font original
versió
codi original
mapping
TLST inicial
governador
refinaments aplicats/ignorats
ResolutionTrace
TLST final
cache generation
nivells no resolts
procedència
precisió espacial
```

Si una font publica una confiança pròpia es pot mostrar com a metadata de font. No hi ha una "confiança TerraLab" inventada.

Representació conceptual:

```text
OBSERVAT
MAPEJAT
REFINAT
INFERIT
PROCEDURAL
```

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

## Estat

**PENDENT**

Aplicació/laboratori per desenvolupar generadors sense dependre necessàriament d'una classificació raster externa.

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

## Procedural urbà experimental

La mida de l'àrea pot governar:

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
V1  TLST 1.0                         COMPLET
    + S2GLC
    + WorldCover
    + auditoria E2E
 │
V2  Raster universal + DEM           COMPLET
 │
V3  Categòric universal              COMPLET
    + registre d'estàndards
    + mappings estàndard → TLST
    + cobertura jeràrquica
 │
V4  Esquemes personalitzats          COMPLET
    + mapping manual → TLST
 │
    Gestor d'adquisició refinaments  IMPLEMENTAT / WIP
 │
V5  Governador + enabled/ignored     PENDENT
 │
V6  Resolver TLST determinista       PENDENT
    + ResolutionTrace
 │
V7  Caché TLST canònica              PENDENT
    + Zarr intern
    + chunks
    + multiresolució
    + invalidació
 │
V8  SpatialPatch + halo              PENDENT
 │
V9  Procedural agricultura           PENDENT
 │
V10 Boscos + shrub + grass            PENDENT
 │
V11 Built-up / vectors                PENDENT
 │
V12 Aigua + wetlands + snow/bare      PENDENT
 │
V13 Assets + materials                PENDENT
 │
V14 LOD procedural                    PENDENT
 │
V15 Estat temporal                    PENDENT
 │
V16 Planificador auto refinaments     PENDENT
    guiat pels buits TLST
 │
V17 Mode Científic + Observador       PENDENT
 │
V18 Procedural Lab                    PENDENT
```

---

# Flux global final revisat

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
             fonts categòriques generals
                           │
                           ▼
                Ràster Governador
            resolució + fallback NoData
                           │
                           ▼
                  node TLST base
                           │
                           ▼
               refinaments compatibles
                           │
                           ▼
               TLST Resolver determinista
        profunditat → resolució → prioritat
                           │
                           ▼
                    ResolutionTrace
                           │
                           ▼
                 Caché TLST canònica
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

---

# Regla final del sistema

La classificació territorial segueix aquesta prioritat conceptual:

```text
1. Observar les fonts categòriques generals actives.
2. Traduir cada font directament a TLST.
3. Escollir el governador espacial més precís amb dada vàlida.
4. Aplicar fallback quan el governador candidat té NoData.
5. Fixar la branca TLST base.
6. Considerar només refinaments compatibles amb aquella branca.
7. Guanyar per profunditat semàntica, després resolució i després prioritat.
8. Conservar una ResolutionTrace determinista.
9. Materialitzar el resultat en una caché TLST canònica progressiva.
10. Construir SpatialPatch sobre la caché quan arribi la vertical corresponent.
11. Generar només amb la precisió TLST realment assolida.
```

Per tant:

> **TLST defineix tot allò que TerraLab3D és capaç d'expressar; el categòric governador determina quina branca descriu espacialment cada posició; els refinaments només poden aprofundir aquesta branca; la caché TLST materialitza el resultat de forma eficient; i el procedural representa la interpretació assolida sense fabricar precisió semàntica inexistent.**
