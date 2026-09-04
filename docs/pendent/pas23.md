# Pas 23 — Capes, datasets, assistent de dades, preferències i feedback

> Estat: **pendent, amb implementació parcial**
> El gestor de capes està en desenvolupament i disposa de l’arquitectura annexada, però la vertical encara no és completa.

## Resultat funcional palpable

L’aplicació disposa d’un gestor de capes i recursos equivalent: instal·lació, fonts externes, progrés, cancel·lació, fallback, visibilitat i restauració de preferències. La interpretació del territori passa a ser guiada per un governador espacial i un resolver TLST determinista que consoliden múltiples fonts en una memòria cau canònica multiresolució.

## Avenç implementat: verticals TLST 1–4 i gestor d'adquisició

La infraestructura base ja és operativa:

- **V1 TLST 1.0**: `[x]` complet. Identitat canònica (`categoryKey`), picking, estats d'observació i datasets base.
- **V2 raster universal + DEM**: `[x]` complet. Descriptors Rasterio, selecció de banda, fallback DEM i regeneració segura.
- **V3 categòric universal**: `[x]` complet. RGB/A exactes, mappings versionats, S2GLC, WorldCover, LCM-10 i CORINE.
- **V4 esquemes personalitzats**: `[x]` complet. Mapping manual i persistència (`scheme_key`, `mapping_revision`).
- **Gestor d'adquisició i normalització de refinaments**: `[/]` implementat parcialment. Descoberta, verificació de llicència, descàrregues CDSE, mosaics, manifest, persistència i UI. Els mosaics actuals són artefactes normalitzats d'instal·lació, no la interpretació territorial global.

## Fonts TerraLab a consultar

- `TerraLab/data/layer_manager.py` i `data/assets_manager.py`
- `TerraLab/data/source_catalog.py`
- `TerraLab/ui/asset_onboarding.py`
- `TerraLab/common/utils.py`
- `TerraLab/ui/widget_controls_builder.py`

## Objectiu

Completar el pipeline d'interpretació territorial separant l'adquisició de dades de la interpretació semàntica. El governador espacial fixa la branca semàntica base, el resolver TLST aprofundeix mitjançant refinaments compatibles i una memòria cau canònica Zarr nodreix el runtime de superfície (`SpatialPatch` i procedurals).

## Tasques d'evolució del sistema categòric i TLST

### Arquitectura i rols de fonts

- [x] Distingir els rols `BASE_CATEGORICAL`, `SEMANTIC_REFINEMENT`, `CONTEXT` i `AUTHORITATIVE_GEOMETRY`.
- [x] Garantir almenys una font `BASE_CATEGORICAL` activa abans d'aplicar refinaments semàntics.
- [x] Separar activació semàntica i instal·lació, de manera que una font instal·lada pugui quedar `IGNORADA`.
- [x] Aplicar una política de llicències *fail-closed* al catàleg automàtic.

### V5 — Governador i estat actiu/ignorat

- [x] Seleccionar el dataset governador per precisió espacial entre les fonts base actives.
- [x] Resoldre empats de resolució per `priority` i, després, per `stable_id`.
- [x] Aplicar fallback de `NoData`, `unknown` i `unclassified` al següent dataset base sense interpolar categories.

### V6 — Resolver TLST determinista

- [ ] Mapar valor natiu, esquema, versió i revisió a TLST abans de comparar semàntica.
- [ ] Permetre que el refinament només aprofundeixi (`same-or-descendant`) dins la branca del governador.
- [ ] Resoldre conflictes entre refinaments germans exclusivament per `priority`.
- [ ] Definir un contracte d'evidència amb `coverage`, `spatial_resolution` i identificadors versionats.
- [ ] Generar una `ResolutionTrace` explicable amb governador, TLST inicial, passos d'avaluació i node final.

### V7 — Memòria cau TLST canònica

