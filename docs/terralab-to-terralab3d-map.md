# Mapa de transformació TerraLab → TerraLab3D

TerraLab és una font de comportament, fórmules, dades i fixtures. No és una arquitectura que s’hagi de copiar. `REUSE` exigeix igualment tipar i verificar; `EXTRACT` aïlla lògica pura; `ADAPT` conserva comportament darrere un port; `REWRITE` conserva requisits i proves; `DISCARD` elimina codi de presentació obsolet; `NEW` crea una capacitat absent.

| # | Capacitat | Fonts actuals | Problema actual | Destí nou | Estratègia |
|---:|---|---|---|---|---|
| 1 | Fonaments científics compartits | `TerraLab/astro/engine.py; TerraLab/scene/projection.py; TerraLab/widgets/spherical_math.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/science` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 2 | Ubicació de l’observador | `TerraLab/ui/widget_controls_builder.py; TerraLab/terrain/terrain_coordinator.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/observer` + cas d’ús + adaptador/vista corresponent | `ADAPT/EXTRACT` |
| 3 | Temps astronòmic i simulació temporal | `TerraLab/ui/time_bar.py; TerraLab/ui/widget_mixins/controls_time.py; TerraLab/astro/engine.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/time` + cas d’ús + adaptador/vista corresponent | `EXTRACT/REWRITE` |
| 4 | Coordenades i transformacions astronòmiques | `TerraLab/scene/projection.py; TerraLab/widgets/spherical_math.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/coordinates` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 5 | Càmera i navegació 360° | `TerraLab/scene/camera.py; TerraLab/ui/canvas_mixins/interaction.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/navigation` + cas d’ús + adaptador/vista corresponent | `ADAPT/REWRITE` |
| 6 | Fons celeste, dia, nit i crepuscle | `TerraLab/render/sky_renderer.py; TerraLab/runtime/offscreen_renderer.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/sky_background` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 7 | Atmosfera i extinció | `TerraLab/weather/system.py; TerraLab/render/sky_renderer.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/atmosphere` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 8 | Meteorologia | `TerraLab/weather/system.py; TerraLab/weather/metno_provider.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/climate` + cas d’ús + adaptador/vista corresponent | `ADAPT/REWRITE` |
| 9 | Contaminació lumínica | `TerraLab/light_pollution/*; TerraLab/terrain/terrain_coordinator.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/light_pollution` + cas d’ús + adaptador/vista corresponent | `ADAPT/EXTRACT` |
| 10 | Fotometria astronòmica compartida | `TerraLab/visual_magnitude_engine.py; TerraLab/physical_math.py; TerraLab/render/stars_renderer.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/photometry` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 11 | Estrelles i catàleg gaia | `TerraLab/data/star_data_coordinator.py; TerraLab/data/catalogs/star_catalog.py; TerraLab/render/stars_renderer.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/stars` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 12 | Traces circumpolars | `TerraLab/runtime/offscreen_renderer.py; camins overlay circumpolars` | Responsabilitats barrejades o absència de frontera explícita | `domain/star_trails` + cas d’ús + adaptador/vista corresponent | `REWRITE` |
| 13 | Sol, lluna i planetes | `TerraLab/astro/engine.py; TerraLab/ephemeris_coordinator.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/solar_system` + cas d’ús + adaptador/vista corresponent | `ADAPT/EXTRACT` |
| 14 | Eclipsis i ocultacions | `TerraLab/astro/engine.py; lògica d’eclipsis del renderer` | Responsabilitats barrejades o absència de frontera explícita | `domain/eclipses` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 15 | Via làctia i pols planck | `TerraLab/render/sky/milkyway_overlay.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/galactic` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 16 | Objectes de cel profund | `TerraLab/astro/ngc_catalog.py; TerraLab/runtime/offscreen_renderer.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/deep_sky` + cas d’ús + adaptador/vista corresponent | `ADAPT/EXTRACT` |
| 17 | Cerca astronòmica | `TerraLab/astro/search_engine.py; handlers UI de cerca` | Responsabilitats barrejades o absència de frontera explícita | `domain/search` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 18 | Elevacions i dem | `TerraLab/terrain/providers/*; TerraLab/terrain/worker.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/elevation` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 19 | Horitzó topogràfic | `TerraLab/terrain/worker.py; TerraLab/terrain/terrain_coordinator.py; TerraLab/render/horizon_renderer.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/horizon` + cas d’ús + adaptador/vista corresponent | `DISCARD/EXTRACT` |
| 20 | Geometria de terreny 3d | `TerraLab/terrain/overlay.py; TerraLab/terrain/render/*; TerraLab/terrain/surface/geometry.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/terrain` + cas d’ús + adaptador/vista corresponent | `EXTRACT/REWRITE` |
| 21 | Superfícies, ortofoto i cobertura categòrica | `TerraLab/terrain/surface/service.py; TerraLab/terrain/surface/rgb.py; TerraLab/terrain/surface/categorical.py; TerraLab/land_cover/*` | Responsabilitats barrejades o absència de frontera explícita | `domain/surface` + cas d’ús + adaptador/vista corresponent | `ADAPT/EXTRACT` |
| 22 | Telescopi, ocular i geometria òptica | `TerraLab/widgets/telescope_scope_mode.py; TerraLab/ui/widget_controls_builder.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/optics` + cas d’ús + adaptador/vista corresponent | `ADAPT/EXTRACT` |
| 23 | Simulació fotogràfica | `TerraLab/widgets/telescope_scope_mode.py; controls de scope; TerraLab/visual_magnitude_engine.py; TerraLab/physical_math.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/imaging` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 24 | Selecció i inspecció | `TerraLab/runtime/offscreen_renderer.py; TerraLab/ui/astro_canvas.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/selection` + cas d’ús + adaptador/vista corresponent | `REWRITE` |
| 25 | Mesures angulars i formes | `TerraLab/widgets/measurement_tools.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/measurements` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 26 | Constel·lacions editables | `TerraLab/widgets/constellation_drawing.py` | Responsabilitats barrejades o absència de frontera explícita | `domain/constellations` + cas d’ús + adaptador/vista corresponent | `EXTRACT` |
| 27 | Capes i visibilitat | `TerraLab/data/layer_manager.py; checkboxes UI` | Responsabilitats barrejades o absència de frontera explícita | `domain/layers` + cas d’ús + adaptador/vista corresponent | `ADAPT` |
| 28 | Datasets, descàrregues i validació | `TerraLab/data/assets/*; TerraLab/data/source_catalog.py; assistent UI` | Responsabilitats barrejades o absència de frontera explícita | `domain/datasets` + cas d’ús + adaptador/vista corresponent | `ADAPT` |
| 29 | Recursos binaris i cicle de vida | `TerraLab/common/cache.py; caches de catàlegs i terreny` | Responsabilitats barrejades o absència de frontera explícita | `domain/resources` + cas d’ús + adaptador/vista corresponent | `ADAPT` |
| 30 | Progrés, errors, mode de reserva i estat visible | `TerraLab/ui/widget_controls_builder.py; coordinadors` | Responsabilitats barrejades o absència de frontera explícita | `domain/feedback` + cas d’ús + adaptador/vista corresponent | `REWRITE` |

## Disciplina obligatòria

1. Capturar el comportament numèric i funcional actual.
2. Separar ciència, coordinació, I/O i presentació.
3. Traslladar només la responsabilitat que pertoca al paquet destí.
4. Substituir diccionaris per DTO tipats.
5. Eliminar Qt i proveïdors concrets del domini i l’aplicació.
6. Exposar dades grans com recursos binaris versionats.
7. Implementar Three.js com a escena persistent, no com a traductor de QPainter.
8. Comparar cada vertical slice amb TerraLab abans de considerar-la homologada.
