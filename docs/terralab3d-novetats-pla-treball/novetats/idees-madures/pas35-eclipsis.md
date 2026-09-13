# Pas 35 — Eclipsis (pestanya dedicada al cercador)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Eclipses".
> Depèn de: Pas 33 (Cercador multipestanya). Reaprofita el càlcul SPICE d'eclipsis ja completat al Pas 9.

## Resultat funcional palpable

Una tercera pestanya al cercador, «Eclipsis», llista els eclipsis solars i lunars calculats amb SPICE i permet situar TerraLab3D automàticament a la data/hora de qualsevol d'ells amb un sol clic.

## Context i decisions preses

- Els eclipsis tenen entitat suficient per a una **pestanya pròpia** dins el cercador multipestanya: `[ Objectes ] [ Efemèrides ] [ Eclipsis ]`.
- Cada eclipsi ha de tenir una acció **«Anar a la data»**, que posi tot TerraLab3D en el moment corresponent (rellotge global).
- El càlcul geomètric topocèntric d'eclipsis solars i lunars ja existeix (Pas 9, completat, amb SPICE); aquest pas és sobre la **UI de llistat i navegació**, no sobre el motor de càlcul.

## Objectiu

Exposar el llistat d'eclipsis ja calculable amb el motor SPICE existent com una pestanya navegable del cercador, amb salt directe a la data.

## Tasques

- [ ] Definir el rang temporal i els criteris de llistat d'eclipsis (p. ex. propers N mesos/anys, visibles o no des de la ubicació actual).
- [ ] Implementar la pestanya «Eclipsis» dins el contenidor del Pas 33.
- [ ] Mostrar per cada eclipsi: tipus (solar/lunar, total/parcial/anular), data, visibilitat des de la ubicació actual (reaprofitant Pas 9 i Pas 28).
- [ ] Acció «Anar a la data»: mou el rellotge global de TerraLab3D a l'instant clau de l'eclipsi.
- [ ] (Opcional, reutilitzant Pas 34) miniatura generada per l'esdeveniment.

## Criteri de sortida

La pestanya llista correctament els propers eclipsis coneguts, distingeix si són visibles des de la ubicació actual, i «Anar a la data» posiciona TerraLab3D exactament a l'instant esperat.

## Evidència obligatòria

- [ ] Llista d'eclipsis generada per a un període conegut, contrastada amb una font externa.
- [ ] Captura de TerraLab3D just després de prémer «Anar a la data» per a un eclipsi de prova.

## Fora d'abast del pas

El càlcul geomètric d'eclipsis (ja fet al Pas 9). Les miniatures/animacions detallades (reaprofiten el Pas 34 si es decideix incloure-les).

## Prompt per a Codex

```
Implementa el Pas 35 (pestanya Eclipsis) descrit a docs/novetats/idees-madures/pas35-eclipsis.md
sobre main, després del Pas 33. NO reimplementis el càlcul d'eclipsis: reaprofiteix el motor SPICE
ja completat al Pas 9 (docs/completat/pas9.md). Afegeix només la pestanya "Eclipsis" al contenidor
multipestanya del Pas 33, amb llistat, indicador de visibilitat des de la ubicació actual (via
ObservableObject del Pas 28) i l'acció "Anar a la data" que mou el rellotge global.
```
