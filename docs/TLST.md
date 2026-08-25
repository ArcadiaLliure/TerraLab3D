# TLST i sistema universal de capes Terra

## Estat implementat

El contracte general d'aquest document continua sent l'autoritat. A data de 2026-08-25, el codi real incorpora TLST 1.0, el lector universal d'elevació, les verticals categòriques i el gestor de refinaments:

- TLST manté `categoryKey` com a identitat estable, amb presentació catalana separada mitjançant `categoryLabelKey`;
- el tooltip mostra el nom descriptiu, la font/versionament subratllats, el codi i l'etiqueta font, sense exposar la clau tècnica;
- `RasterDatasetDescriptor` i el port raster no depenen de tipus públics de Rasterio;
- Rasterio/GDAL decideix els formats disponibles dinàmicament, sense whitelist d'extensions;
- `data_sources.json` conserva l'ordre primària/fallback, mentre `layers.json` i `local_installation_state.json` mantenen responsabilitats diferents;
- una importació gestionada o externa activa un `ElevationPort` recarregable i invalida els resultats dependents del fingerprint anterior.
- la importació categòrica admet enters, paleta, RGB i RGBA exactes i exigeix revisar el mapping abans del commit;
- S2GLC, WorldCover, Copernicus LCM-10 i CORINE són membres del mateix registre versionat d'esquemes;
- cada equivalència publica node TLST, profunditat resolta i descendents no afirmats;
- les classificacions d'usuari es persisteixen i es reutilitzen amb identitat `scheme_key + scheme_version + mapping_revision`.
- el gestor de refinaments cobreix AOI, descoberta multiproveïdor, llicències comercials, harmonització ràster/vector, mosaic TLST incremental, cobertura verificada, persistència i UI;
- ICGC MCSC, CORINE i vuit famílies CLMS estan habilitades; la resta de proveïdors tenen un estat explícit, mai ambigu. Vegeu [tlst-refinement-manager.md](tlst-refinement-manager.md).

La generació procedural continua fora d'aquest lliurament.

**Principi arquitectònic per a les verticals següents:** TLST 1.0 és la lingua franca semàntica. Cada estàndard extern es tradueix directament a TLST fins al node més profund que la seva llegenda permet demostrar. El refinament no torna a classificar el territori des de zero: només intenta resoldre descendents TLST que han quedat oberts després de la traducció inicial. Si no hi ha evidència suficient, el sistema s'atura sense inventar precisió.

Sí. El deixaria així: **Rasterio és l’única API raster que Codex ha de considerar per a la implementació Python**. He eliminat qualsevol referència a altres motors o APIs perquè no obri una segona via de lectura.