- [ ] Materialitzar progressivament una memòria cau `.tlstcache` amb backend Zarr.
- [ ] Organitzar-la per resolució amb blocs i compressió Zstd o Blosc+Zstd.
- [ ] Desar densament `tlst_code` i `validity`; conservar la procedència per bloc.
- [ ] Estimar-ne la mida abans de construir-la mitjançant mostreig de blocs representatius.
- [ ] Invalidar-la de manera determinista o espacial davant canvis de fonts, prioritats o esquemes, però no per moviments de càmera o UI.
- [ ] Connectar-hi el runtime i `SpatialPatch` en lloc de consumir directament els datasets natius.

### Planificació i UI

- [ ] Mostrar `ACTIU` i `IGNORAT` a les pestanyes Elevació, Categòric i Refinament, separats de l'acció d'eliminar.
- [ ] Definir el planificador automàtic de refinaments a partir dels buits TLST de la memòria cau.
- [ ] Migrar el runtime per fases: verificació paral·lela, connexió a la memòria cau i retirada dels codis natius del frontend.

## Tasques generals de la vertical

- [ ] Definir els IDs de capa i descriptors de cel/terra amb fills del sistema solar.
- [ ] Separar visibilitat de disponibilitat de dades.
- [ ] Definir estats ready, partial, missing, invalid, planned, downloading, paused, extracting i error.
- [ ] Definir manifests amb versió, mida, checksum, llicència, procedència i requisit.
- [ ] Implementar biblioteca de dades configurable i estructura de directoris.
- [ ] Implementar fonts administrades i fonts externes sense assumir-ne propietat.
- [ ] Implementar descàrrega reprenable, pausa, cancel·lació i instal·lació atòmica.
- [ ] Implementar checksum i validació després d’instal·lar.
- [ ] Mostrar progrés Gaia, terreny, Via Làctia, Planck, NGC i altres recursos.
- [ ] Mostrar badges de fallback amb estabilització anti-flicker.
- [ ] Persistir visibilitat de capes, ubicació, Bortle, terreny, superfície, scope i estils.
- [ ] Versionar l’esquema de preferències i implementar migracions.
- [ ] Restaurar sessió sense iniciar descàrregues automàtiques no sol·licitades.
- [ ] Implementar errors accionables amb opció d’obrir l’assistent.
- [ ] Preservar pressupostos de memòria cau per bytes i neteja segura.

## Criteri de sortida

La infraestructura diferencia l'adquisició de la interpretació semàntica. El runtime consumeix una memòria cau TLST Zarr determinista generada pel governador i els refinaments compatibles. Totes les capes es poden activar o ignorar, les descàrregues són controlables i les preferències es restauren sense corrupció.

## Evidència obligatòria

- [ ] Proves del governador: resolució, `NoData` i fonts ignorades.
- [ ] Proves de refinament compatible, descendent, germà, incompatible i `NoData`.
- [ ] Prova d'invalidació de la memòria cau per mapping, però no per càmera, amb fingerprint determinista.
- [ ] Prova de persistència de rols, `enabled`, `priority` i mappings.
- [ ] Proves de biblioteca buida, parcial i completa, descàrrega pausada i checksum incorrecte.
- [ ] Vídeo de l'assistent, els estats `ACTIU`/`IGNORAT` i l'estimació de memòria cau.

## Fora d’abast del pas

El pas no inclou una reescriptura integral de les verticals V1–V4, un sistema d'autenticació nou ni un gestor paral·lel. Tampoc implementa els sistemes procedurals o `SpatialPatch` massius; prepara la base canònica que els alimentarà. El pas 24 endureix, mesura i homologa el conjunt complet.

## Annex: Arquitectura del gestor unificat de capes i recursos

Aquesta documentació detalla l'arquitectura del sistema encarregat d'obtenir, persistir i servir conjunts de dades asíncrons per a TerraLab3D. L'objectiu és independitzar la interfície gràfica de la complexitat del sistema d'arxius, errors de xarxa i reintents.

### 1. Conceptes clau: capa, recurs i descàrrega (tasca)

- **Capa (Layer)**: Un element visual en l'escena 3D (ex: Via Làctia, Anells de Saturn). Té un cicle de vida lligat a Three.js i respon a interaccions de visibilitat o opacitat.
- **Recurs (Resource)**: El conjunt de dades subjacent que fa possible la capa (ex: una textura EXR 16K o un fitxer BSP). A vegades, diverses capes poden compartir un mateix recurs.
- **Descàrrega (Job)**: L'acció asíncrona d'obtenir el recurs per la xarxa.

