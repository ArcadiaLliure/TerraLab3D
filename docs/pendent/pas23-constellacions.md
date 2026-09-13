# Pas 23 — Constel·lacions oficials i d'usuari

> Estat: **pendent**. Hi ha models, càlculs, servei i interfície de renderer, però no una vertical observable, editable i persistent.

## Estat actual verificat

- [x] Existeixen el paquet de domini de constel·lacions i `ConstellationLayerRenderer` com a fronteres inicials.
- [ ] El catàleg oficial, el document d'usuari, l'edició, el snapping, la persistència i la integració observable no estan implementats.

## Resultat funcional

L'usuari cerca i observa constel·lacions oficials, en pot mostrar totes les línies i crea constel·lacions pròpies amb grups, traços continus o discontinus, edició, undo/redo i restauració entre sessions.

## Dependències

- [Pas 22 — trajectòries i visibilitat](pas22-trajectories-visibilitat.md).
- [Pas 6 — picking](../completat/pas6.md) i [Pas 13 — selecció](../completat/pas13.md).

## Decisions tancades

- El model separa catàleg oficial IAU i documents d'usuari, però tots exposen identitat, línies i centre/envolupant al contracte observable.
- Un document d'usuari conté grups, nodes i segments; `connect_from_prev` representa talls discontinus sense coordenades sentinella.
- Es persisteixen RA/Dec i identificador/nom d'estrella, mai píxels de pantalla.
- El frontend calcula el radi de snapping en píxels i envia una intenció; el domini resol l'estrella vàlida.
- “Mostrar totes” modifica la presentació, no duplica constel·lacions ni models.
- Totes les operacions d'edició són immutables, versionades i desfables.

## Codi existent a reutilitzar

- Domini: [`models.py`](../../backend/src/terralab3d/domain/constellations/models.py), [`calculations.py`](../../backend/src/terralab3d/domain/constellations/calculations.py) i [`services.py`](../../backend/src/terralab3d/domain/constellations/services.py).
- Render: [`ConstellationLayerRenderer.ts`](../../frontend/src/view/three/layers/ConstellationLayerRenderer.ts), [`PointerGestureRouter.ts`](../../frontend/src/view/three/picking/PointerGestureRouter.ts) i [`StarLayerRenderer.ts`](../../frontend/src/view/three/layers/StarLayerRenderer.ts).
- Selecció: [`CelestialSelectionController.ts`](../../frontend/src/application/CelestialSelectionController.ts).
- Oracle TerraLab: [constellation_drawing.py](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/constellation_drawing.py), [widget_controls_builder.py](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/ui/widget_controls_builder.py) i [spherical_math.py](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/spherical_math.py).

## Treball pendent

- [ ] Definir esquemes versionats per al catàleg oficial i el document d'usuari, amb migració del JSON de TerraLab quan existeixi.
- [ ] Carregar les línies IAU, calcular centre/envolupant esfèric i exposar cerca i adaptador observable.
- [ ] Implementar crear grup, afegir node, acabar amb Enter, reprendre des d'un node i alternar segment continu/discontinu.
- [ ] Implementar snapping, selecció de node/segment/label/grup, multiselecció, rename i eliminació granular.
- [ ] Implementar undo/redo acotat i un repository port persistent.
- [ ] Generar arcs renderer-neutral i batches incrementals; mantenir la visibilitat independent del mode d'edició.
- [ ] Afegir l'acció “mostrar totes” i la cerca sense esperar el cercador multipestanya del pas 33.

## Flux tècnic

Catàleg o document persistent → model esfèric → centre/envolupant observable + geometria d'arcs → delta versionat → renderer. Els gestos UI produeixen intencions d'edició i no muten directament el document.

## Errors, cancel·lació i recursos

- Un document invàlid es rebutja amb diagnòstic i còpia recuperable; les migracions no sobreescriuen l'original abans de validar.
- Sortir del mode d'edició cancel·la el gest obert, no elimina les línies visibles.
- Les geometries, labels i listeners de grups eliminats es disposen explícitament.

## Proves

- Esquema, migració i round-trip de documents oficials i d'usuari.
- Snapping amb diferents DPR/FOV, discontinuïtats, multiselecció i shortcuts Enter/Delete/Backspace.
- Centre/envolupant prop de 0/360° i adaptació al pas 22.
- Undo/redo de totes les operacions i reinici amb restauració.

## Criteri de sortida

Una constel·lació oficial es pot cercar i observar, totes les línies es poden mostrar, i un document propi es pot crear, editar, desfer, persistir i restaurar sense dependències de Qt o coordenades de pantalla.

## Evidències

- [ ] Captura d'una constel·lació oficial amb trajectòria activa.
- [ ] Vídeo del flux continu/discontinu i del mode “mostrar totes”.
- [ ] Resultats de migració, round-trip, snapping i undo/redo.
- [ ] Reinici amb restauració i recompte estable de geometries.

## Fora d'abast

La UX multipestanya del cercador i la planificació temporal.

## Instrucció per a Codex

Completa la vertical a partir dels models i renderer existents. Usa l'oracle TerraLab només per validar el workflow, mantén les dades en RA/Dec i integra constel·lacions amb el contracte observable del pas 22.
