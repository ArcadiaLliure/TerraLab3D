# Pas 33 — Cercador multipestanya (Objectes / Efemèrides / Eclipsis)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Nuevo buscador multipestaña".
> Depèn de: Pas 32 (Motor d'efemèrides), Pas 28 (`ObservableObject`).

## Resultat funcional palpable

El cercador deixa de ser un component monolític i esdevé un contenidor amb pestanyes: «Objectes», «Efemèrides» (i, si el Pas 35 hi és, «Eclipsis»). Sense filtres, la pestanya d'Efemèrides mostra automàticament les properes efemèrides rellevants.

## Context i decisions preses

- El cercador ha de néixer com un **contenidor multipestanya extensible** des del principi, no com un component monolític.
- Pestanya **Objectes**: cerca lliure existent (estrelles, planetes, NGC, constel·lacions...).
- Pestanya **Efemèrides**: filtres per planeta, múltiples planetes i tipus de segon objecte (dinàmic o estàtic destacat); prohibició de combinacions estàtic-estàtic (heretada del Pas 32); **sense filtres, mostra automàticament les properes efemèrides rellevants**.
- "El millor d'aquesta nit" (Pas 30) **no** és una pestanya més d'aquest cercador: viu com a accés separat a la zona dreta de la UI, amb un enllaç discret des de la cerca avançada.

## Objectiu

Refactoritzar/construir el cercador com a contenidor de pestanyes, amb la pestanya d'Efemèrides consumint el motor del Pas 32.

## Tasques

- [ ] Definir l'arquitectura de contenidor multipestanya (afegir una pestanya nova no ha de requerir tocar les altres).
- [ ] Migrar la cerca d'objectes existent a la pestanya «Objectes» sense pèrdua de funcionalitat.
- [ ] Implementar la pestanya «Efemèrides»: selector de planeta(s), selector de segon objecte (dinàmic/estàtic destacat), validació que bloqueja estàtic-estàtic.
- [ ] Vista per defecte (sense filtres) de la pestanya Efemèrides: llista de properes efemèrides rellevants ordenades per data.
- [ ] Des de qualsevol resultat, acció directa «Afegir al pla» (reutilitzant Pas 31) i «Anar a la data».
- [ ] Deixar preparat el punt d'extensió per a la futura pestanya «Eclipsis» (Pas 35).

## Criteri de sortida

El cercador funciona amb pestanyes independents sense regressions a la cerca d'objectes existent; la pestanya d'Efemèrides mostra resultats vàlids amb i sense filtres, i respecta la prohibició estàtic-estàtic.

## Evidència obligatòria

- [ ] Captura de les pestanyes Objectes i Efemèrides.
- [ ] Captura de la vista per defecte d'Efemèrides (sense filtres).
- [ ] Prova que un intent de filtre estàtic-estàtic queda bloquejat a la UI.

## Fora d'abast del pas

Miniatures i animacions dins de cada resultat d'efemèride (Pas 34). Pestanya d'Eclipsis pròpia (Pas 35).

## Prompt per a Codex

```
Implementa el Pas 33 (Cercador multipestanya) descrit a
docs/novetats/idees-madures/pas33-cercador-multipestanya.md sobre main, després del Pas 32.
Refactoritza el cercador actual com a contenidor de pestanyes (Objectes / Efemèrides), migrant la
cerca existent sense regressions. La pestanya Efemèrides ha de consumir l'API del motor
d'efemèrides del Pas 32, mostrar automàticament les properes efemèrides rellevants quan no hi ha
filtres, i bloquejar a la UI qualsevol combinació estàtic-estàtic. Deixa el contenidor preparat per
afegir una pestanya "Eclipsis" en el futur sense refactor addicional.
```