### 2. Arquitectura (Protocol UI ↔ Backend)

```mermaid
sequenceDiagram
    participant UI as UI (SkyPage/Modal)
    participant RM as ResourceManager (Frontend)
    participant Bridge as WebSocketBridge
    participant Backend as DownloadJobManager
    participant Disk as emmagatzematge (Local)

    UI->>RM: requestDownload("sky.milky_way", "16k")
    RM->>Bridge: { type: "request_resource_download" }
    Bridge->>Backend: WebSocket Event
    Backend->>Disk: Crea/Afegeix a milkyway.part
    loop Cada 250ms
        Backend->>Bridge: { type: "download_job_snapshot", progress: 0.X }
        Bridge->>RM: actualitza estat
        RM->>UI: actualitza progress bar
    end
    Backend->>Disk: Canvia el nom a .exr, verifica hash
    Backend->>Bridge: { type: "download_job_snapshot", state: "READY" }
    Bridge->>RM: actualitza estat
    RM->>UI: habilita capa (casella activa)
```

### 3. Estats del cicle de vida d'un Recurs

Els estats estan enumerats a `ResourceInstallState`:
- `NOT_INSTALLED`: Recurs inexistent al disc o corrupte.
- `QUEUED`: Petició acceptada, encara sense transferència de dades.
- `AUTHENTICATING`: Esperant una sessió vàlida del proveïdor; encara no s'estan rebent bytes.
- `DOWNLOADING`: Descarregant via HTTP (suporta streams i `Range`).
- `PAUSED`: L'usuari (o un error) ha aturat el flux. Es pot reprendre sense perdre els bytes descarregats.
- `VERIFYING`: Fent comprovació criptogràfica (MD5/SHA256) contra el manifest.
- `PROCESSING`: Generant els derivats locals després de verificar la descàrrega.
- `ERROR`: Problema insalvable (connexió refusada, HTTP 404).
- `PARTIAL`: (Per a bundles) Alguns fitxers existeixen però no la totalitat.
- `READY`: Descarregat, validat i disponible per muntar a memòria.

### 4. Variants i Bundles

- **Variants**: Versions mútuament exclusives d'un mateix concepte per ajustar-se a la capacitat gràfica de l'usuari. Ex: Via Làctia pot tenir variants de `8k`, `16k`, `32k`.
- **Bundles (Fitxers Múltiples)**: A vegades un sol recurs requereix descarregar múltiples arxius per funcionar (ex: texturitzat de Mart amb albedo, relleu i normals per separat, o col·lecció de satèl·lits de Júpiter). Si algun fitxer falta, l'estat global es considera `PARTIAL`.

### 5. Emmagatzematge (emmagatzematge) i Migració

La persistència de dades es guarda de forma desacoblada del repositori git, concretament a:
`TerraLab3D/data/sky/managed` i `TerraLab3D/state/resources/`.

L'estat instal·lat es guarda a `local_installation_state.json`. Utilitzem rutes relatives al *data root* per permetre que un usuari mogui la carpeta global lliurement sense trencar referències.

#### Migració automàtica i Detecció
En arrencar, el component `ResourceInstallationRepository` escaneja directoris _legacy_ a la recerca de fitxers vàlids (ex. kernels antics). Si els troba, actualitza l'estat local a `READY` directament, evitant descarregar el que l'usuari ja havia obtingut.

### 6. Flux de reintent i Cancel·lació

En cas d'una caiguda de xarxa, el sistema marca el job com a `ERROR`. Si l'usuari clica a "Reintentar" (que internament crida de nou `request_resource_download`), el gestor examina el fitxer parcial (ex: `milkyway.exr.part`) al directori temporal, i si el proveïdor admet `Range: bytes=...`, reprendrà el byte des d'on ho va deixar.
Si l'usuari cancel·la o elimina el recurs des del gestor de capes, s'esborren tant els recursos temporals com els definitius associats i es retorna l'estat a `NOT_INSTALLED`.

