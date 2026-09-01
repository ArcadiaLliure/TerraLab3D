# Gestor de refinaments TLST

## Estat a 2026-08-31

El gestor de refinaments està implementat i parcialment funcional a la branca
`gestor_capes`. En preparar aquesta revisió, el HEAD observat és:

```text
418006ba5c0339ca10d61784542590df8caf06ea
Avenç de Pas 23: Gestor de capes. Parcialment funcional
```

Si existeixen commits posteriors, preval sempre el codi real.

La taxonomia de runtime manté una única font de veritat:

```text
backend/src/terralab3d/data/tlst/tlst-1.0.json
```

`surface` continua sent l'arrel virtual de la interfície. Els tests actuals del
bridge construeixen un workspace de **114 nodes TLST**, de manera que qualsevol
referència documental anterior a 103 categories s'ha de considerar obsoleta.

Les Verticals 1–4 del sistema TLST ja estan completades: TLST 1.0, lector raster
universal, importació categòrica universal i esquemes personalitzats. Aquest
document no les reobre.

El gestor actual resol una part molt important del problema, però convé separar
clarament dues responsabilitats:

```text
GESTOR DE REFINAMENTS ACTUAL
→ descobreix, valida, descarrega, importa, normalitza i registra dades

RESOLVER TERRITORIAL GLOBAL PENDENT
→ combina totes les fonts actives i decideix el TLST final per posició
```

Per tant, el gestor actual és infraestructura d'adquisició i normalització que
s'ha de **reutilitzar**, no substituir.

---

# Flux vertical implementat

```text
AOI GeoJSON / EPSG:4326
  → node TLST consultat
  → descoberta concurrent dels adaptadors habilitats
  → filtre comercial fail-closed
  → selecció i pla immutable d'assets
  → descàrrega reprenable i cancel·lable
  → traducció de cada classe font a TLST
  → alineació a TargetGridSpec
  → postprocessat raster/vector
  → mosaic incremental de la instal·lació
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
TLST, exigeix llicència, procedència i confirmació explícita dels drets
necessaris. Després del commit crea la instal·lació corresponent, polygonitza la
màscara GDAL real —no el `bbox`— i registra cobertura verificada. Els valors
desconeguts, emmascarats o `nodata` no aporten cobertura.

---

# Principi nou: categòric general abans del refinament

Un refinament no és una classificació territorial autònoma. Necessita una base
categòrica general activa.

La UI de Terra s'ha d'entendre així:

```text
TERRA
├── Elevació
├── Categòric
│   └── almenys una font categòrica general activa
└── Refinament
    └── disponible només quan existeix la base categòrica
```

La pestanya `Refinament` pot continuar visible sense base, però no ha de permetre
executar descoberta/aplicació de refinaments com si existís una classificació
territorial de partida. Ha de mostrar un missatge accionable equivalent a:

```text
Cal activar o importar com a mínim una capa categòrica general
abans d'utilitzar refinaments.
```

No es crea cap categòric implícit ni fictici.

---

# Rols de font

La infraestructura ha de poder distingir com a mínim aquests rols conceptuals:

```text
BASE_CATEGORICAL
SEMANTIC_REFINEMENT
CONTEXT
AUTHORITATIVE_GEOMETRY
```

Per a les properes verticals, els dos primers són els essencials.

## `BASE_CATEGORICAL`

Una font general de land-cover/cobertura territorial que pot establir la branca
TLST de base d'una posició.

Exemples actuals o potencialment configurables com a base:

- ICGC MCSC;
- CORINE;
- ESA WorldCover;
- CLMS Global Dynamic Land Cover;
- S2GLC/LCM-10 quan procedeixi;
- qualsevol categòric general importat amb mapping TLST vàlid.

## `SEMANTIC_REFINEMENT`

Una font especialitzada que només aporta informació útil dins d'una branca
TLST concreta.

Exemples:

- CLMS Crop Types;
- CLMS Dominant Leaf Type;
- CLMS Forest Type;
- CLMS Water & Wetness;
- CLMS Snow Phenology.

## `CONTEXT`

Una font que aporta atributs o context però que no té per què modificar TLST.

Exemple: Tree Cover Density quan aporta `canopy_cover`.

## `AUTHORITATIVE_GEOMETRY`

Geometria que pot governar espacialment una subregió quan existeixi una font i
una llicència compatibles. Aquest rol queda preparat per verticals posteriors i
no s'ha de confondre amb el categòric general.

---

# Fonts actives, ignorades i eliminades

Eliminar un dataset i deixar d'utilitzar-lo són operacions diferents.

El sistema categòric ja disposa del concepte `enabled` en la persistència de
fonts. Aquesta semàntica s'ha de reutilitzar o estendre de manera coherent a les
instal·lacions de refinament en lloc de crear una segona llista paral·lela si no
és necessari.

Estats conceptuals de participació:

```text
ACTIU
IGNORAT
```

Una font ignorada:

- continua instal·lada;
- conserva els fitxers;
- conserva llicència i procedència;
- continua visible al gestor;
- es pot reactivar immediatament;
- no participa com a categòric governador;
- no participa com a refinament;
- no aporta cobertura efectiva a la caché TLST canònica.

`Eliminar` continua sent una acció diferent que pot retirar els fitxers locals i
la instal·lació segons el lifecycle existent.

Canviar `Actiu/Ignorat` és un canvi semàntic i invalida la part afectada de la
caché TLST.

---

# Ràster governador

Quan existeixen diversos categòrics generals actius, TerraLab3D ha de resoldre
per cada posició quin és el **ràster governador**.

La regla és espacial, no una prioritat global de proveïdor:

```text
1. considerar només BASE_CATEGORICAL actius;
2. considerar només les fonts que cobreixen la posició;
3. ordenar per precisió espacial real: menor mida de cel·la primer;
4. en empat de resolució, aplicar la prioritat persistent;
5. llegir la font;
6. si el resultat és NoData / unknown / unclassified / sense cobertura,
   provar la següent font;
