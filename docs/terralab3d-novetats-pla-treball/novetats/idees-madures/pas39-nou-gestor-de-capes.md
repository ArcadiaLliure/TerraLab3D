# Pas 39 — Nou Gestor de Capes: estructura Cel / Terra

> Estat: **proposta nova — idea madura (disseny tancat a la pluja d'idees)**
> Origen: pluja d'idees TerraLab3D, "Nuevo Gestor de Capas" i tot el bloc de rediseny de la branca "Gestor de Capes".
> Aquest pas és el **paraigua estructural**; els Pas 40–46 en són els blocs concrets.

## Resultat funcional palpable

El gestor de capes deixa de reflectir l'arquitectura interna d'adquisició de dades i passa a reflectir el model mental de l'usuari: dos blocs principals, **Cel** i **Tierra**, cadascun amb una UI visual i interactiva (no una simple llista tècnica).

## Context i decisions preses

- **Diagnòstic del disseny anterior** (branca "Gestor de Capes" existent, descartat explícitament): mesclava tres conceptes diferents —dades disponibles, capes que l'usuari activa/desactiva, i fonts de refinament— i reflectia l'arquitectura interna d'adquisició en lloc del model mental de l'usuari. El refinament s'havia modelat com una família de capes pròpia quan en realitat és **un procés que utilitza capes**.
- **Estructura acordada, de dalt a baix:**
  - Capçalera simple: títol "Gestor de capes", cos actiu (p. ex. "Terra") amb selector per canviar a Lluna/Mart/Fobos..., icones globals d'activar/desactivar-ho tot.
  - Dos blocs principals: **Cel** (Pas 40, Sistema Solar; Pas 41, Espai profund) i **Terra** (Pas 43, Elevació; Pas 44, Superfície).
  - Cada vista visual (mapamundi d'àrea d'interès, esfera celeste, sistema solar animat) manté el mateix component d'Àrea d'Interès quan aplica, reutilitzat entre seccions.
  - Cada targeta/recurs té un botó **"Descarregar tot"** que llança un assistent curt (detecta què hi ha disponible per aquest context, mostra mida/resolució, permet desmarcar el que no es vulgui).
- Aquest pas és conceptual/estructural: defineix el contenidor i la navegació; el contingut de cada secció es detalla als passos 40, 41, 43, 44.

## Objectiu

Construir l'esquelet del nou gestor de capes (capçalera, selector de cos, blocs Cel/Terra) com a contenidor dels blocs de contingut definits als passos següents.

## Tasques

- [ ] Dissenyar i implementar la capçalera: títol, selector de cos actiu, icones globals d'activar/desactivar-ho tot.
- [ ] Implementar la navegació de primer nivell Cel / Terra.
- [ ] Definir el component reutilitzable d'"Àrea d'Interès" com a peça compartida entre seccions de Terra (i, si aplica, entre subseccions de Cel).
- [ ] Definir el patró genèric de targeta amb botó "Descarregar tot" + assistent curt, reutilitzable per totes les seccions.
- [ ] Eliminar el disseny anterior de la branca "Gestor de Capes" un cop migrades les seves peces reaprofitables (component d'Àrea d'Interès, consultes per jerarquia) als nous blocs.
- [ ] Deixar punts d'extensió clars perquè els Pas 40, 41, 43 i 44 s'hi pengin sense tocar l'esquelet.

## Criteri de sortida

Navegar entre Cel i Terra, i canviar de cos actiu, funciona de manera coherent i sense mesclar dades/capes/refinament en un mateix nivell conceptual; el component d'Àrea d'Interès i el patró "Descarregar tot" són reutilitzats, no reimplementats, a cada secció filla.

## Evidència obligatòria

- [ ] Captura de la capçalera amb selector de cos.
- [ ] Captura de la navegació Cel/Terra.
- [ ] Diagrama o document curt confirmant quines peces del disseny anterior s'han reaprofitat i quines s'han eliminat.

## Fora d'abast del pas

El contingut detallat de cada secció: Sistema Solar (Pas 40), Espai profund (Pas 41), sistema de descàrregues complet (Pas 42), Elevació (Pas 43), Superfície (Pas 44).

## Prompt per a Codex

```
Implementa el Pas 39 (esquelet del nou Gestor de Capes) descrit a
docs/novetats/idees-madures/pas39-nou-gestor-de-capes.md sobre main. Substitueix el disseny previ de
la branca "Gestor de Capes" (que mesclava dades disponibles, capes actives i fonts de refinament en
un sol nivell) per l'esquelet nou: capçalera amb selector de cos actiu, navegació de primer nivell
Cel/Terra, un component reutilitzable d'Àrea d'Interès, i un patró genèric de targeta amb botó
"Descarregar tot" + assistent curt. No implementis encara el contingut de cada secció (això és
material dels Pas 40, 41, 43 i 44): centra't en el contenidor i els punts d'extensió. Documenta
quines peces del disseny anterior es reaprofiten literalment.
```