```text
MISSIÓ — TERRALAB3D: SISTEMA UNIVERSAL DE CAPES TERRA,
TAXONOMIA CANÒNICA, REFINAMENT I BASE DEL MODE PROCEDURAL

Treballa sobre el repositori:

https://github.com/ArcadiaLliure/TerraLab3D

La teva tasca és integrar en l'arquitectura REAL de TerraLab3D tot el sistema
de capes terrestres descrit en aquest document.

IMPORTANT:

NO comencis implementant directament.

Primer revisa exhaustivament el HEAD actual del repositori.

No parteixis d'una arquitectura imaginada.
No assumeixis que aquest prompt descriu correctament l'estat actual del codi.
No creïs una arquitectura paral·lela.

ORDRE D'AUTORITAT:

1. HEAD real del repositori quan executis aquesta tasca.
2. docs/pla-implementacio-pas-a-pas.md
3. README arquitectònics de les diferents capes.
4. Contractes i proves actuals.
5. Aquest prompt per a funcionalitat que encara no existeix.

En preparar aquest encàrrec, el HEAD observat era:

9accc0fbcd2563a7dec161ad43cf9a7289d99bb2

"Avenç de Pas 23: Gestor de capes."

Però si existeixen commits posteriors, preval sempre el HEAD nou.


======================================================================
1. ARQUITECTURA ACTUAL PRIORITÀRIA
======================================================================

TerraLab3D ja manté una separació deliberada aproximadament així:

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

Respecta-la.

Principis ja establerts:

- La capa d'aplicació coordina casos d'ús.
- L'aplicació no coneix adaptadors concrets.
- La ciència i les decisions de negoci autoritatives viuen en Python.
- Els adaptadors no decideixen comportament de producte.
- Three.js no executa càlcul científic.
- TypeScript no ha de duplicar la lògica geoespacial de Python.
- Els buffers grans no s'envien com JSON textual ni Base64.
- Les operacions asíncrones han de mantenir correlació, cancel·lació i
  descart de resultats obsolets.
- Cada vertical funcional ha de deixar TerraLab3D executable.

No creïs un "nou TerraLab3D" al costat de l'actual.

Extén el que existeix.


======================================================================
2. AUDITORIA OBLIGATÒRIA DEL HEAD
======================================================================

Abans de modificar res, inspecciona com a mínim:

README.md
docs/
docs/pla-implementacio-pas-a-pas.md
docs/resource-layer-manager.md
docs/DEM_PARITY.md

backend/src/terralab3d/domain/
backend/src/terralab3d/application/
backend/src/terralab3d/application/ports/
backend/src/terralab3d/infrastructure/
backend/src/terralab3d/infrastructure/adapters/dem/
backend/src/terralab3d/infrastructure/adapters/surface/
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

Revisa específicament:

- LayerDatabase
- ResourceDescriptor
- ResourceDomain
- ResourceCategory
- ResourceInstallationRepository
- DownloadJobManager
- ResourceManager
- ResourceManagerModal
- sistema DEM actual
- ConfiguredSurfaceSampler
- resolució actual de land-cover
- ús actual de Rasterio
- LandCoverCoordinator
- tiles categòrics
- renderer categòric
- picking de superfície
- data_sources.json
- data_location.json
- bridge Python ↔ TypeScript
- recursos binaris
- cachés

Classifica cada peça rellevant com:

REUSE
EXTRACT
ADAPT
REWRITE
DISCARD
NEW

No reescriguis una peça que es pugui extreure o encapsular netament.


======================================================================
3. RASTERIO ÉS LA FAÇANA RASTER DE TERRALAB3D
======================================================================

La implementació raster Python ha d'utilitzar Rasterio com a façana principal.

NO introdueixis una segona API raster paral·lela.

No creïs lectors específics manuals de GeoTIFF, ASC, IMG, JP2, etc.
quan Rasterio ja sigui capaç d'obrir-los.

Estudia, si és útil, el codi font i la documentació de Rasterio per entendre:

- open()
- DatasetReader
- DatasetWriter
- bands
- windows
- transforms
- CRS
- bounds
- nodata
- colormap
- color interpretation
- metadata
- overviews
- block windows
- WarpedVRT
- MemoryFile
- Env
- drivers disponibles
- lectura per finestres
- lectura multibanda
- masks

Extreu patrons de disseny, però no copiïs una arquitectura aliena.

La regla conceptual és:

format físic
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


======================================================================
4. OBJECTIU DEL LECTOR RASTER GENÈRIC
======================================================================

Volem arribar a:

FITXER
   ↓
GenericRasterReader
   ↓
RasterDatasetDescriptor
   ↓
SemanticInterpreter
   ↓
Layer

El lector genèric només ha de saber:

- obrir el dataset;
- inspeccionar-lo;
- llegir finestres;
- descriure metadades;
- proporcionar valors.

NO ha de saber si està llegint:

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

TerraLab3D ha d'acceptar tots els formats raster que la instal·lació de
Rasterio disponible sigui capaç d'obrir de forma segura.

No mantinguis una whitelist artesanal de:

.tif
.tiff
.vrt
.img
.jp2

com a autoritat del sistema.

Entre les famílies esperables:

- GeoTIFF / TIFF
- COG
- VRT
- ASC / AAIGrid
- EHdr
- ENVI
- BIL
- BIP
- BSQ
- FLT + HDR
- ERDAS Imagine / IMG
- JPEG2000
- NetCDF
- HDF / HDF5 quan sigui accessible per la instal·lació
- GRIB
- SAGA
- PCRaster
- Idrisi
- Surfer Grid
- Zarr quan sigui compatible
- altres formats que Rasterio pugui obrir

Això NO significa crear una classe TerraLab per format.

Rasterio normalitza la lectura.


======================================================================
6. TXT / CSV / MATRIUS ARTESANALS
======================================================================

També volem permetre:

.txt
.csv
.xyz
i altres matrius textuals raonables

Pot existir un petit adaptador textual propi TerraLab.

Ha de poder llegir:

- enter
- float
- separador espai
- tabulador
- coma
- punt i coma
- NoData
- capçalera quan existeixi

Si falten dades geogràfiques:

NO inventar-les.

L'assistent ha de demanar només allò que falta:

- CRS
- origen X
- origen Y
- resolució X
- resolució Y
- files
- columnes
- NoData
- unitat quan sigui necessària

També s'han de poder aprofitar sidecars o metadata externa quan existeixin.


======================================================================
7. NO FER HEURÍSTICA SEMÀNTICA
======================================================================

Regla explícita de producte:

L'USUARI DECLARA QUÈ SIGNIFICA EL RÀSTER.

No intentis endevinar si és:

- DEM
- cobertura arbòria
- temperatura
- categòric
- humitat
- màscara
- etc.

TerraLab pot detectar objectivament:

- format
- nombre de bandes
- dtype
- dimensions
- CRS
- transform
- bounds
- resolució
- NoData
- palette
- color interpretation
- metadata
- valors únics quan sigui raonable

Però no el significat científic.


======================================================================
8. TRES FAMÍLIES PRINCIPALS DE TERRA
======================================================================

La UI del domini TERRA ha d'evolucionar cap a:

TERRA

[ Elevació ] [ Categòric ] [ Refinament ]

La funcionalitat existent que actualment no encaixi perfectament,
per exemple contaminació lumínica, no es pot trencar.

Analitza com reclassificar-la o integrar-la sense regressió.


======================================================================
9. CONSERVAR EL GESTOR ACTUAL
======================================================================

ResourceManagerModal és la base.

No el substitueixis per una aplicació nova.

Mantén:

- CEL / TERRA
- look & feel actual
- modal central
- colors
- tipografia
- densitat visual
- cards
- estats de descàrrega
- llicència/citació
- variants
- lifecycle existent


======================================================================
10. BOTÓ + IMPORTAR
======================================================================

A TERRA hi haurà:

+ Importar

Ha d'estar SEMPRE a la mateixa posició i alçada visual a:

- Elevació
- Categòric
- Refinament

No pot pujar o baixar segons el contingut central.

Preferiblement:

zona central amb scroll
+
footer estable

Esquema:

┌────────────────────────────────────────┐
│ Gestor de Recursos i Capes         ×   │
├────────────────────────────────────────┤
│            CEL | TERRA                 │
├────────────────────────────────────────┤
│ Elevació   Categòric   Refinament      │
├────────────────────────────────────────┤
│                                        │
│ contingut                              │
│ recursos                               │
│ cards                                  │
│                                        │
│            ZONA AMB SCROLL             │
│                                        │
├────────────────────────────────────────┤
│ [+ Importar]                [Tancar]   │
└────────────────────────────────────────┘


======================================================================
11. REVELAT PROGRESSIU DE LA UI
======================================================================

No crear un wizard de cinc passos.

Utilitzar una mateixa pantalla d'importació amb seccions condicionals.

SEMPRE VISIBLE:

- fitxer
- nom de capa
- metadades bàsiques
- Importar

SEGONS TIPUS:

- unitats
- esquema categòric
- mapping
- tipus de refinament
- magnitud
- banda
- encoding

PLEGAT PER DEFECTE:

- CRS detallat
- bbox
- transform
- dimensions
- NoData override
- reprojecció
- metadata
- opcions avançades

Si falta una dada imprescindible:

la secció s'obre automàticament.


======================================================================
12. IMPORTACIÓ D'ELEVACIÓ
======================================================================

Flux:

TERRA
→ Elevació
→ + Importar
→ fitxer
→ Rasterio
→ metadades
→ confirmar unitat vertical
→ importar

No existeix mapping categòric.

Necessitem com a mínim:

- CRS
- transform/georeferència
- resolució
- NoData
- unitat vertical

Quan falti informació:

mostrar-la i demanar-la.

Els valors són continus.

L'elevació pot interpolar quan el cas d'ús ho necessiti.

IMPORTANT:

No mantenir dues arquitectures independents:

DEM descarregat per TerraLab
vs
DEM importat per usuari

Després de resoldre el dataset, han de convergir tant com sigui possible
al mateix pipeline DEM existent.


======================================================================
13. IMPORTACIÓ CATEGÒRICA
======================================================================

Un raster categòric pot estar codificat com:

- una banda integer
- una banda indexed/palette
- RGB
- RGBA
- altres representacions justificades

Mai aplicar interpolació bilineal o cúbica a IDs categòrics.

Utilitzar lookup exacte / nearest segons el pipeline.


======================================================================
14. ESQUEMA CATEGÒRIC
======================================================================

Quan l'usuari entra per:

TERRA → Categòric → + Importar

ja sabem que és un raster categòric.

L'autodetecció només intenta respondre:

"Quin esquema de classificació utilitza?"

Pot utilitzar objectivament:

- codis únics
- metadata explícita
- palette
- nombre de bandes quan sigui rellevant

No intenta descobrir què representa el raster.

Una vegada confirmat l'esquema, la traducció és DIRECTA:

S2GLC ─────────→ TLST
WorldCover ────→ TLST
CORINE ────────→ TLST
LCM-10 ────────→ TLST
altres ────────→ TLST

NO:

S2GLC → WorldCover → CORINE → TLST

Cada classe externa es mapeja al node TLST més profund que la definició oficial de la font permet demostrar.

Exemple:

si una llegenda només afirma "tree cover":

→ tree_cover

Encara que TLST tingui descendents més específics.

No completar la jerarquia amb suposicions.


======================================================================
15. CONFIRMACIÓ SEMPRE OBLIGATÒRIA
======================================================================

Encara que la coincidència sigui perfecta:

Estàndard probable:
S2GLC 2017

13/13 codis reconeguts

[ Revisar i confirmar categories ]

L'usuari sempre pot inspeccionar el mapping.


======================================================================
16. RÀSTER CATEGÒRIC ARTESANAL
======================================================================

Si no coincideix amb cap esquema:

Estàndard:
Personalitzat / desconegut

Valors trobats:

1 → [categoria TerraLab ▼]
2 → [categoria TerraLab ▼]
7 → [categoria TerraLab ▼]

Permetre:

[ Guardar esquema com... ]

Exemple:

"Classificació finca Joan v1"

La pròxima vegada es pot reutilitzar.


======================================================================
17. TAXONOMIA CANÒNICA TERRALAB
======================================================================

Aquesta és una peça central.

TLST 1.0 és la taxonomia canònica i la lingua franca semàntica de TerraLab3D.

El motor no pot dependre de:

S2GLC 62
LCM-10 90
WorldCover 50
CLC 111

Ha de treballar amb categories TLST estables.

Flux:

scheme
+
version
+
band/encoding si cal
+
source code
        ↓
SourceSchemeTranslator
        ↓
node TLST més profund justificat
        ↓
interpretació inicial

El raster original es conserva intacte.

El mapping forma part de la interpretació de la capa i és auditable i versionat.

REGLA FONAMENTAL:

estàndard extern
→ TLST

No es tradueixen estàndards entre ells.

Exemple conceptual:

Estàndard A:
"cropland"
→ agriculture

Estàndard B:
"permanent crops"
→ agriculture.permanent_crop

Estàndard C:
"vineyard"
→ agriculture.permanent_crop.vineyard

Els tres mappings poden ser correctes simultàniament.

TLST defineix què pot expressar TerraLab3D.

Cada estàndard determina fins on pot arribar directament.

El refinament posterior intenta resoldre només els nivells que continuen oberts.


======================================================================
18. MODEL: CATEGORIA + QUALIFICADORS + COMPONENTS
======================================================================

Evita explosió combinatòria.

Utilitzar:

categoria TLST
+
qualificadors opcionals
+
components en classes mixtes

Exemple:

category:
tree_cover.broadleaf

qualifiers:
phenology = deciduous
canopy_cover = 0.75

No crear:

dense_deciduous_broadleaf_mid_altitude_forest

Els mappings poden ser conceptualment:

single:
    categoria + qualificadors

composite:
    components ponderats

observation_state:
    estat de la mostra

La profunditat del node TLST és informació.

Un mapping a:

tree_cover

NO afirma res sobre els seus descendents.

Evitar també duplicar semàntica entre categoria i qualificador quan la categoria ja determina inequívocament aquella propietat.


======================================================================
19. JERARQUIA CANÒNICA V1
======================================================================

Base proposada:

surface
│
├── artificial
│   ├── built
│   │   ├── urban_fabric
│   │   ├── residential
│   │   └── mixed_urban
│   ├── industrial_commercial
│   ├── transport
│   │   ├── road
│   │   ├── railway
│   │   ├── airport
│   │   └── port
│   ├── extraction
│   │   ├── quarry_mine
│   │   └── unspecified
│   ├── waste
│   ├── construction_site
│   ├── artificial_green
│   │   ├── urban_green
│   │   └── sport_leisure
│   └── unspecified
│
├── agriculture
│   ├── arable
│   │   ├── annual_crop
│   │   ├── rice
│   │   └── unspecified
│   ├── permanent_crop
│   │   ├── vineyard
│   │   ├── olive_grove
│   │   ├── orchard
│   │   │   ├── fruit_trees
│   │   │   └── berry_plantation
│   │   └── other
│   ├── managed_grassland
│   │   └── pasture
│   ├── agroforestry
│   ├── heterogeneous
│   │   ├── annual_and_permanent
│   │   ├── complex_cultivation
│   │   └── agriculture_natural_mosaic
│   └── cropland_unspecified
│
├── tree_cover
│   ├── broadleaf
│   ├── needleleaf
│   ├── mixed
│   └── unspecified
│
├── low_vegetation
│   ├── shrub
│   │   ├── shrubland
│   │   ├── heath_moor
│   │   ├── sclerophyllous
│   │   └── unspecified
│   ├── herbaceous
│   │   ├── natural_grassland
│   │   └── unspecified
│   ├── transitional_woodland_shrub
│   ├── moss_lichen
│   └── unspecified
│
├── wetland
│   ├── inland
│   │   ├── herbaceous_wetland
│   │   ├── marsh
│   │   ├── peat_bog
│   │   ├── shrub_wetland
│   │   └── forested_wetland
│   ├── coastal
│   │   ├── salt_marsh
│   │   ├── mangrove
│   │   ├── intertidal_flat
│   │   └── saline
│   └── unspecified
│
├── bare_sparse
│   ├── bare_soil
│   ├── bare_rock
│   ├── sand
│   │   ├── beach
│   │   └── dune
│   ├── sparse_vegetation
│   ├── saline_bare
│   └── unspecified
│
├── water
│   ├── inland
│   │   ├── watercourse
│   │   ├── standing_water
│   │   └── unspecified
│   ├── artificial
│   │   ├── reservoir
│   │   ├── canal
│   │   └── unspecified
│   ├── coastal
│   │   ├── lagoon
│   │   ├── estuary
│   │   └── unspecified
│   ├── marine
│   │   └── sea_ocean
│   └── unspecified
│
└── snow_ice
    ├── permanent_snow
    ├── glacier_ice
    ├── seasonal
    └── unspecified

IMPORTANT:

unknown
unclassified
nodata

són `ObservationState`, no superfícies filles de `surface`.

Descriuen l'estat de l'observació o del mapping i no una realitat territorial que el procedural hagi de representar.


======================================================================
20. QUALIFICADORS
======================================================================

Model extensible per a:

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

No inventar valors.


======================================================================
21. CLASSES MIXTES
======================================================================

Permetre conceptualment:

components:
  - agriculture.cropland_unspecified: 0.6
  - low_vegetation.unspecified: 0.4

No obligar una classe externa mosaic a convertir-se falsament en una sola
categoria TerraLab.


======================================================================
22. ESQUEMES A SUPORTAR
======================================================================

Dissenyar el registre perquè afegir-ne sigui principalment dades.

Primera prioritat:

- Copernicus LCM-10
- ESA WorldCover 2020/2021
- S2GLC 2017
- CORINE Land Cover

Segona:

- Dynamic World
- Copernicus CGLS-LC100
- ESA CCI Land Cover
- MODIS MCD12Q1 i les seves diferents classificacions
- GlobeLand30
- GLC_FCS30D
- NLCD
- Urban Atlas
- LUCAS quan sigui útil
- classificacions futures
- esquemes creats per l'usuari

IMPORTANT:

producte != esquema

Un mateix producte pot contenir diverses llegendes.

Per CADA esquema suportat:

scheme + version + source class
→ TLST

La matriu d'equivalències ha de cobrir totes les classes documentades de l'esquema i distingir:

- single
- composite
- observation_state
- cap mapping justificable

Per cada classe externa s'ha d'identificar el node TLST més profund que la definició oficial permet demostrar.

Exemple conceptual:

| Estàndard | Classe externa | TLST màxim justificat |
|-----------|----------------|------------------------|
| A | Cropland | agriculture |
| B | Permanent crops | agriculture.permanent_crop |
| C | Vineyards | agriculture.permanent_crop.vineyard |

A partir dels mappings s'ha de poder derivar la COBERTURA JERÀRQUICA de cada esquema:

- nodes resolts directament;
- bifurcacions que deixa obertes;
- nodes sobre els quals no aporta informació.

Aquesta cobertura és la base del refinament posterior.


======================================================================
23. PERSISTÈNCIA DELS MAPPINGS
======================================================================

En converses prèvies es va considerar SQLite.

Però el HEAD actual ja disposa de LayerDatabase persistent.

Per tant:

NO introdueixis SQLite automàticament.

Primer avalua l'arquitectura real.

Necessitem persistir:

- canonical categories
- classification schemes
- source categories
- mappings
- mapping revisions
- user-defined schemes
- source colors
- TerraLab colors
- qualifiers
- mixed mappings

Cada mapping ha de permetre reconstruir:

scheme_key
scheme_version
source_category/code
mapping_revision
mapping_kind
TLST target quan existeixi
qualifiers
components si és composite
observation_state quan correspongui

El TLST target és el nivell MÀXIM justificat per aquella font.

No persistir una fulla "esperada" més precisa que l'observació.

Els refinaments posteriors es conserven separadament mitjançant evidències i `ResolutionTrace`.

Evita dues bases solapades sense justificació.


======================================================================
24. VERSIONAT
======================================================================

Una capa categòrica ha de guardar:

scheme_key
scheme_version
mapping_revision

Si un mapping es corregeix en el futur:

un projecte antic no canvia silenciosament.

Un canvi de profunditat semàntica és també un canvi de mapping.

Exemple:

revisió A:
tree_cover

revisió B:
tree_cover.broadleaf

si la nova equivalència està documentalment justificada.

Conservar separadament:

mapping inicial
+
evidències de refinament
+
ResolutionTrace
+
interpretació final


======================================================================
25. COLORS
======================================================================

Separar:

COLOR ORIGINAL DE L'ESQUEMA

per reproducció científica.

i

COLOR TERRALAB

com estil intern/fallback.

No barrejar semàntica i presentació.


======================================================================
26. REFINAMENT
======================================================================

Refinament NO és un format.

Tampoc és una segona classificació global del territori.

El refinament intenta resoldre una part de la jerarquia TLST que ha quedat oberta després del mapping inicial.

Flux:

raster categòric
        ↓
scheme/version/code
        ↓
mapping directe
        ↓
node TLST més profund demostrable
        ↓
fills sense resoldre?
     ┌──┴───┐
    NO      SÍ
    │        │
    │        ↓
    │   buscar evidència
    │   capaç de discriminar
    │   aquests fills
    │        ↓
    │     resolt?
    │    ┌──┴──┐
    │   SÍ    NO
    │    │      │
    │    ▼      ▼
    │ continua STOP
    └────┬──────┘
         ↓
interpretació TLST final

Exemple:

mapping inicial:
tree_cover

Dominant Leaf Type:
broadleaf

resultat:
tree_cover.broadleaf

Si no existeix evidència suficient per continuar:

STOP

No s'inventa cap descendent.

Un refinament pot ser físicament:

- raster continu
- raster categòric
- vector
- línia
- polígon
- punt
- informació temporal

Exemples:

- OSM
- EuroCrops
- Tree Cover Density
- Dominant Leaf Type
- SoilGrids
- Water & Wetness
- clima
- HR-VPP
- neu

Però no totes aquestes fonts refinen TLST en tots els casos.

DEM, clima o latitud poden ser només `ContextOnly`.


======================================================================
27. REFINAMENTS TRANSVERSALS
======================================================================

Separar:

A) EVIDÈNCIA CAPAÇ DE REFINAR TLST

Pot discriminar explícitament entre fills d'un node TLST.

Exemples segons el cas:

- EuroCrops
- Dominant Leaf Type
- OSM tags
- Water & Wetness
- productes específics de neu
- altres classificacions especialitzades

B) CONTEXT TRANSVERSAL

Aporta atributs o condicionants però no necessàriament modifica la categoria.

DEM:
  - altitud
  - pendent
  - aspect
  - rugositat

clima

latitud / longitud

SoilGrids

data / estació

HR-VPP / fenologia

Tree Cover Density

imperviousness

etc.

Una mateixa font pot produir evidències amb rols diferents.

Exemples:

OSM building footprint
→ AuthoritativeGeometry

OSM building=industrial
→ AttributeRefinement / possible refinament semàntic

DEM slope
→ ContextOnly

Tots són opcionals.


======================================================================
28. REFINAMENT PER CATEGORIA
======================================================================

NO modelar el refinament com:

categoria grossa
→ llista fixa de fonts

Modelar-lo com:

NODE TLST ACTUAL
+
FILLS ENCARA NO RESOLTS
        ↓
quines evidències poden discriminar aquesta bifurcació?

TREE COVER
----------

Node actual:

tree_cover

Preguntes:

broadleaf?
needleleaf?
mixed?
unspecified?

Fonts com `Dominant Leaf Type` poden ser candidates quan la seva semàntica ho permeti.

`Tree Cover Density` pot aportar densitat/canopy cover sense haver de decidir tipus foliar.


AGRICULTURA
-----------

Node actual:

agriculture

o qualsevol descendent agrícola encara genèric.

Fonts candidates:

- EuroCrops
- SIGPAC quan procedeixi
- altres classificacions agrícoles documentades

Si una font identifica explícitament `vineyard` i el mapping està justificat:

→ agriculture.permanent_crop.vineyard

DEM, clima, parcel·la i fenologia poden després millorar el procedural sense canviar necessàriament TLST.


ARTIFICIAL / CONSTRUÏT
----------------------

OSM pot aportar:

- footprints
- carreteres
- tags
- landuse
- ferrocarril
- indústria
- ports

Separar:

- geometria autoritativa;
- refinament semàntic;
- atributs;
- context visual.

Un footprint no reclassifica automàticament tota la cel·la.


WETLAND / WATER
---------------

Segons el node pendent poden ser útils:

- Water & Wetness
- OSM
- datasets hidrogràfics
- context litoral

DEM i clima poden actuar només com a context.


SNOW / ICE
----------

Fonts específiques de neu/gel poden refinar TLST.

DEM, clima i estació poden aportar context i estat temporal.


LOW VEGETATION / BARE-SPARSE
----------------------------

SoilGrids, HR-VPP, cobertures vegetals específiques, clima i DEM poden aportar atributs i, només quan la seva semàntica ho permeti, resoldre descendents TLST.

No inventar fonts per completar tota la jerarquia.


REGLA GENERAL
-------------

Per cada node TLST:

1. Quins fills té?
2. Quins ja han quedat descartats?
3. Quina evidència pot discriminar els restants?
4. Amb quina confiança, vigència i precisió?
5. Si no hi ha evidència suficient, on ens aturem?

El refinament pot acabar en qualsevol node TLST vàlid.


======================================================================
29. REFINAMENTS OPCIONALS
======================================================================

Regla:

categòric sol
→ ha de funcionar

scheme + version + code
→ TLST

ja produeix una interpretació vàlida encara que no arribi a una fulla.

Refinaments:
→ augmenten la precisió semàntica quan hi ha evidència suficient

Context:
→ millora atributs i procedural encara que TLST no canviï

La seva absència no invalida el sistema.

Resultats perfectament vàlids:

tree_cover

tree_cover.broadleaf

No existeix l'obligació d'arribar a una fulla.


======================================================================
30. EVIDÈNCIES NORMALITZADES
======================================================================

Els adaptadors no passen semàntica específica de proveïdor directament al procedural.

Exemples:

OSM building
→ BuildingFootprintEvidence

OSM road
→ RoadGeometryEvidence

Tree Cover Density 78 %
→ TreeCoverDensityEvidence

Köppen Csa
→ ClimateEvidence

EuroCrops wheat
→ CropTypeEvidence

Dominant Leaf Type broadleaf
→ LeafTypeEvidence

Una Evidence és un fet normalitzat.

No és:

- un asset
- una decisió visual
- un objecte Three.js
- una reclassificació TLST automàtica

Cada evidència conserva, quan sigui aplicable:

source
source_version
source_role
spatial_precision
semantic_precision
confidence
temporal_validity
provenance

Les evidències capaces de refinament jeràrquic han de poder expressar conceptualment:

supports_tlst_node
discriminates_from_node
candidate_child

o un contracte equivalent adaptat al codi real.

Una evidència només participa en bifurcacions on sigui semànticament aplicable.


======================================================================
31. PRIORITAT ENTRE EVIDÈNCIES
======================================================================

No utilitzar:

"la resolució més alta guanya"

Ni:

"totes les evidències voten sobre qualsevol categoria"

Primer:

QUINA PREGUNTA TLST ESTEM RESOLENT?

Exemple:

node actual:
tree_cover

fills:
broadleaf
needleleaf
mixed
unspecified

Només les evidències capaces de discriminar aquesta bifurcació participen.

Tenir en compte:

- compatibilitat semàntica
- precisió espacial
- vigència
- estabilitat temporal
- confiança
- tipus d'evidència
- procedència
- geometria coberta

Conceptes útils:

AuthoritativeGeometry
AttributeOverride
AttributeRefinement
ContextOnly
FallbackOnly

L'usuari no escull hard/soft.

Cada pas del resolver ha de ser auditable:

previous_tlst_node
evidence_used
resolved_tlst_node
confidence
provenance

Si el conflicte no es pot resoldre amb garanties:

mantenir el node segur anterior o representar explícitament l'ambigüitat.

No inventar precisió.


======================================================================
32. GEOMETRIA AUTORITATIVA
======================================================================

Exemple:

cel·la categòrica 10 × 10 m

amb edifici OSM ocupant 40 %

NO:

reemplaçar tota la cel·la

SÍ:

intersecció geomètrica

OSM governa només el footprint.

La resta conserva la categoria base.


======================================================================
33. DOS MODES DE SUPERFÍCIE
======================================================================

MODE CIENTÍFIC
--------------

font
→ dades
→ mapping
→ representació fidel

Per categòric:

píxel
→ codi font
→ mapping versionat
→ TLST inicial
→ color científic

Quan hi hagi refinaments, ha de poder auditar:

TLST inicial
+
evidències
+
ResolutionTrace
+
TLST final

Sense modificar l'observació original.


MODE OBSERVADOR / PROCEDURAL
----------------------------

TLST final disponible
+
refinaments
+
atributs
+
context
→ interpretació espacial
→ procedural
→ representació naturalista

Canviar de mode NO torna a carregar el DEM.

El Mode Observador no exigeix arribar a una fulla TLST.

Si la precisió és limitada:

- generador compatible amb el node disponible;
- o fallback explícit.

Mai inventar una categoria més específica per poder renderitzar.


======================================================================
34. REPARTIMENT DE RESPONSABILITATS
======================================================================

PYTHON:

- lectura i normalització geoespacial
- evidències
- interpretació
- patches
- geometria procedural
- posicions
- rotacions
- escala
- selecció semàntica
- descriptors

TYPESCRIPT:

- bridge
- contractes
- lifecycle
- caches frontend
- streaming
- picking
- recursos
- LOD visual
- coordinació de presentació

THREE.JS:

- render


======================================================================
35. RENDERER DESACOBLAT
======================================================================

Python NO retorna:

THREE.Mesh
THREE.Material
THREE.InstancedMesh

Retorna descriptors neutrals:

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


======================================================================
36. SPATIAL PATCH
======================================================================

El Mode Observador no genera per píxel.

molts píxels contigus
→ patch espacial
→ interpretació
→ procedural

Exemple conceptual:

SpatialPatch:
    id
    source_observations
    initial_tlst_category
    resolved_tlst_category
    resolution_trace
    polygon
    area
    perimeter
    centroid
    neighbours
    terrain_stats
    evidences
    provenance
    seed

La categoria procedural és la precisió TLST realment assolida.

No és obligatòriament una fulla.

El patch conserva:

- observació original;
- mapping inicial;
- refinaments;
- interpretació final.

La creació del patch no esborra procedència.


======================================================================
37. TILE != PATCH
======================================================================

Tile:

- streaming
- cache
- transport
- GPU

SpatialPatch:

- unitat semàntica
- unitat procedural

Un patch pot travessar tiles.

No generar independentment per tile.


======================================================================
38. HALO
======================================================================

Cada patch pot analitzar l'entorn adjacent.

Serveix per:

- continuïtat
- transicions
- carreteres
- vores
- context urbà
- evitar seams


======================================================================
39. PROCEDURAL ESPECIALITZAT
======================================================================

No hi ha un únic algoritme universal.

Exemples conceptuals:

ForestInterpreter
ForestGenerator

CroplandInterpreter
CropLayoutGenerator

BuiltUpInterpreter
UrbanGenerator

WetlandInterpreter
WetlandGenerator

Contractes comuns.
Lògica interna especialitzada.

La selecció del generador respecta el node TLST REALMENT RESOLT.

Exemple:

agriculture.permanent_crop.vineyard
→ pot usar un generador específic de vinya.

agriculture
→ NO pot convertir-se arbitràriament en vinya.

Cal usar:

- generador compatible amb el nivell disponible;
- fallback explícit;
- o ometre aquell detall.

El procedural consumeix semàntica.

No crea retroactivament evidència científica.


======================================================================
40. CULTIUS
======================================================================

Exemple:

polígon irregular
→ analitzar geometria
→ orientació candidata
→ pendent
→ accessos/camins
→ línies paral·leles
→ clip al polígon
→ passadissos
→ separació
→ posicions d'assets
→ seed

NO:

si pentàgon → X
si hexàgon → Y


======================================================================
41. BOSC
======================================================================

patch
→ densitat
→ distribució tipus blue-noise / Poisson o alternativa justificada
→ clústers
→ clarianes
→ gradients de vora
→ assets compatibles

No files.

No una cel·la = un arbre.


======================================================================
42. MATOLLAR
======================================================================

- distribució irregular
- clústers
- clarianes
- densitat variable
- alçades variables
- sòl/roca visible


======================================================================
43. HERBASSARS
======================================================================

Lluny:

material / shader

A prop:

instàncies / geometria

No milions de brins sempre.


======================================================================
44. HUMEDALS
======================================================================

Un patch pot contenir:

- aigua
- fang
- vegetació
- transicions

segons context.


======================================================================
45. MOLSES / LÍQUENS / SÒL NU
======================================================================

Prioritzar:

- materials
- PBR
- màscares
- variació procedural

No assets individuals innecessaris.


======================================================================
46. SUPERFÍCIES ARTIFICIALS
======================================================================

Quan existeix OSM:

LC categòric built-up
+
roads
+
building footprints
+
tags
+
DEM
+
context
→ BuiltUpInterpreter
→ UrbanGenerator


======================================================================
47. QUÈ ÉS VS COM ÉS
======================================================================

QUÈ ÉS:

- casa
- bloc
- nau
- granja
- oficina
- equipament
- església
- generic building

COM ÉS:

- mediterrani
- centreeuropeu
- nòrdic
- muntanya
- etc.

No barrejar les dues decisions.


======================================================================
48. EDIFICIS
======================================================================

Si OSM té footprint:

conservar-lo

→ extrusió
→ coberta
→ façana procedural

Si hi ha tag fiable:

usar-lo.

Si no:

heurística mínima i conservadora.

Cas ambigu:

generic_building

No inventar hotel, fàbrica, etc. sense evidència.


======================================================================
49. PERFIL ARQUITECTÒNIC INICIAL
======================================================================

Inicialment Europa.

Context:

clima
+
latitud

Perfils amb pesos:

mediterranean
central_european
nordic
mountain

No classificació rígida.


======================================================================
50. INTERPRETACIÓ PERSISTENT
======================================================================

Separar:

què és el lloc

de:

quin asset el representa

Exemple:

conifer
mediterranean
mid_altitude
dense_canopy

Assets:

tags / affinities

Afegir un asset nou NO obliga a recalcular dades geogràfiques.


======================================================================
51. ESTACIÓ
======================================================================

Una seed estructural estable.

Estació modifica:

- fullatge
- color
- verdor
- cultiu
- neu

No mou arbitràriament:

- carreteres
- edificis
- arbres


======================================================================
52. DETERMINISME
======================================================================

Seed derivada de:

worldSeed
+
semanticId
+
coordenades globals
+
patchId

Mateixos inputs
→ mateix món


======================================================================
53. LOD
======================================================================

ARBRE:

FAR
→ canopy / massa

MID
→ simplificat / impostor

NEAR
→ asset 3D


EDIFICI:

FAR
→ volum

MID
→ footprint extruït + coberta

NEAR
→ façana


CULTIU:

FAR
→ material / textura

MID
→ files simplificades

NEAR
→ instàncies

No regenerar el món per LOD.


======================================================================
54. BRIDGE
======================================================================

No enviar milions de posicions en JSON textual.

Estudia el protocol binari actual.

Preferir:

- typed arrays
- buffers existents
- estructures compactes

No introduir frameworks de serialització nous si no són necessaris.

Mesura abans.


======================================================================
55. PROCEDÈNCIA
======================================================================

Cada element procedural ha de poder distingir:

- observat
- mapejat
- refinat
- inferit
- generat/procedural

Exemple:

Edifici
Geometria: OpenStreetMap — observada
Categoria base: esquema categòric → TLST — mapejada
Tipus: inferit
Aparença: procedural

o:

⚠ Fallback procedural

La procedència ha de poder reconstruir:

source observation
→ mapping revision
→ initial TLST node
→ refinement evidences
→ ResolutionTrace
→ final TLST node
→ procedural interpretation
→ representation


======================================================================
56. REFINEMENT CACHE
======================================================================

Després d'importar/obtenir categòric:

Refinar cobertura

NO ha de significar:

"descarrega totes les fonts conegudes"

Ha de significar:

1. determinar quins nodes TLST s'han assolit;
2. detectar quines bifurcacions continuen sense resoldre;
3. consultar `RefinementRegistry`;
4. identificar quines fonts poden aportar informació nova;
5. evitar fonts redundants;
6. descarregar només allò justificat;
7. retallar;
8. normalitzar com `Evidence`;
9. executar `HierarchicalInterpretationResolver`;
10. guardar cache, procedència i `ResolutionTrace`.

Exemple:

node actual:
tree_cover.broadleaf

Una font que només diferencia tree/no-tree no aporta precisió nova.

Una font capaç de discriminar descendents encara oberts sí pot ser candidata.

Pipeline:

AOI
↓
mappings estàndard → TLST
↓
nodes assolits
↓
buits jeràrquics
↓
RefinementRegistry
↓
fonts útils
↓
download/import
↓
Evidence
↓
HierarchyResolver
↓
cache


======================================================================
57. NO FER UN RÀSTER CÚBIC
======================================================================

No construir una matriu densa amb:

clima
soil
tree density
crop
OSM
etc.

Mantenir:

base categòrica

+
raster channels disponibles

+
vector channels disponibles

+
provenance

de forma dispersa.


======================================================================
58. REFINAMENT IMPORTAT
======================================================================

TERRA → Refinament → + Importar

pot acceptar:

- qualsevol raster compatible amb Rasterio
- GeoPackage
- GeoJSON
- Shapefile
- OSM
- CSV geogràfic
- altres formats vectorials que encaixin amb la pila GIS existent

L'usuari declara el significat:

- OpenStreetMap
- Cobertura arbòria
- Tipus de fulla
- Conreus
- Clima
- Sòl
- Water & Wetness
- Fenologia
- Neu
- Personalitzat

No fer heurística semàntica.

El sistema també ha de conèixer el paper de la font:

ContextOnly
AuthoritativeGeometry
AttributeRefinement
AttributeOverride
FallbackOnly

Quan pugui refinar TLST, el perfil ha de declarar conceptualment:

- des de quin node és aplicable;
- quina bifurcació pot discriminar;
- quins resultats TLST pot justificar.

No obligar l'usuari a conèixer aquests detalls si el perfil versionat de la font ja els defineix.

Un raster categòric que és un estàndard general de land-cover ha d'entrar preferentment pel pipeline categòric:

scheme
→ mapping directe TLST

i no disfressar-se de refinament.


======================================================================
59. RECURSOS OFICIALS I LOCALS
======================================================================

Un dataset descarregat per TerraLab i un importat per l'usuari han de
convergir tant com sigui possible al mateix model de:

Resource
Layer

No crear dos gestors independents.

Estats visuals possibles:

LOCAL
INSTAL·LAT
DISPONIBLE
DESCARREGANT
ERROR


======================================================================
60. CONSERVAR LAYER / RESOURCE / JOB
======================================================================

No destruir la distinció existent:

Layer
Resource
Download Job

Una capa local:

pot tenir Resource
sense Download Job.

Un recurs oficial:

pot tenir Download Job.

Una Layer:

pot dependre de múltiples Resources.


======================================================================
61. NO SOBRECARREGAR EL MODAL
======================================================================

Si el codi actual ho justifica, extreure peces com:

ResourceManagerModal
ImportLayerView
RasterMetadataView
CategoricalMappingView
RefinementImportView
ResourceCard

Però només si resolen responsabilitats reals.

No arquitectura ornamental.


======================================================================
62. NO ENGREIXAR ENTRYPOINTS
======================================================================

No posar a __main__.py o main.ts:

- raster parsing
- taxonomy
- mappings
- refinement
- procedural
- asset selection

Només bootstrap/composition quan correspongui.


======================================================================
63. PROVES DEL LECTOR RASTER
======================================================================

Provar, quan els formats siguin accessibles a la instal·lació:

- GeoTIFF
- COG
- VRT
- ASC
- ENVI/raw
- IMG
- JP2
- NetCDF
- palette
- RGB
- NoData
- CRS absent
- transform absent
- multibanda

Quan un format depengui d'una capacitat no disponible a CI:

detectar-la
+
skip explícit justificat

No falsificar suport.


======================================================================
64. PROVES TXT / CSV
======================================================================

Casos:

- TXT amb header
- TXT només matriu
- CSV
- espais
- tabs
- comes
- punt i coma
- float
- integer
- NoData
- files irregulars
- georeferència incompleta


======================================================================
65. PROVES CATEGÒRIQUES
======================================================================

Com a mínim:

- S2GLC
- LCM-10
- WorldCover
- CORINE
- custom scheme

Verificar:

scheme + version + source code
→ node TLST correcte

IMPORTANT:

un mateix source code pot significar coses diferents en esquemes diferents.

Mai:

code → canonical category

Sempre:

scheme + version + code
→ canonical interpretation

Afegir proves de PROFUNDITAT SEMÀNTICA.

Cas A:

font només permet `tree_cover`
→ resultat exacte `tree_cover`
→ cap descendent inventat.

Cas B:

font permet node intermedi
→ node intermedi exacte.

Cas C:

font permet una fulla
→ fulla.

Cas D:

mapping composite
→ components conservats.

Cas E:

nodata / unknown / unclassified
→ `ObservationState`
→ no categoria `surface`.

Cas F:

dos estàndards amb profunditats diferents
→ mappings independents directes a TLST.

Afegir proves de refinament:

initial TLST node
+
Evidence compatible
→ descendent justificat

i:

initial TLST node
+
Evidence insuficient/incompatible
→ STOP al node segur anterior.


======================================================================
66. NO INTERPOLACIÓ CATEGÒRICA
======================================================================

Crear fixture amb fronteres categòriques.

Comprovar:

- no apareixen classes inexistents
- no s'interpolen IDs
- frontera amb política definida


======================================================================
67. PROVES UI
======================================================================

Verificar:

- + Importar mateixa posició a les tres pestanyes
- footer estable
- scroll només al contingut
- seccions avançades plegades
- errors obligatoris obren la secció
- mapping sempre revisable
- mapping custom
- cancel·lar no deixa estat parcial
- persistència correcta
- reobrir gestor conserva estat


======================================================================
68. REGRESSIÓ
======================================================================

No trencar:

- DEM actual
- horitzó
- tiles
- LOD terreny
- picking
- categòric actual
- estils actuals
- descàrregues
- cancel·lació
- recuperació
- contaminació lumínica
- recursos CEL


======================================================================
69. DOCUMENTACIÓ
======================================================================

Actualitzar segons el codi real:

docs/pla-implementacio-pas-a-pas.md
docs/resource-layer-manager.md
README corresponents

No documentar arquitectura fictícia.

Decidir si la feina forma part del Pas 23 o requereix passos posteriors
després de revisar el pla actual.

No renumerar arbitràriament.


======================================================================
70. FASES PROPOSADES
======================================================================

Revisa críticament aquest ordre tenint en compte que les dues primeres verticals ja estan implementades.


FASE A — JA IMPLEMENTADA: LECTOR RASTER COMÚ

- model neutral raster
- Rasterio adapter
- importador textual
- metadades
- ports
- tests


FASE B — JA IMPLEMENTADA: IMPORTACIÓ ELEVACIÓ

- UI
- local resource
- metadata
- units
- pipeline DEM existent
- persistència


FASE C — CATEGÒRIC UNIVERSAL

- importació categòrica universal
- integer / palette / RGB / RGBA quan correspongui
- detecció objectiva d'esquema
- confirmació obligatòria
- registry data-driven
- sampler categòric
- Mode Científic
- reutilitzar S2GLC i WorldCover existents


FASE D — MATRIU UNIVERSAL ESTÀNDARD → TLST

- mapping directe per esquema i versió
- node TLST màxim justificat per classe
- single / composite / observation_state
- cobertura jeràrquica
- versionat
- CORINE
- LCM-10
- extensibilitat per altres estàndards
- proves de no sobreclassificació


FASE E — ESQUEMES PERSONALITZATS

- mapping manual cap a qualsevol node TLST vàlid
- no obligar a seleccionar fulla
- persistència i reutilització


FASE F — REFINEMENT REGISTRY + EVIDENCE

- fonts raster/vector
- rols d'evidència
- provenance
- semantic_precision
- spatial_precision
- confidence
- temporal_validity
- capacitat de discriminar bifurcacions TLST


FASE G — HIERARCHICAL INTERPRETATION RESOLVER

- node TLST inicial
- fills no resolts
- evidències elegibles
- resolució pas a pas
- STOP sense evidència
- ResolutionTrace
- observació original immutable


FASE H — CONTEXT PROCEDURAL

- SpatialPatch
- halo
- interpretation context
- provenance
- cache


FASE I — PRIMER PROCEDURAL PILOT

Preferentment agricultura per validar:

- polígons irregulars
- jerarquia TLST
- tipus de cultiu
- DEM
- orientació
- clipping
- determinisme
- assets repetitius


FASE J — BOSC / SHRUB / GRASS

Validar una família no basada en files.


FASE K — BUILT-UP + OSM

Validar:

- geometria autoritativa
- semàntica
- context arquitectònic
- procedural urbà


POSTERIORS:

- resta de categories
- assets/materials
- LOD procedural
- estacions
- refinement cache automàtica basada en buits TLST
- Mode Científic / Observador complet
- Procedural Lab standalone

Cada fase ha de deixar resultat observable.


======================================================================
71. VERTICAL FUNCIONAL
======================================================================

Cada fase implementada ha de deixar:

python -m terralab3d

funcional.

No acceptar com a resultat:

"infraestructura creada però no connectada"

Cada fase ha de tenir resultat observable.


======================================================================
72. NO MOCKS MENTIDERS
======================================================================

Si OSM no està connectat:

no presentar edificis com si fossin OSM.

Si EuroCrops no està disponible:

indicar no disponible.

Si no hi ha refinament:

fallback explícit.


======================================================================
73. LLICÈNCIES
======================================================================

Qualsevol font de dades incorporada al catàleg oficial TerraLab ha de ser
compatible amb ús comercial sense pagament obligatori.

Verificar:

- ús comercial
- atribució
- share-alike
- redistribució
- cache

No incorporar datasets NC com a dependència oficial obligatòria.

Separar la llicència del software de la llicència de les dades.


======================================================================
74. CRITERI DE DISSENY
======================================================================

Per cada nova classe o interfície pregunta:

"Quin problema funcional resol?"

Evitar:

- factories decoratives
- interfaces sense frontera real
- jerarquies profundes
- duplicació Python/TypeScript
- un reader per format
- if/elif per extensió
- if/elif per classificació
- if/elif gegants per procedural

Preferir:

- composició
- registries
- descriptors
- mappings data-driven
- ports en fronteres reals


======================================================================
75. QUÈ HAS DE FER PRIMER
======================================================================

Abans d'implementar:

1. Indica HEAD real.
2. Resumeix l'estat actual del Pas 23.
3. Identifica què ja existeix.
4. Identifica què falta.
5. Classifica REUSE / EXTRACT / ADAPT / REWRITE / DISCARD / NEW.
6. Proposa arquitectura integrada amb noms de fitxers reals.
7. Actualitza el pla pas a pas.
8. Separa:

   IMPLEMENTAR ARA
   DISSENYAR ARA / IMPLEMENTAR DESPRÉS
   JA EXISTEIX — NO TOCAR
   REFATORITZAR

9. Comença només la primera vertical mínima segura.
10. Executa proves.


======================================================================
76. RESULTAT A CURT TERMINI
======================================================================

ELEVACIÓ:

JA IMPLEMENTAT:

TERRA
→ Elevació
→ + Importar
→ seleccionar raster
→ completar georeferència només si falta
→ importar
→ usar com DEM


CATEGÒRIC:

TERRA
→ Categòric
→ + Importar
→ seleccionar raster
→ seleccionar/confirmar esquema
→ revisar categories
→ mapping directe estàndard → TLST
→ conservar node màxim justificat
→ importar
→ Mode Científic


CUSTOM:

TERRA
→ Categòric
→ + Importar
→ esquema personalitzat
→ cada codi → node TLST seleccionat
→ guardar esquema/versionament


REFINAMENT:

TERRA
→ Refinament
→ + Importar
→ seleccionar raster/vector
→ declarar significat/perfil
→ normalitzar Evidence
→ registrar rol i capacitat de refinament
→ disponible per al Hierarchical InterpretationResolver

Distingir sempre:

OBSERVACIÓ ORIGINAL

de:

MAPPING TLST

de:

REFINAMENT POSTERIOR.


======================================================================
77. RESULTAT A MITJÀ TERMINI
======================================================================

classificació categòrica
        ↓
mapping directe estàndard → TLST
        ↓
node TLST inicial
        ↓
evidències disponibles
        ↓
Hierarchical InterpretationResolver
        ↓
node TLST final segur
+
ResolutionTrace
+
DEM/context
        ↓
interpretació persistent
        ↓
SpatialPatches
        ↓
generadors procedurals Python
        ↓
descriptors neutrals
        ↓
bridge
        ↓
Three.js

Si el resolver s'atura en un node intermedi:

el procedural treballa amb aquell nivell

i no fabrica una fulla TLST fictícia.


======================================================================
78. PRINCIPI FINAL
======================================================================

Rasterio
sap llegir i descriure el raster.

Els estàndards
descriuen observacions segons les seves pròpies llegendes.

SourceSchemeTranslator
tradueix cada estàndard DIRECTAMENT a TLST fins al node més profund que aquella font pot demostrar.

TLST
és la lingua franca semàntica i defineix tot allò que TerraLab3D és capaç d'expressar.

RefinementRegistry + Evidence
identifiquen quines dades poden resoldre els nivells TLST que continuen oberts.

Hierarchical InterpretationResolver
refina només quan existeix evidència suficient i s'atura quan deixa d'existir-ne.

Python
sap interpretar el territori i calcular el procedural.

TypeScript
sap transportar, gestionar lifecycle i presentació.

Three.js
sap dibuixar.

No barregis aquestes responsabilitats.

Regla:

1. OBSERVAR.
2. IDENTIFICAR L'ESQUEMA.
3. TRADUIR DIRECTAMENT A TLST.
4. ATURAR-SE AL NIVELL MÀXIM DEMOSTRABLE.
5. IDENTIFICAR DESCENDENTS NO RESOLTS.
6. BUSCAR NOMÉS EVIDÈNCIES CAPACES DE DISCRIMINAR-LOS.
7. REFINAR SI HI HA PROVA SUFICIENT.
8. ATURAR-SE SI NO N'HI HA.
9. GENERAR NOMÉS AMB LA PRECISIÓ REALMENT ASSOLIDA.

No:

"TLST té una fulla, per tant l'hem d'omplir."

Sí:

"TLST pot expressar aquesta fulla, però només hi arribarem si alguna font o refinament la pot justificar."

I sobretot:

LA NOVA ARQUITECTURA HA DE NÉIXER DE TERRALAB3D TAL COM EXISTEIX EN EL
HEAD ACTUAL.

Aquest prompt defineix necessitats funcionals i restriccions.
El repositori actual defineix com s'han d'integrar.

```

Aquest és el que jo donaria ara a Codex. Queden fixades dues regles arquitectòniques independents:

1. **Una sola via raster:** `Rasterio → abstracció pròpia → intèrpret semàntic`.
2. **Una sola lingua franca territorial:** cada estàndard es tradueix **directament a TLST** fins al nivell màxim demostrable; el refinament només intenta resoldre els descendents encara oberts i s'atura quan no hi ha evidència suficient.
