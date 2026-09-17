# Pas 38 — Homologació final, recuperació i rendiment

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** homologació final, recuperació i rendiment, integració observable i persistència associada.

## Descripció funcional

TerraLab3D cobreix el pla acordat amb evidència científica, funcional i visual; compleix pressupostos, es recupera de fallades, tanca recursos netament, no depèn de TerraLab en execució i manté interactives les transicions llargues.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- La matriu avalua cada capacitat amb casos, toleràncies, evidència i propietari; una carpeta o contracte buit no compta com a implementació.
- Comparació visual significa semàntica, llegibilitat i interacció equivalents, no píxels idèntics a TerraLab.
- Pressupostos mínims: frame P50/P95, CPU, GPU, RSS, bytes/freqüència de bridge, draw calls, temps de càrrega freda i recuperació.
- Pan, zoom, viatge, descàrrega, càlcul o refinament llarg mantenen l'escena útil i interactiva amb progrés/cancel·lació quan pertoqui; no es tapen amb pantalles decoratives.
- `start`, `suspend`, `resume`, `restart` i `close` són idempotents i tota pèrdua de context o reconnexió reconstrueix la vista des d'un snapshot autoritatiu.
- S'eliminen mocks, flags, rutes legacy i dependències executives de TerraLab només amb proves substitutes i recuperació clara.
- Contractes, esquemes, formats, procedència i llicències queden congelats/documentats per a la versió homologada.

## Objectiu

