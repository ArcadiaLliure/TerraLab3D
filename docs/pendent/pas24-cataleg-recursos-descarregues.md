# Pas 24 — Catàleg de recursos i descàrregues persistents

> Estat: **parcial**. Ja hi ha un catàleg, adquisidors, instal·lacions, un gestor central bàsic i UI; falten persistència completa de treballs, pausa/reanudació robusta i semàntica unificada.

## Estat actual verificat

- [x] Backend i frontend ja modelen recursos, adquisició, instal·lació i progrés bàsic.
- [x] Existeixen modal central, cards de recurs i base de dades de capes.
- [ ] Els treballs no cobreixen encara tot el cicle persistent, reanudable, verificat i recuperable després d'un reinici.

## Resultat funcional

L'usuari descobreix recursos des d'un catàleg únic, entén mida/llicència/variant, inicia o pausa descàrregues, les reprèn després de reiniciar, les cancel·la o elimina i mai veu un progrés falsament bloquejat.

## Dependències

- [Pas 8.6 — recursos del Sistema Solar](../completat/pas8.6.md).
- [Pas 12 — robustesa i recursos](../completat/pas12.md).

## Decisions tancades

- `ResourceDescriptor`, `LayerDescriptor` i `DownloadJob` són conceptes diferents, units per identificadors estables.
- El catàleg declara versions, variants, bundles, mida, checksum, llicència i mode `managed` o `external`.
- Estats mínims del treball: en cua, resolent, descarregant, pausant, pausat, verificant, instal·lant, completat, cancel·lat i error recuperable/terminal.
- Pausa i reanudació utilitzen HTTP Range quan l'origen ho admet; si no, la UI explica que cal reiniciar la transferència.
- La instal·lació és atòmica: temporal → verificació de mida/checksum → `rename` → registre. Un fitxer parcial mai compta com a disponible.
- En arrencar, els treballs interromputs es reconcilien una sola vegada i es presenta una decisió clara; no es creen descàrregues automàtiques.
- Progrés indeterminat, bytes, MB/s i temps estimat tenen semàntica separada.

## Codi existent a reutilitzar

- Backend: [`download_manager.py`](../../backend/src/terralab3d/infrastructure/resources/download_manager.py), [`acquirers.py`](../../backend/src/terralab3d/infrastructure/resources/acquirers.py), [`installation_repository.py`](../../backend/src/terralab3d/infrastructure/resources/installation_repository.py) i [`layer_database.py`](../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- Domini: [`resources/models.py`](../../backend/src/terralab3d/domain/resources/models.py) i [`resources/services.py`](../../backend/src/terralab3d/domain/resources/services.py).
- Frontend: [`ResourceManager.ts`](../../frontend/src/application/ResourceManager.ts), [`ResourceManagerModal.ts`](../../frontend/src/view/ui/modals/ResourceManagerModal.ts), [`ResourceBackedLayerRow.ts`](../../frontend/src/view/ui/components/ResourceBackedLayerRow.ts) i [`resource_manager_contracts.ts`](../../frontend/src/contracts/resource_manager_contracts.ts).
- Pont: [`ScienceBridge.ts`](../../frontend/src/bridge/ScienceBridge.ts) i [`bridge_messages.ts`](../../frontend/src/contracts/bridge_messages.ts).

## Treball pendent

- [ ] Formalitzar esquemes versionats de catàleg, instal·lació i treball, amb migracions i invariants.
- [ ] Persistir cues, temporals, offsets, ETag/Last-Modified, intents i últim error de manera transaccional.
- [ ] Implementar pausa, reanudació, cancel·lació cooperativa, reintents amb backoff i eliminació segura.
- [ ] Verificar mida/checksum i fer instal·lació atòmica; reconciliar temporals i registres després d'un crash.
- [ ] Representar variants, bundles, dependències, recursos externs i llicències a la UI.
- [ ] Mostrar progrés determinat o indeterminat, bytes, velocitat i ETA sense confondre transferència amb instal·lació.
- [ ] Unificar tots els punts d'entrada en el mateix gestor i emetre deltes, no snapshots globals continus.

## Flux tècnic

Catàleg versionat → selecció de variant/bundle → `DownloadJob` persistent → adquisidor cancel·lable → temporal reanudable → verificació → instal·lació atòmica → registre → delta de disponibilitat cap a la UI.

## Errors, cancel·lació i recursos

- Cancel·lar conserva o elimina el parcial segons una decisió explícita; eliminar no afecta fitxers externs sense confirmació específica.
- Canvis d'ETag, checksum incorrecte o espai insuficient produeixen error accionable i mai promocionen el temporal.
- Reiniciar recupera una cua coherent i no duplica treballs pel mateix recurs/variant.
- Streams, fitxers temporals, tasks i subscripcions es tanquen en tots els camins.

## Proves

- Servidor amb/sense Range, tall de xarxa, ETag canviat, checksum erroni, cancel·lació i reintent.
- Reinici durant descàrrega, verificació i instal·lació; reconciliació de temporals orfes.
- Bundles, variants, dependències, recursos externs i eliminació.
- Curses de comandes i monotonia de bytes/progrés.

## Criteri de sortida

Qualsevol recurs gestionat passa per un únic cicle persistent i auditable; les transferències es poden recuperar i la disponibilitat només canvia després d'una verificació i instal·lació atòmiques.

## Evidències

- [ ] Matriu automatitzada de recuperació i cancel·lació.
- [ ] Vídeo de pausa, reinici de l'aplicació i reanudació.
- [ ] Registre de checksum fallit sense recurs disponible.
- [ ] Captures de variants, bundles, llicència i progrés indeterminat.

## Fora d'abast

Descobriment específic de DEM, UX de capes Cel/Terra i dades base que s'empaqueten amb l'aplicació.

## Instrucció per a Codex

Evoluciona el gestor existent; no en creïs un de paral·lel. Separa recurs, capa i treball, conserva temporals verificables i demostra recuperació després de reinici abans de marcar el pas complet.
