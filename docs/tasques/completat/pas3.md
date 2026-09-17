# Pas 3 — Rellotge de simulació, temps sideral i moviment visible

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** rellotge de simulació, temps sideral i moviment visible implementat, verificat i observable en el repositori.

## Descripció funcional

La UI disposa de timeline, data, dia anterior/següent i mode temps real; en moure l’hora, una volta celeste de referència gira correctament al voltant de l’eix polar.

## Fonts a consultar

- `TerraLab/ui/time_bar.py`
- `TerraLab/ui/widget_mixins/controls_time.py`
- `TerraLab/astro/engine.py`
- `TerraLab/scene/projection.py`
- `TerraLab/application/controller.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 2 — Ubicació geogràfica de l'observador i orientació local](pas2.md)

**En depenen:**
- [Pas 4 — Grid celeste, brúixola, etiquetes i HUD](pas4.md)
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](pas5.md)
- [Pas 7 — Cel, atmosfera, contaminació lumínica i Bortle](pas7.md)
- [Pas 8 — Sol, Lluna i planetes amb posicions i aparença reals](pas8.md)
- [Pas 14 — Traces circumpolars i exposició temporal](pas14.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Definir `SimulationInstant`, mode pausat/temps real/simulat i factor de velocitat.
- [x] Implementar comandes de data, hora, dia anterior, dia següent, temps real i velocitat.
- [x] Implementar dia julià, segles julians i temps sideral local amb convencions documentades.
- [x] Construir una timeline de 24 hores amb marcador arrossegable i feedback immediat.
- [x] Mostrar data i hora actuals amb selector de calendari.
- [x] Implementar un rellotge autoritatiu Python amb ticks desacoblats del FPS.
- [x] Enviar al frontend només temps autoritatiu, angle sideral i paràmetres derivats necessaris.
- [x] Interpolar la rotació sideral al frontend entre actualitzacions autoritatives.
- [x] Crear una esfera o node de referència amb meridians celestes per visualitzar el moviment.
- [x] Fer que arrossegar la timeline sigui fluid amb política latest-wins.
- [x] Evitar que un canvi d’un segon recreï càmera, escena o recursos persistents.
- [x] Gestionar salts temporals grans sense interpolacions absurdes.
- [x] Comparar valors de temps sideral i orientació amb TerraLab en dates representatives.

## Criteri de sortida

La timeline i el mode temps real funcionen; la volta de referència es mou de manera contínua i correcta; un tick ordinari només actualitza transforms/uniforms i no recrea objectes Three.js.

## Proves i evidències obligatòries

- [ ] Assertions numèriques de JD i LST.
- [ ] Vídeo de timeline, temps real i acceleració.
- [ ] Traça de deltes que demostri que no s’envien recursos grans.
- [ ] Mesura P50/P95 durant arrossegament temporal.

## Fora d'abast

No inclou encara estrelles reals ni efemèrides de cossos.

## Instrucció per a Codex

Pas 3 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
