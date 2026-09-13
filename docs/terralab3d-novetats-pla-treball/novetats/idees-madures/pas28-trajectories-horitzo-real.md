# Pas 28 — Trajectòries i visibilitat amb horitzó topogràfic real

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Trayectorias y visibilidad de objetos".

## Resultat funcional palpable

En seleccionar qualsevol objecte observable (estrella, planeta, satèl·lit, NGC, constel·lació...), TerraLab3D dibuixa la seva trajectòria aparent al cel i marca amb una etiqueta d'hora els punts on surt i es pon, calculats contra el **relleu real** de l'observador (muntanyes incloses), no només l'horitzó matemàtic.

## Context i decisions preses

- Estrelles, planetes, satèl·lits, NGC, etc. comparteixen una abstracció comuna d'**"objecte observable"**: totes tenen trajectòria i visibilitat, però cada tipus la calcula de manera diferent (herència de comportament, no un model únic).
- La trajectòria és una línia; als seus extrems, un label amb l'hora en què l'objecte apareix/desapareix per l'horitzó real (rere una muntanya o el terreny) o pel matemàtic quan no hi ha obstrucció.
- El càlcul ha d'utilitzar el **perfil d'horitzó real** ja disponible al projecte (Pas 15, horitzó i oclusió celeste), no un horitzó pla.
- Aquesta abstracció és la base tant de constel·lacions (Pas 29) com de "El millor d'aquesta nit" (Pas 30) i del planificador (Pas 31): tots pregunten a l'objecte per la seva trajectòria/visibilitat i cada tipus respon a la seva manera.

## Objectiu

Definir i implementar el model comú `ObservableObject` amb trajectòria i visibilitat calculades contra l'horitzó topogràfic real, i el seu renderitzat (línia + etiquetes d'hora).

## Tasques

- [ ] Definir la interfície/abstracció `ObservableObject` (posició aparent en funció del temps, mètode de càlcul de visibilitat).
- [ ] Implementar especialitzacions per estrella, planeta, satèl·lit natural, objecte NGC/IC.
- [ ] Integrar el perfil d'horitzó real (Pas 15) en el càlcul d'aparició/ocultació, en lloc de l'horitzó matemàtic.
- [ ] Renderitzar la trajectòria com una línia contínua sobre l'escena celeste.
- [ ] Renderitzar etiquetes d'hora als extrems (sortida/posta) i, si aplica, al punt d'oclusió per relleu.
- [ ] Gestionar el cas d'objectes circumpolars (sense sortida/posta) i objectes que no arriben mai a ser visibles des de la ubicació actual.
- [ ] Exposar l'API perquè altres funcionalitats (constel·lacions, "el millor d'aquesta nit", planificador) puguin consultar visibilitat/trajectòria de qualsevol objecte de manera uniforme.

## Criteri de sortida

Seleccionar qualsevol tipus d'objecte mostra sempre trajectòria + hores de sortida/posta coherents amb l'horitzó real; el mateix objecte donaria hores diferents si es desactivés l'horitzó real, cosa verificable en una prova de regressió.

## Evidència obligatòria

- [ ] Captura amb un objecte l'ocultació del qual es produeix clarament abans per una muntanya que pel càlcul matemàtic, amb ambdós valors documentats.
- [ ] Prova per a un objecte circumpolar (sense trajectòria de sortida/posta).
- [ ] Prova d'API consultant visibilitat des d'un altre mòdul (per exemple, "el millor d'aquesta nit").

## Fora d'abast del pas

Filtres i llistats agregats sobre múltiples objectes (Pas 30). Integració amb el planificador (Pas 31).

## Prompt per a Codex

```
Implementa el Pas 28 (Trajectòries i visibilitat amb horitzó real) descrit a
docs/novetats/idees-madures/pas28-trajectories-horitzo-real.md sobre main. Defineix una abstracció
ObservableObject compartida per estrelles, planetes, satèl·lits i objectes NGC/IC, amb un mètode de
càlcul de visibilitat que reutilitzi el perfil d'horitzó real ja implementat al Pas 15
(docs/completat/pas15.md) en lloc de l'horitzó matemàtic. Renderitza la trajectòria com a línia amb
etiquetes d'hora de sortida/posta als extrems. Exposa l'API de manera que altres mòduls (constel·lacions,
"el millor d'aquesta nit", planificador) puguin consultar-la sense duplicar el càlcul.
```
