# TLST i sistema universal de capes Terra

## Estat implementat — 2026-08-31

Aquest document continua sent l'autoritat funcional del sistema TLST i de les
verticals de superfície de TerraLab3D, sempre subordinat al codi real del HEAD.

En preparar aquesta revisió, la branca observada és `gestor_capes` i el HEAD és:

```text
418006ba5c0339ca10d61784542590df8caf06ea
Avenç de Pas 23: Gestor de capes. Parcialment funcional
```

Si existeixen commits posteriors, preval el HEAD nou.

El codi real incorpora:

- TLST 1.0 amb `categoryKey` com a identitat estable i presentació catalana separada mitjançant `categoryLabelKey`;
- `SampleValidity`, `SingleSurface`, `CompositeSurface` i `ObservationState`;
- picking i tooltip descriptiu sense exposar la clau tècnica TLST a l'usuari ordinari;
- descriptor raster neutral i Rasterio com a façana de fonts raster externes;
- formats disponibles dinàmicament segons GDAL/Rasterio, sense whitelist artesanal com a autoritat;
- importador TXT/CSV/XYZ per matrius textuals quan Rasterio no és aplicable;
- importació d'elevació managed/external, persistència i recàrrega segura del DEM;
- importació categòrica enter/paleta/RGB/RGBA exacta i sense interpolació categòrica;
- S2GLC, WorldCover, Copernicus LCM-10 i CORINE dins del mateix registre versionat d'esquemes;
- mappings directes estàndard → TLST amb profunditat semàntica real;
- classificacions d'usuari persistents amb identitat `scheme_key + scheme_version + mapping_revision`;
- gestor d'adquisició de refinaments amb AOI, descoberta multiproveïdor, llicències fail-closed, plans, descàrrega, cancel·lació, autenticació, harmonització, postprocessat, mosaic d'instal·lació, cobertura verificada, persistència, importació manual i UI;
- ICGC MCSC, CORINE, les famílies CLMS habilitades i ESA WorldCover 2021 v200 al rollout actual, subjectes sempre al HEAD real.

Les **Verticals 1–4 estan completades** i no s'han de reobrir per aquesta
revisió.

El gestor d'adquisició de refinaments existeix i s'ha de reutilitzar, però encara
no constitueix el resolver territorial global.

Continuen pendents:

```text
V5  Ràster Governador + Actiu/Ignorat
V6  Resolver TLST determinista + ResolutionTrace
V7  Caché TLST canònica progressiva
V8  SpatialPatch + halo
V9+ procedural
```

La generació procedural continua fora del lliurament actual.

**Principi arquitectònic central:** TLST 1.0 és la lingua franca semàntica. Cada
estàndard extern es tradueix directament a TLST fins al node més profund que la
seva llegenda permet demostrar. Entre categòrics generals, la font activa més
precisa espacialment amb dada vàlida governa la posició. Els refinaments només
poden aprofundir dins d'aquesta branca. `NoData` activa fallback. El resultat es
materialitzarà en una caché TLST canònica abans de construir SpatialPatches.

---

```text
MISSIÓ — TERRALAB3D: SISTEMA UNIVERSAL DE CAPES TERRA,
TAXONOMIA CANÒNICA, GOVERNADOR, REFINAMENT, CACHÉ TLST
I BASE DEL MODE PROCEDURAL

Treballa sobre el repositori:

https://github.com/ArcadiaLliure/TerraLab3D

Branca de treball quan aquesta missió s'executi:

gestor_capes

IMPORTANT:

NO comencis implementant directament.

Primer revisa exhaustivament el HEAD actual del repositori.

No parteixis d'una arquitectura imaginada.
No assumeixis que aquest document descriu exactament l'estat actual del codi.
No creïs una arquitectura paral·lela.

ORDRE D'AUTORITAT:

1. HEAD real del repositori quan executis la tasca.
2. Proves i contractes actuals.
3. docs/pla-implementacio-pas-a-pas.md.
4. README arquitectònics de les diferents capes.
5. Aquest document per a funcionalitat que encara no existeix.

HEAD observat en preparar aquesta revisió:

418006ba5c0339ca10d61784542590df8caf06ea

"Avenç de Pas 23: Gestor de capes. Parcialment funcional"

Si existeixen commits posteriors, preval sempre el HEAD nou.
```

======================================================================
1. ARQUITECTURA ACTUAL PRIORITÀRIA
======================================================================

TerraLab3D manté una separació deliberada aproximadament així:

```text
domini
  ↓
aplicació
  ↓
ports
  ↓
infraestructura
  ↓
escena neutral / contractes
  ↓
frontend TypeScript
  ↓
Three.js
```

Respecta-la.

Principis establerts:

- La capa d'aplicació coordina casos d'ús.
- L'aplicació no coneix adaptadors concrets.
- La ciència i les decisions de negoci autoritatives viuen en Python.
- Els adaptadors no decideixen comportament de producte.
- Three.js no executa càlcul científic.
- TypeScript no duplica la lògica geoespacial de Python.
- Els buffers grans no s'envien com JSON textual ni Base64.
- Les operacions asíncrones mantenen correlació, cancel·lació i descart de resultats obsolets.
- Cada vertical funcional deixa TerraLab3D executable.
- No es crea un nou gestor de recursos al costat del que ja existeix.
- No es crea una nova taxonomia territorial al costat de TLST.

No creïs un "nou TerraLab3D" al costat de l'actual.

Extén el que existeix.

======================================================================
2. AUDITORIA OBLIGATÒRIA DEL HEAD
======================================================================

Abans de modificar res, inspecciona com a mínim:

```text
README.md
docs/
docs/TLST.md
docs/TLST-vertical.md
docs/tlst-refinement-manager.md
docs/pla-implementacio-pas-a-pas.md
docs/resource-layer-manager.md
docs/DEM_PARITY.md

backend/src/terralab3d/domain/
backend/src/terralab3d/application/
backend/src/terralab3d/application/ports/
backend/src/terralab3d/application/refinement/
backend/src/terralab3d/infrastructure/
backend/src/terralab3d/infrastructure/adapters/dem/
backend/src/terralab3d/infrastructure/adapters/surface/
backend/src/terralab3d/infrastructure/adapters/refinement/
backend/src/terralab3d/infrastructure/resources/
backend/src/terralab3d/__main__.py

frontend/src/application/
frontend/src/contracts/
frontend/src/view/
frontend/src/view/ui/
frontend/src/view/ui/modals/
frontend/src/view/three/

contracts/
backend/tests/
frontend/tests/ si existeixen
```

