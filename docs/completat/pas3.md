# Pas 3 — Rellotge de simulació, temps sideral i moviment visible de la volta celeste

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

La UI disposa de timeline, data, dia anterior/següent i mode temps real; en moure l’hora, una volta celeste de referència gira correctament al voltant de l’eix polar.

## Fonts TerraLab a consultar

- `TerraLab/ui/time_bar.py`
- `TerraLab/ui/widget_mixins/controls_time.py`
- `TerraLab/astro/engine.py`
- `TerraLab/scene/projection.py`
- `TerraLab/application/controller.py`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

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

## Evidència obligatòria

- [ ] Assertions numèriques de JD i LST.
- [ ] Vídeo de timeline, temps real i acceleració.
- [ ] Traça de deltes que demostri que no s’envien recursos grans.
- [ ] Mesura P50/P95 durant arrossegament temporal.

## Fora d’abast del pas

No inclou encara estrelles reals ni efemèrides de cossos.
