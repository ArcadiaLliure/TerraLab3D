# Pas 48 — Cims i muntanyes (nomenclàtor + visualització)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Picos y montañas" + "Visualización de cimas".

## Resultat funcional palpable

Els cims visibles des de la posició de l'observador es poden mostrar amb el seu nom real: en mode prismàtics, els que entren dins la mira; opcionalment, tots els cims disponibles, amb una línia vertical i el nom escalat segons el zoom per evitar col·lisions d'etiquetes.

## Context i decisions preses

- **GeoNames també serveix com a nomenclàtor de cims** (classe relleu). **No confondre amb el DEM**: el DEM és geometria (l'altura real del terreny, ja disponible al projecte); GeoNames aporta el nom i la localització puntual del cim, res més.
- **Forma de mostrar-ho, decidida després de dubtar entre diverses opcions:** combinar dues formes —
  - en **mode prismàtics**, es mostren sempre visibles els cims que **estan dins del camp de la mira** (o el que s'apunta directament);
  - com a **opció global**, es poden mostrar **tots** els cims disponibles, independentment del mode.
- **Etiqueta:** no un label a cada cim indiscriminadament (es trepitgen quan hi ha cims molt junts). Solució acordada: **línia vertical** des del punt del cim cap amunt, amb el **label flotant a dalt, escalat segons el nivell de zoom** perquè no es trepitgin. Si estan molt junts, s'agrupa o es prioritza segons el nivell de zoom.

## Objectiu

Integrar el nomenclàtor de cims de GeoNames i el seu sistema de visualització (línia + label escalat) en mode prismàtics i com a capa global opcional.

## Tasques

- [ ] Filtrar la classe de relleu/cims de GeoNames i empaquetar-la com a asset (mateix tractament que assentaments, Pas 47; connecta amb el Pas 49).
- [ ] Renderitzar, en mode prismàtics (Pas 25), els cims continguts dins el camp de la mira amb línia vertical + label.
- [ ] Afegir l'opció global "mostrar tots els cims" independent del mode òptic actiu.
- [ ] Implementar l'escalat del label segons zoom i la lògica d'agrupació/prioritat quan els cims estan molt junts.
- [ ] Assegurar que el DEM (geometria del terreny) i el nomenclàtor de cims (GeoNames) romanen com a fonts separades i sense confusió a nivell de codi.

## Criteri de sortida

En mode prismàtics, apuntar a una serralada mostra els cims corresponents amb nom llegible; activar "mostrar tots" no genera un amuntegament il·legible d'etiquetes a cap nivell de zoom raonable.

## Evidència obligatòria

- [ ] Captura en mode prismàtics apuntant a una serralada amb diversos cims etiquetats.
- [ ] Captura amb l'opció "mostrar tots" activada a diferents nivells de zoom.
- [ ] Captura d'una zona amb cims molt junts mostrant l'agrupació/prioritat de labels.

## Fora d'abast del pas

El DEM en si mateix (ja existent). L'elevació multi-proveïdor (Pas 43).

## Prompt per a Codex

```
Implementa el Pas 48 (Cims i muntanyes) descrit a docs/novetats/idees-madures/pas48-cims-i-muntanyes.md
sobre main, després del Pas 25 (modes òptics) i el Pas 47 (patró de dataset GeoNames empaquetat).
Filtra la classe de relleu/cims de GeoNames i empaqueta-la com a asset. En mode prismàtics, mostra
els cims dins el camp de la mira amb una línia vertical i el label flotant a dalt, escalat segons
zoom. Afegeix una opció global "mostrar tots els cims" independent del mode. Implementa agrupació/
prioritat de labels quan hi ha cims molt junts per evitar que es trepitgin. GeoNames és NOMÉS
nomenclatura i localització puntual; el DEM (geometria) és una font totalment separada, no la toquis.
```
