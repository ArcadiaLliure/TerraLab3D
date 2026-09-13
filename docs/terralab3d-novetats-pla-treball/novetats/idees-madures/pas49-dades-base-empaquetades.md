# Pas 49 — Cims i assentaments com a dades base empaquetades

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Cimas y asentamientos como datos base".
> Complementa els Pas 47 i 48.

## Resultat funcional palpable

Els datasets de cims i assentaments (GeoNames filtrat) es distribueixen **dins del producte** com a CSV inclòs, sense passar mai pel gestor de capes ni pel flux de descàrrega sota demanda: apareixen automàticament sempre que hi hagi topografia carregada.

## Context i decisions preses

- **Decisió explícita i tancada durant la pluja d'idees**, després de descartar l'opció de tractar-los com a recurs descarregable dins l'àrea d'interès: "no ho farem així". En comptes d'això:
- Cims i assentaments **no formen part de la jerarquia de refinament** ni del flux de descàrrega del Pas 42.
- Es distribueixen **per defecte dins d'un CSV empaquetat amb el producte**.
- Es pinten **sempre que la topografia estigui carregada**, sense acció addicional de l'usuari.
- Aquesta decisió tanca conceptualment el disseny del gestor de capes ("amb això, el disseny... queda coherent i separat per responsabilitats").

## Objectiu

Assegurar que els assets de cims (Pas 48) i assentaments (Pas 47) es distribueixen com a dades base empaquetades amb el producte, fora del sistema de descàrregues, i es mostren automàticament amb topografia carregada.

## Tasques

- [ ] Empaquetar el CSV filtrat de GeoNames (classes assentaments + cims) com a asset intern del producte, versionat com altres recursos científics del projecte.
- [ ] Assegurar que aquestes capes **no** apareixen al gestor de descàrregues (Pas 42) ni requereixen consulta d'Àrea d'Interès.
- [ ] Activar automàticament el pintat de cims i assentaments quan hi ha topografia carregada a l'escena, sense toggle manual addicional obligatori.
- [ ] Documentar aquesta decisió a `docs/normes_arquitectura.md` (o equivalent) perquè futures capes de dades base segueixin el mateix patró en lloc de reobrir el debat.

## Criteri de sortida

Carregar topografia per a qualsevol zona mostra automàticament els cims i pobles corresponents sense cap pas de descàrrega; el CSV empaquetat no apareix mai al gestor de capes com a recurs "pendent de descarregar".

## Evidència obligatòria

- [ ] Captura de topografia carregada amb cims i pobles visibles sense cap acció de descàrrega prèvia.
- [ ] Confirmació que el gestor de capes (Pas 39-42) no llista aquest CSV com a recurs descarregable.

## Fora d'abast del pas

El contingut i l'algorisme d'assignació dels datasets (ja coberts als Pas 47 i 48) — aquest pas només tracta la seva distribució i integració com a dada base.

## Prompt per a Codex

```
Implementa el Pas 49 (Cims i assentaments com a dades base) descrit a
docs/novetats/idees-madures/pas49-dades-base-empaquetades.md sobre main, després dels Pas 47 i 48.
Empaqueta el CSV filtrat de GeoNames (assentaments + cims) com a asset intern versionat del producte,
FORA del gestor de descàrregues (Pas 42) i sense pas per l'Àrea d'Interès. Activa automàticament el
seu pintat quan hi ha topografia carregada, sense toggle manual addicional. Documenta aquest patró a
docs/normes_arquitectura.md com a referència per a futures capes de dades base incloses amb el
producte.
```
