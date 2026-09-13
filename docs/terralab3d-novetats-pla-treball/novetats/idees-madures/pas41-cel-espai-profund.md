# Pas 41 — Cel → Espai profund (carta celeste interactiva)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Cielo → Espacio profundo".
> Depèn de: Pas 39 (esquelet del gestor de capes).

## Resultat funcional palpable

Dins de "Cel", la subsecció "Espai profund" mostra una projecció equirectangular 2D del cel amb la Via Làctia dibuixada de forma procedural travessant-la; clicant sobre la Via Làctia, les estrelles de fons o la "galàxia" estilitzada de fons, s'obren targetes amb els recursos corresponents (OpenNGC, Gaia, textures de la Via Làctia, pols de Planck, nucli galàctic).

## Context i decisions preses

- Representació com una **esfera celeste envolupant en projecció 2D equirectangular** ("all-sky"), no com un "Sistema Solar gegant".
- Elements clicables amb **labels perquè l'usuari sàpiga que són interaccionables**:
  - **Via Làctia:** dibuixada de forma procedural creuant la imatge; en fer clic (o hover), es ressalta tota la banda i s'obren les seves targetes (textures a diferents resolucions, pols de Planck, nucli galàctic).
  - **Nucli galàctic:** un cercle dins la banda de la Via Làctia; en passar-hi per sobre es ressalta només el nucli; en clicar-hi s'accedeix a l'animació del forat negre (desenvolupada en una conversa paral·lela, ja disponible com a recurs).
  - **Fons d'estrelles:** capa de fons, dona accés als catàlegs estel·lars (Gaia o el seu substitut).
  - **Galàxia gran desproporcionada** (estil Andromeda, dibuixada de forma senzilla en 2D): porta d'accés a "Objectes de cel profund", on hi ha realment el catàleg **OpenNGC** (actualment l'únic disponible; si en el futur n'hi ha més, es mostraran com a targetes addicionals dins d'aquest mateix accés, no com a icones noves).
- Sota la imatge interactiva, les targetes amb **scroll** (tantes com calgui).
- Botó **"Descarregar tot"** (patró del Pas 39) a la vista.

## Objectiu

Construir la carta celeste 2D interactiva com a porta d'entrada visual als catàlegs de cel profund existents.

## Tasques

- [ ] Generar la projecció equirectangular 2D de la Via Làctia de forma procedural.
- [ ] Implementar el hotspot clicable de la banda de la Via Làctia amb ressaltat en hover.
- [ ] Implementar el hotspot del nucli galàctic dins la banda, amb ressaltat diferenciat i accés a l'animació del forat negre.
- [ ] Implementar el hotspot del fons d'estrelles → targetes de catàleg estel·lar (Gaia).
- [ ] Dibuixar la "galàxia" estilitzada desproporcionada com a hotspot cap a "Objectes de cel profund" (OpenNGC).
- [ ] Llista de targetes amb scroll sota la imatge, per al hotspot seleccionat.
- [ ] Botó "Descarregar tot" reutilitzant el patró del Pas 39.
- [ ] Labels visibles sobre els elements interaccionables perquè l'usuari identifiqui que ho són.

## Criteri de sortida

Cada hotspot (Via Làctia, nucli, estrelles, galàxia/OpenNGC) obre les targetes correctes; el hover distingeix visualment banda completa vs. nucli; la navegació no requereix sortir de la vista 2D.

## Evidència obligatòria

- [ ] Captura de la vista arrel amb els quatre hotspots etiquetats.
- [ ] Captura del hover sobre el nucli galàctic diferenciat de la banda completa.
- [ ] Captura de les targetes d'OpenNGC amb scroll.

## Fora d'abast del pas

Ampliació futura de catàlegs de cel profund més enllà d'OpenNGC (s'afegirien com a targetes noves sense canviar la UI).

## Prompt per a Codex

```
Implementa el Pas 41 (Cel → Espai profund) descrit a
docs/novetats/idees-madures/pas41-cel-espai-profund.md sobre main, després del Pas 39. Construeix una
carta celeste 2D en projecció equirectangular amb la Via Làctia dibuixada de forma procedural, amb
quatre hotspots clicables: banda de la Via Làctia (textures + pols Planck + nucli), nucli galàctic
(accés a l'animació de forat negre ja existent), fons d'estrelles (catàleg Gaia) i una "galàxia"
estilitzada desproporcionada com a porta a "Objectes de cel profund" (catàleg OpenNGC, vegeu
docs/completat/pas11.md). Afegeix labels sobre els elements interaccionables i el patró
"Descarregar tot" del Pas 39.
```