7. la primera observació semàntica vàlida fixa el node TLST base.
```

La precisió espacial i l'especificitat semàntica tenen funcions diferents:

```text
PRECISIÓ ESPACIAL
→ decideix quina observació base representa realment la posició

PROFUNDITAT TLST
→ decideix fins on podem aprofundir semànticament després
```

Exemple:

```text
MCSC 1 m:
artificial.built

WorldCover 10 m:
cropland

→ governa MCSC 1 m
```

Un categòric gros no pot esborrar un objecte territorial més petit detectat per
una font categòrica més precisa.

---

# NoData i fallback

`nodata`, `unknown` i `unclassified` continuen sent estats d'observació, no
superfícies TLST.

En el governador:

```text
font A 1 m
→ NoData
→ provar font B 10 m
→ dada vàlida
→ B governa aquella posició
```

En un refinament:

```text
refinament A
→ NoData
→ no modifica el node actual
→ provar el següent refinament compatible
```

No s'interpolen IDs categòrics.

---

# Refinament semàntic compatible

Una vegada fixat el node TLST de base pel governador, una font de refinament no
pot tornar a classificar la posició des de zero.

Sigui:

```text
base_tlst
candidate_tlst
```

El candidat només és aplicable si:

```text
candidate_tlst == base_tlst
```

o bé:

```text
candidate_tlst és descendent de base_tlst
```

Si pertany a una altra branca:

```text
NOT_APPLICABLE
```

Exemple incompatible:

```text
Governador 1 m:
artificial.built

Crop Types 10 m:
vineyard

→ Crop Types s'ignora en aquella posició
```

Exemple compatible:

```text
Governador:
agriculture.cropland

Crop Types:
vineyard

