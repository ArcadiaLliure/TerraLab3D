# Pas 11 — Cel profund NGC/IC

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

Galàxies, nebuloses, cúmuls oberts i globulars apareixen amb tipus, dimensions, orientació, magnitud i visibilitat coherents.

## Fonts TerraLab a consultar

- `TerraLab/astro/ngc_catalog.py`
- `TerraLab/runtime/offscreen_renderer.py` — selecció i dibuix NGC
- `TerraLab/data/layer_manager.py` — `SKY_NGC`
- `TerraLab/astro/search_engine.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Adaptar el parser OpenNGC a entitats tipades amb ID, àlies, tipus i coordenades.
- [ ] Normalitzar galàxies, nebuloses, cúmuls oberts, globulars i altres tipus.
- [ ] Conservar eixos major/menor, angle de posició i magnitud quan existeixin.
- [ ] Implementar selecció per camp visible, magnitud i extinció.
- [ ] Preparar buffers o instàncies persistents per tipus visual.
- [ ] Definir símbols/materials Three.js diferenciats i escalables.
- [ ] Gestionar objectes sense magnitud o dimensions sense inventar valors científics.
- [ ] Implementar toggle i estat de dataset.
- [ ] Integrar els factors de contaminació lumínica i atmosfera.
- [ ] Fer que un canvi de FOV pugui canviar LOD/labels sense recarregar el catàleg.
- [ ] Comparar recompte, categories, posicions i aparença semàntica amb TerraLab.

## Criteri de sortida

El catàleg NGC és visible i filtrable, els tipus són distingibles, les dades incompletes es gestionen explícitament i el catàleg roman resident.

## Evidència obligatòria

- [ ] Fixtures d’almenys una galàxia, nebulosa i dos tipus de cúmul.
- [ ] Recompte de registres i hash de l’índex.
- [ ] Captures a diferents FOV i Bortle.
- [ ] Mesura de culling i draw calls.

## Fora d’abast del pas

La cerca unificada i el focus es completen al pas següent.
