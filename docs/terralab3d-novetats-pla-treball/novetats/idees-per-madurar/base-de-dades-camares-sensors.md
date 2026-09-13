# Idea pendent de madurar — Base de dades de càmeres/sensors

> Origen: pluja d'idees TerraLab3D, bloc "Base de datos de cámaras/sensores" / "Pendientes de investigación".

## Què s'ha decidit ja

- Per afinar el simulador fotogràfic (Pas 26), interessaria un selector de model de càmera/sensor d'una llista, que calculés automàticament la mida del marc al cel, estrelles estimades i necessitat de seguiment.
- **Explícitament no bloquejant**: el simulador fotogràfic (Pas 26) **no ha de dependre obligatòriament** d'aquesta base de dades — ha d'acceptar també paràmetres manuals o *presets* interns bàsics mentre no hi hagi font adequada.

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

## Relació amb altres idees pendents

Cap directa. És una millora opcional del Pas 26 (Simulador fotogràfic, ja madur), que ja funciona sense aquesta peça.
