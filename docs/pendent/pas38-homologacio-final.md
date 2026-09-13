# Pas 38 — Homologació final, recuperació i rendiment

> Estat: **pendent**. És el tancament verificable de tots els passos executables anteriors (1–17 i 19–37), no un contenidor per afegir funcionalitats noves.

## Estat actual verificat

- [x] Els passos 1–16 tenen especificació completada i evidències històriques.
- [x] Hi ha escena persistent, pont científic, registre de recursos, workers i lifecycle reutilitzables.
- [ ] Falta una matriu única de paritat, pressupostos mesurats, recuperació integral i auditoria de totes les transicions llargues.

## Resultat funcional

TerraLab3D cobreix el pla acordat amb evidència científica, funcional i visual; compleix pressupostos, es recupera de fallades, tanca recursos netament, no depèn de TerraLab en execució i manté interactives les transicions llargues.

## Dependències

- Tots els passos [1–16 completats](../README.md#passos-completats) i [17–37 pendents](../README.md#passos-pendents).

## Decisions tancades

- La matriu avalua cada capacitat amb casos, toleràncies, evidència i propietari; una carpeta o contracte buit no compta com a implementació.
- Comparació visual significa semàntica, llegibilitat i interacció equivalents, no píxels idèntics a TerraLab.
- Pressupostos mínims: frame P50/P95, CPU, GPU, RSS, bytes/freqüència de bridge, draw calls, temps de càrrega freda i recuperació.
- Pan, zoom, viatge, descàrrega, càlcul o refinament llarg mantenen l'escena útil i interactiva amb progrés/cancel·lació quan pertoqui; no es tapen amb pantalles decoratives.
- `start`, `suspend`, `resume`, `restart` i `close` són idempotents i tota pèrdua de context o reconnexió reconstrueix la vista des d'un snapshot autoritatiu.
- S'eliminen mocks, flags, rutes legacy i dependències executives de TerraLab només amb proves substitutes i recuperació clara.
- Contractes, esquemes, formats, procedència i llicències queden congelats/documentats per a la versió homologada.

## Codi existent a reutilitzar

- Escena i recursos: [`ThreeSceneHostImpl.ts`](../../frontend/src/view/three/ThreeSceneHostImpl.ts), [`RenderLoopImpl.ts`](../../frontend/src/view/three/RenderLoopImpl.ts) i [`ResourceRegistry.ts`](../../frontend/src/view/three/ResourceRegistry.ts).
- Pont: [`ScienceBridge.ts`](../../frontend/src/bridge/ScienceBridge.ts), [`WebSocketBridge.ts`](../../frontend/src/bridge/WebSocketBridge.ts) i [`bridge_messages.ts`](../../frontend/src/contracts/bridge_messages.ts).
- Lifecycle/workers: [`use_cases/lifecycle.py`](../../backend/src/terralab3d/application/use_cases/lifecycle.py) i [`workers/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/workers/adapter.py).
- Normes: [`normes_arquitectura.md`](../normes_arquitectura.md) i [`inventari-funcional.md`](../inventari-funcional.md).
- Oracle funcional fixat: [TerraLab al commit auditat](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d).

## Treball pendent

- [ ] Construir i executar la matriu dels passos 1–17 i 19–37 amb escenaris, dades, toleràncies, proves i evidència per fila.
- [ ] Comparar ubicacions, dates, càmeres, capes, datasets, instruments i fluxos equivalents amb l'oracle fixat.
- [ ] Fixar pressupostos i perfilar pan/zoom, ticks temporals, salts, Gaia, DEM, superfície, scope, planificador i previews.
- [ ] Eliminar reconstruccions, còpies, transferències i allocations que superin pressupost, sense canviar contractes científics.
- [ ] Provar i completar context loss WebGL, desconnexió/reconnexió del bridge, restart frontend i resync autoritatiu.
- [ ] Fer idempotent el lifecycle i verificar disposició GPU, workers, fitxers, sockets, timers i handles.
- [ ] Auditar cada transició llarga per interactivitat, progrés, cancel·lació, reducció de moviment i absència de pantalles decoratives.
- [ ] Eliminar codi temporal/legacy només després de demostrar el reemplaçament i actualitzar documentació, crèdits, dades i troubleshooting.
- [ ] Congelar versions i registrar diferències intencionals amb acceptació explícita.

## Flux tècnic

Matriu versionada → execució automatitzada/manual → mètriques i evidències → desviació reproduïble → correcció a la vertical propietària → regressió completa → informe d'homologació i snapshot de versions.

## Errors, cancel·lació i recursos

- Una fila sense evidència o una mètrica sense pressupost és fallida, no “no aplicable”, tret que l'exclusió estigui justificada.
- Les proves de fallada injecten context loss, desconnexió, resposta tardana, recurs corrupte i shutdown durant treball actiu.
- El tancament verifica zero workers/handles/subscripcions no autoritzats i disposició de recursos GPU.
- La recuperació no reutilitza revisions antigues ni inicia descàrregues o càlculs no confirmats.

## Proves

- Suite completa backend/frontend/arquitectura, golden científics, captures semàntiques i recorreguts manuals principals.
- Benchmarks repetibles P50/P95 de CPU/GPU/RSS/bridge/draw calls/càrrega.
- Context loss, restart, reconnexió, resync, suspend/resume i shutdown sota càrrega.
- Auditoria de transicions amb pan/zoom actius, cancel·lació i `prefers-reduced-motion`.
- Instal·lació neta sense checkout ni ruta local de TerraLab.

## Criteri de sortida

No queda cap fila del pla sense evidència ni desviació sense decisió; ciència i UX compleixen toleràncies/pressupostos, totes les recuperacions són deterministes i una instal·lació neta arrenca, opera i tanca sense TerraLab.

## Evidències

- [ ] Informe final de paritat funcional i científica dels passos 1–17 i 19–37.
- [ ] Quadre de pressupostos i resultats P50/P95 reproduïbles.
- [ ] Captures/vídeos dels fluxos principals i de transicions interactives.
- [ ] Informe de GPU, RSS, bridge, còpies, workers i handles.
- [ ] Proves de context loss, desconnexió, restart, resync i shutdown.
- [ ] Llista zero de capacitats sense propietari/evidència.

## Fora d'abast

Noves capacitats posteriors al pas 37 i la navegació espacial física descrita a [navegació lliure pel Sistema Solar](../idees-per-madurar/navegacio-lliure-sistema-solar.md).

## Instrucció per a Codex

Tracta aquest pas com una homologació, no com un calaix de noves features. Executa la matriu dels passos 1–17 i 19–37, corregeix cada desviació a la seva vertical, prova recuperació i transicions interactives i no eliminis cap fallback abans de demostrar el reemplaçament.
