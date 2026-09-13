# Pas 22 — Trajectòries i visibilitat sobre l'horitzó real

> Estat: **parcial**. Les trajectòries aparents de cossos del Sistema Solar i l'horitzó real existeixen per separat; falta convertir-ho en una capacitat comuna per a qualsevol objecte observable.

## Estat actual verificat

- [x] El pas 9 calcula i transporta trajectòries aparents versionades de cossos del Sistema Solar.
- [x] Els passos 9 i 15 aporten separacions angulars, esdeveniments astronòmics, mostreig d'horitzó i oclusió visual.
- [ ] No existeix encara un contracte general d'objecte observable ni el càlcul integrat de sortides, postes i trams visibles contra l'horitzó local.

## Resultat funcional

L'usuari activa la trajectòria temporal de qualsevol objecte suportat —estrella, planeta, satèl·lit, objecte de cel profund o constel·lació— i veu els trams visibles i ocults, les interseccions amb l'horitzó real i els casos circumpolar o mai visible.

## Dependències

- [Pas 9 — eclipsis i esdeveniments](../completat/pas9.md).
- [Pas 15 — horitzó real](../completat/pas15.md).

## Decisions tancades

- `ObservableObject` serà un contracte tipat amb identitat, posició aparent per instant i metadades; no obliga els models de domini a heretar d'una classe comuna.
- Cada família d'objectes tindrà un adaptador explícit. Les constel·lacions aportaran centre/envolupant al pas 23.
- El domini mostreja la trajectòria, interpola els creuaments i classifica visibilitat; el renderer només projecta batches.
- Un perfil d'horitzó real preval sobre l'horitzó astronòmic, amb fallback explícit quan no estigui disponible.
- Les peticions són `latest-wins` per revisió d'observador, interval i objecte.

## Codi existent a reutilitzar

- Coordinadors: [`apparent_trajectory.py`](../../backend/src/terralab3d/application/apparent_trajectory.py) i [`horizon_coordinator.py`](../../backend/src/terralab3d/application/horizon_coordinator.py).
- Esdeveniments: [`astronomical_events.py`](../../backend/src/terralab3d/application/astronomical_events.py) i el seu [port](../../backend/src/terralab3d/application/ports/astronomical_events.py).
- Contractes i render: [`astronomical_event_contracts.ts`](../../frontend/src/contracts/astronomical_event_contracts.ts), [`ApparentTrajectoryRenderer.ts`](../../frontend/src/view/three/ApparentTrajectoryRenderer.ts) i [`HorizonLayerRenderer.ts`](../../frontend/src/view/three/layers/HorizonLayerRenderer.ts).
- Proves de base: [`test_astronomical_events_step9.py`](../../backend/tests/test_astronomical_events_step9.py), [`astronomical_events_step9.test.ts`](../../frontend/src/tests/astronomical_events_step9.test.ts) i [`test_horizon_step15.py`](../../backend/tests/test_horizon_step15.py).

## Treball pendent

- [ ] Definir DTO i port renderer-neutral d'objecte observable i adaptadors per a les famílies ja disponibles.
- [ ] Generalitzar el coordinador sense regressar el format binari i el renderer del pas 9.
- [ ] Mostrejar altura/azimut, comparar-los amb el perfil real i interpolar creuaments temporals.
- [ ] Classificar sortida, posta, circumpolaritat, invisibilitat completa i buits de perfil.
- [ ] Renderitzar trams visibles/ocults i labels d'esdeveniment sense recrear tota la geometria.
- [ ] Connectar controls d'interval, resolució i activació a la selecció actual.

## Flux tècnic

Selecció + observador + interval → adaptador observable → mostreig en worker → comparació amb el perfil d'horitzó → trajectòria i esdeveniments versionats → transferible binari → actualització incremental del renderer.

## Errors, cancel·lació i recursos

- Una revisió obsoleta es descarta abans de publicar; canviar selecció, temps o ubicació cancel·la la feina anterior.
- Els buits del DEM es marquen i utilitzen el fallback astronòmic sense inventar relleu.
- Buffers i geometries substituïts s'alliberen; el renderer conserva una sola trajectòria activa per vista.

## Proves

- Casos de sortida/posta, circumpolar, mai visible, pas pel nord i discontinuïtat 0/360°.
- Comparació del mateix objecte amb horitzó pla i real.
- Curses de revisions i cancel·lació durant un mostreig llarg.
- Contracte binari, actualització parcial i pressupost de memòria del renderer.

## Criteri de sortida

Totes les famílies suportades recorren el mateix flux observable i mostren una trajectòria temporal coherent amb el perfil real, sense bloquejar la UI ni duplicar la lògica astronòmica.

## Evidències

- [ ] Captures del mateix objecte amb horitzó astronòmic i real.
- [ ] Proves automatitzades de classificació i interpolació.
- [ ] Traça de cancel·lació `latest-wins` i de revisió acceptada.
- [ ] Mètriques de temps, bytes transferits i geometries vives.

## Fora d'abast

Planificació de sessions, edició de constel·lacions i càlcul de nous tipus d'efemèride.

## Instrucció per a Codex

Amplia els coordinadors dels passos 9 i 15 amb un contracte observable renderer-neutral. Conserva els formats i renderers existents, implementa cancel·lació per revisió i no introdueixis dependències cap als passos posteriors.
