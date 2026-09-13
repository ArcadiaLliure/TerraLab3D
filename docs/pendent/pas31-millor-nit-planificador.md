# Pas 31 — “El millor d'aquesta nit” i planificador temporal

> Estat: **pendent**. Hi ha barra temporal, selecció, cerca i trajectòries reutilitzables; no existeixen el rànquing nocturn, el model de pla ni la banda editable.

## Estat actual verificat

- [x] La UI ja disposa de barra temporal, picking, fitxa/selecció i cerca.
- [x] El pas 22 defineix la visibilitat comuna contra l'horitzó real.
- [ ] No hi ha score 0–100, recomanacions, blocs temporals, detecció de conflictes ni persistència de plans.

## Resultat funcional

L'usuari consulta objectes recomanats per a la ubicació i nit actuals, els filtra i afegeix a un pla integrat a la barra temporal; allí mou i redimensiona blocs, veu qualitat, solapaments i trànsits de meridià, desfà eliminacions i pot generar una proposta automàtica editable.

## Dependències

- [Pas 22 — trajectòries i visibilitat](pas22-trajectories-visibilitat.md).
- [Pas 23 — constel·lacions observables](pas23-constellacions.md).

## Decisions tancades

- “El millor d'aquesta nit” és un panell lateral, obert des d'una targeta compacta a la dreta sobre el bloc de capes; no forma part del quadre de cerca.
- Cada resultat mostra nom, tipus, magnitud, mida angular, inici/final, altura màxima i una corba d'altura en V invertida.
- Els filtres són multiselecció tipus Excel, combinables per columna. La targeta destacada usa miniatures pròpies, no fotografies externes.
- El planificador és una banda sobre [`TimeBar.ts`](../../frontend/src/view/ui/components/TimeBar.ts), no una pantalla nova.
- Vora esquerra/dreta redimensiona; centre desplaça; X elimina i ofereix “Desfer”. Hi ha snapping suau a límits veïns.
- Score 0–100: 0–35 vermell, 35–80 groc, 80–100 verd. Els solapaments usen una trama diferent del color de qualitat.
- El trànsit pel meridià es mostra amb un diamant i hora; només avisa.
- “Afegir al pla” té la mateixa semàntica des de picking, cerca, fitxa, constel·lació i recomanacions.
- “Suggerir planificació” crea una proposta determinista i editable; mai controla equips físics.

## Codi existent a reutilitzar

- Temps: [`TimeBar.ts`](../../frontend/src/view/ui/components/TimeBar.ts) i [`astronomical_event_contracts.ts`](../../frontend/src/contracts/astronomical_event_contracts.ts).
- Selecció/cerca: [`CelestialSelectionController.ts`](../../frontend/src/application/CelestialSelectionController.ts), [`SearchWidget.ts`](../../frontend/src/view/ui/components/SearchWidget.ts) i [`SearchPanel.ts`](../../frontend/src/view/ui/panels/SearchPanel.ts).
- Visibilitat: [`apparent_trajectory.py`](../../backend/src/terralab3d/application/apparent_trajectory.py) i [`horizon_coordinator.py`](../../backend/src/terralab3d/application/horizon_coordinator.py).
- Persistència: [`persistence.py`](../../backend/src/terralab3d/application/ports/persistence.py).

## Treball pendent

- [ ] Definir nit astronòmica, candidat, score explicable i model versionat de pla/bloc.
- [ ] Calcular candidats i sèries d'altura des del pas 22 amb límits de catàleg, cache i cancel·lació.
- [ ] Implementar panell, targeta compacta, gràfic en V invertida i filtres multiselecció combinables.
- [ ] Afegir la banda a TimeBar amb drag de centre/vores, X, Desfer, snapping i feedback en temps real.
- [ ] Calcular i renderitzar qualitat, trama de solapament i marca de meridià sense confondre semàntiques.
- [ ] Connectar “Afegir al pla” a tots els punts d'entrada amb una única comanda.
- [ ] Implementar suggeriment determinista sota restriccions i persistència/migració del pla.

## Flux tècnic

Observador + nit + catàlegs → observables del pas 22 → mostreig/score en worker → rànquing i filtres → comanda comuna d'afegir → pla persistent → deltes de blocs → banda temporal.

## Errors, cancel·lació i recursos

- Canviar nit, ubicació o filtres cancel·la càlculs obsolets; el pla no canvia fins que una revisió nova és vàlida.
- Objectes sense magnitud o mida declaren el camp desconegut i no inventen valors; la política de score documenta el tractament.
- Un drag es pot cancel·lar i reverteix a l'últim model vàlid. Undo és acotat i no sobreviu a migracions incompatibles.
- Workers, timers, listeners i previews es disposen en tancar el panell o substituir la nit.

## Proves

- Score a llindars 35/80, objectes circumpolars/invisibles i camps desconeguts.
- Filtres combinats, ordenació estable i rànquing determinista.
- Drag de vores/centre, snapping, solapaments, X/Desfer i meridià.
- Persistència, migració, suggeriment automàtic i totes les entrades d'“Afegir al pla”.
- Accessibilitat per teclat i pressupost durant recalculs continus de temps.

## Criteri de sortida

El panell ofereix recomanacions coherents i filtrables i permet construir o suggerir una nit completa a la banda temporal; totes les operacions són editables, persistents i mantenen feedback fluid.

## Evidències

- [ ] Panell amb almenys deu objectes i filtres combinats.
- [ ] Vídeo de moure/redimensionar, solapament, X i Desfer.
- [ ] Captures de score, trama i diamant de meridià.
- [ ] Pla suggerit, reinici i restauració amb les mateixes dades.

## Fora d'abast

Meridian flip mecànic, control de muntures i execució automàtica de captures. La idea relacionada continua a [integració amb muntures](../idees-per-madurar/integracio-amb-muntures.md).

## Instrucció per a Codex

Implementa recomanacions i planificador com una sola vertical sobre el contracte observable del pas 22 i la TimeBar existent. Centralitza “Afegir al pla”, mantén el score determinista i no creïs una pantalla de planificació separada.
