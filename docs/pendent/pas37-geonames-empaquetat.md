# Pas 37 — Nomenclàtor GeoNames empaquetat

> Estat: **pendent**. No hi ha dataset GeoNames ni renderers de nomenclàtor; la superfície categòrica, el terreny i els modes d'observació instrumental són les bases reutilitzables.

## Estat actual verificat

- [x] El terreny/DEM ja aporta geometria i el pas 29 aporta classes canòniques, inclosa superfície artificial.
- [x] El Pas 19 defineix els modes d'observació instrumental (el mode prismàtics s'ha descartat; el zoom visual global i el camp/reticle instrumental en són la referència).
- [ ] GeoNames filtrat, l'assignació assentament↔taca, la consulta de cims i el sistema de labels no estan implementats.

## Resultat funcional

Amb topografia carregada, TerraLab3D etiqueta assentaments reals associats a les taques artificials i permet veure cims nomenats dins el camp visual (o filtrats pel reticle instrumental) o mitjançant una opció global, amb línies/labels llegibles i sense descàrrega addicional.

## Dependències

- [Pas 19 — modes d'observació instrumental](../completat/pas19-modes-optics.md).
- [Pas 29 — superfície semàntica](pas29-superficie-semantica.md).

## Decisions tancades

- S'utilitza GeoNames filtrat: classe `P` per a populated places i els feature codes de relleu aprovats per a cims, sota CC BY 4.0 amb atribució visible.
- El CSV/índex derivat és dada base versionada i empaquetada: queda fora del gestor del pas 24, de l'AOI i de l'arbre de refinament.
- GeoNames només aporta nom i punt. El raster determina l'extensió artificial; el DEM determina l'altura/oclusió del cim.
- Assignació d'assentaments: punt dins la taca → directa; si no, proximitat sota un llindar documentat. Diverses localitats a la mateixa taca conserven totes les etiquetes.
- Les dades es carreguen automàticament amb topografia. Els assentaments pertinents es representen; els cims visibles es mostren segons el FOV/camp instrumental o mitjançant l'opció global.
- Els cims usen línia vertical i label flotant escalat; decluttering/prioritat evita col·lisions segons zoom, distància i importància.

## Codi existent a reutilitzar

- Superfície: [`surface/land_cover.py`](../../backend/src/terralab3d/domain/surface/land_cover.py), [`land_cover_coordinator.py`](../../backend/src/terralab3d/application/land_cover_coordinator.py) i [`LandCoverTextureManager.ts`](../../frontend/src/view/three/terrain/LandCoverTextureManager.ts).
- Terreny: [`elevation_coordinator.py`](../../backend/src/terralab3d/application/elevation_coordinator.py) i [`TerrainLayerRenderer.ts`](../../frontend/src/view/three/layers/TerrainLayerRenderer.ts).
- Òptica: [`ScopeLayerRenderer.ts`](../../frontend/src/view/three/layers/ScopeLayerRenderer.ts) i [especificació del pas 19](../completat/pas19-modes-optics.md).
- Recursos base: [`domain/resources/models.py`](../../backend/src/terralab3d/domain/resources/models.py) i [`layer_database.py`](../../backend/src/terralab3d/infrastructure/resources/layer_database.py), només per assegurar que GeoNames no s'ofereix com a descàrrega.

## Treball pendent

- [ ] Fixar versió/font, llicència, feature codes i pipeline reproducible de filtratge GeoNames.
- [ ] Definir format empaquetat, índex espacial, manifest/checksum i carregador read-only.
- [ ] Implementar components de taques artificials i assignació punt-dins/proximitat amb política multi-localitat.
- [ ] Implementar consulta de cims visible/AOI de vista, altura des del DEM i filtratge per camp visual / instrumental.
- [ ] Crear batch renderer de línies i labels amb escala, prioritat, agrupació i decluttering estable.
- [ ] Connectar càrrega automàtica a disponibilitat de topografia i toggle global de cims, sense entrada de descàrrega.
- [ ] Afegir atribució CC BY 4.0 a crèdits, manifest i documentació de dades.

## Flux tècnic

Asset empaquetat verificat → índex espacial per vista → assentaments + components artificials / cims + DEM → assignació i oclusió → candidats de label → decluttering → batches incrementals.

## Errors, cancel·lació i recursos

- Asset absent/incompatible desactiva el nomenclàtor amb diagnòstic; no ofereix descarregar-lo ni bloqueja el terreny.
- Canviar vista, topografia o mira cancel·la consultes obsoletes; només la revisió vigent actualitza labels.
- Índex, resultats i glyphs tenen caches acotades; geometries/labels descartats s'alliberen.
- Noms/UTF-8 i duplicats es preserven segons claus estables i política documentada.

## Proves

- Pipeline reproduïble, checksum, llicència, UTF-8, feature codes i asset corrupte/absent.
- Punt dins taca, proximitat, fora de llindar i dues localitats dins una mateixa taca.
- Cim dins/fora de camp, ocult pel DEM, mode global i canvis de zoom.
- Golden layouts de labels densos, determinisme, cancel·lació i pressupostos CPU/GPU.

## Criteri de sortida

Una zona amb pobles pròxims i una serralada mostra noms correctes i llegibles a partir de l'asset empaquetat, conserva separades semàntica/DEM/nomenclatura i no exposa GeoNames al gestor de descàrregues.

## Evidències

- [ ] Manifest reproducible i atribució CC BY 4.0 visible.
- [ ] Captura d'una taca amb una i amb dues localitats.
- [ ] Captures de cims en camp instrumental i mode global a diversos zooms.
- [ ] Confirmació automatitzada que el catàleg de descàrregues no conté GeoNames base.

## Fora d'abast

Límits administratius, rius, inferència de topònims, correcció de GeoNames i descàrregues regionals del nomenclàtor.

## Instrucció per a Codex

Empaqueta i versiona GeoNames com a dada base fora del gestor. Mantén punts nominals, taques artificials i geometria DEM com a fonts separades; implementa assignació i labels incrementals amb cancel·lació i atribució.
