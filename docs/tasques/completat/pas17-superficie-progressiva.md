# Pas 17 — Superfície categòrica, estils i refinament visual

> **Estat:** completat per ajust d'abast. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** superfície categòrica, estils i refinament visual implementat, verificat i observable en el repositori.

## Descripció funcional

L'usuari alterna entre terreny tècnic i cobertura categòrica original o vibrant. La geometria no es reconstrueix en canviar d'estil i una ubicació nova mostra primer una superfície basta que es refina per tiles sense bloquejar la càmera.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d).

## Objectiu

Completar la vertical funcional de «superfície categòrica, estils i refinament visual» de punta a punta, mantenint la separació de responsabilitats i comprovant-ne el rendiment i funcionament observable.

## Dependències

**Depèn de:**
- [Pas 16 — Terreny 3D retingut, tiles, LOD i picking](pas16.md)

**En depenen:**
- [Pas 29 — Superfície semàntica, TLST i refinament](../pendent/pas29-superficie-semantica.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Coordinació: [`land_cover_coordinator.py`](../../../backend/src/terralab3d/application/land_cover_coordinator.py).
- Resolució i mostreig: [`surface/adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/surface/adapter.py) i [`land_cover_port.py`](../../../backend/src/terralab3d/infrastructure/adapters/surface/land_cover_port.py).
- Textura retinguda: [`LandCoverTextureManager.ts`](../../../frontend/src/view/three/terrain/LandCoverTextureManager.ts) i [`DemTerrainLayerRenderer.ts`](../../../frontend/src/view/three/layers/DemTerrainLayerRenderer.ts).
- UI: [`EarthPage.ts`](../../../frontend/src/view/ui/drawer_pages/EarthPage.ts).
- Proves actuals: [`test_land_cover_step17.py`](../../../backend/tests/test_land_cover_step17.py), [`test_terrain_surface_step16.py`](../../../backend/tests/test_terrain_surface_step16.py) i [`land_cover_texture.test.ts`](../../../frontend/src/tests/land_cover_texture.test.ts).
- Oracle TerraLab: [servei de superfície](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/terrain/surface/service.py) i [categories](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/terrain/surface/categorical.py).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

`SetSurfaceMode` o canvi de font → coordinador de superfície → port categòric → tile versionat → bridge binari → gestor de textura retinguda → actualització del material existent. Un canvi només de paleta entra directament al gestor de material.

## Errors, cancel·lació i recursos

- Distingir font absent, cobertura fora d'àrea, `nodata`, error de lectura, cancel·lació i resultat obsolet.
- Cap error d'una font automàtica impedeix provar la següent; un error manual sí es mostra sense substituir silenciosament la font.
- El propietari de cada textura ha de substituir-la atòmicament i executar `dispose` sobre l'anterior.

## Tasques

- [x] Implementació i integració completa de superfície categòrica, estils i refinament visual.

## Criteri de sortida

Les tres presentacions visuals —terreny tècnic, categòric original i categòric vibrant— són utilitzables; les dades informen honestament de font i qualitat; l'estil no reconstrueix la malla; la superfície apareix i es refina progressivament amb memòria acotada.

## Proves i evidències obligatòries

- [x] Numèriques: CRS, veí més proper categòric, `nodata`, ordre de fallback i revisió obsoleta.
- [x] Aplicació: cancel·lació/latest-wins i canvi d'estil sense nova petició de geometria.
- [x] Frontend: la mateixa `BufferGeometry` sobrevive a original/vibrant i a canvis de font compatibles.
- [x] Integració: connexió lenta simulada, primera superfície visible, refinament posterior i navegació fluida.

## Fora d'abast

Descoberta de refinadors semàntics, TLST i AOI avançada ([pas 29](../pendent/pas29-superficie-semantica.md)); meteorologia ([dossier per madurar](../idees-per-madurar/meteorologia.md)).

## Instrucció per a Codex

Implementa només les caselles pendents d'aquest document. Parteix dels coordinadors, adaptadors i renderers enllaçats; no substitueixis el terreny retingut del Pas 16. Tanca el pas només amb proves científiques, integració visual i evidències actualitzades aquí.

## Treball pendent

Cap després del criteri de sortida.
