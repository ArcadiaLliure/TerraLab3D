# Pas 33 — Cercador d'objectes i efemèrides

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** cercador d'objectes i efemèrides, integració observable i persistència associada.

## Descripció funcional

L'usuari obre un únic cercador, alterna entre Objectes i Efemèrides, filtra tipus i interval, inspecciona resultats tipats i pot centrar un objecte, anar a l'instant d'un esdeveniment o afegir-lo al pla.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- El panell conserva una sola caixa/entrada i dues pestanyes de primer nivell: Objectes i Efemèrides; Eclipsis s'afegirà com a extensió al pas 35.
- Canviar de pestanya conserva la consulta compatible, però cada pestanya manté filtres i paginació propis.
- Efemèrides exigeix interval acotat i ofereix presets propers; no llança consultes obertes silencioses.
- Els resultats d'objecte mantenen la selecció actual; els d'esdeveniment exposen actors, instant/interval, tipus, geometria i procedència.
- “Anar a la data” actualitza el temps i l'escena de forma atòmica. “Afegir al pla” usa la comanda comuna del pas 31.

## Objectiu

Completar la vertical de «cercador d'objectes i efemèrides» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 31 — “El millor d'aquesta nit” i planificador](pas31-millor-nit-planificador.md)
- [Pas 32 — Motor general d'efemèrides](pas32-motor-efemerides.md)

**En depenen:**
- [Pas 34 — Miniatures i animacions d'efemèrides](pas34-previsualitzacions-efemerides.md)
- [Pas 35 — Pestanya d'eclipsis](pas35-pestanya-eclipsis.md)
- [Pas 36 — Esdeveniments propis de planetes i Lluna](pas36-esdeveniments-objectes.md)
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Backend: [`search_coordinator.py`](../../../backend/src/terralab3d/application/search_coordinator.py), [`search/indexer.py`](../../../backend/src/terralab3d/domain/search/indexer.py) i [`search/services.py`](../../../backend/src/terralab3d/domain/search/services.py).
- UI: [`SearchWidget.ts`](../../../frontend/src/view/ui/components/SearchWidget.ts), [`SearchPanel.ts`](../../../frontend/src/view/ui/panels/SearchPanel.ts) i [`CelestialSelectionController.ts`](../../../frontend/src/application/CelestialSelectionController.ts).
- Pont: [`bridge_messages.ts`](../../../frontend/src/contracts/bridge_messages.ts) i [`ScienceBridge.ts`](../../../frontend/src/bridge/ScienceBridge.ts).
- Efemèrides: [`astronomical_event_contracts.ts`](../../../frontend/src/contracts/astronomical_event_contracts.ts).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Estat de pestanya → consulta validada → coordinador corresponent → lot versionat/paginat → view-model tipat → acció de selecció, temps o planificació.

## Errors, cancel·lació i recursos

- Escriure, canviar filtres o pestanya cancel·la la revisió anterior; una resposta tardana no substitueix resultats vigents.
- Un error del motor d'efemèrides no trenca la cerca d'objectes i conserva el context per reintentar.
- Llistes virtualitzades i subscripcions tenen límits i es disposen en tancar el panell.

## Tasques

- [x] Existeixen índex/coordinador de cerca, widget/panell i selecció d'objectes.
- [x] El pas 32 aporta una API de consulta d'efemèrides.
- [ ] No hi ha pestanyes Objectes/Efemèrides, filtres temporals ni accions “anar a la data”/“afegir al pla” per a esdeveniments.
- [ ] Definir estat per pestanya, query DTO, paginació, filtres i union tipada de resultats.
- [ ] Estendre coordinador/pont per consultar el pas 32 amb revisions i cancel·lació.
- [ ] Implementar tabs accessibles, presets d'interval, filtres de tipus/actors i validació immediata.
- [ ] Crear files/cards d'efemèride amb càrrega incremental, buits i errors parcials.
- [ ] Connectar centrar, anar a la data i afegir al pla amb comandes existents.
- [ ] Preservar focus, selecció i scroll davant resultats asíncrons.

## Criteri de sortida

Objectes i efemèrides es consulten en un únic patró UI sense regressar la cerca existent, amb resultats cancel·lables i accions coherents sobre escena, temps i planificador.

## Proves i evidències obligatòries

- [ ] Estat independent de tabs, teclat, focus, lector de pantalla i scroll.
- [ ] Debounce/cancel·lació, resposta fora d'ordre, paginació i error parcial.
- [ ] Validació d'interval, filtres combinats i presets.
- [ ] Accions de centrar, anar a data i afegir al pla.
- [ ] Captures de les dues pestanyes amb filtres i resultats.
- [ ] Prova automatitzada de respostes fora d'ordre.
- [ ] Vídeo d'“anar a la data” i “afegir al pla”.
- [ ] Auditoria de teclat/focus i llista gran.

## Fora d'abast

Miniatures animades i la presentació específica d'eclipsis.

## Instrucció per a Codex

Amplia el cercador existent amb estat i resultats tipats per pestanya. Consumeix el motor del pas 32, conserva la selecció d'objectes i aplica `latest-wins` a totes les consultes asíncrones.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
