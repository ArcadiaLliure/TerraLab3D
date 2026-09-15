# Idea pendent de madurar — Base de dades de càmeres/sensors

> Estat: **per madurar**. No forma part de l'ordre executable fins que es resolguin les preguntes obertes.

> Origen: pluja d'idees TerraLab3D, bloc "Base de datos de cámaras/sensores" / "Pendientes de investigación".

## Què s'ha decidit ja

- Per afinar el mode càmera i la previsualització fotogràfica del [Pas 19](../pendent/pas19-modes-optics.md) (que absorbeix l'antic Pas 20), interessaria un selector de model de càmera/sensor d'una llista, que calculés automàticament la mida del marc al cel, estrelles estimades i necessitat de seguiment.
- **Explícitament no bloquejant**: el simulador fotogràfic **no ha de dependre obligatòriament** d'aquesta base de dades — ha d'acceptar també paràmetres manuals o *presets* interns bàsics mentre no hi hagi font adequada.

## Per què encara no és una fase concreta

Pendent d'investigar si existeix una **font reutilitzable comercialment** amb:
- fabricant/model;
- mida del sensor;
- resolució;
- mida de píxel (pixel pitch).

No s'ha trobat ni avaluat cap font concreta durant la pluja d'idees.

## Preguntes obertes

1. Existeix alguna base de dades oberta de sensors de càmera amb llicència d'ús comercial?
2. Si no n'hi ha cap adequada, quants presets manuals (models de càmera habituals en astrofotografia) calen per cobrir el 80% dels casos d'ús sense aquesta base de dades?

## Relació amb el pla i altres idees

Cap directa. És una millora opcional del [Pas 19](../pendent/pas19-modes-optics.md) (antic Pas 20), que s'ha de poder completar sense aquesta peça.