Revisa específicament:

- `TaxonomyCatalog` i la font `tlst-1.0.json`;
- `LayerDatabase`;
- `ResourceDescriptor`;
- `ResourceDomain`;
- `ResourceCategory`;
- `ResourceInstallationRepository`;
- `DownloadJobManager`;
- `ResourceManager`;
- `ResourceManagerModal`;
- sistema DEM actual;
- `ConfiguredSurfaceSampler` o successor real;
- resolució actual de land-cover;
- ús actual de Rasterio;
- `LandCoverCoordinator` si continua existint;
- tiles categòrics;
- renderer categòric;
- picking de superfície;
- `data_sources.json`;
- `data_location.json`;
- `classification_schemes.json`;
- repositori d'instal·lacions de refinament;
- `RefinementService`;
- `RefinementBridgeController`;
- `RefinementSession`;
- `RefinementManagerView`;
- `RasterRefinementMosaicProcessor`;
- postprocessador de refinaments;
- providers habilitats;
- bridge Python ↔ TypeScript;
- recursos binaris;
- cachés actuals.

Classifica cada peça rellevant com:

```text
REUSE
EXTRACT
ADAPT
REWRITE
DISCARD
NEW
```

No reescriguis una peça que es pugui extreure o encapsular netament.

======================================================================
3. RASTERIO ÉS LA FAÇANA RASTER EXTERNA DE TERRALAB3D
======================================================================

La implementació raster Python utilitza Rasterio com a façana principal per a
**fonts raster externes**.

NO introdueixis una segona API raster paral·lela per obrir GeoTIFF, ASC, IMG,
JP2, etc.

Estudia, quan sigui útil:

- `open()`;
- `DatasetReader`;
- `DatasetWriter`;
- bandes;
- finestres;
- transforms;
- CRS;
- bounds;
- nodata;
- colormap;
- color interpretation;
- metadata;
- overviews;
- block windows;
- `WarpedVRT`;
- `MemoryFile`;
- `Env`;
- drivers disponibles;
- masks.

La regla conceptual continua sent:

```text
format físic extern
    ↓
Rasterio
    ↓
descriptor raster neutral TerraLab
    ↓
semàntica declarada
    ↓
intèrpret
    ↓
capa TerraLab
```

La futura caché interna Zarr no contradiu aquesta regla perquè Zarr queda darrere
un port de caché propi i no és una segona via general d'importació raster.

======================================================================
4. OBJECTIU DEL LECTOR RASTER GENÈRIC
======================================================================

```text
FITXER
   ↓
GenericRasterReader
   ↓
RasterDatasetDescriptor
   ↓
SemanticInterpreter
   ↓
Layer
```

El lector genèric només sap:

- obrir el dataset;
- inspeccionar-lo;
- llegir finestres;
- descriure metadades;
- proporcionar valors.

NO sap si està llegint:

- elevació;
- cobertura arbòria;
- temperatura;
- classificació del sòl;
- humitat;
- neu;
- etc.

======================================================================
5. SUPORT DE FORMATS
======================================================================

TerraLab3D accepta els formats raster que la instal·lació de Rasterio/GDAL
sigui capaç d'obrir de forma segura.

No mantinguis una whitelist artesanal d'extensions com a autoritat.

Famílies esperables:

- GeoTIFF / TIFF;
- COG;
- VRT;
- ASC / AAIGrid;
- EHdr;
- ENVI;
- BIL/BIP/BSQ;
- FLT + HDR;
- ERDAS Imagine / IMG;
- JPEG2000;
- NetCDF;
- HDF/HDF5 quan la instal·lació ho permeti;
- GRIB;
- SAGA;
- PCRaster;
- Idrisi;
- Surfer Grid;
- Zarr quan Rasterio/GDAL ho pugui obrir;
- altres formats suportats pel runtime.

Això NO significa crear una classe TerraLab per format.

======================================================================
6. TXT / CSV / MATRIUS ARTESANALS
======================================================================

També es permet:

```text
.txt
.csv
.xyz
```

i altres matrius textuals raonables mitjançant un adaptador específic TerraLab.

Pot llegir:

- integer;
- float;
- espai;
- tab;
- coma;
- punt i coma;
- NoData;
- capçalera quan existeixi.

Si falten dades geogràfiques:

NO inventar-les.

L'assistent demana només allò que falta:

- CRS;
- origen X/Y;
- resolució X/Y;
- files/columnes;
- NoData;
- unitat quan sigui necessària.

======================================================================
7. NO FER HEURÍSTICA SEMÀNTICA
======================================================================

Regla explícita de producte:

> L'USUARI DECLARA QUÈ SIGNIFICA EL RÀSTER.

No intentis endevinar si és DEM, categòric, humitat, temperatura, màscara, etc.

TerraLab3D pot detectar objectivament:

- format;
- bandes;
- dtype;
- dimensions;
- CRS;
- transform;
- bounds;
- resolució;
- NoData;
- palette;
- color interpretation;
- metadata;
- valors únics quan sigui raonable.

Però no el significat científic.

======================================================================
8. TRES FAMÍLIES PRINCIPALS DE TERRA
======================================================================

La UI del domini TERRA és:

```text
TERRA

[ Elevació ] [ Categòric ] [ Refinament ]
```

La funcionalitat existent que no encaixi perfectament no es pot trencar.

Nova regla funcional:

```text
Refinament
→ només aplicable quan hi ha ≥ 1 categòric general actiu
```

La pestanya es pot mostrar deshabilitada o en estat informatiu, però no pot
inventar una base territorial.

======================================================================
9. CONSERVAR EL GESTOR ACTUAL
======================================================================

