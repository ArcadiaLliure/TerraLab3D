# Pas 20 — Simulació fotogràfica, senyal, soroll, traces i exportació

> Estat: **pendent**. Els models de sessió i els ports existeixen; les traces del Pas 14 són funcionals, però no hi ha simulador fotogràfic integrat.

## Estat actual verificat

- [x] Existeixen `ImagingSession`, `ImagingSignalEstimate`, protocols de càlcul i port d'exportació.
- [x] El motor i renderer de traces circumpolars són persistents i controlables.
- [ ] El càlcul fotomètric, la previsualització, el botó «Fer foto» i l'exportació no estan implementats.

## Resultat funcional

Sobre el scope del Pas 19, focal, obertura, sensor, ISO, exposició, atmosfera i tracking produeixen una previsualització reproduïble de senyal, soroll, saturació, magnitud límit i traces, exportable a PNG o JPEG amb metadades.

## Dependències

- [Pas 19 — modes òptics](pas19-modes-optics.md).
- [Pas 14 — traces circumpolars](../completat/pas14.md).
- [Pas 7 — atmosfera i contaminació lumínica](../completat/pas7.md).

## Decisions tancades

- No és un nou mode d'escena: és una capa de càlcul i previsualització sobre `scope`.
- La simulació no modifica magnituds ni registres Gaia; deriva una selecció i paràmetres visuals per captura.
- S'ofereixen regla 500 i NPF com a estimacions identificades, no com a veritat instrumental universal.
- La base de models comercials de càmera és opcional i queda fora; els paràmetres manuals i presets bàsics són suficients.
- Una exportació inclou els paràmetres i revisions científiques que permeten reproduir-la.

## Codi existent a reutilitzar

- Domini: [`imaging/models.py`](../../backend/src/terralab3d/domain/imaging/models.py), [`imaging/calculations.py`](../../backend/src/terralab3d/domain/imaging/calculations.py), [`photometry`](../../backend/src/terralab3d/domain/photometry/README.md) i [`optics/models.py`](../../backend/src/terralab3d/domain/optics/models.py).
- Ports: [`imaging.py`](../../backend/src/terralab3d/application/ports/imaging.py) i [`imaging_export/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/imaging_export/adapter.py).
- Render previst: [`ImagingPreviewLayerRenderer.ts`](../../frontend/src/view/three/layers/ImagingPreviewLayerRenderer.ts) i [`StarTrailLayerRendererImpl.ts`](../../frontend/src/view/three/layers/StarTrailLayerRendererImpl.ts).
- Proves de traces: [`star_trails.test.ts`](../../frontend/src/tests/star_trails.test.ts).
- Oracle TerraLab: [motor de magnitud visual](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/visual_magnitude_engine.py), [matemàtica física](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/physical_math.py) i [proves de referència](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/tests/test_visual_magnitude_engine.py).

## Treball pendent

- [ ] Tancar unitats i invariants de sensor, guany, flux, soroll de lectura/fons, full well, saturació i SNR.
- [ ] Implementar magnitud→flux, senyal, soroll, saturació, magnitud límit i monotonicitat.
- [ ] Integrar extinció atmosfèrica, Bortle i brillantor de fons sense duplicar càlculs.
- [ ] Implementar regla 500 i NPF amb resultat, supòsits i advertiments visibles.
- [ ] Derivar longitud de trace per temps, declinació i tracking; reutilitzar la geometria del Pas 14.
- [ ] Publicar un snapshot versionat de previsualització i aplicar-lo amb uniforms/postprocés persistent.
- [ ] Afegir panell, SNR estimat, límit, saturació, temps sense traces i botó «Fer foto».
- [ ] Exportar PNG/JPEG i metadades: instrument, sensor, UTC, observador, atmosfera, catàleg, tracking i versions.

## Flux tècnic

Canvi de paràmetres → cas d'ús de previsualització → càlcul fotomètric pur → snapshot de captura → renderer de previsualització/trace → exportador a petició. El render loop només aplica estat preparat.

## Errors, cancel·lació i recursos

- Separar configuració invàlida, dades atmosfèriques aproximades, exportació fallida i context gràfic no disponible.
- Cancel·lar una exportació o previsualització substituïda; no aplicar snapshots d'una revisió anterior.
- Targets, textures temporals i URLs de descàrrega tenen propietari i neteja explícits.

## Proves

- Fixtures de flux, SNR, saturació i monotonicitat respecte d'obertura/exposició.
- Casos regla 500/NPF i tracking activat/desactivat.
- Integració amb Bortle/atmosfera i traces.
- Reproducció byte-a-byte de metadades i dimensions d'exportació.
- Prova de recursos i rendiment de la previsualització.

## Criteri de sortida

Els paràmetres modifiquen de forma explicable la captura, la previsualització no altera el catàleg, punts/traces responen al tracking i una exportació es pot reproduir amb les seves metadades.

## Evidències

- [ ] Comparativa curta/llarga, ISO baix/alt i tracking on/off.
- [ ] Taula de regla 500/NPF i fixtures fotomètriques.
- [ ] PNG i JPEG de mostra amb metadades llegides de nou.
- [ ] Mètriques de GPU, memòria i latència d'exportació.

## Fora d'abast

Base comercial de càmeres ([idea per madurar](../idees-per-madurar/base-de-dades-camares-sensors.md)) i interpretació de fotografies reals ([pas 30](pas30-plate-solving.md)).

## Instrucció per a Codex

Implementa aquesta capacitat sobre el scope i les traces existents. Mantén separats enquadrament, càlcul fotomètric, render i exportació; documenta qualsevol aproximació científica.
