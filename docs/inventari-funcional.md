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
| Cel, atmosfera i contaminació lumínica | [Pas 7](tasques/completat/pas7.md) | Dia/nit/crepuscle, Bortle i magnitud límit; meteorologia real queda fora. |
| Sistema Solar i il·luminació | [Passos 8, 8.5, 8.6 i 8.7](README.md#passos-completats) | Posicions/aparença, Lluna, actius planetaris i il·luminació física. |
| Eclipsis i trajectòries solars | [Pas 9](tasques/completat/pas9.md) | Cerca SPICE, separacions i trajectòries aparents de cossos suportats. |
| Via Làctia i cel profund | [Passos 10–11](README.md#passos-completats) | Planck/galàctic i catàleg OpenNGC renderitzats. |
| Traces circumpolars | [Pas 14](tasques/completat/pas14.md) | Exposició temporal i renderer incremental. |
| Horitzó i terreny | [Passos 15–16](README.md#passos-completats) | DEM local, perfil/oclusió, malla retinguda, tiles, LOD i picking. |
| Òptica i observació instrumental | [`ObservationModeController.ts`](../frontend/src/application/ObservationModeController.ts), [`observation_coordinator.py`](../backend/src/terralab3d/application/observation_coordinator.py) i [Pas 19](tasques/completat/pas19-modes-optics.md) | Modes `eye/camera/telescope`, overlays retinguts, fotometria V1, perfils persistents, GoTo i Gaia profunda cancel·lable. |
| Eines de mesura esfèrica | [Pas 21](tasques/completat/pas21-eines-mesura.md) | Quatre eines esfèriques editables (regla, quadrat, rectangle, cercle), historial undo/redo, batches retinguts, labels projectats i persistència versionada. |
| Trajectòries i visibilitat sobre l'horitzó real | [Pas 22](tasques/completat/pas22-trajectories-visibilitat.md) | Trajectòries temporals d'objectes observables (cossos solars, satèl·lits, estrelles, cel profund, coordenades), classificació contra relleu real (DEM) i astronòmic, creuaments refinats, marcadors temporals, homologació visual en navegador i evidències. |

## Capacitats parcials

| Capacitat | Implementació observable actual | Què no s'ha de donar per fet | Pla |
|---|---|---|---|
| Superfície categòrica | [`land_cover_coordinator.py`](../backend/src/terralab3d/application/land_cover_coordinator.py), adaptadors raster i [`LandCoverTextureManager.ts`](../frontend/src/view/three/terrain/LandCoverTextureManager.ts) | El refinament visual/semàntic avançat queda consolidat al Pas 29. | [17](tasques/completat/pas17-superficie-progressiva.md), [29](tasques/pendent/pas29-superficie-semantica.md) |
| Catàleg de recursos i descàrregues | Catàleg de manifests i descàrregues bàsiques | Gestor de capes integrat i selecció interactiva d'AOI | [24](tasques/pendent/pas24-cataleg-recursos-descarregues.md) |
| Recursos del Sistema Solar | Posicions i textures planetàries bàsiques | Gestor unificat de recursos i textures d'alta resolució | [26](tasques/pendent/pas26-recursos-sistema-solar.md) |
| Recursos d'espai profund | Catàleg OpenNGC i pols Planck carregats | Carta d'espai profund interactiva i descàrrega progressiva | [27](tasques/pendent/pas27-recursos-espai-profund.md) |
| DEM multiproveïdor | Carregador DEM local i tiling retingut | Descobriment automàtic de proveïdors i mosaic dinàmic | [28](tasques/pendent/pas28-dem-multiproveidor.md) |
| Superfície semàntica i TLST | Superfície categòrica base (Pas 17) | TLST, ontologia i arbre de refinament semàntic | [29](tasques/pendent/pas29-superficie-semantica.md) |
| Motor general d'efemèrides | Càlculs puntuals SPICE i DE440 | Motor generalitzat per a qualsevol cos i rang temporal | [32](tasques/pendent/pas32-motor-efemerides.md) |
| Cercador d'objectes i efemèrides | Cerca bàsica d'estrelles i cel profund | Cercador multipestanya amb efemèrides integrades | [33](tasques/pendent/pas33-cercador-objectes-efemerides.md) |
| Pestanya d'eclipsis | Cerca d'eclipsis puntuals SPICE | Pestanya interactiva d'eclipsis amb circumstàncies locals | [35](tasques/pendent/pas35-pestanya-eclipsis.md) |
| Esdeveniments de planetes i Lluna | Esdeveniments bàsics solars | Esdeveniments propis per cos amb visualització | [36](tasques/pendent/pas36-esdeveniments-objectes.md) |

## Capacitats en esquelet o pendents

| Capacitat | Estat actual | Pla |
|---|---|---|
| Gestor de capes Cel/Terra | Pendent d'implementació | [Pas 25](tasques/pendent/pas25-gestor-capes.md) |
| Plate solving i comparador foto/simulació | Pendent d'implementació | [Pas 30](tasques/pendent/pas30-plate-solving.md) |
| “El millor d'aquesta nit” i planificador | Pendent d'implementació | [Pas 31](tasques/pendent/pas31-millor-nit-planificador.md) |
| Miniatures i animacions d'efemèrides | Pendent d'implementació | [Pas 34](tasques/pendent/pas34-previsualitzacions-efemerides.md) |
| Nomenclàtor GeoNames empaquetat | Pendent d'implementació | [Pas 37](tasques/pendent/pas37-geonames-empaquetat.md) |
| Homologació final, recuperació i rendiment | Pendent d'implementació | [Pas 38](tasques/pendent/pas38-homologacio-final.md) |

## Regla d'actualització

Quan es completa un pas, aquest inventari s'ha d'actualitzar amb l'enllaç a la implementació observable i a les proves. No es promociona una fila perquè s'hagin creat carpetes, protocols, DTOs o renderers de només interfície.
