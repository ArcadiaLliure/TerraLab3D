# Idea pendent de madurar — Nau 3D en tercera persona i HUD de viatge

> Estat: **per madurar**. No forma part de l'ordre executable fins que es resolguin les preguntes obertes.

> Origen: pluja d'idees TerraLab3D, bloc "Nueva: nave física en tercera persona" + "HUD de navegación".

## Què s'ha decidit ja

- El viatge no s'hauria de visualitzar només com una càmera flotant: hi ha d'haver una **nau 3D modelada i animada**, visible en **tercera persona**.
- La càmera pot seguir la nau des de darrere, amb certa llibertat per orbitar-hi al voltant sense alterar necessàriament la trajectòria.
- HUD específic en mode nau, amb com a mínim dues accions:
  - **«Continuar viatge»**: reprèn la trajectòria prevista si l'usuari l'ha pausada o s'ha aturat a explorar.
  - **«Tornar»**: abandona el trajecte actual i calcula el retorn a l'origen o a l'últim cos des del qual es va partir.
- La velocitat segueix governada pel rellotge global (vegeu navegació lliure).
- Es considera una extensió natural del mode "navegació pel Sistema Solar", no una funcionalitat separada.

## Per què encara no és una fase concreta

- No hi ha model 3D de la nau ni decisió d'estil visual.
- La semàntica exacta de «Tornar» (origen del viatge? últim cos visitat? configurable?) **encara s'ha de concretar** — queda dit explícitament a la pluja d'idees que "todavía debe concretarse".
- Depèn completament de la navegació lliure pel Sistema Solar, que al seu torn no és una fase encara.

## Preguntes obertes

1. Disseny/estil visual de la nau: genèric, personalitzable, un únic model?
2. Definició exacta de «Tornar»: a on torna exactament l'observador?
3. Com es gestiona la llibertat d'orbitar la càmera al voltant de la nau sense desorientar l'usuari?

## Relació amb el pla i altres idees

[Navegació lliure pel Sistema Solar](navegacio-lliure-sistema-solar.md) (depèn directament), [Go In / superfícies planetàries](go-in-superficies-planetaries.md), i el viatge com a transició real —la norma de no usar pantalles decoratives ja és al [pas 38](../pendent/pas38-homologacio-final.md); aquest dossier només cobreix la nau i el seu HUD.
