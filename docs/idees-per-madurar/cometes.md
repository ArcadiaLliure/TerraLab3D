# Idea pendent de madurar — Cometes

> Estat: **per madurar**. No forma part de l'ordre executable fins que es resolguin les preguntes obertes.

> Origen: pluja d'idees TerraLab3D, bloc "Cometas". Decisió explícita: **aparcat per a una conversa posterior**, no descartat.

## Què s'ha decidit ja

- Està decidit que els cometes **arribaran**, probablement amb entitat pròpia a la UI (possiblement pestanya pròpia, similar a Eclipsis).
- Explícitament deixat per a una conversa futura; no hi ha cap disseny concret encara.

## Per què encara no és una fase concreta

Falta resoldre completament:

- catàleg de cometes a utilitzar;
- actualització orbital (els cometes tenen elements orbitals que canvien i cal actualitzar periòdicament, a diferència de planetes);
- estimació de magnitud (molt més variable i incerta que en altres cossos);
- càlcul de periheli;
- quins tipus d'esdeveniments generen (relació amb el [motor d'efemèrides, pas 32](../pendent/pas32-motor-efemerides.md));
- integració amb el motor d'efemèrides previst (els cometes s'haurien d'afegir al grup “dinàmics”, però això no s'ha confirmat ni especificat).

## Preguntes obertes

1. Quina font de dades orbitals de cometes s'utilitzarà i amb quina llicència?
2. Amb quina freqüència cal actualitzar els elements orbitals?
3. Cometes entren directament com a nou tipus dins el contracte observable del [pas 22](../pendent/pas22-trajectories-visibilitat.md) i el grup “dinàmics” del [pas 32](../pendent/pas32-motor-efemerides.md), o necessiten un subsistema propi?

## Relació amb el pla i altres idees

[Motor d'efemèrides (pas 32)](../pendent/pas32-motor-efemerides.md) — probablement el punt d'integració natural un cop es resolguin les preguntes obertes.
