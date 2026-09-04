# Pas 17 — Ortofoto, cobertura categòrica i estils de superfície

> Estat: **pendent, amb implementació parcial**  
> La cobertura categòrica ja és funcional, però el pas encara no compleix tot el criteri de sortida.

## Resultat funcional palpable

El terreny pot alternar entre ortofoto, cobertura categòrica, estil original i vibrant sense reconstruir la geometria.

## Fonts TerraLab a consultar

- `TerraLab/terrain/surface/service.py`
- `TerraLab/terrain/surface/rgb.py`
- `TerraLab/terrain/surface/categorical.py`
- `TerraLab/terrain/surface/geometry.py`
- `TerraLab/land_cover/*`
- `TerraLab/data/layer_manager.py` — superfícies RGB/categòriques

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir ports separats per ortofoto i cobertura categòrica.
- [ ] Adaptar CRS, mostreig, nodata, procedència i resolució.
- [ ] Preservar fallback entre fonts en l’ordre seleccionat.
- [ ] Preservar caché per bytes i caché persistent quan sigui útil.
- [ ] Extreure remostreig, subdivisió adaptativa i LOD renderer-neutral.
- [ ] Publicar textures o atributs categòrics versionats per tile.
- [ ] Implementar materials Three.js separats de la geometria.
- [ ] Implementar estil original i vibrant com a canvi de material/uniforms.
- [ ] Mostrar llegenda de categories quan el mode ho requereixi.
- [ ] Gestionar canvis de font manual/automàtica.
- [ ] Mostrar estat de resolució, CRS, font efectiva i fallback.
- [ ] Evitar tornar a mostrejar quan només canvia l’estil visual.
- [ ] Comparar colors, categories i cobertura amb TerraLab.

## Criteri de sortida

L’usuari pot alternar modes i estils de superfície de manera visible; la geometria roman intacta; nodata i fallback es representen de manera coherent.

## Evidència obligatòria

- [ ] Captures d’ortofoto, categòric original i vibrant.
- [ ] Prova que el canvi d’estil no genera una malla nova.
- [ ] Mesures de sampling, caché, bytes i memòria GPU.
- [ ] Fixtures de nodata i fonts múltiples.

## Fora d’abast del pas

No inclou encara clima dinàmic.
