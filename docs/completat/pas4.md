# Pas 4 — Grid celeste, brúixola, etiquetes i HUD astronòmic

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’entorn 3D mostra una quadrícula azimut-altura útil, brúixola, zenit, horitzó, etiquetes legibles i HUD configurable mentre la càmera i el temps es mouen.

## Fonts TerraLab a consultar

- `TerraLab/render/grid_renderer.py`
- `TerraLab/render/overlays_renderer.py`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/scene/projection.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [x] Definir geometria renderer-neutral per a grid horitzontal i referències principals.
- [x] Implementar línies d’azimut, cercles d’altitud, horitzó i marca de zenit.
- [x] Implementar etiquetes N/E/S/O i valors angulars amb orientació llegible.
- [x] Aplicar densitat adaptativa segons FOV per evitar soroll visual.
- [x] Evitar regenerar tota la geometria quan només canvia la càmera.
- [x] Implementar culling d’etiquetes i prevenció de solapaments bàsica.
- [x] Afegir toggles per grid, brúixola, labels i HUD.
- [x] Mostrar azimut, altitud i FOV actuals al HUD.
- [x] Fer que les etiquetes mantinguin una mida coherent amb DPR i resize.
- [x] Definir una capa overlay separada dels objectes celestes.
- [x] Afegir mode de colors purs/diagnòstic per verificar geometria i contrast.
- [x] Comparar orientació, densitat i convencions amb TerraLab.

## Criteri de sortida

La navegació ja és espacialment comprensible: l’usuari pot orientar-se, llegir azimut/altitud i activar o desactivar overlays sense canviar l’estat científic.

## Evidència obligatòria

- [x] Captures amb diferents FOV, DPR i orientacions.
- [x] Prova que moure càmera no reconstrueix buffers estàtics del grid.
- [x] Proves de convencions angulars i punts cardinals.

## Fora d’abast del pas

No inclou catàlegs astronòmics.
