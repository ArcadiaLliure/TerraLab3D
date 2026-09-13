# Pas 32 — Motor d'efemèrides (creuaments dinàmic↔dinàmic i dinàmic↔estàtic)

> Estat: **proposta nova — idea molt madura**
> Origen: pluja d'idees TerraLab3D, bloc "Motor de efemérides".
> Depèn de: Pas 28 (`ObservableObject`).

## Resultat funcional palpable

TerraLab3D detecta i llista automàticament aproximacions, conjuncions i ocultacions rellevants entre cossos del Sistema Solar i entre aquests i estrelles/objectes destacats, sense necessitat de cercar-los manualment.

## Context i decisions preses

- Dos grups d'objectes:
  - **Dinàmics:** Sol, Lluna, planetes; més endavant cometes (vegeu idea pendent "Cometes").
  - **Estàtics destacats:** estrelles molt brillants i objectes seleccionats de catàlegs Messier/NGC (galàxies, nebuloses, cúmuls).
- Creuaments permesos: **dinàmic↔dinàmic** i **dinàmic↔estàtic destacat**.
- Creuaments **no permesos**: estàtic↔estàtic (no té sentit astronòmic buscar-los).
- Tipus d'esdeveniments: aproximacions, conjuncions, ocultacions, alineacions rellevants.
- El motor ha de reaprofitar l'arquitectura de trajectòries/visibilitat del Pas 28 i les efemèrides SPICE/DE440 ja integrades al projecte.

## Objectiu

Implementar el càlcul i la detecció automàtica d'esdeveniments d'efemèrides entre objectes dinàmics i entre objectes dinàmics i estàtics destacats.

## Tasques

- [ ] Definir el catàleg d'objectes "estàtics destacats" apte per a creuaments (subconjunt d'estrelles brillants + Messier/NGC seleccionat).
- [ ] Implementar el càlcul de separació angular entre parells d'objectes dinàmics al llarg del temps (usant SPICE/DE440 ja disponible).
- [ ] Implementar el càlcul de separació angular entre un objecte dinàmic i cada estàtic destacat.
- [ ] Detectar mínims locals de separació (aproximacions/conjuncions) per sota d'un llindar configurable.
- [ ] Detectar ocultacions (separació angular menor que la suma de radis aparents), reaprofitant la lògica d'eclipsis/ocultacions del Pas 9 quan sigui aplicable.
- [ ] Exposar l'API de consulta d'efemèrides properes per a un rang de dates i un conjunt d'objectes.
- [ ] Prohibir explícitament (a nivell d'API i UI) les consultes estàtic↔estàtic.

## Criteri de sortida

El motor troba correctament aproximacions/conjuncions/ocultacions conegudes (verificables contra efemèrides publicades) per a un període de referència, sense generar creuaments estàtic↔estàtic.

## Evidència obligatòria

- [ ] Llista d'esdeveniments generats per a un mes conegut, contrastada amb una font externa (p. ex. un almanac astronòmic).
- [ ] Prova que confirma que una consulta estàtic↔estàtic és rebutjada.

## Fora d'abast del pas

La UI del cercador (Pas 33), les miniatures/animacions (Pas 34), la pestanya d'eclipsis (Pas 35) i els esdeveniments propis de cada objecte (Pas 36) es construeixen sobre aquest motor però són passos separats.

## Prompt per a Codex

```
Implementa el Pas 32 (Motor d'efemèrides) descrit a docs/novetats/idees-madures/pas32-motor-efemerides.md
sobre main, després del Pas 28. Reaprofita les efemèrides SPICE/DE440 ja integrades (vegeu
docs/completat/pas8.md i docs/completat/pas9.md) per calcular separacions angulars entre objectes
dinàmics (Sol, Lluna, planetes) i entre aquests i un subconjunt d'estrelles brillants + Messier/NGC
seleccionat com "estàtics destacats". Detecta mínims locals de separació (conjuncions/aproximacions)
i ocultacions, reaprofitant la lògica d'ocultacions del Pas 9. Exposa una API de consulta per rang de
dates i objectes, i prohibeix a nivell d'API els creuaments estàtic-estàtic.
```
