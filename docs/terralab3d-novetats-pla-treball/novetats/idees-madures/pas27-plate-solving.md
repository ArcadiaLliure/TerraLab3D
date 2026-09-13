# Pas 27 — Plate solving (resolució astromètrica de fotografies reals)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Plate solving".

## Resultat funcional palpable

L'usuari puja una fotografia del cel (encara que no tingui EXIF), TerraLab3D detecta el patró d'estrelles, la resol astromètricament contra un índex basat en Gaia, mou automàticament la càmera al camp fotografiat i hi superposa etiquetes d'estrelles i objectes.

## Context i decisions preses

- Funciona **sense EXIF**: la data, ubicació, focal i orientació no són obligatòries. L'EXIF, si hi és, només accelera el procés.
- No és triangulació manual: és **plate solving** / resolució astromètrica, a l'estil `astrometry.net`.
- Flux: foto → detecció d'estrelles (centroides x,y) → patrons geomètrics (triangles/quadrilàters) → comparació amb un índex derivat de Gaia → solució astromètrica (WCS: centre RA/Dec, orientació, escala angular px, FOV, opcionalment distorsió òptica) → moviment de la càmera de TerraLab3D a aquest punt.
- **Gaia sí, però no en brut**: cal construir (durant la instal·lació o distribuir ja construït) un **índex astromètric derivat de Gaia** (filtre de magnitud → divisió de l'esfera celeste → quadrilàters característics → hash geomètric), no recórrer el catàleg sencer en cada resolució.
- Gaia dona astrometria però no **noms humans**: cal un petit catàleg de nomenclatura/crossmatch (Gaia ID ↔ catàleg d'estrelles nomenades) per mostrar "Deneb", "Vega", etc.
- Per a cel profund: WCS de la foto + catàleg NGC/IC → identificar M31, NGC 7000, etc.
- Un cop obtingut el WCS, la fotografia real i el cel simulat de TerraLab3D **comparteixen el mateix sistema de coordenades**: possibilitat d'un comparador amb slider "Foto real ↔ TerraLab3D".
- Aquesta funcionalitat és conceptualment diferent del mode telescopi/simulador fotogràfic (Pas 25/26): un és per *planificar* una captura, l'altre és per *interpretar* una captura ja feta. Encaixen molt bé juntes.

## Objectiu

Implementar el pipeline complet de resolució astromètrica ("blind solve") d'una fotografia i la seva integració amb l'escena de TerraLab3D.

## Tasques

- [ ] Construir l'índex astromètric derivat de Gaia DR3 (filtre de magnitud, quadrilàters característics, hash geomètric), generat en build o distribuït com a asset versionat (igual que altres catàlegs del projecte).
- [ ] Implementar la detecció d'estrelles (centroides) sobre la imatge pujada per l'usuari.
- [ ] Implementar la cerca de patrons geomètrics i la comparació contra l'índex (blind solve).
- [ ] Calcular i retornar el WCS: centre RA/Dec, rotació, escala (arcsec/px), FOV, RMS astromètric.
- [ ] Moure automàticament la càmera de TerraLab3D al camp resolt.
- [ ] Crossmatch amb catàleg de noms d'estrelles i amb OpenNGC per etiquetar estrelles i objectes de cel profund sobre la foto/escena.
- [ ] UI: pujar foto (amb o sense EXIF), botó "Identificar fotografia", visualització dels labels superposats.
- [ ] Comparador amb slider "Foto real ↔ simulació TerraLab3D" reutilitzant el WCS compartit.
- [ ] Gestionar el cas de "no solve" (patró insuficient) amb missatge clar a l'usuari.

## Criteri de sortida

Una fotografia real de prova sense EXIF es resol correctament (RA/Dec del centre dins d'una tolerància raonable), la càmera de TerraLab3D es mou al camp corresponent i les etiquetes d'estrelles/NGC coincideixen amb el contingut real de la foto.

## Evidència obligatòria

- [ ] Almenys 3 fotografies de prova (diferents camps, sense EXIF) resoltes amb èxit, amb el WCS resultant documentat.
- [ ] Captura de l'escena de TerraLab3D movent-se al camp resolt amb etiquetes superposades.
- [ ] Captura del comparador amb slider.
- [ ] Cas de fallada controlada (imatge sense prou estrelles) amb missatge a l'usuari.

## Fora d'abast del pas

Integració amb muntures per corregir l'apuntat automàticament (idea encara immadura, vegeu `docs/novetats/idees-per-madurar/integracio-amb-muntures.md`).

## Prompt per a Codex

```
Implementa el Pas 27 (Plate solving) descrit a docs/novetats/idees-madures/pas27-plate-solving.md sobre
la branca main de TerraLab3D. Construeix un índex astromètric derivat de Gaia DR3 (a l'estil
astrometry.net: quadrilàters característics + hash geomètric), un pipeline de detecció d'estrelles i
blind solve sobre una imatge pujada per l'usuari, i el moviment automàtic de la càmera al WCS resolt.
Reutilitza el catàleg Gaia i el catàleg OpenNGC ja integrats al projecte (vegeu docs/completat/pas5.md
i docs/completat/pas11.md) per al crossmatch de noms. Afegeix el comparador amb slider foto-real vs.
simulació. Documenta el format de l'índex com a asset versionat, seguint el patró d'altres recursos
científics descrit a docs/normes_arquitectura.md.
```
