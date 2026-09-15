# Pas 30 — Plate solving i comparador fotografia/simulació

> Estat: **pendent**. Gaia, OpenNGC, càmera i exportació d'imatge existeixen com a peces reutilitzables; el pipeline astromètric i l'índex derivat no estan implementats.

## Estat actual verificat

- [x] Els catàlegs Gaia i OpenNGC, la selecció celeste i el control de càmera ja funcionen.
- [x] Hi ha un port/adaptador d'exportació d'imatge i la previsualització fotogràfica instrumental està especificada al Pas 19 (després d'absorbir l'antic Pas 20).
- [ ] No existeixen detecció de centroides, índex geomètric Gaia, blind solve, solució WCS ni comparador registrat.

## Resultat funcional

L'usuari carrega una fotografia del cel, fins i tot sense EXIF, TerraLab3D en resol el camp, mou la càmera al WCS obtingut, etiqueta estrelles i objectes de cel profund i compara la foto amb la simulació mitjançant un slider registrat.

## Dependències

- [Pas 5 — Gaia](../completat/pas5.md) i [Pas 11 — OpenNGC](../completat/pas11.md).
- [Pas 19 — modes d'observació instrumental i simulació fotogràfica](pas19-modes-optics.md) (que absorbeix l'antic Pas 20).

## Decisions tancades

- És un `blind solve`: data, ubicació, focal i orientació no són obligatòries; EXIF només restringeix la cerca quan és fiable.
- Pipeline: imatge → centroides → quàdruples invariants → hash geomètric → candidats d'índex → ajust WCS → validació independent.
- Gaia no es recorre en brut: es genera o distribueix un índex derivat, versionat, particionat per escala i cel, amb procedència i criteri de magnitud.
- WCS retorna com a mínim centre RA/Dec, rotació, escala angular, FOV, RMS, nombre d'inliers i, si s'ha ajustat, distorsió.
- Noms humans provenen d'un crossmatch versionat; OpenNGC s'interroga amb l'empremta WCS.
- Foto i simulació es projecten al mateix WCS. El slider no deforma ni aproxima una de les dues capes.

## Codi existent a reutilitzar

- Catàlegs: [`gaia_catalog/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/gaia_catalog/adapter.py), [`ngc_catalog/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/ngc_catalog/adapter.py) i [`star_coordinator.py`](../../backend/src/terralab3d/application/star_coordinator.py).
- Càmera/escena: [`CameraRig.ts`](../../frontend/src/view/three/CameraRig.ts), [`CameraRigImpl.ts`](../../frontend/src/view/three/CameraRigImpl.ts) i [`ThreeSceneHostImpl.ts`](../../frontend/src/view/three/ThreeSceneHostImpl.ts).
- Imatge: [`ports/imaging.py`](../../backend/src/terralab3d/application/ports/imaging.py), [`imaging_export/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/imaging_export/adapter.py) i [`ImagingPreviewLayerRenderer.ts`](../../frontend/src/view/three/layers/ImagingPreviewLayerRenderer.ts).
- Selecció: [`CelestialSelectionController.ts`](../../frontend/src/application/CelestialSelectionController.ts).

## Treball pendent

- [ ] Especificar, construir i validar l'índex astromètric derivat de Gaia amb manifest, particions i golden fixtures.
- [ ] Implementar ingestió segura d'imatge, normalització, detecció/subpíxel de centroides i filtratge d'artefactes.
- [ ] Implementar hash de quàdruples, recuperació de candidats, RANSAC/ajust WCS i validació per estrelles no usades.
- [ ] Exposar progrés i cancel·lació del solve en worker/process, amb límits de memòria i temps.
- [ ] Fer crossmatch de noms i OpenNGC, moure la càmera i dibuixar labels en coordenades WCS.
- [ ] Implementar comparador foto/simulació amb slider, opacitat i reset, compartint exactament la projecció.
- [ ] Donar diagnòstics útils per patró insuficient, desenfocament, escala fora d'índex i solució ambigua.

## Flux tècnic

Fitxer validat → imatge normalitzada → centroides → signatures geomètriques → consulta d'índex Gaia → candidats WCS → ajust/validació → crossmatch → comanda de càmera + overlay registrat.

## Errors, cancel·lació i recursos

- La càrrega limita mida, dimensions i format i no confia en metadades EXIF.
- Cancel·lar o substituir la foto atura CPU/I/O, descarta revisions obsoletes i elimina temporals.
- Un `no solve` no mou la càmera ni conserva overlays parcials; informa la causa probable i les escales provades.
- Imatges, buffers, índexs mmap i textures tenen propietat, cache i disposició explícites.

## Proves

- Com a mínim tres camps sense EXIF, escales/rotacions diferents i WCS de referència.
- Imatges amb soroll, hot pixels, desenfocament, pocs astres, camp ambigu i escala no indexada.
- Determinisme de l'índex, compatibilitat de versió, cancel·lació i pressupostos de temps/memòria.
- Exactitud de labels, moviment de càmera i registre del comparador a cantonades i centre.

## Criteri de sortida

Tres fotografies de prova sense EXIF es resolen dins la tolerància documentada, la càmera i els labels coincideixen amb el camp i els casos sense solució acaben de manera clara, cancel·lable i sense estat parcial.

## Evidències

- [ ] Manifest reproduïble de l'índex i golden fixtures.
- [ ] Taula de WCS esperat/obtingut, RMS, inliers i temps per a tres camps.
- [ ] Captura del camp resolt amb labels i del comparador.
- [ ] Traça de cancel·lació i cas `no solve` controlat.

## Fora d'abast

Correcció automàtica d'una muntura, astrometria de camp extrem sense índex preparat i calibratge fotomètric absolut.

## Instrucció per a Codex

Implementa el solver com una vertical separada de la previsualització fotogràfica del Pas 19, reutilitzant Gaia/OpenNGC, càmera i exportació existents. Versiona l'índex derivat, valida la solució amb estrelles independents i no exigeixis EXIF.
