# Pas 20 — Simulació fotogràfica, senyal, soroll i llarga exposició

> Estat: **pendent**
> Conserva l’especificació original i encara requereix completar el criteri de sortida.

## Resultat funcional palpable

ISO, exposició, obertura, sensor i tracking produeixen una previsualització fotogràfica coherent amb senyal, soroll, saturació i traces.

## Fonts TerraLab a consultar

- `TerraLab/widgets/visual_magnitude_engine.py`
- `TerraLab/widgets/physical_math.py`
- `TerraLab/widgets/telescope_scope_mode.py`
- `TerraLab/ui/widget_controls_builder.py` — ISO i exposició
- `TerraLab/render/stars_renderer.py` — comportament instrumental actual

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Separar enquadrament òptic de simulació fotomètrica.
- [ ] Definir `ExposureSettings`, guany, senyal, soroll i saturació amb unitats.
- [ ] Implementar relació entre magnitud, flux relatiu, obertura, ISO i exposició.
- [ ] Implementar magnitud límit instrumental.
- [ ] Integrar extinció atmosfèrica i brillantor de fons.
- [ ] Implementar previsualització amb uniforms o postprocessat, no alterant el catàleg científic.
- [ ] Implementar saturació i halo de fonts brillants amb límits visuals.
- [ ] Implementar tracking activat/desactivat i longitud de trace per exposició.
- [ ] Integrar traces circumpolars o curtes segons la configuració.
- [ ] Mostrar paràmetres i estimació de SNR al HUD.
- [ ] Definir metadades reproduïbles de la simulació.
- [ ] Preparar un port d’exportació sense implementar formats no necessaris.
- [ ] Comparar resposta instrumental i magnituds amb TerraLab.

## Criteri de sortida

Modificar ISO, exposició, obertura o sensor produeix un efecte visible i científicament documentat; l’enquadrament i la fotometria són responsabilitats separades.

## Evidència obligatòria

- [ ] Fixtures fotomètriques i proves de monotonicitat.
- [ ] Captures amb exposicions i ISO diferents.
- [ ] Prova de saturació i tracking.
- [ ] Informe de diferències respecte de TerraLab.

## Fora d’abast del pas

L’exportació final d’imatges pot quedar com a extensió posterior si TerraLab no la té homologada.