`ResourceManagerModal` i el gestor de refinaments actual són la base.

No els substitueixis per una aplicació nova.

Mantén:

- CEL / TERRA;
- look & feel;
- modal central;
- colors;
- tipografia;
- cards;
- estats de descàrrega;
- llicència/citació;
- variants;
- lifecycle;
- AOI;
- descoberta;
- plans;
- cancel·lació;
- cobertura;
- UI de refinaments.

======================================================================
10. BOTÓ + IMPORTAR
======================================================================

A TERRA hi ha:

```text
+ Importar
```

Ha d'estar a la mateixa posició visual a Elevació, Categòric i Refinament.

Preferir:

```text
zona central amb scroll
+
footer estable
```

No crear un wizard independent per cada format.

======================================================================
11. REVELAT PROGRESSIU DE LA UI
======================================================================

No crear un wizard de cinc passos quan una única pantalla amb seccions
condicionals és suficient.

Sempre visible:

- fitxer;
- nom de capa;
- metadades bàsiques;
- Importar.

Segons tipus:

- unitats;
- esquema categòric;
- mapping;
- tipus/rol de refinament;
- magnitud;
- banda;
- encoding.

Plegat per defecte:

- CRS detallat;
- bbox;
- transform;
- dimensions;
- NoData override;
- reprojecció;
- metadata;
- opcions avançades.

======================================================================
12. IMPORTACIÓ D'ELEVACIÓ
======================================================================

Aquesta vertical està completada i no s'ha de reobrir.

Flux:

```text
TERRA
→ Elevació
→ + Importar
→ fitxer
→ Rasterio
→ metadades
→ confirmar unitat vertical
→ importar
```

No existeix mapping categòric.

Els valors són continus i poden interpolar quan el cas d'ús ho necessita.

DEM descarregat i DEM importat convergeixen al mateix pipeline tant com sigui
possible.

======================================================================
13. IMPORTACIÓ CATEGÒRICA
======================================================================

Aquesta vertical està completada.

Un raster categòric pot estar codificat com:

- una banda integer;
- indexed/palette;
- RGB;
- RGBA;
- altres representacions justificades.

Mai aplicar interpolació bilineal o cúbica a IDs categòrics.

======================================================================
14. ESQUEMA CATEGÒRIC
======================================================================

Quan l'usuari entra per:

```text
TERRA → Categòric → + Importar
```

ja sabem que és un raster categòric.

L'autodetecció només intenta respondre:

```text
Quin esquema de classificació utilitza?
```

Una vegada confirmat, la traducció és DIRECTA:

```text
S2GLC ─────────→ TLST
WorldCover ────→ TLST
CORINE ────────→ TLST
LCM-10 ────────→ TLST
altres ────────→ TLST
```

Mai:

```text
S2GLC → WorldCover → CORINE → TLST
```

Cada classe externa es mapeja al node TLST més profund que la definició oficial
permet demostrar.

======================================================================
15. CONFIRMACIÓ SEMPRE OBLIGATÒRIA
======================================================================

Encara que la coincidència sigui perfecta:

```text
Estàndard probable:
S2GLC 2017

13/13 codis reconeguts

[ Revisar i confirmar categories ]
```

L'usuari sempre pot inspeccionar el mapping abans del commit inicial.

======================================================================
16. RÀSTER CATEGÒRIC ARTESANAL
======================================================================

Si no coincideix amb cap esquema:

```text
Estàndard:
Personalitzat / desconegut

1 → [node TLST ▼]
2 → [node TLST ▼]
7 → [node TLST ▼]
```

Permetre:

```text
[ Guardar esquema com... ]
```

La Vertical 4 ja persisteix aquests esquemes.

======================================================================
17. TAXONOMIA CANÒNICA TERRALAB
======================================================================

TLST 1.0 és la taxonomia canònica i lingua franca semàntica.

El motor no depèn de codis externs com:

```text
S2GLC 62
LCM-10 90
WorldCover 50
CLC 111
```

Flux:

```text
scheme
+
version
+
band/encoding
+
source code
        ↓
SourceSchemeTranslator
        ↓
node TLST més profund justificat
        ↓
interpretació inicial
```

El raster original es conserva intacte.

El mapping és auditable i versionat.

======================================================================
18. MODEL: CATEGORIA + QUALIFICADORS + COMPONENTS
======================================================================

Evitar explosió combinatòria.

Utilitzar:

```text
categoria TLST
+
qualificadors opcionals
+
components en classes mixtes
```

Exemple:

```text
category:
tree_cover.broadleaf

qualifiers:
phenology = deciduous
canopy_cover = 0.75
```

No crear categories combinatòries artificials.

Els mappings poden ser:

```text
single
composite
observation_state
```

La profunditat TLST forma part de la semàntica.

======================================================================
19. JERARQUIA CANÒNICA V1
======================================================================

La font autoritativa és:

```text
backend/src/terralab3d/data/tlst/tlst-1.0.json
```

No mantenir una segona còpia manual de la taxonomia com a autoritat executable.

La jerarquia cobreix, entre altres, les grans branques:

```text
surface
├── artificial
├── agriculture
├── tree_cover
├── low_vegetation
├── wetland
├── bare_sparse
├── water
└── snow_ice
```

`unknown`, `unclassified` i `nodata` són `ObservationState`, no fills de
`surface`.

Els tests actuals del bridge construeixen 114 nodes TLST al workspace; el codi
real decideix el recompte vigent.

======================================================================
20. QUALIFICADORS
======================================================================

Model extensible per a:

```text
leaf_type
phenology
vegetation_cover
canopy_cover
vegetation_height
management
crop_type
crop_cycle
irrigation
water_regime
salinity
flow
origin
urban_density
imperviousness
land_use
disturbance
biome
```

No inventar valors.

======================================================================
21. CLASSES MIXTES
======================================================================

Permetre conceptualment:

```text
components:
  - agriculture.cropland_unspecified: 0.6
  - low_vegetation.unspecified: 0.4
```

No obligar una classe mosaic a convertir-se falsament en una sola categoria.

