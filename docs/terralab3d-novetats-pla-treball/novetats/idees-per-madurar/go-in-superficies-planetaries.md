# Idea pendent de madurar — «Go In» / superfícies planetàries

> Origen: pluja d'idees TerraLab3D, blocs "Go In / superficie de otros cuerpos" i "Ampliació de cossos amb model d'elevació".

## Què s'ha decidit ja

- No limitar el GoTo a mirar un cos des de lluny: `Tierra → GoTo Luna → Go In → superfície lunar`.
- Arquitectura **genèrica** per a qualsevol cos que disposi de DEM/model de forma, textura i sistema de coordenades.
- Primer candidat: **Lluna**. Segon candidat natural: **Mart**.
- S'ha investigat i confirmat model d'elevació (2D o model de forma 3D per a cossos irregulars) i llicència d'ús comercial per: Terra, Lluna, Mart, Mercuri, Venus, Ceres, Vesta, Encèlad (DEM Cassini 200 m/px, 2024), Fobos i Deimos (aquests dos requereixen model de forma 3D, no DEM 2D clàssic, per la seva forma irregular).
- Candidats addicionals detectats però sense validar cobertura/prioritat: Titan, Plutó, Caront, Mimas, Tetis, Dione, Rea, Febe, Ío, Europa, Ganimedes, Cal·listo, i cossos menors (Eros, Steins, Itokawa, Bennu —amb model submètric—, Arrokoth). Alguns productes existeixen però estan incomplets o no publicats (Miranda, Tritó).
- Llicències verificades: LOLA (Lluna) i MOLA (Mart) són **domini públic**; MESSENGER (Mercuri), Dawn (Ceres/Vesta) i el DEM de Cassini (Encèlad) permeten **ús lliure amb citació d'autors**.

## Per què encara no és una fase concreta

- El backend de malla 3D per a cossos irregulars (no DEM 2D pla) **encara no existeix** i passa de ser opcional a ser clau per a Fobos/Deimos i cossos menors.
- No hi ha decisió sobre com s'integra "Go In" amb el terreny local existent (streaming, LOD) més enllà del requisit transversal ja tancat al Pas 37/38.
- No hi ha prioritat tancada de quins cossos, més enllà de Lluna i Mart, entren a la primera versió.

## Preguntes obertes que cal resoldre abans de convertir-ho en un Pas

1. Quin format de malla/model de forma 3D s'adoptarà per a cossos irregulars (Fobos, Deimos, asteroides)?
2. Com es defineix exactament la transició GoTo → Go In (animació, temps, punt d'entrada a la superfície)?
3. Quins cossos entren a la v1 més enllà de Lluna (candidat confirmat) i Mart (candidat natural)?
4. Com es reutilitza la càrrega progressiva del Pas 37 per a superfícies planetàries diferents de la Terra?

## Relació amb altres idees pendents

Depèn de/es relaciona amb: navegació lliure pel Sistema Solar, transició terreny local → planeta esfèric, nau 3D en tercera persona, representació del Sol, satèl·lits de Júpiter.