→ es pot aprofundir fins al node TLST de vineyard justificat pel mapping
```

El fet que el refinament tingui una cel·la més gran no li permet sobrescriure
subregions incompatibles detectades pel governador.

---

# Ordre entre refinaments compatibles

TerraLab3D **no implementa una puntuació pròpia de fiabilitat, confiança o
qualitat dels datasets**.

El sistema interpreta les fonts actives segons la seva semàntica declarada. Si
una font publica una confiança pròpia, es pot conservar literalment com a
metadata, però no es converteix en un `trust score` de TerraLab3D.

Entre refinaments compatibles, l'ordre és:

```text
1. major profunditat semàntica TLST assolida;
2. major precisió espacial;
3. prioritat persistent;
4. identificador estable només com a últim tie-break tècnic si encara cal.
```

La prioritat ha de formar un ordre total i estable perquè el resultat sigui
determinista.

Els conflictes poden continuar registrant-se per auditoria, però no requereixen
un sistema probabilístic.

---

# Contribució normalitzada per al resolver

No és necessari crear una gran jerarquia de subclasses `Evidence` per cada
proveïdor. El resolver sí necessita un contracte normalitzat que impedeixi que
la lògica específica d'un proveïdor arribi al nucli.

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

Opcional quan realment aplica:

```text
temporal_validity
source_confidence   # només si la pròpia font el publica
qualifiers
geometry
```

Aquest contracte es pot materialitzar amb descriptors data-driven o models ja
existents. No cal crear una subclasse distinta per Crop Types, Forest Type,
Water & Wetness, etc. si no resol cap frontera funcional real.

---

# ResolutionTrace mínim

La resolució final ha de ser explicable.

Traça conceptual mínima:

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

No cal afegir una `confidence` calculada per TerraLab3D.

---

# Ràster canònic i sortides actuals del postprocessador

La implementació actual no desa codis crus barrejats. Cada píxel vàlid del
mosaic d'una instal·lació/pla conté el codi estable del node TLST més profund
justificable per aquella font. Els qualificadors continus (`canopy_cover`,
durada de neu, etc.) es mantenen separats de la categoria.

Cada actualització pot produir de manera transaccional:

- `refinement_mosaic.tif`: categoria TLST canònica del postprocessat actual;
- `refinement_source.tif`: font guanyadora dins del mosaic actual;
- `refinement_quality.tif`: prioritat/qualitat tècnica aplicada pel mosaic actual;
- `refinement_conflict.tif`: conflictes observats;
- `refinement_manifest.json`: graella, fonts, traduccions, llicències, hashes i finestres actualitzades;
- `refinement_qualifier_*.tif`: qualificadors continus disponibles.

Aquests artefactes **es conserven**. No s'ha de llençar la feina existent.

Però el seu paper canvia conceptualment:

> són artefactes normalitzats d'una instal·lació o d'un pla de refinament; no
> constitueixen per si sols la interpretació territorial global definitiva.

La interpretació global es construirà per sobre de tots els categòrics i
refinaments actius mitjançant governador + resolver + caché TLST canònica.

`refinement_quality.tif` no es converteix en una puntuació epistemològica de
fiabilitat.

---

# Prioritat antiga del mosaic

La implementació actual utilitza la prioritat:

```text
LOCAL_OFFICIAL
>
THEMATIC_REFINEMENT
>
EUROPEAN_HIGH_RESOLUTION
>
GENERAL_LAND_COVER
```

Aquesta prioritat pot continuar existint transitòriament dins del postprocessat
actual mentre sigui necessària per mantenir determinisme i compatibilitat.

No és, però, la regla semàntica final del territori.

La regla final és:

```text
BASE CATEGÒRICA:
resolució espacial
→ prioritat
→ fallback NoData

REFINAMENT:
compatibilitat TLST
→ profunditat TLST
→ resolució espacial
→ prioritat
```

---

# Caché TLST canònica

El runtime de superfície i el futur procedural no han de consumir directament
els codis d'un proveïdor concret.

Pipeline final:

```text
fonts categòriques generals actives
+
refinaments actius
+
mappings versionats
+
prioritats
        ↓
ràster governador
        ↓
resolver TLST determinista
        ↓
CACHÉ TLST CANÒNICA
        ↓
runtime de superfície
        ↓
SpatialPatch
        ↓
procedural
```

La caché és derivada i regenerable. Les fonts originals i els mappings
continuen sent l'autoritat d'auditoria.

---

# Format intern de caché

Format lògic proposat:

```text
<cache-id>.tlstcache/
├── manifest.json
└── data.zarr/
    ├── resolution_1m/
    ├── resolution_10m/
    ├── resolution_100m/
    └── ...
```

`.tlstcache` és el bundle lògic TerraLab3D.

Zarr és un backend intern de caché, no un format públic d'intercanvi i no una
segona façana d'entrada raster.

La separació és:

```text
FONTS RASTER EXTERNES
→ Rasterio