======================================================================
22. ESQUEMES A SUPORTAR
======================================================================

Dissenyar el registre perquè afegir un esquema sigui principalment dades.

Actualment implementats com a mínim:

- S2GLC;
- ESA WorldCover 2020/2021;
- Copernicus LCM-10;
- CORINE;
- custom schemes.

Altres classificacions futures es poden afegir quan existeixin mappings
documentats i proves.

Producte != esquema.

Per cada esquema:

```text
scheme + version + source class
→ TLST
```

======================================================================
23. PERSISTÈNCIA DELS MAPPINGS
======================================================================

No introduir SQLite automàticament si l'arquitectura actual ja disposa de
persistència adequada.

Necessitem conservar:

- classification schemes;
- source categories;
- mappings;
- mapping revisions;
- user-defined schemes;
- source colors;
- TerraLab colors;
- qualifiers;
- mixed mappings.

Cada mapping reconstrueix:

```text
scheme_key
scheme_version
source_category/code
mapping_revision
mapping_kind
TLST target
qualifiers
components
observation_state
```

Els refinaments i la `ResolutionTrace` es conserven separadament de l'observació
inicial.

======================================================================
24. VERSIONAT
======================================================================

Una capa categòrica guarda:

```text
scheme_key
scheme_version
mapping_revision
```

Un mapping corregit en el futur no canvia silenciosament projectes antics.

Un canvi de mapping que alteri el resultat TLST també invalida la caché TLST
corresponent.

======================================================================
25. COLORS
======================================================================

Separar:

```text
COLOR ORIGINAL DE L'ESQUEMA
```

per reproducció científica, i:

```text
COLOR TERRALAB
```

com estil intern/fallback.

No barrejar semàntica i presentació.

======================================================================
26. REFINAMENT: DEFINICIÓ REVISADA
======================================================================

Refinament no és un format ni una segona classificació global.

Però tampoc s'aplica sobre el buit.

Abans de refinar cal una classificació categòrica general activa.

Flux:

```text
categòrics generals actius
        ↓
ràster governador
        ↓
node TLST base
        ↓
queden descendents oberts?
     ┌──┴───┐
    NO      SÍ
    │        │
    │        ↓
    │ refinaments compatibles
    │        ↓
    │ aprofundiment possible?
    │    ┌───┴───┐
    │   SÍ      NO
    │    │        │
    │ continua  STOP
    └────┬────────┘
         ↓
TLST final
```

Un refinament no pot saltar a una altra branca TLST.

======================================================================
27. RÀSTER GOVERNADOR
======================================================================

Per cada posició:

```text
1. considerar BASE_CATEGORICAL actius;
2. filtrar els que cobreixen la posició;
3. ordenar per resolució espacial: menor mida de cel·la primer;
4. en empat, prioritat persistent;
5. llegir el valor;
6. NoData/unknown/unclassified → fallback al següent;
7. primera observació semàntica vàlida → TLST base.
```

Aquesta regla respon a:

```text
què hi ha exactament en aquesta posició segons la font espacialment més precisa?
```

Exemple:

```text
categòric general 1 m:
artificial.built

Crop Types 10 m:
vineyard
```

Crop Types no pot governar aquella posició perquè no és un categòric general i,
a més, la branca seria incompatible.

======================================================================
28. ACTIU / IGNORAT
======================================================================

Eliminar no és desactivar.

Una font pot estar:

```text
ACTIVA
IGNORADA
```

Una font ignorada conserva:

- fitxers;
- metadades;
- llicència;
- procedència;
- instal·lació;
- capacitat de reactivació.

Però no participa en governador ni resolver.

Reutilitzar l'`enabled` existent sempre que sigui arquitectònicament correcte.

======================================================================
29. REFINAMENT COMPATIBLE
======================================================================

Una vegada tenim:

```text
current_tlst
```

un refinament només participa si:

```text
candidate_tlst == current_tlst
```

o:

```text
candidate_tlst descendant_of current_tlst
```

Una altra branca és `NOT_APPLICABLE`.

Exemple:

```text
base:
agriculture.cropland

Crop Types:
vineyard

→ compatible
```

```text
base:
artificial.built

Crop Types:
vineyard

→ incompatible
```

======================================================================
30. CONTRIBUCIÓ NORMALITZADA
======================================================================

Els adaptadors no passen semàntica de proveïdor directament al procedural ni al
resolver.

No és necessari crear una classe específica `Evidence` per cada dataset.

