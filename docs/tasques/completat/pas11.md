# Pas 11 — Cel profund NGC/IC

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** cel profund ngc/ic implementat, verificat i observable en el repositori.

## Descripció funcional

Galàxies, nebuloses, cúmuls oberts i globulars apareixen amb tipus, dimensions, orientació, magnitud i visibilitat coherents.

## Fonts a consultar

- `TerraLab/astro/ngc_catalog.py`
- `TerraLab/runtime/offscreen_renderer.py` — selecció i dibuix NGC
- `TerraLab/data/layer_manager.py` — `SKY_NGC`
- `TerraLab/astro/search_engine.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](pas5.md)
- [Pas 10 — Via Làctia i pols galàctica Planck](pas10.md)

**En depenen:**
- [Pas 12 — Cerca astronòmica, focus i seguiment](pas12.md)
- [Pas 27 — Carta de recursos d'espai profund](../pendent/pas27-recursos-espai-profund.md)
- [Pas 30 — Plate solving i comparador foto/simulació](../pendent/pas30-plate-solving.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

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

## Proves i evidències obligatòries

- [ ] Fixtures d’almenys una galàxia, nebulosa i dos tipus de cúmul.
- [ ] Recompte de registres i hash de l’índex.
- [ ] Captures a diferents FOV i Bortle.
- [ ] Mesura de culling i draw calls.

## Fora d'abast

La cerca unificada i el focus es completen al pas següent.

## Instrucció per a Codex

Pas 11 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