Completar la vertical de «homologació final, recuperació i rendiment» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](../completat/pas1.md)
- [Pas 2 — Ubicació geogràfica de l'observador i orientació local](../completat/pas2.md)
- [Pas 3 — Rellotge de simulació, temps sideral i moviment visible](../completat/pas3.md)
- [Pas 3.5 — Càmera translacional, mode caminar i mode avió](../completat/pas3.5.md)
- [Pas 4 — Grid celeste, brúixola, etiquetes i HUD](../completat/pas4.md)
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](../completat/pas5.md)
- [Pas 6 — Picking estel·lar precís](../completat/pas6.md)
- [Pas 7 — Cel, atmosfera, contaminació lumínica i Bortle](../completat/pas7.md)
- [Pas 8 — Sol, Lluna i planetes amb posicions i aparença reals](../completat/pas8.md)
- [Pas 8.5 — Superfície lunar LRO/LOLA, orientació i libració](../completat/pas8.5.md)
- [Pas 8.6 — Planetes, anells i satèl·lits naturals](../completat/pas8.6.md)
- [Pas 8.7 — Il·luminació física de l'escena](../completat/pas8.7.md)
- [Pas 9 — Eclipsis, ocultacions, separacions i trajectòries](../completat/pas9.md)
- [Pas 10 — Via Làctia i pols galàctica Planck](../completat/pas10.md)
- [Pas 11 — Cel profund NGC/IC](../completat/pas11.md)
- [Pas 12 — Cerca astronòmica, focus i seguiment](../completat/pas12.md)
- [Pas 13 — Picking real, hover, selecció i inspecció](../completat/pas13.md)
- [Pas 14 — Traces circumpolars i exposició temporal](../completat/pas14.md)
- [Pas 15 — Elevació real, perfil d'horitzó i oclusió](../completat/pas15.md)
- [Pas 16 — Terreny 3D retingut, tiles, LOD i picking](../completat/pas16.md)
- [Pas 17 — Superfície categòrica, estils i refinament visual](../completat/pas17-superficie-progressiva.md)
- [Pas 19 — Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope](../completat/pas19-modes-optics.md)
- [Pas 21 — Eines de mesura esfèrica](../completat/pas21-eines-mesura.md)
- [Pas 22 — Trajectòries i visibilitat sobre l'horitzó real](../completat/pas22-trajectories-visibilitat.md)
- [Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari](../completat/pas23-constellacions.md)
- [Pas 24 — Catàleg de recursos i descàrregues persistents](pas24-cataleg-recursos-descarregues.md)
- [Pas 25 — Gestor de capes Cel/Terra](pas25-gestor-capes.md)
- [Pas 26 — Vista de recursos del Sistema Solar](pas26-recursos-sistema-solar.md)
- [Pas 27 — Carta de recursos d'espai profund](pas27-recursos-espai-profund.md)
- [Pas 28 — Descobriment de DEM multiproveïdor](pas28-dem-multiproveidor.md)
- [Pas 29 — Superfície semàntica, TLST i refinament](pas29-superficie-semantica.md)
- [Pas 30 — Plate solving i comparador foto/simulació](pas30-plate-solving.md)
- [Pas 31 — “El millor d'aquesta nit” i planificador](pas31-millor-nit-planificador.md)
- [Pas 32 — Motor general d'efemèrides](pas32-motor-efemerides.md)
- [Pas 33 — Cercador d'objectes i efemèrides](pas33-cercador-objectes-efemerides.md)
- [Pas 34 — Miniatures i animacions d'efemèrides](pas34-previsualitzacions-efemerides.md)
- [Pas 35 — Pestanya d'eclipsis](pas35-pestanya-eclipsis.md)
- [Pas 36 — Esdeveniments propis de planetes i Lluna](pas36-esdeveniments-objectes.md)
- [Pas 37 — Nomenclàtor GeoNames empaquetat](pas37-geonames-empaquetat.md)

**En depenen:**
- Cap pas posterior directe.

## Codi existent a reutilitzar

- **Repositori actual:** - Escena i recursos: [`ThreeSceneHostImpl.ts`](../../../frontend/src/view/three/ThreeSceneHostImpl.ts), [`RenderLoopImpl.ts`](../../../frontend/src/view/three/RenderLoopImpl.ts) i [`ResourceRegistry.ts`](../../../frontend/src/view/three/ResourceRegistry.ts).
- Pont: [`ScienceBridge.ts`](../../../frontend/src/bridge/ScienceBridge.ts), [`WebSocketBridge.ts`](../../../frontend/src/bridge/WebSocketBridge.ts) i [`bridge_messages.ts`](../../../frontend/src/contracts/bridge_messages.ts).
- Lifecycle/workers: [`use_cases/lifecycle.py`](../../../backend/src/terralab3d/application/use_cases/lifecycle.py) i [`workers/adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/workers/adapter.py).
- Normes: [`normes_arquitectura.md`](../../normes-arquitectura.md) i [`inventari-funcional.md`](../../inventari-funcional.md).
- Oracle funcional fixat: [TerraLab al commit auditat](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Matriu versionada → execució automatitzada/manual → mètriques i evidències → desviació reproduïble → correcció a la vertical propietària → regressió completa → informe d'homologació i snapshot de versions.

## Errors, cancel·lació i recursos

- Una fila sense evidència o una mètrica sense pressupost és fallida, no “no aplicable”, tret que l'exclusió estigui justificada.
- Les proves de fallada injecten context loss, desconnexió, resposta tardana, recurs corrupte i shutdown durant treball actiu.
- El tancament verifica zero workers/handles/subscripcions no autoritzats i disposició de recursos GPU.
- La recuperació no reutilitza revisions antigues ni inicia descàrregues o càlculs no confirmats.

## Tasques

- [x] Els passos 1–16 tenen especificació completada i evidències històriques.
- [x] Hi ha escena persistent, pont científic, registre de recursos, workers i lifecycle reutilitzables.
- [ ] Falta una matriu única de paritat, pressupostos mesurats, recuperació integral i auditoria de totes les transicions llargues.
- [ ] Construir i executar la matriu dels passos 1–17 i 19–37 amb escenaris, dades, toleràncies, proves i evidència per fila.
- [ ] Comparar ubicacions, dates, càmeres, capes, datasets, instruments i fluxos equivalents amb l'oracle fixat.
- [ ] Fixar pressupostos i perfilar pan/zoom, ticks temporals, salts, Gaia, DEM, superfície, scope, planificador i previews.
- [ ] Eliminar reconstruccions, còpies, transferències i allocations que superin pressupost, sense canviar contractes científics.
- [ ] Provar i completar context loss WebGL, desconnexió/reconnexió del bridge, restart frontend i resync autoritatiu.
- [ ] Fer idempotent el lifecycle i verificar disposició GPU, workers, fitxers, sockets, timers i handles.
- [ ] Auditar cada transició llarga per interactivitat, progrés, cancel·lació, reducció de moviment i absència de pantalles decoratives.
- [ ] Eliminar codi temporal/legacy només després de demostrar el reemplaçament i actualitzar documentació, crèdits, dades i troubleshooting.
- [ ] Congelar versions i registrar diferències intencionals amb acceptació explícita.

## Criteri de sortida

No queda cap fila del pla sense evidència ni desviació sense decisió; ciència i UX compleixen toleràncies/pressupostos, totes les recuperacions són deterministes i una instal·lació neta arrenca, opera i tanca sense TerraLab.

## Proves i evidències obligatòries

- [ ] Suite completa backend/frontend/arquitectura, golden científics, captures semàntiques i recorreguts manuals principals.
- [ ] Benchmarks repetibles P50/P95 de CPU/GPU/RSS/bridge/draw calls/càrrega.
- [ ] Context loss, restart, reconnexió, resync, suspend/resume i shutdown sota càrrega.
- [ ] Auditoria de transicions amb pan/zoom actius, cancel·lació i `prefers-reduced-motion`.
- [ ] Instal·lació neta sense checkout ni ruta local de TerraLab.
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

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