### 7. Afegir un nou recurs

Afegir un recurs nou **no requereix modificar la lògica asíncrona ni la UI**. Simplement, s'ha d'afegir el descriptor al fitxer estàtic del backend (o carregar-lo des d'un manifest JSON).

Exemple de descriptor afegit a la llista del `ResourceCatalog`:
```python
ResourceDescriptor(
    id="celestial.ngc",
    title="OpenNGC (Galàxies i Nebuloses)",
    provider="Mattia Verga / OpenNGC",
    acquisition_kind=AcquisitionKind.STATIC_FILE,
    variants=[
        ResourceVariant(
            id="default",
            title="Catàleg complet NGC/IC",
            source_url="https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/NGC.csv",
            expected_bytes=1500000
        )
    ]
)
```
Amb això, apareixerà instantàniament al `ResourceManagerModal` per ser descarregat, posat en pausa, i reportar errors sota la mateixa capa de validació.

## 8. Importació raster local d'elevació

La importació local és una operació diferent d'una descàrrega. No crea cap `DownloadJob` i separa tres documents:

- `layers.json`: descriptor publicable del recurs;
- `local_installation_state.json`: disponibilitat i propietat local;
- `data_sources.json`: font raster, ordre primària/fallback i selecció activa.

El frontend usa sessions HTTP correlacionades (`POST`, `PUT` binari, `inspect`, `commit`, `DELETE`). Els bundles gestionats es mantenen en staging fins al commit; cancel·lar-los no modifica els catàlegs. Les fonts externes només es registren i mai s'eliminen del disc. Després del commit, el `ReloadableElevationPort` canvia d'adaptador de manera atòmica, conserva lectures en curs i força un nou fingerprint de terreny i horitzó.

La pestanya TERRA queda dividida en `Elevació`, `Categòric` i `Refinament`. La contaminació lumínica existent viu a `Refinament`.

## 9. Importació raster categòrica i esquemes TLST

`Categòric → + Importar` reutilitza les mateixes sessions HTTP locals i els
mateixos modes `managed`/`external`, però analitza valors discrets sense
interpolació. Admet una banda entera, índex amb paleta i colors RGB/RGBA
exactes. El fitxer font es conserva i només es genera una vista indexada
`uint16` reconstruïble per als hot paths actuals.

TerraLab proposa coincidències del registre només després que la font s'ha
declarat categòrica. L'usuari ha de revisar i confirmar esquema, versió i
revisió. El registre incorpora S2GLC, WorldCover, Copernicus LCM-10, CORINE i
els esquemes personals persistits a `classification_schemes.json`. Un mapping
personal pot apuntar a qualsevol node TLST; no cal inventar una fulla.

Després del commit, `data_sources.json` conserva el valor i dtype font,
l'encoding, les bandes, la revisió i el raster derivat. El canvi retira els
tiles categòrics obsolets i torna a publicar llegenda i cobertura. El picking
continua mostrant el valor font real, no el codi compacte d'execució quan són
diferents.

## 10. Refinaments TLST

`TERRA → Refinament` és una capacitat vertical del mateix gestor. Defineix una
AOI en un mapa OpenLayers autònom, consulta tots els adaptadors habilitats,
calcula cobertura local/planificada/pendent i congela els assets seleccionats en
un pla paramètric reproduïble. Els jobs reutilitzen pausa, represa, verificació i
cancel·lació del `DownloadJobManager`; el progrés tècnic es tradueix a missatges
de refinament sense crear un segon motor de descàrregues.

La descàrrega no es considera instal·lada fins que el postprocessador ha traduït
les classes a TLST, les ha alineat a la graella canònica, ha actualitzat el
mosaic incremental i ha calculat cobertura des dels píxels vàlids. La importació
manual iniciada des d'un node segueix el mateix principi i exigeix metadades de
llicència comercial abans de registrar cobertura verificada.

La matriu actual de productes, llicències, proveïdors desactivats i buits de
cobertura es manté a [tlst-refinement-manager.md](../tlst-refinement-manager.md).
