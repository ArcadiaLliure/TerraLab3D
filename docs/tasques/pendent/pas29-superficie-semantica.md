# Pas 29 — Superfície semàntica, TLST i refinament

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** superfície semàntica, tlst i refinament, integració observable i persistència associada.

## Descripció funcional

L'usuari selecciona una AOI, veu quines fonts i refinadors poden millorar-la i obté una superfície categòrica coherent: una base global canònica i refinaments locals instal·lables, consultats i renderitzats sota demanda.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- La cadena és font + versió + codi → classe canònica; els codis d'un proveïdor mai arriben directament al renderer.
- L'ontologia base té com a mínim 13 classes estables i identificadors independents de color/estil.
- TLST és un contenidor/mosaic versionat amb índex espacial, metadades de font, taula de classes, overviews i checksum; no es pressuposa que existeixi al codi actual.
- Les categories es reprojecten i remostregen amb veí més proper; els overviews acceleren l'espai, no fusionen semàntica.
- La consulta avalua només refinadors instal·lats, de més específic a més general, i pren el primer valor vàlid; la base global és el fallback.
- L'arbre de refinament descriu cobertura i precedència per AOI, no força descàrregues. Qualsevol instal·lació passa pel pas 24.
- El resultat és exclusivament un raster categòric + paleta/estil; no incorpora cap mode fotogràfic.

## Objectiu

Completar la vertical de «superfície semàntica, tlst i refinament» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 17 — Superfície categòrica, estils i refinament visual](../completat/pas17-superficie-progressiva.md)
- [Pas 24 — Catàleg de recursos i descàrregues persistents](pas24-cataleg-recursos-descarregues.md)
- [Pas 25 — Gestor de capes Cel/Terra](pas25-gestor-capes.md)

**En depenen:**
- [Pas 37 — Nomenclàtor GeoNames empaquetat](pas37-geonames-empaquetat.md)
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Domini: [`surface/land_cover.py`](../../../backend/src/terralab3d/domain/surface/land_cover.py), [`surface/models.py`](../../../backend/src/terralab3d/domain/surface/models.py) i [`surface/services.py`](../../../backend/src/terralab3d/domain/surface/services.py).
- Adaptadors actuals: [`surface/adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/surface/adapter.py), [`surface/land_cover_port.py`](../../../backend/src/terralab3d/infrastructure/adapters/surface/land_cover_port.py) i [`landcover/adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/landcover/adapter.py).
- Aplicació/render: [`land_cover_coordinator.py`](../../../backend/src/terralab3d/application/land_cover_coordinator.py), [`LandCoverTextureManager.ts`](../../../frontend/src/view/three/terrain/LandCoverTextureManager.ts) i [`SurfaceLayerRenderer.ts`](../../../frontend/src/view/three/layers/SurfaceLayerRenderer.ts).
- Recursos: [`layer_database.py`](../../../backend/src/terralab3d/infrastructure/resources/layer_database.py) i [`installation_repository.py`](../../../backend/src/terralab3d/infrastructure/resources/installation_repository.py).
- Oracle TerraLab per al mosaic, sense assumir compatibilitat directa: [mosaic.py](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/data/copernicus/mosaic.py).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

AOI/tile + revisió → índex de refinadors instal·lats → lectura TLST específica/base → classes canòniques → tile categòric transferible → cache per clau semàntica → textura/paleta incremental.

## Errors, cancel·lació i recursos

- Fitxers TLST amb versió, checksum, CRS o ontologia incompatibles es rebutgen abans de publicar dades.
- Un refinador corrupte degrada a la següent font i deixa diagnòstic visible; no contamina la cache de base.
- Canviar AOI, estil o revisió cancel·la lectures obsoletes; buffers, rasters i textures tenen propietari i límits explícits.
- La UI mai ofereix una font sense llicència/procedència coneguda ni la descarrega implícitament.

## Tasques

- [x] El pas 17 aporta una base categòrica parcial sobre els tiles del pas 16.
- [x] Existeixen models de superfície, normalització inicial de classes i adaptadors de dades raster.
- [ ] No hi ha mosaic TLST versionat, ontologia canònica completa ni arbre de refinament per AOI.
- [ ] Qualsevol directori o cache residual amb noms `raster`/`refinement` no constitueix un contracte implementat.
- [ ] Tancar ontologia, identificadors, taula de mapeig per font i política de `nodata`/classe desconeguda.
- [ ] Especificar i implementar lector, escriptor, validador i migració TLST amb índex espacial i overviews.
- [ ] Construir la base global a partir de fonts autoritzades i publicar-ne manifest reproducible.
- [ ] Definir descriptors de refinador, cobertura, prioritat, versió, resolució i compatibilitat semàntica.
- [ ] Implementar consulta per tile/AOI de l'arbre: refinadors instal·lats → base → `nodata`, amb cache i cancel·lació.
- [ ] Crear UI d'AOI i arbre de cobertura/refinament connectada als passos 24–25.
- [ ] Enviar tiles categòrics versionats al gestor de textures del pas 17 i aplicar estils sense reconstruir geometria.

## Criteri de sortida

Una AOI produeix el mateix resultat categòric canònic de manera reproducible, utilitza el refinador instal·lat més específic, degrada a la base sense buits artificials i actualitza l'escena incrementalment.

## Proves i evidències obligatòries

- [ ] Golden files TLST: lectura/escriptura, checksum, índex, overviews, migració i corrupció.
- [ ] Mapeig de totes les classes/font, `nodata`, desconeguda i invariància davant canvis de paleta.
- [ ] Precedència amb refinadors superposats, absents, corruptes i resolucions diferents.
- [ ] Antimeridià, vores de tile/AOI, nearest-neighbour i cancel·lació de consultes.
- [ ] Integració visual i pressupostos de CPU, I/O, cache i GPU.
- [ ] Especificació TLST versionada i golden files reproduïbles.
- [ ] Mapa d'una AOI abans/després d'instal·lar un refinador, amb procedència consultable.
- [ ] Proves completes d'ontologia, precedència i corrupció.
- [ ] Mètriques de latència, cache, bytes i textures en una navegació sostinguda.

## Fora d'abast

Inferència automàtica de classes amb IA, edició manual de l'ontologia i dades hidrogràfiques encara immadures.

## Instrucció per a Codex

No pressuposis cap TLST o `mosaic.py` local. Defineix primer el format i l'ontologia, després amplia els adaptadors/coordinadors actuals perquè consultin només refinadors instal·lats i publiquin tiles canònics al gestor de textures existent.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
