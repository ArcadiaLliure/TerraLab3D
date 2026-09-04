# Pas 19 — Telescopi, ocular, sensors i enquadrament instrumental

> Estat: **pendent**  
> Conserva l’especificació original i encara requereix completar el criteri de sortida.

## Resultat funcional palpable

L’usuari pot activar un scope circular o rectangular, configurar focal, obertura, ocular, sensor, aspecte i moviment, i anar a unes coordenades RA/Dec.

## Fonts TerraLab a consultar

- `TerraLab/widgets/telescope_scope_mode.py`
- `TerraLab/widgets/telescope_runtime.py`
- `TerraLab/widgets/physical_math.py`
- `TerraLab/ui/widget_controls_builder.py` — panell scope complet

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir `OpticalInstrument`, `SensorFormat`, `FieldOfView` i `ScopeState`.
- [ ] Caracteritzar presets 1/2.8, APS-C i full frame.
- [ ] Implementar FOV horitzontal/vertical des de focal i sensor.
- [ ] Implementar mode telescopi amb ocular, augment i pupil·la de sortida.
- [ ] Implementar obertura per diàmetre o nombre f.
- [ ] Implementar formats circular i rectangular.
- [ ] Implementar aspecte automàtic, 1:1, 4:3, 3:2, 16:9, 21:9 i personalitzat.
- [ ] Renderitzar màscara exterior, vora, retícula, centre i HUD al frontend.
- [ ] Implementar selecció inicial del centre per click i arrossegament del scope.
- [ ] Implementar moviment lent i ràpid amb passos i hold rate equivalents.
- [ ] Implementar entrada RA/Dec i acció Go RA/Dec.
- [ ] Fer que el scope sol·liciti consultes de con Gaia cancel·lables quan calgui més profunditat.
- [ ] Mantenir la càmera i el reticle fluids mentre el catàleg profund carrega.
- [ ] Comparar FOV, presets i moviment amb TerraLab.

## Criteri de sortida

El scope és usable de punta a punta, els camps angulars són correctes, la consulta profunda no bloqueja i els controls equivalen funcionalment als de TerraLab.

## Evidència obligatòria

- [ ] Proves numèriques de FOV, augment i aspectes.
- [ ] Vídeo de scope circular/rectangular i Go RA/Dec.
- [ ] Prova de consulta profunda cancel·lada per un nou focus.
- [ ] Mesura de frame en camp estel·lar dens.

## Fora d’abast del pas

ISO i exposició encara no alteren científicament la captura fins al pas 20.
