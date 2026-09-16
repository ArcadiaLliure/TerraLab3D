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
| Òptica i observació instrumental | [`ObservationModeController.ts`](../frontend/src/application/ObservationModeController.ts), [`observation_coordinator.py`](../backend/src/terralab3d/application/observation_coordinator.py) i [Pas 19](completat/pas19-modes-optics.md) | Modes `eye/camera/telescope`, overlays retinguts, fotometria V1, perfils persistents, GoTo i Gaia profunda cancel·lable. |
| Eines de mesura esfèrica | [Pas 21](completat/pas21-eines-mesura.md) | Quatre eines esfèriques editables (regla, quadrat, rectangle, cercle), historial undo/redo, batches retinguts, labels projectats i persistència versionada. |
| Trajectòries i visibilitat sobre l'horitzó real | [Pas 22](completat/pas22-trajectories-visibilitat.md) | Trajectòries temporals d'objectes observables (cossos solars, satèl·lits, estrelles, cel profund, coordenades), classificació contra relleu real (DEM) i astronòmic, creuaments refinats, marcadors temporals, homologació visual en navegador i evidències. |

## Capacitats parcials

| Capacitat | Implementació observable actual | Què no s'ha de donar per fet | Pla |
|---|---|---|---|
| Superfície categòrica | [`land_cover_coordinator.py`](../backend/src/terralab3d/application/land_cover_coordinator.py), adaptadors raster i [`LandCoverTextureManager.ts`](../frontend/src/view/three/terrain/LandCoverTextureManager.ts) | El refinament visual/semàntic avançat queda consolidat al Pas 29. | [17](completat/pas17-superficie-progressiva.md), [29](pendent/pas29-superficie-semantica.md) |
|---|---|
| TLST, ontologia i arbre de refinament semàntic | [Pas 29](pendent/pas29-superficie-semantica.md) |
| Plate solving i comparador registrat | [Pas 30](pendent/pas30-plate-solving.md) |
| Recomanacions i planificador temporal | [Pas 31](pendent/pas31-millor-nit-planificador.md) |
| GeoNames empaquetat, assignació i labels | [Pas 37](pendent/pas37-geonames-empaquetat.md) |
| Homologació integral i auditoria de transicions | [Pas 38](pendent/pas38-homologacio-final.md) |

## Regla d'actualització

Quan es completa un pas, aquest inventari s'ha d'actualitzar amb l'enllaç a la implementació observable i a les proves. No es promociona una fila perquè s'hagin creat carpetes, protocols, DTOs o renderers de només interfície.