CACHÉ INTERNA
→ CanonicalTlstCacheStore
→ backend Zarr
```

No s'ha d'exposar `zarr.Array` al domini o a la UI.

L'exportació futura a GeoTIFF/COG queda fora d'aquesta fase.

---

# Multiresolució

No es barregen píxels d'1 m, 10 m i 100 m dins de la mateixa matriu.

Cada array/grup té una resolució fixa:

```text
resolution_1m
resolution_10m
resolution_100m
...
```

Els nivells es creen de forma progressiva i només quan es necessiten.

La resolució més fina disponible en una zona no obliga a materialitzar tot el
món a aquella resolució.

---

# Chunking i compressió

La caché és chunked.

La mida exacta del chunk no es congela sense benchmark. Candidats inicials:

```text
512 × 512
1024 × 1024
```

Compressors a comparar amb dades TLST reals:

```text
Zstd
Blosc + Zstd
```

El manifest conserva almenys:

```text
codec
codec_level
chunk_shape
dtype
cache_schema_version
```

Els categòrics solen ser molt compressibles perquè hi ha grans regions amb
codis repetits, però no s'ha de prometre una ratio fixa.

---

# Dades denses mínimes

Core dens recomanat:

```text
tlst_code
validity
```

`uint16` és suficient per la taxonomia actual mentre hi càpiga, però no és la
identitat pública.

La identitat estable continua sent:

```text
categoryKey
```

El manifest conserva la taula:

```text
code ↔ categoryKey
```

No guardar per defecte a resolució completa:

```text
source_id
quality
confidence
```

si la mateixa traçabilitat es pot representar més eficientment amb:

```text
diccionari de traces per chunk
trace_id opcional
metadades de procedència
canals diagnòstics opcionals
```

---

# Caché progressiva

La caché no s'ha de precomputar necessàriament per tot el món.

Unitat conceptual de treball:

```text
AOI
+
resolució
+
chunk
```

Flux:

```text
request chunk
→ cache hit?
  ├── sí → publicar
  └── no
      → resoldre fonts
      → calcular TLST
      → escriure atomically
      → publicar
```

Les operacions han de conservar correlació, cancel·lació i latest-wins.

Una cancel·lació no pot publicar un chunk parcial com a vàlid.

---

# Invalidació

El fingerprint de la caché inclou almenys:

- versió TLST;
- versió del resolver;
- conjunt de fonts actives;
- rol de cada font;
- `enabled/ignored`;
- ordre de prioritat;
- fingerprints dels fitxers;
- `scheme_key`;
- `scheme_version`;
- `mapping_revision`;
- resolució espacial;
- CRS i graella objectiu;
- versió del format de caché.

Invaliden la caché:

- instal·lar una nova font;
- eliminar una font;
- activar-la;
- ignorar-la;
- canviar prioritat;
- canviar mapping;
- substituir els fitxers d'una font;
- canviar TLST;
- canviar una regla del resolver que afecti el resultat.

No invaliden:

- moure la càmera;
- canviar FOV;
- pan/zoom visual;
- obrir/tancar modals;
- canviar un estil visual sense semàntica.

Quan el footprint és conegut, la invalidació ha de preferir només els chunks que
intersequen la zona afectada.

Si no es pot demostrar que una invalidació parcial és segura:

```text
invalidació completa
```

La correcció té prioritat sobre l'optimització.

---

# Estimació d'espai de disc

Abans d'una construcció gran, TerraLab3D pot informar l'usuari de la mida
prevista.

Mida bruta:

```text
number_of_cells × bytes_per_cell dels canals obligatoris
```

Mida comprimida:

```text
sample de chunks representatius
→ compressió real
→ ratio mesurada
→ extrapolació
```

La UI pot mostrar:

```text
Caché TLST estimada

Brut:                 ...
Comprimit estimat:    ...
Espai lliure:         ...
```

amb una nota equivalent a:

```text
La mida final pot variar segons la distribució de les categories
i l'eficiència de compressió dels chunks.
```

No prometre una xifra comprimida exacta abans de construir-la.

---

# Integració progressiva amb el runtime de superfície

La ruta actual de land-cover encara conserva dependències de fonts/esquemes
concrets.

La migració s'ha de fer sense trencar el terreny existent:

```text
FASE 1
fonts actuals
→ governor/resolver/cache en paral·lel

FASE 2
consumer de superfície
→ caché TLST canònica

