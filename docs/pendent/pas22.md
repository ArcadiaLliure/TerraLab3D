# Pas 22 — Constel·lacions editables amb snapping, grups i persistència

> Estat: **pendent**  
> Conserva l’especificació original i encara requereix completar el criteri de sortida.

## Resultat funcional palpable

L’usuari pot crear grups de constel·lació, unir estrelles, fer traços discontinus, seleccionar nodes/segments/grups, reanomenar, eliminar i desfer.

## Fonts TerraLab a consultar

- `TerraLab/widgets/constellation_drawing.py`
- `TerraLab/ui/widget_controls_builder.py` — shortcuts Delete, Backspace i Enter
- `TerraLab/scene/spherical_math.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir document, grup, node, segment i semàntica `connect_from_prev`.
- [ ] Implementar snapping a estrelles visibles amb radi en píxels controlat pel frontend.
- [ ] Emmagatzemar RA/Dec i identificador/nom d’estrella, no coordenades de pantalla.
- [ ] Implementar crear grup, afegir node i finalitzar amb Enter.
- [ ] Implementar traços discontinus i reprendre des d’un node.
- [ ] Implementar selecció de node, segment, label, grup i multiselecció.
- [ ] Implementar eliminació granular i de grups múltiples.
- [ ] Implementar rename i labels persistents.
- [ ] Implementar undo/redo de totes les operacions.
- [ ] Implementar geometria d’arcs renderer-neutral i batches Three.js.
- [ ] Implementar repository port amb schema versionat.
- [ ] Migrar i validar el JSON actual de TerraLab quan existeixi.
- [ ] Implementar visibilitat independent del mode d’edició.
- [ ] Comparar workflow i shortcuts amb TerraLab.

## Criteri de sortida

Les constel·lacions es poden crear, editar, reanomenar, eliminar, desfer i restaurar; els documents no depenen de Qt ni de coordenades de pantalla.

## Evidència obligatòria

- [ ] Proves de schema, migració i round-trip.
- [ ] Vídeo de grup continu i discontinu.
- [ ] Prova de snapping, multiselecció i eliminació.
- [ ] Reinici de l’aplicació amb restauració del document.

## Fora d’abast del pas

La gestió unificada de preferències i datasets es tanca al pas 23.
