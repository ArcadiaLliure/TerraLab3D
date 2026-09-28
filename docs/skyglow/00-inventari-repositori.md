# Inventari del repositori rellevant per al nou skyglow

> Inspecció feta sobre `main@e432454273befdcc7f33cb552d2b58cb0719298f`. Aquest document descriu estat observat, no implementació proposada.

## Stack

- Backend: Python 3.12+, `aiohttp`, `numpy`, `astropy`, `rasterio`, `pyproj`, `skyfield`, `spiceypy`.
- Frontend: TypeScript 5.8, Three.js 0.179, esbuild, Vitest.
- Bridge: WebSocket tipat + recursos binaris versionats.
- Arquitectura: `domain/`, `application/`, `infrastructure/adapters/`, `scene/` al backend; contracts/bridge/application/view/three al frontend.

## Skyglow existent

`backend/src/terralab3d/domain/light_pollution/models.py` defineix modes Bortle/magnitud/dataset i models de qualitat del cel. `calculations.py` conté conversions empíriques Bortle↔SQM/magnitud i altres aproximacions. `services.py` orquestra aquest model. `ports.py` defineix fronteres de dades. `infrastructure/adapters/light_pollution/adapter.py` és una especificació abstracta, no un adaptador VIIRS físic complet.

Per tant, la nova vertical no parteix d'un `PropagationKernel` preexistent.

## Atmosfera existent

`domain/atmosphere` conté models/càlculs de cel i estat visual. El Pas 7 construeix `SkyEnvironmentSnapshot` amb colors lineals, turbidity, twilight, Bortle i altres uniforms. No hi ha un `OpticalField(x,y,z,t)` físic amb `β_ext/β_sca/β_abs` per banda.

## Renderer i shader actuals

`frontend/src/view/three/AtmosphereRenderer.ts` manté una caixa invertida persistent i uniforms. Quan `lightPollutionEnabled`, transforma Bortle a `u_artificialBrightness` amb smoothstep cúbic.

`frontend/src/view/three/shaders/skyShader.ts` aplica el glow actual amb `lpFalloff=(1-viewAltNormalized)^2.5`, color fix `COLOR_LP_GLOW` i `mix` sobre el color de cel. Això és una heurística visual; no és suma de radiància física. El shader aplica tone mapping/colorspace al final.

Aquest és el punt concret que el nou renderer haurà de substituir progressivament, mantenint el Pas 7 com a fallback fins a l'homologació.

## Contractes i escena

`frontend/src/contracts/scene.ts` ja disposa de `SceneResourceDescriptor`, `ResourceLifetime`, `SceneDelta` i components versionats. `SkyUniformComponentPayload` només té luminàncies zenit/horitzó, turbidity, twilight i cloudCover; no és suficient per a cúpules espectrals.

`ScienceBridge.ts` exposa deltes, events i recursos binaris. `WebSocketBridge.ts` té listeners tipats, revisions/snapshots per diverses verticals i `binaryType=arraybuffer`. El nou skyglow ha d'afegir contractes específics o un recurs binari versionat, no enviar rasters sencers.

## DEM, geodèsia i ràsters

`infrastructure/adapters/dem/adapter.py` usa Rasterio, NumPy i PyProj, descobreix `.asc/.npy/.tif/.tiff/.tifa`, manté LRU de datasets/windows, transforma CRS i prioritza resolució. Té comptadors `cache_hits`, `cache_misses`, `raster_bytes_read`, `sampled_points`.

`domain/horizon` i `domain/terrain` ja proporcionen la vertical de perfil d'horitzó/oclusió i terreny 3D. El nou kernel ha de reutilitzar la convenció geodèsica, però els raigs source→P poden exigir una API de visibilitat diferent del perfil 2D observer→horizon.

## Cache

Hi ha caches específiques de recursos/ràster i escena, però no una `PropagationCacheEntry` física basada en error de canvi. El nou cache és una capacitat nova i no s'ha de confondre amb l'LRU de finestres DEM.

## Workers i lifecycle

`infrastructure/adapters/workers/adapter.py` és encara una especificació abstracta mínima (`open/close`). Altres verticals del projecte ja implementen correlació/cancel·lació a coordinadors i bridge; el nou càlcul ha de seguir aquest patró real i no assumir un pool genèric ja disponible.

## Tests

El repositori té tests backend i frontend per verticals existents i Vitest al frontend. Els passos skyglow exigeixen unit tests numèrics, contract tests Python↔TS, golden/reference tests i benchmarks separats. La mera existència de models no promou l'inventari.

## Documentació i pla

`AGENTS.md` exigeix skill `plan`; no és accessible en aquest entorn. `docs/README.md`, `docs/normes-arquitectura.md`, `docs/inventari-funcional.md`, `tools/validate_docs.py` i el Pas 22.5 són el protocol de contingència aplicat.

Abans d'aquest dossier, el punt de represa era Pas 24 i el Pas 7 figurava completat pel seu abast visual. El nou bloc 23.50–23.74 s'insereix com a retrofit prioritzat sense reescriure l'evidència històrica del Pas 7.

## Codi experimental

No s'ha localitzat un solver físic VIIRS/RT ja implementat al repositori inspeccionat. Sí existeix el namespace `light_pollution`, però la ruta observable actual és Bortle/magnitud + shader heurístic. Qualsevol experiment local no versionat queda fora d'aquesta inspecció i s'ha de revisar a l'entorn de desenvolupament abans d'implementar.

## Implicacions

1. El backend Python és el lloc natural per a ingestió, segmentació, òptica i kernel.
2. El bridge ja pot transportar revisions i recursos compactes.
3. Three.js ha de rebre `DomeProfile`/LUT, no executar transferència radiativa.
4. DEM/raster/geodèsia són reutilitzables, però la visibilitat source→P és una extensió real.
5. La cache física, AD, biblioteques espectrals/aerosol/núvol i reference solver són nous.