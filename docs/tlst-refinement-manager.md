# Gestor de refinaments TLST

Estat a 2026-08-25: les fases 1–3 i el desplegament segur de la fase 4 estan
implementats a la branca `gestor_capes`. La taxonomia de runtime continua tenint
una única font de veritat: `backend/src/terralab3d/data/tlst/tlst-1.0.json`
(103 categories). `surface` només és l'arrel virtual de la interfície.

## Flux vertical

```text
AOI GeoJSON / EPSG:4326
  → node TLST
  → descoberta concurrent de tots els adaptadors habilitats
  → filtre comercial fail-closed
  → selecció i pla immutable d'assets
  → descàrrega reprenable i cancel·lable
  → traducció de cada classe font a TLST
  → alineació a TargetGridSpec
  → mosaic incremental i resolució determinista de conflictes
  → cobertura verificada des de la màscara real
  → persistència atòmica
  → actualització WebSocket de l'arbre i el mapa
```

El frontend no coneix particularitats dels proveïdors. `RefinementManagerView`
manté l'AOI durant la sessió, descarta revisions obsoletes i presenta mapa,
arbre, candidats, llicència, cobertura planificada/verificada, mida, progrés i
cancel·lació. El mapa és OpenLayers amb Natural Earth 110m empaquetat; no fa cap
petició a OSM ni incorpora dades ODbL. Les geometries de Natural Earth es tallen
a l'antimeridià abans de projectar-les per evitar franges de farciment falses.

La importació manual reutilitza el wizard categòric. Quan s'inicia des d'un node
TLST, exigeix llicència, procedència i confirmació explícita de drets comercials
i de derivació. Després del commit crea una instal·lació per categoria observada,
polygonitza la màscara GDAL real —no el `bbox`— i la registra com a cobertura
verificada. Els valors desconeguts, emmascarats o `nodata` no aporten cobertura.

## Ràster canònic i sortides

El mosaic no desa codis crus barrejats. Cada píxel vàlid conté el codi estable
del node TLST més profund justificable per la font. Els qualificadors continus
(`canopy_cover`, durada de neu, etc.) es mantenen separats de la categoria.

Cada actualització produeix de manera transaccional:

- `refinement_mosaic.tif`: categoria TLST canònica;
- `refinement_source.tif`: font guanyadora;
- `refinement_quality.tif`: prioritat/qualitat aplicada;
- `refinement_conflict.tif`: conflictes observats;
- `refinement_manifest.json`: graella, fonts, traduccions, llicències, hashes i finestres actualitzades;
- `refinement_qualifier_*.tif`: qualificadors continus disponibles.

La prioritat és `LOCAL_OFFICIAL > THEMATIC_REFINEMENT >
EUROPEAN_HIGH_RESOLUTION > GENERAL_LAND_COVER`; a igual prioritat guanya la
semàntica TLST més profunda i després l'identificador estable de font. ICGC és
local, els HRL de CLMS són temàtics, CORINE és europeu i el Global Dynamic Land
Cover és el fallback general.

## Matriu de productes habilitats

| Adaptador / dataset | Abast i resolució | Nodes que pot justificar | Llicència comercial | Verificació |
|---|---|---|---|---|
| ICGC MCSC 2024 | Catalunya, 1 m | artificial, agricultura, arbres, vegetació baixa, aiguamolls, nu/spars, aigua; 41 classes | CC BY 4.0 | fixture, mapping complet i smoke del GeoTIFF oficial |
| CORINE Land Cover 2018 | Europa, 100 m | 44 classes de nivell 3, inclosos transport, extracció, cultius, vegetació, costes, aigua i glacera | Copernicus CLMS | HTTP paginat simulat i GeoJSON oficial real |
| CLMS Crop Types | Europa, 10 m anual | cultius anuals, arròs, vinya, olivera, fruiters i altres permanents | Copernicus CLMS | OData simulat i oficial |
| CLMS Grassland | Europa, 10 m anual | herbaci genèric; no afirma pastura si el producte no la distingeix | Copernicus CLMS | OData simulat i oficial |
| CLMS Tree Cover Density | Europa, 10 m anual | `tree_cover` + qualificador `canopy_cover` | Copernicus CLMS | contracte OData compartit verificat |
| CLMS Dominant Leaf Type | Europa, 10 m anual | broadleaf i needleleaf | Copernicus CLMS | contracte OData compartit verificat |
| CLMS Forest Type | Europa, 10 m cada 3 anys | broadleaf, needleleaf i mixed | Copernicus CLMS | contracte OData compartit verificat |
| CLMS Snow Phenology S2 | Europa, 20 m anual | neu estacional i neu permanent; durada com a qualificador | Copernicus CLMS | OData simulat i oficial |
| CLMS Global Dynamic Land Cover | global, 10 m, 2020 beta | fallback general d'11 classes | Copernicus CLMS | OData simulat i oficial |
| CLMS Water & Wetness 2018 | Europa, 10 m | aigua permanent/temporal, humitat permanent/temporal i mar | Copernicus CLMS | ImageServer simulat i export GeoTIFF analític oficial |

