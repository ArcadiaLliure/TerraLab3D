# Pas 7 — Cel, atmosfera, contaminació lumínica i Bortle

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** cel, atmosfera, contaminació lumínica i bortle implementat, verificat i observable en el repositori.

## Descripció funcional

El cel passa contínuament de dia a nit; existeixen crepuscles civil, nàutic i astronòmic; alba i posta són visuals i direccionals; zenit i horitzó tenen aspecte diferent; hi ha glow al voltant de la direcció solar; no hi ha quadrícules/tiles visibles; Bortle 1 i Bortle 9 són clarament diferents; mode Bortle funciona; mode magnitud manual funciona; mode automàtic funciona només si hi ha font real; les estrelles s'atenuen de manera contínua; les estrelles invisibles deixen de ser pickables; Gaia NO es reenvia; els buffers estel·lars NO es reconstrueixen; la translació local no recalcula atmosfera ni contaminació; camera rotation NO genera bridge calls.

## Fonts a consultar

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

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](pas1.md)
- [Pas 3 — Rellotge de simulació, temps sideral i moviment visible](pas3.md)

**En depenen:**
- [Pas 8.7 — Il·luminació física de l'escena](pas8.7.md)
- [Pas 10 — Via Làctia i pols galàctica Planck](pas10.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

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

## Proves i evidències obligatòries

- [x] Captures Bortle 1, 4, 7 i 9.
- [x] Proves numèriques de conversió.
- [x] Prova de canvi automàtic en reubicar.
- [x] Traça que demostri absència de retransferència de Gaia.

## Fora d'abast

La integració amb raster DVNL/SQM complet s’acaba al pas 23.

## Instrucció per a Codex

Pas 7 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
