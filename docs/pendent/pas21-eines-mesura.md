# Pas 21 — Regla, quadrat, rectangle i cercle editables

> Estat: **pendent**. Models, comanda i interfície de renderer existeixen; no hi ha eines connectades a la UI.

## Estat actual verificat

- [x] Existeixen `Measurement`, `MeasurementGeometry`, `MeasurementCalculator`, `StartMeasurement` i `MeasurementBatchComponent`.
- [ ] Càlculs, gestos, historial, picking, render i persistència són pendents.

## Resultat funcional

L'usuari crea regla, quadrat, rectangle i cercle sobre l'esfera celeste; els pot seleccionar, moure, redimensionar, eliminar i desfer, amb etiquetes angulars coherents en canviar càmera, FOV o viewport.

## Dependències

- [Pas 6 — picking](../completat/pas6.md) i [Pas 13 — selecció](../completat/pas13.md).
- [Pas 19](pas19-modes-optics.md) per compartir convencions de camps angulars, no la seva UI.

## Decisions tancades

- Les entitats persisteixen coordenades celestes/horizontals i paràmetres geomètrics, mai píxels de pantalla.
- Distància, arcs geodèsics i punts de destí són càlcul pur renderer-neutral.
- La UI interpreta gestos; el domini aplica operacions immutables; Three.js manté batches retinguts.
- L'historial és acotat i cobreix crear, moure, redimensionar i eliminar.

## Codi existent a reutilitzar

- Models i càlcul: [`measurements/models.py`](../../backend/src/terralab3d/domain/measurements/models.py), [`measurements/calculations.py`](../../backend/src/terralab3d/domain/measurements/calculations.py) i [`measurements/services.py`](../../backend/src/terralab3d/domain/measurements/services.py).
- Aplicació: [`commands.py`](../../backend/src/terralab3d/application/commands.py) i [`use_cases/tools.py`](../../backend/src/terralab3d/application/use_cases/tools.py).
- Escena/render: [`components.py`](../../backend/src/terralab3d/scene/components.py), [`MeasurementLayerRenderer.ts`](../../frontend/src/view/three/layers/MeasurementLayerRenderer.ts) i [`PointerGestureRouter.ts`](../../frontend/src/view/three/picking/PointerGestureRouter.ts).
- Oracle TerraLab: [measurement_tools.py](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/measurement_tools.py).

## Treball pendent

- [ ] Implementar distància angular estable, arcs, rectangle/quadrat orientat i cercle esfèric.
- [ ] Definir operacions immutables i historial undo/redo amb límit configurable.
- [ ] Implementar creació amb preview, finalització/cancel·lació i arbitratge amb navegació de càmera.
- [ ] Implementar picking de forma, vora i nansa; moure i redimensionar sense trencar geometria esfèrica.
- [ ] Generar labels de distància, amplada/alçada, radi/diàmetre i unitat.
- [ ] Publicar batches versionats i actualitzar només l'entitat modificada.
- [ ] Persistir document amb esquema i migració; restaurar-lo en reiniciar.

## Flux tècnic

Gest pointer → intenció tipada → operació sobre document immutable → geometria neutral → delta de batch → renderer. La projecció de nanses a pantalla només existeix al frontend.

## Errors, cancel·lació i recursos

- Gest incomplet o cancel·lat no crea historial; coordenades degenerades generen validació, no geometria corrupta.
- Un canvi de càmera reproyecta la presentació sense mutar el document.
- El renderer allibera geometries, materials, labels i listeners en `dispose`.

## Proves

- Geometria prop de 0/360°, zenit, radi nul i distàncies petites/antipodals.
- Transicions immutables i undo/redo de totes les operacions.
- Gestos, resize, DPR, canvi de FOV i conflicte amb navegació.
- Round-trip i migració del document.

## Criteri de sortida

Les quatre eines són completes, editables, persistents i numèricament estables; el seu render no es reconstrueix globalment ni contamina la UI amb matemàtica esfèrica.

## Evidències

- [ ] Vídeo de cada eina i del cicle crear/moure/redimensionar/eliminar/desfer.
- [ ] Resultats numèrics de casos límit.
- [ ] Reinici amb restauració.
- [ ] Comptadors de geometries abans/després d'editar una sola mesura.

## Fora d'abast

Anotacions terrestres, mesures de superfície geodèsica i exportació GIS.

## Instrucció per a Codex

Completa la vertical sobre els esquelets existents. No emmagatzemis coordenades de pantalla ni implementis la geometria dins dels components UI o Three.js.