Els productes OData de CDSE requereixen un token vigent a
`COPERNICUS_CDSE_TOKEN` per descarregar els assets. La descoberta del catàleg és
pública. ICGC, CORINE i Water & Wetness no requereixen autenticació.

## Cobertura auditada de la taxonomia

Les traduccions habilitades cobreixen semànticament 64 de les 75 fulles de la
font TLST 1.0. L'auditoria és executable i falla si un mapping apunta a una clau
no canònica. Els onze buits explícits són:

- placeholders `unspecified`: `artificial.extraction.unspecified`,
  `low_vegetation.shrub.unspecified`, `low_vegetation.unspecified`,
  `snow_ice.permanent.unspecified`, `water.artificial.unspecified`,
  `water.coastal.unspecified` i `water.inland.unspecified`;
- dues fulles antigues paral·leles conservades per estabilitat de TLST 1.0:
  `wetland.herbaceous_wetland` i `wetland.marsh` (les branques
  `wetland.inland.*` sí que tenen fonts);
- dos buits temàtics reals: `wetland.inland.shrub_wetland` i
  `bare_sparse.saline_bare`.

No es fa servir una classe pare com si demostrés totes les fulles descendents.
Per això aquests buits continuen visibles en lloc d'inventar precisió. Es poden
cobrir immediatament amb una importació local de llicència compatible; un nou
adaptador automàtic només s'habilitarà quan tingui llegenda adequada, endpoint
estable, llicència comercial verificada i smoke real.

## Proveïdors desactivats explícitament

| Família | Estat i motiu |
|---|---|
| ICGC RTT | Desactivat: no hi ha encara un contracte AOI desatès i un mapping de camps congelat |
| CLCplus Backbone | Desactivat: packaging i traducció exacta encara no han passat el smoke oficial |
| Urban Atlas / Imperviousness / Built-Up / BBH | Desactivat: falten adaptadors AOI i llindars per producte; imperviousness/altura han de ser qualificadors |
| EU-Hydro / Coastal / Riparian | Desactivat: no comparteixen un endpoint AOI estable i únic; cal adaptar cada producte |
| INSPIRE/HVD Buildings | Desactivat: serveis federats i llicència a revisar per país |
| INSPIRE/HVD Transport | Desactivat: esquema i llicència a revisar per país |
| Open Maps for Europe 2 | Desactivat: cal congelar assets AOI i llinatge d'atribució per producte |
| NASA/USGS | Desactivat: no s'ha seleccionat cap producte que millori el fallback global de 10 m sense perdre semàntica |

La matriu que consumeixen les proves és
`refinement_provider_rollout()`. No hi ha adaptadors mig habilitats: un dataset
amb `endpoint_verified=False` queda fora tant del catàleg com de la descoberta.

## Política de llicències

El filtre s'executa abans de mostrar un candidat i de nou abans de crear el job.
Admet domini públic, CC0, CC BY 4.0, equivalents només d'atribució revisats i la
política Copernicus CLMS. Rebutja metadades incompletes, ús no comercial,
`research only`, ShareAlike, CC BY-SA, ODbL, bases derivades recíproques i
llinatge OSM. EuroCrops i qualsevol font OSM/ODbL queden exclosos explícitament.

Referències oficials:

- ICGC MCSC i reutilització: <https://www.icgc.cat/ca/Geoinformacio-i-mapes/Mapes/Mapa-de-cobertes-del-sol-de-Catalunya> i <https://www.icgc.cat/ca/LICGC/Informacio-publica/Transparencia/Reutilitzacio-de-la-informacio>
- CORINE 2018: <https://land.copernicus.eu/en/products/corine-land-cover/clc2018>
- Catàleg i identificadors CDSE/CLMS: <https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CLMS.html>
- Condicions d'ús CLMS: <https://land.copernicus.eu/en/faq/data-use-terms-and-conditions>
- Water & Wetness 2018: <https://land.copernicus.eu/en/products/high-resolution-layer-water-and-wetness/water-and-wetness-status-2018>
- Natural Earth: <https://www.naturalearthdata.com/about/terms-of-use/>

## Afegir un proveïdor

1. Implementar `RefinementProviderPort` sense bifurcacions al nucli.
2. Congelar assets immutables amb footprint, ordre, mida, autenticació i mapping.
3. Afegir metadades de llicència completes i passar els dos gates comercials.
4. Reutilitzar el postprocessador canònic ràster/vector i declarar la prioritat.
5. Afegir fixture determinista, servidor HTTP simulat, smoke oficial opt-in i prova que totes les claus TLST són canòniques.
6. Afegir la família a `refinement_provider_rollout()` com `enabled`; si algun requisit falla, deixar-la `disabled` amb el motiu concret.
