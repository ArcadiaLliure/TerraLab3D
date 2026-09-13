# Idea pendent de madurar — Cometes

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
- quins tipus d'esdeveniments generen (relació amb el motor d'efemèrides, Pas 32);
- integració amb el motor d'efemèrides existent (els cometes s'haurien d'afegir al grup "dinàmics" del Pas 32, però això no s'ha confirmat ni especificat).

## Preguntes obertes

1. Quina font de dades orbitals de cometes s'utilitzarà i amb quina llicència?
2. Amb quina freqüència cal actualitzar els elements orbitals?
3. Cometes entren directament com a nou tipus dins `ObservableObject` (Pas 28) i el grup "dinàmics" del motor d'efemèrides (Pas 32), o necessiten un subsistema propi?

## Relació amb altres idees pendents

Motor d'efemèrides (Pas 32, madur) — probablement el punt d'integració natural un cop es resolguin les preguntes obertes.