Contracte conceptual mínim:

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
```

Opcional:

```text
temporal_validity
source_confidence   # només si la font el publica
qualifiers
geometry
```

Rols conceptuals:

```text
BASE_CATEGORICAL
SEMANTIC_REFINEMENT
CONTEXT
AUTHORITATIVE_GEOMETRY
```

Una mateixa font pot aportar més d'un rol en canals diferents, però cada
contribució ha de declarar què està fent.

======================================================================
31. PRIORITAT ENTRE REFINAMENTS
======================================================================

TerraLab3D no utilitza:

```text
"la font amb més resolució sempre guanya"
```

ni:

```text
"totes les fonts voten"
```

ni:

```text
"quality/trust score TerraLab"
```

Primer es filtra per compatibilitat TLST.

Després:

```text
1. major profunditat semàntica TLST
2. major precisió espacial
3. prioritat persistent
4. stable ID si encara cal desempatar tècnicament
```

Si una font publica una confiança pròpia, es preserva literalment com metadata
per auditoria, no com un score inventat per TerraLab3D.

======================================================================
32. GEOMETRIA AUTORITATIVA
======================================================================

Quan existeixi una font vectorial autoritzada amb geometria més precisa que una
cel·la categòrica, la geometria pot governar només el seu footprint.

Exemple conceptual:

```text
cel·la categòrica 10 × 10 m
+
footprint edifici ocupant 40 %
```

No:

```text
reclassificar tota la cel·la
```

Sí:

```text
intersecció geomètrica
→ la geometria governa només la seva subregió
```

Aquest principi es desenvoluparà a les verticals de SpatialPatch/Built-up.

No assumir OSM com a font oficial actual: qualsevol font vectorial incorporada
ha de respectar la política de llicències del producte.

======================================================================
33. DOS MODES DE SUPERFÍCIE
======================================================================

MODE CIENTÍFIC:

```text
font
→ observació
→ mapping
→ TLST inicial
→ governador
→ refinaments
→ ResolutionTrace
→ TLST final
```

Sense modificar l'observació original.

MODE OBSERVADOR / PROCEDURAL:

```text
TLST final
+
atributs
+
context
→ SpatialPatch
→ procedural
→ representació naturalista
```

Canviar de mode no torna a carregar el DEM.

El Mode Observador no exigeix arribar a una fulla TLST.

======================================================================
34. REPARTIMENT DE RESPONSABILITATS
======================================================================

PYTHON:

- lectura i normalització geoespacial;
- mappings;
- governador;
- resolver;
- caché TLST;
- interpretació;
- patches;
- geometria procedural;
- selecció semàntica;
- descriptors.

TYPESCRIPT:

- bridge;
- contractes;
- lifecycle;
- caches frontend;
- streaming;
- picking;
- recursos;
- LOD visual;
- coordinació de presentació.

THREE.JS:

- render.

======================================================================
35. RENDERER DESACOBLAT
======================================================================

Python no retorna `THREE.Mesh`, `THREE.Material` ni `THREE.InstancedMesh`.

Retorna descriptors neutrals:

```text
assetId
materialId
position
rotation
scale
polygon
polyline
height
semanticType
seed
provenance
```

======================================================================
36. CACHÉ TLST CANÒNICA
======================================================================

Aquesta peça es construeix **abans de SpatialPatch**.

El runtime de superfície no ha de dependre per sempre d'un raster concret de
Copernicus o d'un esquema de 13 categories.

Flux:

```text
fonts categòriques generals
+
refinaments
+
mappings
+
prioritats
        ↓
ràster governador
        ↓
TLST resolver
        ↓
CACHÉ TLST CANÒNICA
```

La caché és:

- derivada;
- regenerable;
- georeferenciada;
- chunked;
- progressiva;
- multiresolució;
- auditable mitjançant manifest i traces.

No modifica cap raster original.

======================================================================
37. FORMAT DE CACHÉ
======================================================================

Bundle lògic:

```text
<cache-id>.tlstcache/
├── manifest.json
└── data.zarr/
```

`.tlstcache` és el contracte lògic TerraLab3D.

Zarr és un backend intern, no el format públic del domini.

Separació:

```text
fonts raster externes
→ Rasterio

caché interna
→ CanonicalTlstCacheStore
→ ZarrCanonicalTlstCacheStore
```

No exposar `zarr.Array` fora de l'adaptador d'infraestructura.

L'exportació a GeoTIFF/COG queda per una fase futura.

======================================================================
38. MULTIRESOLUCIÓ DE CACHÉ
======================================================================

No construir una matriu amb cel·les de mida variable.

Sí:

```text
resolution_1m/
resolution_10m/
resolution_100m/
...
```

Cada array té resolució fixa.

Els nivells es generen només quan cal.

La màxima precisió disponible pot variar espacialment perquè no totes les zones
tenen chunks a tots els nivells.

======================================================================
39. CHUNKING I COMPRESSIÓ
======================================================================

Candidats inicials a benchmark:

```text
512 × 512
1024 × 1024
```

Compressors:

```text
Zstd
Blosc + Zstd
```

No congelar valors sense mesurar dades TLST reals.

El manifest registra:

```text
codec
codec_level
chunk_shape
dtype
cache_schema_version
```

======================================================================
40. ENCODING I DADES DENSES
======================================================================

Core dens recomanat:

```text
tlst_code
validity
```

`uint16` és un encoding intern viable mentre hi càpiga la taxonomia actual.

La identitat pública continua sent `categoryKey`.

Manifest:

```text
tlst_version
cache_schema_version
resolver_version
code_to_category_key
crs
resolution
chunk_shape
codec
source_fingerprint
```

Evitar canals densos permanents de `source_id`, `quality` o `confidence` si la
traçabilitat es pot representar de manera més compacta.

Preferir:

```text
TLST dens
+
trace dictionary per chunk
+
trace_id opcional
```

======================================================================
41. INVALIDACIÓ DE CACHÉ
======================================================================

Fingerprint mínim:

- TLST version;
- resolver version;
- fonts actives;
- rols de font;
- enabled/ignored;
- priority;
- fingerprints de fitxers;
- scheme/version/mapping_revision;
- CRS/graella/resolució;
- cache schema version.

Invaliden:

- instal·lar font;
- eliminar font;
- activar/ignorar;
- canviar prioritat;
- canviar mapping;
- substituir fitxer;
- canviar TLST;
- canviar resolver.

No invaliden:

- càmera;
- FOV;
- resize;
- pan/zoom;
- estils visuals sense semàntica.

Quan existeix footprint fiable, invalidar només chunks afectats.

Si no és demostrablement segur:

```text
full invalidation
```

======================================================================
42. ESTIMACIÓ D'ESPAI
======================================================================

Mida bruta:

```text
number_of_cells × bytes obligatoris per cel·la
```

Mida comprimida estimada:

```text
mostra de chunks
→ compressor real
→ ratio observada
→ extrapolació
```

UI:

```text
Caché TLST estimada
Brut: ...
Comprimit estimat: ...
Espai lliure: ...
```

La mida final pot variar segons distribució de categories i compressió.

======================================================================
43. SPATIAL PATCH
======================================================================

SpatialPatch ve després de la caché TLST.

Molts píxels relacionats:

```text
████████
██████████
  ███████
   █████
