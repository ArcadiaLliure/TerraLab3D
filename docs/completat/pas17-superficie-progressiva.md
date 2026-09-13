# Pas 17 — Superfície categòrica i càrrega visual progressiva

> Estat: **parcial**. La cobertura categòrica és funcional; falten els estils complets i la seva càrrega visual progressiva.

## Estat actual verificat

- [x] El Pas 16 ja manté terreny DEM per chunks, LOD i recursos GPU persistents.
- [x] La selecció de cobertura categòrica, el mostreig en el CRS nadiu, `nodata`, procedència i llegenda tenen implementació i proves.
- [x] El frontend aplica textures categòriques sense barrejar-les amb la geometria DEM.
- [ ] El canvi original/vibrant i el refinament progressiu de superfície encara no compleixen la vertical.

## Resultat funcional

L'usuari alterna entre terreny tècnic i cobertura categòrica original o vibrant. La geometria no es reconstrueix en canviar d'estil i una ubicació nova mostra primer una superfície basta que es refina per tiles sense bloquejar la càmera.

## Dependències

- [Pas 16 — terreny retingut, tiles i LOD](../completat/pas16.md).
- [Normes d'arquitectura](../normes_arquitectura.md), especialment escena persistent, cancel·lació i resultats obsolets.

## Decisions tancades

- DEM, color de superfície i estil visual són responsabilitats separades.
- En mode manual només s'utilitza la font escollida; en mode automàtic s'aplica la cadena de prioritat configurada i `nodata` pot continuar a la font següent.
- Les classes categòriques sempre es remostregen amb veí més proper.
- Original/vibrant és un canvi de paleta, material o uniforms, mai una nova malla ni un nou mostreig.
- La qualitat baixa visible és un estat explícit i temporal; no pot presentar-se com a dada científica definitiva.

## Codi existent a reutilitzar

- Coordinació: [`land_cover_coordinator.py`](../../backend/src/terralab3d/application/land_cover_coordinator.py).
- Resolució i mostreig: [`surface/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/surface/adapter.py) i [`land_cover_port.py`](../../backend/src/terralab3d/infrastructure/adapters/surface/land_cover_port.py).
- Textura retinguda: [`LandCoverTextureManager.ts`](../../frontend/src/view/three/terrain/LandCoverTextureManager.ts) i [`DemTerrainLayerRenderer.ts`](../../frontend/src/view/three/layers/DemTerrainLayerRenderer.ts).
- UI: [`EarthPage.ts`](../../frontend/src/view/ui/drawer_pages/EarthPage.ts).
- Proves actuals: [`test_land_cover_step17.py`](../../backend/tests/test_land_cover_step17.py), [`test_terrain_surface_step16.py`](../../backend/tests/test_terrain_surface_step16.py) i [`land_cover_texture.test.ts`](../../frontend/src/tests/land_cover_texture.test.ts).
- Oracle TerraLab: [servei de superfície](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/terrain/surface/service.py) i [categories](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/terrain/surface/categorical.py).

## Treball pendent

- [ ] Publicar atributs categòrics versionats per tile i descartar respostes de revisions antigues.
- [ ] Afegir modes terreny/categòric i estils original/vibrant a la UI.
- [ ] Conservar la geometria i els buffers de posició quan només canvia la font de color o la paleta.
- [ ] Mostrar font efectiva, mode manual/automàtic, resolució, CRS, fallback i fase de refinament.
- [ ] Aplicar primer una representació basta i prioritzar tiles visibles/pròxims abans de refinar la resta.
- [ ] Aplicar a la cobertura categòrica un protocol progressiu amb pressupostos de memòria CPU/GPU.
- [ ] Alliberar textures substituïdes, cancel·lar treball pendent en canviar d'ubicació i conservar la càmera interactiva.

## Flux tècnic

`SetSurfaceMode` o canvi de font → coordinador de superfície → port categòric → tile versionat → bridge binari → gestor de textura retinguda → actualització del material existent. Un canvi només de paleta entra directament al gestor de material.

## Errors, cancel·lació i recursos

- Distingir font absent, cobertura fora d'àrea, `nodata`, error de lectura, cancel·lació i resultat obsolet.
- Cap error d'una font automàtica impedeix provar la següent; un error manual sí es mostra sense substituir silenciosament la font.
- El propietari de cada textura ha de substituir-la atòmicament i executar `dispose` sobre l'anterior.

## Proves

- Numèriques: CRS, veí més proper categòric, `nodata`, ordre de fallback i revisió obsoleta.
- Aplicació: cancel·lació/latest-wins i canvi d'estil sense nova petició de geometria.
- Frontend: la mateixa `BufferGeometry` sobrevive a original/vibrant i a canvis de font compatibles.
- Integració: connexió lenta simulada, primera superfície visible, refinament posterior i navegació fluida.

## Criteri de sortida

Les tres presentacions visuals —terreny tècnic, categòric original i categòric vibrant— són utilitzables; les dades informen honestament de font i qualitat; l'estil no reconstrueix la malla; la superfície apareix i es refina progressivament amb memòria acotada.

## Evidències

- [ ] Captures de terreny, categòric original i vibrant.
- [ ] Identitat o comptador que demostri que un canvi d'estil no crea geometria nova.
- [ ] Vídeo de baixa a alta resolució i mètriques P50/P95 de primera aparició.
- [ ] Mesures de sampling, caché, bridge i memòria GPU.

## Fora d'abast

Descoberta de refinadors semàntics, TLST i AOI avançada ([pas 29](pas29-superficie-semantica.md)); meteorologia ([dossier per madurar](../idees-per-madurar/meteorologia.md)).

## Instrucció per a Codex

Implementa només les caselles pendents d'aquest document. Parteix dels coordinadors, adaptadors i renderers enllaçats; no substitueixis el terreny retingut del Pas 16. Tanca el pas només amb proves científiques, integració visual i evidències actualitzades aquí.
