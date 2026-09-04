# Pas 18 — Meteorologia real, fallback i efectes atmosfèrics

> Estat: **pendent**
> Conserva l’especificació original i encara requereix completar el criteri de sortida.

## Resultat funcional palpable

La capa de clima mostra estat remot o fallback, núvols, boira, precipitació i efectes sobre la transparència del cel.

## Fonts TerraLab a consultar

- `TerraLab/weather/system.py`
- `TerraLab/weather/metno_provider.py`
- `TerraLab/ui/widget_controls_builder.py` — toggle i badge fallback
- `TerraLab/data/layer_manager.py` — `SKY_WEATHER`

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir `ClimateState` amb cobertura per capes, humitat, visibilitat, boira i precipitació.
- [ ] Adaptar MET Norway darrere un port amb User-Agent, caché i errors tipats.
- [ ] Reescriure el fallback com a model determinista amb llavor explícita.
- [ ] Eliminar la generació QPixmap/QPainter de núvols del camí nou.
- [ ] Escollir una representació Three.js viable per núvols i estrats.
- [ ] Implementar moviment per vent independent del FPS.
- [ ] Implementar pluja/neu com a efecte visual amb pressupost de partícules.
- [ ] Aplicar transparència, extinció i boira al cel i als objectes.
- [ ] Mostrar font remota/fallback amb anti-flicker equivalent.
- [ ] Gestionar dades parcials i transicions entre slots meteorològics.
- [ ] Fer que desactivar clima alliberi o suspengui recursos costosos.
- [ ] Comparar estats i efectes amb TerraLab.

## Criteri de sortida

La meteorologia modifica visiblement l’escena, informa de la seva font, funciona offline amb fallback determinista i no bloqueja la càmera o la timeline.

## Evidència obligatòria

- [ ] Captures de cel clar, núvols, boira, pluja i neu.
- [ ] Prova de xarxa absent i recuperació remota.
- [ ] Mesura de frame en condicions cobertes.
- [ ] Assertions de normalització del proveïdor.

## Fora d’abast del pas

No inclou encara la simulació òptica/fotogràfica.
