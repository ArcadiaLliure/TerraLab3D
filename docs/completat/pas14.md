# Pas 14 — Traces circumpolars i exposició temporal

> Estat: **completat**  
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’usuari pot iniciar i aturar una simulació circumpolar, veure el temps acumulat i obtenir traces fluides centrades en el pol celeste corresponent.

## Fonts TerraLab a consultar

- `TerraLab/ui/widget_controls_builder.py` — botó i temps de trace
- `TerraLab/scene/contracts.py` — `TrailState`
- `TerraLab/runtime/offscreen_renderer.py` — acumulació actual
- `TerraLab/render/overlays_renderer.py` o plans equivalents

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir interval, inici, durada, pas temporal i magnitud límit de traces.
- [ ] Calcular la geometria des de coordenades celestes i rotació sideral.
- [ ] Evitar acumular captures raster o textures de pantalla.
- [ ] Crear buffers de línies persistents actualitzables incrementalment.
- [ ] Limitar nombre d’estrelles, segments i memòria.
- [ ] Implementar iniciar, pausar, reprendre, aturar i netejar.
- [ ] Mostrar temps acumulat i estat de l’exposició.
- [ ] Gestionar canvis d’ubicació o data durant una trace.
- [ ] Integrar tracking de muntura quan s’introdueixi la simulació fotogràfica.
- [ ] Aplicar color, opacitat i intensitat derivats de fotometria.
- [ ] Comparar forma i velocitat amb TerraLab.

## Criteri de sortida

Les traces es construeixen incrementalment, es poden controlar, no depenen de la resolució del canvas i no degraden la memòria sense límit.

## Evidència obligatòria

- [ ] Vídeo d’una trace curta i una accelerada.
- [ ] Gràfica de segments i memòria al llarg del temps.
- [ ] Proves de polaritat nord/sud i cancel·lació.

## Fora d’abast del pas

La simulació fotogràfica de llarga exposició completa arriba al pas 20.

## Annex de comparació reproduïble de traces circumpolars

L’escenari canònic està versionat a
[`star-trails-north-pole.json`](../reference-scenarios/star-trails-north-pole.json).
Fixa l’observador, UTC, exposició, càmera, viewport, magnitud, projecció i commits
de referència. La vista se centra en el pol nord celeste: azimut 0° i elevació
igual a la latitud de l’observador.

### Procediment

1. Utilitzar un viewport CSS de 1920×1080 i DPR 1 a les dues aplicacions.
2. Fixar Barcelona (41,3874° N, 2,1686° E, 12 m) i `2026-08-14T16:00:00Z`.
3. Desactivar el seguiment, les etiquetes de selecció i els overlays innecessaris;
   mantenir la mateixa política de terreny, grid, contaminació lumínica i atmosfera.
4. Fixar la magnitud límit a 6,0 i Bortle 1.
5. Centrar la càmera a azimut 0°, elevació 41,3874° i FOV nominal 120°.
6. Iniciar la circumpolar i portar el temps simulat exactament a
   `2026-08-14T22:00:00Z` (21.600 s d’exposició).
7. Capturar un PNG sense reescalat. No comparar una captura HiDPI amb una altra a DPR 1.

### Comprovacions

- El pol queda al centre i les traces no canvien de radi en girar la càmera.
- L’arc d’una estrella fixa abasta 90,2464118416°, no 90° exactes.
- La projecció conserva els radis i el retall estereogràfic en camp ampli.
- El catàleg Gaia local aporta 6.793 estrelles amb magnitud ≤ 6,0; no hi intervé
  el límit de seguretat de 20.000.
- Les línies tenen una cobertura perceptiva aproximada d’1 px, alfa 138/255 i
  composició `SourceOver`; no hi ha d’haver nuclis blancs a les unions.
- El camp estel·lar puntual desapareix quan l’exposició és visible. El Sol, la
  Lluna i els planetes romanen a la posició instantània, sense una rotació
  estel·lar científicament falsa.

Les proves `star_trails.test.ts` verifiquen les invariants numèriques compartides
amb el shader: selecció, arc sideri, disposició instanciada, projecció, composició,
recursos persistents i transicions de sessió.