FASE 3
retirar dependència runtime d'un esquema concret
quan existeixi paritat funcional i de tests
```

Canviar una capa categòrica o un refinament no obliga a reconstruir la geometria
DEM.

---

# Matriu de productes habilitats al HEAD observat

La matriu exacta continua sent autoritativa al codi i a
`refinement_provider_rollout()`.

| Adaptador / dataset | Abast i resolució | Paper principal | Llicència comercial | Estat |
|---|---|---|---|---|
| ICGC MCSC 2024 | Catalunya, 1 m | categòric general d'alta resolució / refinament local segons configuració | CC BY 4.0 | habilitat |
| CORINE Land Cover 2018 | Europa, 100 m | categòric general europeu | Copernicus CLMS | habilitat |
| CLMS Crop Types | Europa, 10 m anual | refinament agrícola | Copernicus CLMS | habilitat |
| CLMS Grassland | Europa, 10 m anual | refinament/observació herbàcia | Copernicus CLMS | habilitat |
| CLMS Tree Cover Density | Europa, 10 m anual | qualificador `canopy_cover` / context | Copernicus CLMS | habilitat |
| CLMS Dominant Leaf Type | Europa, 10 m anual | refinament broadleaf/needleleaf | Copernicus CLMS | habilitat |
| CLMS Forest Type | Europa, 10 m cada 3 anys | refinament broadleaf/needleleaf/mixed | Copernicus CLMS | habilitat |
| CLMS Snow Phenology S2 | Europa, 20 m anual | refinament/qualificadors de neu | Copernicus CLMS | habilitat |
| CLMS Global Dynamic Land Cover | global, 10 m, 2020 beta | categòric general/fallback global | Copernicus CLMS | habilitat |
| CLMS Water & Wetness 2018 | Europa, 10 m | refinament d'aigua/humitat | Copernicus CLMS | habilitat |
| ESA WorldCover 2021 v200 | global, 10 m | categòric general global | CC BY 4.0 | habilitat |

L'estat real del codi preval si aquesta taula queda desactualitzada.

---

# Autenticació CDSE

La descoberta del catàleg públic no exigeix les mateixes credencials que la
descàrrega d'assets protegits.

El HEAD actual incorpora coordinació d'autenticació i suport de credencials al
magatzem segur del sistema operatiu quan l'usuari decideix recordar-les.

Regles de producte:

- si l'usuari no marca `Recordar`, TerraLab3D no ha de persistir usuari i
  contrasenya;
- els tokens/sessions es tracten com a credencials temporals;
- si la sessió ja no és vàlida, es torna a autenticar o es torna a demanar
  credencials segons el flux disponible;
- si `Recordar` està activat, les credencials persistents s'emmagatzemen al
  keyring del sistema operatiu, no en text pla dins del projecte.

La UI no ha de descriure l'autenticació de CDSE com si els datasets fossin
necessàriament "productes comercials"; autenticació i compatibilitat de
llicència són conceptes diferents.

---

# Cobertura auditada de TLST

Les traduccions només poden justificar nodes que la llegenda real de la font
permet demostrar.

No s'utilitza una classe pare com si demostrés totes les fulles descendents.
Els buits de cobertura TLST continuen sent informació explícita i no es
completen amb precisió inventada.

Les proves han de fallar si un mapping apunta a una clau TLST no canònica.

El recompte exacte de fulles cobertes i buits s'ha de derivar de la taxonomia i
els mappings del HEAD real, no mantenir com una xifra manual eterna dins de la
documentació.

---

# Proveïdors desactivats explícitament

Els proveïdors no validats continuen fora del catàleg executable.

| Família | Estat i motiu general |
|---|---|
| ICGC RTT | desactivat fins disposar de contracte AOI i mapping verificat |
| CLCplus Backbone | desactivat fins validar packaging, mapping i smoke oficial |
| Urban Atlas / Imperviousness / Built-Up / BBH | desactivat fins disposar d'adaptadors i semàntica exacta per producte |
| EU-Hydro / Coastal / Riparian | desactivat fins disposar de contractes AOI estables per producte |
| INSPIRE/HVD Buildings | desactivat; serveis i llicència a revisar per país |
| INSPIRE/HVD Transport | desactivat; esquema i llicència a revisar per país |
| Open Maps for Europe 2 | desactivat fins congelar assets, mapping i llinatge d'atribució |
| NASA/USGS | desactivat fins seleccionar un producte que aporti informació nova justificable |

No hi ha adaptadors mig habilitats: un dataset amb endpoint, mapping o llicència
no verificats ha de quedar fora de la descoberta oficial.

---

# Política de llicències

El filtre comercial continua sent **fail-closed** i s'executa abans de mostrar
un candidat i de nou abans de crear el job quan el flux ho exigeix.

S'admeten, segons la política actual:

- domini públic;
- CC0;
- CC BY 4.0;
- equivalents d'atribució revisats;
- política Copernicus compatible amb el producte.

Es rebutgen com a fonts oficials automàtiques quan entren en conflicte amb la
política comercial del producte:

- metadata incompleta;
- ús no comercial;
- `research only`;
- ShareAlike;
- CC BY-SA;
- ODbL;
- bases derivades recíproques;
- llinatge OSM/ODbL.

EuroCrops i OSM no s'han de presentar com a fonts oficials ja habilitades pel
simple fet que documents antics els utilitzessin com a exemple. Poden aparèixer
com a fonts conceptuals o importacions externes amb règim de llicència separat,
però no com a membres actuals del catàleg oficial si la política vigent els
exclou.

Referències oficials actuals:

- ICGC MCSC i reutilització: <https://www.icgc.cat/ca/Geoinformacio-i-mapes/Mapes/Mapa-de-cobertes-del-sol-de-Catalunya>
- Reutilització ICGC: <https://www.icgc.cat/ca/LICGC/Informacio-publica/Transparencia/Reutilitzacio-de-la-informacio>
- CORINE 2018: <https://land.copernicus.eu/en/products/corine-land-cover/clc2018>
- Catàleg CDSE/CLMS: <https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CLMS.html>
- Condicions d'ús CLMS: <https://land.copernicus.eu/en/faq/data-use-terms-and-conditions>
- Water & Wetness 2018: <https://land.copernicus.eu/en/products/high-resolution-layer-water-and-wetness/water-and-wetness-status-2018>
- ESA WorldCover: <https://esa-worldcover.org/>
- Natural Earth: <https://www.naturalearthdata.com/about/terms-of-use/>

---

# Afegir un proveïdor

1. Implementar `RefinementProviderPort` sense bifurcacions específiques al nucli.
2. Congelar assets immutables amb footprint, ordre, mida, autenticació i mapping.
3. Afegir metadades de llicència completes i passar els gates comercials.
4. Declarar de forma explícita el rol semàntic del producte.
5. Reutilitzar el postprocessador canònic raster/vector quan sigui apropiat.
6. Afegir fixture determinista, servidor HTTP simulat, smoke oficial opt-in i prova que totes les claus TLST són canòniques.
7. Afegir la família a `refinement_provider_rollout()` com `enabled` només quan els requisits reals estiguin verificats.
8. Si algun requisit falla, mantenir-la `disabled` amb un motiu concret.
9. No crear una prioritat epistemològica especial només perquè sigui un proveïdor nou.
10. Documentar si el producte és `BASE_CATEGORICAL`, `SEMANTIC_REFINEMENT`, `CONTEXT` o aporta un altre rol justificat.

---

# Pròximes verticals relacionades

L'ordre de treball revisat és:

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
V9+ Procedural                       PENDENT
```