```

es converteixen en una geometria semàntica coherent.

Contracte conceptual:

```text
id
category
polygon
area
perimeter
centroid
neighbours
terrain_stats
resolution_trace_ref
provenance
seed
```

No cal duplicar tota la traça si es pot referenciar eficientment.

======================================================================
44. TILE != PATCH
======================================================================

Tile:

- streaming;
- cache;
- transport;
- GPU.

SpatialPatch:

- unitat semàntica;
- unitat procedural.

Un patch pot travessar tiles.

======================================================================
45. HALO
======================================================================

Cada patch pot analitzar l'entorn adjacent.

Serveix per:

- continuïtat;
- transicions;
- carreteres;
- vores;
- aigua;
- context urbà;
- evitar seams.

======================================================================
46. PROCEDURAL ESPECIALITZAT
======================================================================

No hi ha un únic algoritme universal.

Exemples:

```text
ForestInterpreter / ForestGenerator
CroplandInterpreter / CropLayoutGenerator
BuiltUpInterpreter / UrbanGenerator
WetlandInterpreter / WetlandGenerator
```

La selecció del generador respecta el node TLST realment resolt.

======================================================================
47. CULTIUS
======================================================================

Exemple:

```text
polígon irregular
→ analitzar geometria
→ orientació candidata
→ pendent
→ accessos/camins
→ línies paral·leles
→ clip
→ passadissos
→ separació
→ assets
→ seed
```

No codificar regles del tipus "si pentàgon → X".

======================================================================
48. BOSC
======================================================================

```text
patch
→ densitat
→ blue-noise / Poisson o alternativa justificada
→ clústers
→ clarianes
→ gradients de vora
→ assets compatibles
```

No una cel·la = un arbre.

======================================================================
49. MATOLLAR
======================================================================

- distribució irregular;
- clústers;
- clarianes;
- densitat variable;
- alçades variables;
- sòl/roca visible.

======================================================================
50. HERBASSARS
======================================================================

Lluny:

```text
material / shader
```

A prop:

```text
instàncies / geometria
```

No milions de brins sempre.

======================================================================
51. HUMEDALS
======================================================================

Un patch pot contenir:

- aigua;
- fang;
- vegetació;
- transicions;

segons context.

======================================================================
52. MOLSES / LÍQUENS / SÒL NU
======================================================================

Prioritzar:

- materials;
- PBR;
- màscares;
- variació procedural.

No assets individuals innecessaris.

======================================================================
53. SUPERFÍCIES ARTIFICIALS
======================================================================

Flux general futur:

```text
TLST artificial
+
geometria vectorial autoritzada quan existeixi
+
atributs
+
DEM
+
context
→ BuiltUpInterpreter
→ UrbanGenerator
```

No assumir OSM com a font oficial habilitada: la política comercial actual
exclou ODbL/llinatge OSM del catàleg oficial.

======================================================================
54. QUÈ ÉS VS COM ÉS
======================================================================

QUÈ ÉS:

- casa;
- bloc;
- nau;
- granja;
- oficina;
- equipament;
- església;
- generic building.

COM ÉS:

- mediterrani;
- centreeuropeu;
- nòrdic;
- muntanya;
- etc.

No barrejar les dues decisions.

======================================================================
55. EDIFICIS
======================================================================

Si existeix footprint autoritatiu:

```text
conservar-lo
→ extrusió
→ coberta
→ façana procedural
```

Si hi ha tipus fiable, usar-lo.

Cas ambigu:

```text
generic_building
```

No inventar hotel/fàbrica/etc. sense evidència.

======================================================================
56. PERFIL ARQUITECTÒNIC INICIAL
======================================================================

Inicialment Europa.

Context:

```text
clima
+
latitud
```

Perfils amb pesos:

```text
mediterranean
central_european
nordic
mountain
```

No classificació rígida.

======================================================================
57. INTERPRETACIÓ PERSISTENT
======================================================================

Separar:

```text
què és el lloc
```

de:

```text
quin asset el representa
```

Afegir un asset nou no obliga a recalcular dades geogràfiques.

======================================================================
58. ESTACIÓ
======================================================================

Una seed estructural estable.

L'estació modifica:

- fullatge;
- color;
- verdor;
- cultiu;
- neu.

No mou arbitràriament carreteres, edificis o arbres.

======================================================================
59. DETERMINISME
======================================================================

Seed derivada de:

```text
worldSeed
+
semanticId
+
coordenades globals
+
patchId
```

Mateixos inputs → mateix món.

======================================================================
60. LOD
======================================================================

ARBRE:

```text
FAR  → canopy / massa
MID  → simplificat / impostor
NEAR → asset 3D
```

EDIFICI:

```text
FAR  → volum
MID  → footprint + coberta
NEAR → façana
```

CULTIU:

```text
FAR  → material / textura
MID  → files simplificades
NEAR → instàncies
```

No regenerar el món per LOD.

======================================================================
61. BRIDGE
======================================================================

No enviar milions de posicions en JSON textual.

Preferir:

- typed arrays;
- buffers existents;
- estructures compactes.

No introduir frameworks de serialització nous sense necessitat mesurada.

======================================================================
62. PROCEDÈNCIA
======================================================================

Cada element procedural ha de distingir:

- observat;
- mapejat;
- refinat;
- inferit;
- procedural.

La procedència final pot reconstruir:

```text
source observation
→ mapping revision
→ governing source
→ initial TLST
→ refinement steps
→ ResolutionTrace
→ final TLST
→ cache generation
→ SpatialPatch
→ procedural interpretation
→ representation
```

======================================================================
63. PLANIFICADOR AUTOMÀTIC DE REFINAMENTS
======================================================================

Aquesta responsabilitat substitueix l'antic concepte de "Refinement Cache
automàtic".

La caché TLST ja existeix abans, a V7.

La futura V16 fa:

```text
TLST cache
+
ResolutionTrace
↓
quins nodes continuen genèrics?
↓
quines fonts poden aprofundir-los?
↓
reutilitzar RefinementRegistry/discovery existent
↓
filtre de llicència
↓
plan/download/import
↓
activar instal·lació
↓
invalidar chunks afectats
↓
reconstruir cache
```

No descarregar totes les fonts conegudes indiscriminadament.

======================================================================
64. NO FER UN RÀSTER CÚBIC
======================================================================

No construir una matriu densa amb tots els canals del món:

```text
clima
soil
tree density
crop
vectors
...
```

Mantenir:

```text
base categòrica
+
refinaments raster disponibles
+
canals continus
+
vectors
+
provenance
+
caché TLST final compacta
```

======================================================================
65. REFINAMENT IMPORTAT
======================================================================

```text
TERRA → Refinament → + Importar
```

pot acceptar formats raster/vector compatibles amb la pila GIS existent.

L'usuari declara el significat/perfil.

El perfil conegut pot declarar:

- rol;
- node/s aplicables;
- mappings;
- qualificadors;
- capacitat de refinament.

Un land-cover general ha d'entrar preferentment pel pipeline `Categòric`, no
disfressar-se de refinament.

======================================================================
66. RECURSOS OFICIALS I LOCALS
======================================================================

Un dataset descarregat per TerraLab3D i un importat per l'usuari convergeixen
tant com sigui possible al mateix model de:

```text
Resource
Layer
```

No crear dos gestors independents.

Estats visuals possibles:

```text
LOCAL
INSTAL·LAT
DISPONIBLE
DESCARREGANT
ERROR
IGNORAT
```

======================================================================
67. CONSERVAR LAYER / RESOURCE / JOB
======================================================================

No destruir la distinció:

```text
Layer
Resource
DownloadJob
```

Una capa local pot tenir Resource sense DownloadJob.

La caché TLST és un **derived resource**, no un DownloadJob.

======================================================================
68. NO SOBRECARREGAR EL MODAL
======================================================================

Extreure components només quan resolguin responsabilitats reals.

No arquitectura ornamental.

======================================================================
69. NO ENGREIXAR ENTRYPOINTS
======================================================================

No posar a `__main__.py` o `main.ts`:

- raster parsing;
- taxonomy;
- mappings;
- governor logic;
- resolver;
- cache algorithms;
- procedural;
- asset selection.

Només bootstrap/composition quan correspongui.

======================================================================
70. PROVES DEL LECTOR RASTER
======================================================================

Aquesta vertical ja existeix, però la regressió ha de conservar:

- GeoTIFF;
- COG;
- VRT;
- ASC;
- ENVI/raw;
- IMG;
- JP2;
- NetCDF;
- palette;
- RGB;
- NoData;
- CRS absent;
- transform absent;
- multibanda.

Si una capacitat no està disponible a CI, skip explícit justificat.

======================================================================
71. PROVES TXT / CSV
======================================================================

Conservar:

- TXT amb header;
- TXT només matriu;
- CSV;
- espais;
- tabs;
- comes;
- punt i coma;
- float;
- integer;
- NoData;
- files irregulars;
- georeferència incompleta.

======================================================================
72. PROVES CATEGÒRIQUES I DEL RESOLVER
======================================================================

Mappings:

```text
scheme + version + source code
→ node TLST correcte
```

Casos obligatoris:

```text
A. font només permet tree_cover
   → exactament tree_cover

