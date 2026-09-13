# Pas 32 — Motor general d'efemèrides

> Estat: **parcial**. SPICE, separacions angulars i cerca d'eclipsis ja funcionen; falta generalitzar els càlculs i resultats a més tipus d'esdeveniment.

## Estat actual verificat

- [x] El pas 9 implementa posicions SPICE, mostreig/refinament temporal i resultats d'eclipsi.
- [x] Existeixen models, serveis i ports d'esdeveniments astronòmics.
- [ ] No hi ha motor únic per conjuncions, mínims de separació i ocultacions entre objectes suportats.

## Resultat funcional

L'usuari o qualsevol consumidor demana efemèrides per interval i rep esdeveniments tipats, refinats i ordenats —conjuncions, mínims angulars i ocultacions— amb instant, actors, geometria, qualitat i procedència.

## Dependències

- [Pas 9 — eclipsis SPICE](../completat/pas9.md).
- [Pas 22 — contracte observable](pas22-trajectories-visibilitat.md).

## Decisions tancades

- Es calculen parelles dinàmic↔dinàmic i dinàmic↔estàtic seleccionat; no es generen combinacions estàtic↔estàtic sense canvi temporal útil.
- El motor separa generació de candidats, refinament d'extrems/arrels, classificació i presentació.
- Tots els esdeveniments exposen instant/interval UTC, objectes, separació o magnitud geomètrica, incertesa/resolució, mètode i versions de dades.
- SPICE continua sent la font de geometria dinàmica quan aplica; els observables estàtics usen els catàlegs existents.
- Les consultes són acotades per tipus, objectes, interval i llindars; mai fan productes cartesians globals implícits.

## Codi existent a reutilitzar

- Aplicació/ports: [`astronomical_events.py`](../../backend/src/terralab3d/application/astronomical_events.py) i [`ports/astronomical_events.py`](../../backend/src/terralab3d/application/ports/astronomical_events.py).
- Eclipsis: [`eclipses/models.py`](../../backend/src/terralab3d/domain/eclipses/models.py), [`eclipses/calculations.py`](../../backend/src/terralab3d/domain/eclipses/calculations.py) i [`eclipses/services.py`](../../backend/src/terralab3d/domain/eclipses/services.py).
- Efemèride: [`spice_adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/ephemeris/spice_adapter.py).
- Contractes frontend: [`astronomical_event_contracts.ts`](../../frontend/src/contracts/astronomical_event_contracts.ts).

## Treball pendent

- [ ] Definir jerarquia/union d'esdeveniments, criteris de consulta i errors de validació.
- [ ] Extreure del pas 9 primitives comunes de mostreig, bracketing, refinament i separació sense regressar eclipsis.
- [ ] Implementar conjunció i mínim de separació per parelles admeses.
- [ ] Implementar candidat i validació d'ocultació amb radis aparents i observador explícit.
- [ ] Integrar adaptadors observables estàtics i dinàmics amb caches/versionat.
- [ ] Exposar API cancel·lable, paginada/streaming i contractes serialitzables estables.

## Flux tècnic

Consulta validada → resolució d'actors → generació de candidats mostrejats → refinament numèric → classificació geomètrica → deduplicació/ordenació → resultats versionats.

## Errors, cancel·lació i recursos

- Intervals o combinacions no suportats fallen abans d'iniciar càlcul.
- La cancel·lació es comprova entre lots i iteracions de refinament; resultats d'una revisió obsoleta no es publiquen.
- Errors/absència de kernel identifiquen l'actor i recurs afectats, sense convertir-se en “cap esdeveniment”.
- Caches de posicions i mostres tenen límits per interval, observador i versions.

## Proves

- Golden fixtures per conjunció, mínim i ocultació, incloent no-esdeveniment.
- Vores d'interval, esdeveniment tangencial, múltiples mínims, wrap angular i precisió del refinament.
- Compatibilitat dels resultats d'eclipsi del pas 9.
- Cancel·lació, paginació, cache i absència de productes cartesians accidentals.

## Criteri de sortida

Una API comuna retorna de manera reproduïble els tipus suportats, manté la precisió i proves del pas 9 i pot ser consumida sense conèixer SPICE ni el procediment numèric intern.

## Evidències

- [ ] Taula de golden fixtures amb font i tolerància.
- [ ] Proves de regressió completes del pas 9.
- [ ] Traça d'una consulta mixta, paginada i cancel·lada.
- [ ] Mètriques de temps/cache per interval i nombre d'actors.

## Fora d'abast

La UI multipestanya, miniatures, la pestanya específica d'eclipsis i esdeveniments especialitzats per planeta/Lluna.

## Instrucció per a Codex

Generalitza les primitives del pas 9 en un motor tipat i cancel·lable, sense reescriure SPICE ni crear una API per tipus. Limita explícitament actors i intervals i conserva les proves d'eclipsis com a regressió.
