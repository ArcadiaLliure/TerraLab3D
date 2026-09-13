# Pas 28 — Descobriment de DEM multiproveïdor per AOI

> Estat: **parcial**. L'aplicació pot llegir un DEM configurat i construir terreny, però no descobrir ni comparar productes per àrea d'interès.

## Estat actual verificat

- [x] Existeixen port, adaptador rasterio, coordinador d'elevació i renderer de terreny.
- [x] Els passos 15 i 16 consumeixen DEM local per a horitzó i terreny progressiu.
- [ ] No hi ha cerca remota multiproveïdor, normalització de resultats, llicències ni instal·lació per AOI.

## Resultat funcional

L'usuari defineix una àrea d'interès, consulta diversos proveïdors de DEM, compara cobertura, resolució, mida, llicència i cost, i instal·la el producte seleccionat mitjançant el gestor central.

## Dependències

- [Pas 24 — catàleg i descàrregues](pas24-cataleg-recursos-descarregues.md).
- [Pas 25 — gestor de capes i AOI](pas25-gestor-capes.md).
- [Pas 16 — terreny progressiu](../completat/pas16.md).

## Decisions tancades

- Cada proveïdor implementa un port de descobriment i torna descriptors normalitzats; credencials, preus i llicències no entren al domini científic.
- La consulta inicial inclou almenys un proveïdor obert tipus NASADEM i admet proveïdors comercials sense fingir equivalència de llicència.
- Els resultats s'ordenen per criteri explícit —cobertura, resolució, cost o mida— i mostren la causa de qualsevol exclusió.
- L'AOI prové del pas 25 i es normalitza de manera segura a l'antimeridià.
- Descarregar crea recursos/treballs del pas 24; un DEM extern també es pot registrar sense copiar-lo.

## Codi existent a reutilitzar

- Port i coordinador: [`terrain.py`](../../backend/src/terralab3d/application/ports/terrain.py) i [`elevation_coordinator.py`](../../backend/src/terralab3d/application/elevation_coordinator.py).
- Adaptador: [`dem/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/dem/adapter.py) i [`dem/crs.py`](../../backend/src/terralab3d/infrastructure/adapters/dem/crs.py).
- UI/render: [`EarthPage.ts`](../../frontend/src/view/ui/drawer_pages/EarthPage.ts) i [`DemTerrainLayerRenderer.ts`](../../frontend/src/view/three/layers/DemTerrainLayerRenderer.ts).
- Recursos: [`layer_database.py`](../../backend/src/terralab3d/infrastructure/resources/layer_database.py) i [`ResourceManager.ts`](../../frontend/src/application/ResourceManager.ts).

## Treball pendent

- [ ] Definir port de descobriment, AOI normalitzada i descriptor de producte/cobertura/llicència.
- [ ] Implementar adaptador obert inicial i fixtures; definir l'extensió per a proveïdors autenticats.
- [ ] Construir cerca concurrent cancel·lable amb timeout, deduplicació, ordenació i resultats parcials.
- [ ] Crear cards comparables i filtres de resolució, cobertura, cost, mida i llicència.
- [ ] Transformar el producte triat en descriptor i treball del pas 24, incloent mosaics quan siguin necessaris.
- [ ] Registrar metadades d'origen, AOI, CRS, datum vertical, resolució i checksum amb la instal·lació.

## Flux tècnic

AOI versionada → consultes concurrents a adaptadors → descriptors normalitzats → deduplicació/ordenació → selecció → recurs/variant → descàrrega i verificació del pas 24 → DEM disponible per als coordinadors existents.

## Errors, cancel·lació i recursos

- Canviar AOI cancel·la les consultes anteriors; un proveïdor lent no bloqueja els altres.
- Errors d'autenticació, quota, llicència, cobertura i xarxa es mostren per proveïdor.
- Les respostes i previews tenen cache acotada; tokens i credencials no s'escriuen als manifests de projecte.

## Proves

- AOI normal, antimeridià, pols, sense cobertura i cobertura parcial.
- Timeout d'un proveïdor, resultats parcials, deduplicació i ordenació estable.
- Conversió a treball de descàrrega i lectura posterior amb l'adaptador actual.
- Contractes de llicència, metadades i cancel·lació per revisió.

## Criteri de sortida

Una mateixa AOI produeix una comparació auditable de productes i permet instal·lar-ne un sense camins especials fora del gestor central, conservant tota la procedència necessària.

## Evidències

- [ ] Captura de resultats de dos proveïdors amb criteri d'ordre visible.
- [ ] Proves d'antimeridià, timeout i resultat parcial.
- [ ] Manifest instal·lat amb AOI, CRS, datum, resolució, origen i llicència.
- [ ] DEM instal·lat consumit pels fluxos dels passos 15–16.

## Fora d'abast

Corregir científicament datums incompatibles, comprar llicències o implementar la semàntica de cobertura superficial.

## Instrucció per a Codex

Amplia el port de terreny amb adaptadors de descobriment, sense acoblar proveïdors al domini. Reutilitza l'AOI del pas 25 i el cicle de recursos del pas 24; conserva procedència i llicència a cada instal·lació.