B. font permet node intermedi
   → node intermedi

C. font permet fulla
   → fulla

D. composite
   → components conservats

E. nodata/unknown/unclassified
   → ObservationState

F. dos estàndards amb profunditats diferents
   → mappings independents
```

Nous tests governador/resolver:

```text
G. governor 1 m vàlid + 10 m vàlid
   → 1 m governa

H. governor 1 m NoData + 10 m vàlid
   → fallback 10 m

I. governor disabled
   → següent font

J. refinament descendent
   → acceptat

K. refinament altra branca
   → ignorat

L. refinament NoData
   → no modifica

M. empat profunditat
   → millor resolució

N. empat profunditat + resolució
   → prioritat
```

======================================================================
73. PROVES DE CACHÉ TLST
======================================================================

Obligatòries a V7:

```text
1. mateix input → mateix hash de chunk
2. canvi mapping → chunk stale
3. canvi enabled → chunk stale
4. canvi priority → chunk stale quan afecta el resultat
5. nova font amb footprint → només chunks solapats stale quan és segur
6. font eliminada → invalidació afectada
7. càmera/FOV → zero invalidacions
8. cancel·lació → cap chunk parcial vàlid
9. write atomic → generació anterior recuperable davant fallada
10. code table ↔ categoryKey round-trip
11. chunks de resolucions diferents no es barregen
12. cache hit evita rellegir fonts innecessàriament
13. estimació de mida bruta exacta
14. estimació comprimida marcada com a estimació
```

Benchmark:

```text
chunk 512² vs 1024²
Zstd vs Blosc+Zstd
lectura random
escriptura incremental
compression ratio
CPU
RSS
```

======================================================================
74. PROVES UI
======================================================================

Verificar:

- `+ Importar` mateixa posició;
- footer estable;
- scroll correcte;
- mapping sempre revisable;
- mapping custom;
- cancel·lació sense estat parcial;
- persistència;
- reobrir gestor conserva estat;
- `Refinament` bloquejat sense categòric general actiu;
- `Actiu/Ignorat` visible i diferent d'Eliminar;
- reactivació sense redescàrrega;
- canvi d'activació actualitza/invalida la caché corresponent;
- requests stale no sobreescriuen revisions noves.

======================================================================
75. REGRESSIÓ
======================================================================

No trencar:

- DEM;
- horitzó;
- tiles;
- LOD terreny;
- picking;
- categòric actual;
- estils;
- descàrregues;
- cancel·lació;
- recuperació;
- contaminació lumínica;
- recursos CEL;
- CDSE;
- providers habilitats;
- custom schemes.

======================================================================
76. LLICÈNCIES
======================================================================

Qualsevol font incorporada al catàleg oficial TerraLab3D ha de ser compatible
amb la política comercial del producte.

Verificar:

- ús comercial;
- atribució;
- share-alike;
- redistribució;
- cache;
- procedència;
- metadata completa.

La política actual és fail-closed i exclou com a fonts oficials automàtiques
ODbL/llinatge OSM i altres llicències recíproques incompatibles amb la política
definida.

EuroCrops i OSM no s'han de presentar com a fonts oficials actuals només perquè
documents antics els utilitzessin com a exemples.

======================================================================
77. FASES / VERTICALS REVISADES
======================================================================

```text
V1  TLST 1.0                         COMPLET
V2  Raster universal + DEM           COMPLET
V3  Categòric universal              COMPLET
V4  Esquemes personalitzats          COMPLET

    Gestor d'adquisició refinaments  IMPLEMENTAT / WIP

