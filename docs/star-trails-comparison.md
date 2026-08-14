# Comparación reproducible de trazas circumpolares

El escenario canónico está versionado en
[`reference-scenarios/star-trails-north-pole.json`](reference-scenarios/star-trails-north-pole.json).
Fija observador, UTC, exposición, cámara, viewport, magnitud, proyección y commits
de referencia. La vista se centra en el polo norte celeste: azimut 0° y elevación
igual a la latitud del observador.

## Procedimiento

1. Usar un viewport CSS de 1920×1080 y DPR 1 en ambas aplicaciones.
2. Fijar Barcelona (41.3874° N, 2.1686° E, 12 m) y
   `2026-08-14T16:00:00Z`.
3. Desactivar tracking, etiquetas de selección y overlays no necesarios. Mantener
   la misma política de terreno, grid, contaminación lumínica y atmósfera.
4. Fijar magnitud límite 6,0 y Bortle 1.
5. Centrar la cámara en azimut 0°, elevación 41.3874° y FOV nominal 120°.
6. Iniciar la circumpolar y llevar el tiempo simulado exactamente a
   `2026-08-14T22:00:00Z` (21.600 s de exposición).
7. Capturar PNG sin reescalado. No comparar una captura HiDPI con otra DPR 1.

## Comprobaciones

- El polo queda en el centro y las trazas no cambian de radio al rotar la cámara.
- El arco de una estrella fija abarca 90.2464118416°, no 90° exactos.
- La proyección conserva los radios y el clipping estereográfico en campo amplio.
- El catálogo Gaia local de TerraLab3D aporta 6.793 estrellas con magnitud ≤ 6,0;
  no interviene el límite de seguridad de 20.000.
- Las líneas tienen cobertura perceptiva aproximada de 1 px, alpha 138/255 y
  composición SourceOver; no deben existir núcleos blancos en las uniones.
- El campo estelar puntual desaparece cuando la exposición es visible. Sol, Luna
  y planetas permanecen en su posición instantánea, sin una rotación estelar
  científicamente falsa.

Los tests `star_trails.test.ts` verifican las invariantes numéricas compartidas
con el shader: selección, arco sidéreo, layout instanciado, proyección,
composición, recursos persistentes y transiciones de sesión.
