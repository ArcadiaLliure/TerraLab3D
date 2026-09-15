# Inventari funcional verificat

Aquest inventari separa tres realitats que abans es barrejaven:

- **observable**: la capacitat està connectada a l'entrypoint real, produeix comportament visible i té proves/evidències;
- **parcial**: existeix una vertical útil, però no cobreix encara el resultat funcional consolidat;
- **esquelet**: hi ha models, càlculs, ports o interfícies de renderer, però no una experiència executable de punta a punta.

La font de veritat de l'ordre i del tancament és el [pla de millores](README.md). L'existència d'un directori sota [`domain/`](../backend/src/terralab3d/domain/) no certifica implementació.

## Capacitats observables

| Capacitat | Evidència principal | Abast verificat |
|---|---|---|
| Entorn, càmera, bridge, observador i temps | [Passos 1–4](README.md#passos-completats) | Entrada real, escena, càmera, ubicació, temps i HUD. |
| Gaia, picking i selecció | [Passos 5–6 i 12–13](README.md#passos-completats) | Catàleg real/fallback declarat, buffers retinguts, cerca, picking i inspecció. |
| Cel, atmosfera i contaminació lumínica | [Pas 7](completat/pas7.md) | Dia/nit/crepuscle, Bortle i magnitud límit; meteorologia real queda fora. |
| Sistema Solar i il·luminació | [Passos 8, 8.5, 8.6 i 8.7](README.md#passos-completats) | Posicions/aparença, Lluna, actius planetaris i il·luminació física. |
| Eclipsis i trajectòries solars | [Pas 9](completat/pas9.md) | Cerca SPICE, separacions i trajectòries aparents de cossos suportats. |
| Via Làctia i cel profund | [Passos 10–11](README.md#passos-completats) | Planck/galàctic i catàleg OpenNGC renderitzats. |
| Traces circumpolars | [Pas 14](completat/pas14.md) | Exposició temporal i renderer incremental. |
| Horitzó i terreny | [Passos 15–16](README.md#passos-completats) | DEM local, perfil/oclusió, malla retinguda, tiles, LOD i picking. |

## Capacitats parcials

| Capacitat | Implementació observable actual | Què no s'ha de donar per fet | Pla |
|---|---|---|---|
| Superfície categòrica | [`land_cover_coordinator.py`](../backend/src/terralab3d/application/land_cover_coordinator.py), adaptadors raster i [`LandCoverTextureManager.ts`](../frontend/src/view/three/terrain/LandCoverTextureManager.ts) | Estils de producte i refinament visual/semàntic complet. | [17](pendent/pas17-superficie-progressiva.md), [29](pendent/pas29-superficie-semantica.md) |
| Trajectòries i visibilitat | [`apparent_trajectory.py`](../backend/src/terralab3d/application/apparent_trajectory.py) i horitzó del pas 15 | Contracte observable general i creuaments de l'horitzó real per totes les famílies. | [22](pendent/pas22-trajectories-visibilitat.md) |
| Recursos i descàrregues | [`download_manager.py`](../backend/src/terralab3d/infrastructure/resources/download_manager.py), instal·lacions, catàleg i [`ResourceManager.ts`](../frontend/src/application/ResourceManager.ts) | Reanudació/persistència integral, verificació atòmica i recuperació completa. | [24](pendent/pas24-cataleg-recursos-descarregues.md) |
| Vistes de recursos | Catàlegs, renderers del Sistema Solar/espai profund i modal genèric | Navegadors jeràrquic solar i carta all-sky especialitzada. | [26](pendent/pas26-recursos-sistema-solar.md), [27](pendent/pas27-recursos-espai-profund.md) |
| DEM | [`elevation_coordinator.py`](../backend/src/terralab3d/application/elevation_coordinator.py) i [`dem/adapter.py`](../backend/src/terralab3d/infrastructure/adapters/dem/adapter.py) | Descobriment multiproveïdor, comparació de llicències i instal·lació per AOI. | [28](pendent/pas28-dem-multiproveidor.md) |
| Efemèrides i eclipsis | Motor del pas 9 i contractes d'esdeveniments | Motor general, cercador multipestanya, previews, tab d'eclipsis i fites per cos. | [32](pendent/pas32-motor-efemerides.md)–[36](pendent/pas36-esdeveniments-objectes.md) |

## Esquelets sense vertical completa

| Capacitat | Fronteres ja presents | Implementació que falta | Pla |
|---|---|---|---|
| Meteorologia | [`domain/climate/`](../backend/src/terralab3d/domain/climate/) i [`WeatherLayerRenderer.ts`](../frontend/src/view/three/layers/WeatherLayerRenderer.ts) | Abast de producte, autoritat temporal, proveïdor, fallback, efectes, UI i lifecycle. | [Dossier per madurar](idees-per-madurar/meteorologia.md) |
| Òptica i observació instrumental | [`domain/optics/`](../backend/src/terralab3d/domain/optics/) i [`ScopeLayerRenderer.ts`](../frontend/src/view/three/layers/ScopeLayerRenderer.ts) | Coordinació, modes, geometria/HUD, Gaia cancel·lable, UI i persistència. | [19](pendent/pas19-modes-optics.md) |
| Simulació fotogràfica | [`domain/imaging/`](../backend/src/terralab3d/domain/imaging/) i [`ImagingPreviewLayerRenderer.ts`](../frontend/src/view/three/layers/ImagingPreviewLayerRenderer.ts) | Senyal/soroll integrats, controls, tracking, traces i exportació completa (integrat a l'observació instrumental de l'antic Pas 20). | [19](pendent/pas19-modes-optics.md) |
| Mesures | [`domain/measurements/`](../backend/src/terralab3d/domain/measurements/) i [`MeasurementLayerRenderer.ts`](../frontend/src/view/three/layers/MeasurementLayerRenderer.ts) | Gestos, càlculs finals, edició, historial, batches i persistència. | [21](pendent/pas21-eines-mesura.md) |
| Constel·lacions | [`domain/constellations/`](../backend/src/terralab3d/domain/constellations/) i [`ConstellationLayerRenderer.ts`](../frontend/src/view/three/layers/ConstellationLayerRenderer.ts) | Catàleg oficial, document d'usuari, observable, edició, snapping i persistència. | [23](pendent/pas23-constellacions.md) |
| Capes | [`domain/layers/`](../backend/src/terralab3d/domain/layers/) i casos d'ús inicials | Contracte Cel/Terra, AOI, separació d'estats, UI comuna i preferències. | [25](pendent/pas25-gestor-capes.md) |

## Capacitats especificades sense implementació operativa

| Capacitat | Pla |
|---|---|
| TLST, ontologia i arbre de refinament semàntic | [Pas 29](pendent/pas29-superficie-semantica.md) |
| Plate solving i comparador registrat | [Pas 30](pendent/pas30-plate-solving.md) |
| Recomanacions i planificador temporal | [Pas 31](pendent/pas31-millor-nit-planificador.md) |
| GeoNames empaquetat, assignació i labels | [Pas 37](pendent/pas37-geonames-empaquetat.md) |
| Homologació integral i auditoria de transicions | [Pas 38](pendent/pas38-homologacio-final.md) |

## Regla d'actualització

Quan es completa un pas, aquest inventari s'ha d'actualitzar amb l'enllaç a la implementació observable i a les proves. No es promociona una fila perquè s'hagin creat carpetes, protocols, DTOs o renderers de només interfície.
