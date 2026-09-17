# Pas 27 — Carta de recursos d'espai profund

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** carta de recursos d'espai profund, integració observable i persistència associada.

## Descripció funcional

L'usuari explora una carta equirectangular del cel profund, identifica famílies de dades mitjançant hotspots i labels i obre les cards corresponents per instal·lar, actualitzar o eliminar recursos.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- La carta usa projecció equirectangular all-sky coherent amb les coordenades galàctiques ja implementades.
- Quatre hotspots inicials cobreixen Via Làctia, estrelles, objectes de cel profund i recursos compartits; són descriptors de catàleg, no zones científiques rígides.
- Hover/focus revela label i resum; activar obre les cards sense perdre el context de la carta.
- La carta comunica disponibilitat de dades, no densitat ni brillantor científica tret que el descriptor ho declari.
- “Descarregar-ho tot” és un bundle explícit amb mida, dependències i llicències.

## Objectiu

Completar la vertical de «carta de recursos d'espai profund» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 10 — Via Làctia i pols galàctica Planck](../completat/pas10.md)
- [Pas 11 — Cel profund NGC/IC](../completat/pas11.md)
- [Pas 24 — Catàleg de recursos i descàrregues persistents](pas24-cataleg-recursos-descarregues.md)
- [Pas 25 — Gestor de capes Cel/Terra](pas25-gestor-capes.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Projecció/render: [`galacticCoordinates.ts`](../../../frontend/src/view/three/galacticCoordinates.ts), [`GalacticLayerRenderer.ts`](../../../frontend/src/view/three/layers/GalacticLayerRenderer.ts) i [`DeepSkyLayerRenderer.ts`](../../../frontend/src/view/three/layers/DeepSkyLayerRenderer.ts).
- Adaptadors: [`file_assets/galactic.py`](../../../backend/src/terralab3d/infrastructure/adapters/file_assets/galactic.py), [`gaia_catalog/adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/gaia_catalog/adapter.py) i [`ngc_catalog/adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/ngc_catalog/adapter.py).
- Gestor: [`ResourceManagerModal.ts`](../../../frontend/src/view/ui/modals/ResourceManagerModal.ts), [`ResourceManager.ts`](../../../frontend/src/application/ResourceManager.ts) i [`layer_database.py`](../../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Descriptors de catàleg → view-model de hotspots → carta interactiva → selecció de família → cards del pas 24 → treball persistent → delta de disponibilitat reflectit a carta i cards.

## Errors, cancel·lació i recursos

- Una preview o textura absent degrada a la llista textual completa.
- Canviar de hotspot cancel·la càrregues visuals obsoletes, no treballs confirmats.
- En tancar es disposen textures i listeners locals; les dades científiques compartides continuen governades pels seus renderers.

## Tasques

- [x] Els passos 10 i 11 implementen coordenades galàctiques, textura de Via Làctia, Gaia i OpenNGC.
- [x] El gestor central pot representar recursos i variants.
- [ ] No hi ha una carta all-sky interactiva amb hotspots, labels i cards contextuals.
- [ ] Afegir descriptors de família/hotspot, preview, recursos relacionats i ordre estable.
- [ ] Implementar carta responsive amb projecció, labels, hover, focus, teclat i mode tàctil.
- [ ] Connectar hotspots a cards, variants, bundles i estats del gestor central.
- [ ] Reutilitzar previews empaquetades o generades, amb fallback determinista i atribució.
- [ ] Preservar focus i selecció quan arriben deltes de descàrrega.
- [ ] Verificar contrast, reducció de moviment i alternatives textuals.

## Criteri de sortida

Les quatre famílies són descobribles i accessibles des de la carta i des d'una alternativa textual, i qualsevol operació de recursos conserva una única font de veritat al pas 24.

## Proves i evidències obligatòries

- [ ] Transformacions galàctiques ↔ carta, vores de projecció i coordenades de hotspots.
- [ ] Teclat, lector de pantalla, tàctil, hover/focus i viewport petit.
- [ ] Bundle parcial, recurs compartit, preview absent i actualització asíncrona.
- [ ] Pressupost de memòria i desmuntatge net.
- [ ] Captures de carta, focus i cards de les quatre famílies.
- [ ] Proves de projecció i accessibilitat.
- [ ] Vídeo d'una descàrrega que actualitza hotspot i card sense salt de navegació.
- [ ] Mètriques de memòria abans/després de tancar.

## Fora d'abast

Un nou renderer científic de la Via Làctia o dels catàlegs, i el cercador multipestanya.

## Instrucció per a Codex

Implementa la carta com una vista del gestor, reutilitzant projecció i adaptadors existents. No dupliquis els datasets ni converteixis els hotspots en una ontologia científica que el catàleg no garanteix.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