La futura automatització de refinaments no crearà la caché des de zero: la
caché ja existirà a V7. La futura V16 actuarà com a **planificador automàtic de
refinaments guiat pels buits TLST** i reutilitzarà aquest gestor per descobrir,
descarregar i instal·lar només les fonts que aportin profunditat semàntica nova.

---

# Definition of Done de la pròxima evolució

El bloc governador/resolver/cache no es considera tancat fins que:

- [ ] existeix almenys un categòric general actiu abans de refinar;
- [ ] la UI explica el bloqueig quan no existeix base;
- [ ] un dataset es pot ignorar i reactivar sense eliminar-lo;
- [ ] `enabled/ignored` persisteix;
- [ ] la prioritat persisteix;
- [ ] el governador es decideix per resolució espacial + fallback;
- [ ] `NoData` activa fallback;
- [ ] un refinament incompatible no sobrescriu el governador;
- [ ] un refinament compatible pot aprofundir TLST;
- [ ] l'empat es resol per profunditat → resolució → prioritat;
- [ ] el resultat conserva `ResolutionTrace` determinista;
- [ ] existeix un port de caché canònica;
- [ ] Zarr queda encapsulat en infraestructura;
- [ ] la caché és chunked i multiresolució amb arrays de resolució fixa;
- [ ] les escriptures són atòmiques;
- [ ] existeix fingerprint de generació;
- [ ] els footprints permeten invalidació parcial quan és segur;
- [ ] existeix fallback a invalidació completa;
- [ ] la UI pot estimar mida de disc abans d'una construcció gran;
- [ ] el runtime de superfície pot consumir TLST canònic;
- [ ] no es reconstrueix el DEM només per canviar semàntica;
- [ ] no s'ha introduït cap quality/trust score propi;
- [ ] la suite de regressió continua passant.
