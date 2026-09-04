# Pas 21 — Regla, quadrat, rectangle i cercle amb edició

> Estat: **pendent**  
> Conserva l’especificació original i encara requereix completar el criteri de sortida.

## Resultat funcional palpable

Les quatre eines de mesura es poden crear sobre el cel, seleccionar, moure, redimensionar, eliminar, desfer i llegir amb valors angulars.

## Fonts TerraLab a consultar

- `TerraLab/widgets/measurement_tools.py`
- `TerraLab/widgets/spherical_math.py` o `scene/spherical_math.py`
- `TerraLab/ui/widget_controls_builder.py` — toolbar d’eines

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir entitats immutables per ruler, square, rectangle i circle.
- [ ] Extreure distància angular, arcs geodèsics i punts de destinació.
- [ ] Implementar construcció esfèrica de cada forma.
- [ ] Implementar labels de distància, amplada/alçada i radi/diàmetre.
- [ ] Implementar gestos de creació amb preview.
- [ ] Implementar picking de forma, vores i handles.
- [ ] Implementar moure i redimensionar mantenint geometria esfèrica.
- [ ] Implementar selecció, eliminar seleccionat i netejar-ho tot.
- [ ] Implementar undo/redo amb límit de memòria.
- [ ] Renderitzar overlays amb batches persistents o geometria actualitzada per entitat.
- [ ] Evitar que la UI contingui la geometria matemàtica.
- [ ] Preparar persistència tipada per al pas 23.
- [ ] Comparar etiquetes i interacció amb TerraLab.

## Criteri de sortida

Totes quatre eines són completes i editables; les mesures són numèricament correctes i continuen coherents en moure càmera o canviar FOV.

## Evidència obligatòria

- [ ] Proves de geometria esfèrica i casos prop de 0/360°.
- [ ] Vídeo de crear, moure, redimensionar, eliminar i undo/redo.
- [ ] Prova de resize i canvi de càmera.

## Fora d’abast del pas

La persistència en disc es connecta al pas 23.