V5  Governador + enabled/ignored     PENDENT
V6  Resolver TLST determinista       PENDENT
V7  Caché TLST canònica              PENDENT
V8  SpatialPatch + halo              PENDENT
V9  Procedural agricultura           PENDENT
V10 Bosc/shrub/grass                  PENDENT
V11 Built-up / vectors                PENDENT
V12 Water/wetland/snow/bare           PENDENT
V13 Assets/materials                  PENDENT
V14 LOD                               PENDENT
V15 Temporal                          PENDENT
V16 Planificador auto refinaments     PENDENT
V17 Modes Científic/Observador        PENDENT
V18 Procedural Lab                    PENDENT
```

No renumerar V9–V18 arbitràriament.

La responsabilitat antiga de V16 canvia: ja no crea la caché, sinó que planifica
refinaments útils guiats pels buits TLST i reutilitza el gestor d'adquisició.

======================================================================
78. QUÈ HAS DE FER PRIMER
======================================================================

Abans d'implementar la pròxima vertical:

1. Indica HEAD real.
2. Resumeix l'estat actual del Pas 23 i del gestor de refinaments.
3. Identifica què ja existeix.
4. Identifica què falta.
5. Classifica REUSE / EXTRACT / ADAPT / REWRITE / DISCARD / NEW.
6. Proposa arquitectura integrada amb noms de fitxers reals.
7. No reobris V1–V4.
8. Separa:

```text
IMPLEMENTAR ARA
DISSENYAR ARA / IMPLEMENTAR DESPRÉS
JA EXISTEIX — NO TOCAR
REFATORITZAR NOMÉS SI ÉS NECESSARI
```

9. Comença per V5: governador + Actiu/Ignorat.
10. Executa proves i mantén TerraLab3D executable.

======================================================================
79. RESULTAT A CURT TERMINI
======================================================================

ELEVACIÓ — JA IMPLEMENTAT:

```text
TERRA
→ Elevació
→ + Importar
→ seleccionar raster
→ completar georeferència només si falta
→ importar
→ usar com DEM
```

CATEGÒRIC — JA IMPLEMENTAT:

```text
TERRA
→ Categòric
→ + Importar
→ seleccionar raster
→ seleccionar/confirmar esquema
→ revisar categories
→ mapping directe → TLST
→ importar
```

CUSTOM — JA IMPLEMENTAT:

```text
TERRA
→ Categòric
→ + Importar
→ esquema personalitzat
→ cada codi → node TLST
→ guardar revisió
```

REFINAMENT — GESTOR D'ADQUISICIÓ JA IMPLEMENTAT / RESOLUCIÓ GLOBAL PENDENT:

```text
TERRA
→ Refinament
→ base categòrica activa obligatòria
→ descobrir/importar
→ instal·lar
→ normalitzar mapping/procedència
→ registrar font
→ disponible per governor/resolver/cache
```

======================================================================
80. RESULTAT A MITJÀ TERMINI
======================================================================

```text
fonts categòriques generals
        ↓
mapping directe estàndard → TLST
        ↓
ràster governador
        ↓
node TLST base
        ↓
refinaments compatibles
        ↓
TLST Resolver determinista
        ↓
TLST final
+
ResolutionTrace
        ↓
Caché TLST canònica
        ↓
SpatialPatch
        ↓
DEM/context
        ↓
procedural Python
        ↓
descriptors neutrals
        ↓
bridge
        ↓
Three.js
```

Si el resolver s'atura en un node intermedi, el procedural treballa amb aquell
nivell i no fabrica una fulla TLST fictícia.

======================================================================
81. PRINCIPI FINAL
======================================================================

Rasterio sap llegir i descriure fonts raster externes.

Els estàndards descriuen observacions segons les seves pròpies llegendes.

`SourceSchemeTranslator` tradueix cada estàndard DIRECTAMENT a TLST fins al node
més profund que aquella font pot demostrar.

El **Ràster Governador** decideix quina observació categòrica base representa
cada posició segons precisió espacial, activació, cobertura i fallback NoData.

El **TLST Resolver** només accepta refinaments compatibles amb la branca
establerta i guanya per profunditat semàntica, resolució i prioritat.

La **Caché TLST canònica** materialitza de forma progressiva i regenerable la
interpretació territorial final perquè el runtime no depengui d'un esquema de
proveïdor concret.

`SpatialPatch` transforma després aquesta base raster en unitats semàntiques per
al procedural.

Python sap interpretar el territori.

TypeScript sap transportar, gestionar lifecycle i presentació.

Three.js sap dibuixar.

No barregis aquestes responsabilitats.

Regla final:

```text
1. OBSERVAR LES FONTS ACTIVES.
2. TRADUIR DIRECTAMENT A TLST.
3. ESCOLLIR EL GOVERNADOR ESPACIAL.
4. FER FALLBACK SI NO HI HA DADA VÀLIDA.
5. FIXAR LA BRANCA TLST BASE.
6. CONSIDERAR NOMÉS REFINAMENTS COMPATIBLES.
7. APROFUNDIR PER SEMÀNTICA, RESOLUCIÓ I PRIORITAT.
8. CONSERVAR RESOLUTIONTRACE.
9. MATERIALITZAR LA CACHÉ TLST.
10. CONSTRUIR SPATIALPATCH QUAN CORRESPONGUI.
11. GENERAR NOMÉS AMB LA PRECISIÓ REALMENT ASSOLIDA.
```

No:

```text
"TLST té una fulla, per tant l'hem d'omplir."
```

Sí:

```text
"TLST pot expressar aquesta fulla, però només hi arribarem si una font activa
compatible la pot justificar dins de la branca que governa aquella posició."
```

I sobretot:

```text
LA NOVA ARQUITECTURA HA DE NÉIXER DE TERRALAB3D TAL COM EXISTEIX EN EL HEAD.
```

Aquest document defineix necessitats funcionals i restriccions.

El repositori actual defineix com s'han d'integrar.
