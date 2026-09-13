# Pas 36 — Esdeveniments propis dels objectes (oposició, elongació, fases, perigeu/apogeu)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Eventos propios de objetos".
> Depèn de: Pas 32 (Motor d'efemèrides).

## Resultat funcional palpable

La fitxa de determinats cossos (planetes, Lluna) mostra directament els seus propers esdeveniments propis —oposició, elongació, fase lunar, perigeu/apogeu— amb icona i acció per saltar-hi a la data.

## Context i decisions preses

- Dins de les cards/fitxa d'un cos poden aparèixer directament:
  - propera oposició;
  - propera elongació;
  - fases lunars;
  - perigeu/apogeu;
  - altres fites pròpies rellevants.
- Amb iconografia i acció per saltar a la data (mateix patró «Anar a la data» que efemèrides i eclipsis).

## Objectiu

Calcular i exposar els esdeveniments propis de cada cos (no creuaments amb altres objectes) a la seva fitxa individual.

## Tasques

- [ ] Definir, per tipus de cos, quins esdeveniments propis apliquen (planetes exteriors: oposició; interiors: elongació; Lluna: fases i perigeu/apogeu).
- [ ] Implementar el càlcul de cada tipus d'esdeveniment reaprofitant les efemèrides SPICE/DE440 ja disponibles.
- [ ] Afegir la secció d'esdeveniments propis a la fitxa de cada cos amb icona pròpia per tipus.
- [ ] Acció «Anar a la data» consistent amb la resta del producte (Pas 31, 33, 35).

## Criteri de sortida

La fitxa de cada planeta i de la Lluna mostra els seus propers esdeveniments propis correctament calculats i navegables.

## Evidència obligatòria

- [ ] Captura de la fitxa de Mart mostrant la propera oposició.
- [ ] Captura de la fitxa de la Lluna mostrant fase actual i proper perigeu/apogeu.

## Fora d'abast del pas

Els creuaments entre objectes (Pas 32) i la seva presentació al cercador (Pas 33/34).

## Prompt per a Codex

```
Implementa el Pas 36 (Esdeveniments propis dels objectes) descrit a
docs/novetats/idees-madures/pas36-esdeveniments-propis-objectes.md sobre main, després del Pas 32.
Calcula oposicions, elongacions, fases lunars i perigeu/apogeu reaprofitant les efemèrides SPICE/DE440
ja integrades (docs/completat/pas8.md). Afegeix aquesta informació a la fitxa de cada cos rellevant,
amb l'acció "Anar a la data" consistent amb la resta del producte.
```
