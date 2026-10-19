# Pas 7.11 — Terreny, curvatura i visibilitat física

> **Estat:** completat. **Estat funcional:** observable offline en el domini declarat. **Origen:** planificat. **Abast vigent:** visibilitat directa offline del terreny en ECEF esfèric; sense gate 7.12.

## Descripció funcional

La ruta directa incorpora terreny opac en els trajectes font→P i observador→cel. Les fixtures sintètiques, DEM real, regressions i mesures de cost són verificades; la radiància continua sent offline i prescrita.

## Fonts a consultar

- [Pla canònic](../../skyglow/19-pla-executable-codex.md), [algorismes](../../skyglow/01-especificacio-algorismes.md) i [arquitectura](../../skyglow/02-arquitectura-integracio.md), consultats.
- [Möller–Trumbore, 1997](https://my.eng.utah.edu/~cs6965/papers/MT97.pdf), fórmula d’intersecció; derivació pròpia, cap codi copiat.
- [GDAL, geotransformació](https://gdal.org/en/stable/tutorials/geotransforms_tut.html) i [reprojecció](https://gdal.org/en/stable/programs/gdal_raster_reproject.html): CRS horitzontal i convenció vertical separats.

## Objectiu

Verificar muntanya, font parcial, font llunyana i discontinuïtats amb SG-REF independent. Mesurar el cost d’oclusió. Preservar el pressupost i les evidències espectrals de 7.10.

## Dependències

**Depèn de:**
- [7.10 — Transport espectral](../completat/pas7.10-gas-spectral-kernel.md).

**En depenen:**
- [7.12 — Gate zenital](../pendent/pas7.12-zenith-transport-gate.md), pendent, no s’executa aquí.

## Codi existent a reutilitzar

- **Repositori actual:** REUSE `SphericalFrame`, `RayGeometry`, `ElevationPort`, `RasterioElevationAdapter`, GK15, SourceModel i TransportProfiler. ADAPT kernel B0/B1/B2/B4 i SG-REF. NEW superfície triangular, plans d’ombra i retall d’àrea. DISCARD perfil 2D d’horitzó com substitut del trajecte font→P.
- **Projectes de referència autoritzats:** no s’importa codi extern ni es modifica el checkout TerraLab. La biblioteca DEM configurada només es llegeix mitjançant l’adaptador existent.

## Flux tècnic

DEM amb màscara/procedència → conversió vertical explícita → vèrtexs amb SphericalFrame → triangles ECEF → primera intersecció de LOS i intervals d’ombra de font puntual. Les àrees es resten per polígons d’ombra i s’integren directament; no hi ha alfa ni suavitzat. SG-REF resol sistemes lineals NumPy i franges d’àrea independentment.

## Errors, cancel·lació i recursos

Dades absents, cobertura insuficient, actors sota terra, radis incompatibles i pressupostos excedits produeixen error; no es fabriquen altures. Cancel·lació cooperativa i revisió obsoleta abans de publicar. Cap xarxa/GPU ni índex espacial nou; dades immutables i treball local a la petició.

## Tasques

- [x] Integrar DEM/geodèsia existents per als dos trajectes.
- [x] Incorporar curvatura ECEF/ENU i visibilitat binària explícita.
- [x] Partir discontinuïtats i tractar l’àrea parcial per geometria.
- [x] Verificar fixtures i diagnòstics SG-REF independents.
- [x] Mesurar cost B0/B1/B2/B4 i oclusió.
- [x] Executar regressions i tancar documentació/evidències.

## Criteri de sortida

Els casos sintètics de terreny/curvatura verifiquen topologia i oclusió, documenten la comparació diagnòstica amb SG-REF i detecten els flips com a discontinuïtats. El primer PASS/FAIL numèric de transport és 7.12.

## Proves i evidències obligatòries

- [x] Proves unitàries, propietats i regressions backend.
- [x] Fixtures reproduïbles, refinament d’àrea i contrast independent.
- [x] Cost d’oclusió separat i procedència DEM verificada.
- [x] README, inventari, manual, normes i punt de represa coherents.
- [x] Preservació de totes les evidències anteriors i enllaços locals vàlids.

**Resultats verificats:** 2026-10-19, 427 proves backend (22 noves), SG-REF independent, cost B0/B1/B2/B4 i fonts extenses, Ruff/Pyright afectat sense errors. [Informe, dades i límits](../../evidencies/pas7.11/validacio-terreny-i-visibilitat.md).

## Fora d'abast

- Gate radiomètric 7.12, elecció definitiva del sostre, H i renderer de producte.
- Reutilització per moviment, índexs accelerats, AD, quadtree o FFT.
- El·lipsoide WGS84, transformació geoidal automàtica i relleu absent del DEM.

## Instrucció per a Codex

Primer fes correcta la topologia. No introdueixis reuse per moviment ni comencis 7.12. Conserva les evidències existents. Si no es demostra el criteri de sortida, mantén el pas pendent i documenta la causa.

## Treball pendent

Les verificacions pròpies estan completades. No queda feina pròpia pendent. El sostre de 10 km omet fins al **22,45%** respecte a 50 km en el zenit B4 de 7.10; la cua superior continua desconeguda. La justificació definitiva del domini correspon a 7.12.
