# Pas 7 — Cel diürn/nocturn, crepuscle, atmosfera visual, contaminació lumínica, Bortle i magnitud límit

> Estat: **completat**  
> Classificat mitjançant implementació, proves i validacions del repositori.

> **Nota**: Aquest pas fusiona l'antic annex (Cel diürn, nocturn, crepuscle i atmosfera visual contínua) amb l'antic Pas 7 (Contaminació lumínica, Bortle i magnitud límit). La fusió és intencionada perquè ambdós sistemes convergeixen en el mateix resultat: llum natural del cel + llum artificial + extinció atmosfèrica + magnitud límit = visibilitat astronòmica final.

## Resultat funcional palpable

El cel passa contínuament de dia a nit; existeixen crepuscles civil, nàutic i astronòmic; alba i posta són visuals i direccionals; zenit i horitzó tenen aspecte diferent; hi ha glow al voltant de la direcció solar; no hi ha quadrícules/tiles visibles; Bortle 1 i Bortle 9 són clarament diferents; mode Bortle funciona; mode magnitud manual funciona; mode automàtic funciona només si hi ha font real; les estrelles s'atenuen de manera contínua; les estrelles invisibles deixen de ser pickables; Gaia NO es reenvia; els buffers estel·lars NO es reconstrueixen; la translació local no recalcula atmosfera ni contaminació; camera rotation NO genera bridge calls.

## Fonts TerraLab a consultar

- `TerraLab/render/sky_renderer.py` — `sky_color_phys()` i `draw_background()`
- `TerraLab/light_pollution/bortle.py` — SQM→Bortle
- `TerraLab/light_pollution/mlim.py` — magnitud límit
- `TerraLab/light_pollution/modes.py` — modes automatic/bortle/magnitude
- `TerraLab/light_pollution/processing.py` — pipeline DVNL/SQM (referència, no portar)
- `TerraLab/widgets/visual_magnitude_engine.py` — motor fotomètric
- `TerraLab/widgets/physical_math.py` — math instrumental
- `TerraLab/ui/widget_controls_builder.py` — controls UI
- `TerraLab/ui/time_bar.py` — gradient solar

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Arquitectura

```text
Python domain
├── SolarSkyCalculator
├── LightPollutionModel
├── SkyVisibilityModel
└── SkyEnvironmentComposer
        ↓
SkyEnvironmentSnapshot (typed, generation)
        ↓
Bridge
        ↓
TypeScript
├── SkyEnvironmentState
├── AtmosphereRenderer (fullscreen shader pass)
├── StarVisibilityState (uniforms only)
└── UI/HUD
```

## Tasques

- [x] Implementar posició solar autoritativa (alt, az, ENU) reutilitzable pel futur Sistema Solar.
- [x] Implementar fases twilight categòriques (day/civil/nautical/astronomical/night).
- [x] Implementar twilight factor continu sense salts als boundaries.
- [x] Implementar shader analític continu del cel (zenith, horitzó, glow solar, antisolar, night floor).
- [x] Separar la llum natural del cel de la contaminació lumínica artificial.

- [x] Implementar l’estat tipat dels modes `automatic`, `bortle` i `magnitude`.
- [x] Implementar conversions Bortle ↔ magnitud límit i luminància amb unitats explícites.
- [x] Implementar controls equivalents i labels que canviïn segons el mode.
- [x] Aplicar el límit científic a la selecció o intensitat estel·lar sense reconstruir el catàleg complet.
- [x] Aplicar la brillantor de cel com a uniform de l’atmosfera.
- [x] Preparar els factors de contrast per Via Làctia i NGC.
- [x] Definir un port per a estimació geogràfica automàtica.
- [x] Mostrar clarament si el valor és manual, estimat, raster o fallback.
- [x] Implementar actualització en canviar ubicació o alçada.
- [x] Evitar oscil·lacions visuals quan una estimació remota o raster arriba tard.
- [x] Afegir casos de calibratge i toleràncies de magnitud.
- [x] Comparar classes Bortle i magnituds representatives amb TerraLab.

## Criteri de sortida

Canviar mode o valor produeix un efecte coherent i immediat; l’origen del valor és visible; les fórmules viuen al domini i Three.js només rep paràmetres finals.

## Evidència obligatòria

- [x] Captures Bortle 1, 4, 7 i 9.
- [x] Proves numèriques de conversió.
- [x] Prova de canvi automàtic en reubicar.
- [x] Traça que demostri absència de retransferència de Gaia.

## Fora d’abast del pas

La integració amb raster DVNL/SQM complet s’acaba al pas 23.
