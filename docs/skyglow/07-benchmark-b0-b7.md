# Benchmark executable B0–B7

## Objectiu

Mesurar la frontera precisió↔cost abans de congelar configuració. El benchmark és determinista i no depèn del renderer visual.

## Metadades obligatòries

`gitCommit`, `modelVersion`, `datasetFixtureVersion`, `os`, `cpuModel`, `cpuCores`, `ramBytes`, `pythonVersion`, `numpyVersion`, `compilerFlags`, `gpuModel` si aplica, `timestampUtc`, `seed`.

Seed canònica inicial: `0x544C3344534B5947` (ASCII-like «TL3DSKYG»). No té significat científic; només reproductibilitat.

## Escenaris fixos

1. `FLAT_CLEAR_NEAR`: observador 100 m, 100 fonts sintètiques entre 5–80 km, atmosfera clara homogènia.
2. `CURVED_CLEAR_FAR`: fonts 20–300 km, curvatura activa.
3. `MOUNTAIN_OCCLUSION`: DEM fixture amb oclusions parcials de regions extenses.
4. `AEROSOL_GRADIENT`: dos dominis de tile amb AOD/phase diferents.
5. `SPECTRAL_MIX`: fonts amb cinc barreges SPD.
6. `CLOUD_LAYER`: capa single-scattering només per B6/B7.

Cada escenari usa exactament 100 `EmissionRegion` sintètiques per la sèrie principal i una sèrie d'escalat `N={1,10,25,50,100,200}`. Cada font s'avalua a 9 elevacions; per tant la sèrie principal té 900 LOS per passada abans de refinament intern.

## Warm-up i repeticions

Warm-up: 5 passades completes descartades. Mesura: 30 passades per configuració; si la durada total supera 10 minuts, mínim 10 passades i registrar la desviació del protocol. Ordre de configuracions aleatoritzat amb seed fix per reduir biaix tèrmic. Registrar temperatura/thermal throttling si el sistema ho exposa.

## Toleràncies

Les toleràncies de producció no es fixen aquí. Per benchmark comparatiu: reference solver amb tolerància almenys 10× més estricta que la configuració candidata i comprovació de convergència duplicant exigència. `ε_quad` s'escombra logarítmicament (`1e-3,3e-4,1e-4,3e-5,1e-5` relatiu a escala normalitzada de l'escenari) i es reporta, no es tria per intuïció.

## B0 — infraestructura

Geometria esfèrica, segmentació per tiles, GK 7/15 i integrand trivial. AD OFF. Mesura overhead pur, nodes/LOS, segments/LOS i subdivisions.

## B1a/B1b

B1a: Rayleigh + aerosol HG, 1 banda, 1 base, AD OFF. B1b idèntic amb forward AD `(B,dBx,dBy,dBz)`. `AD_overhead=t_B1b/t_B1a`.

## B2a

Bandes `1,2,4,8`, una base. Reportar `t(Nbands)` i nodes; verificar que la geometria no es repeteix accidentalment.

## B2b

Nombre de bandes candidat fix i bases `1,2,3,5`. Reportar increments marginals i memòria. No assumir linealitat.

## B3

HG, Legendre 4/8/12/20. Per cada variant: cost i error radiomètric/angular contra fase de referència d'ordre alt o taula Mie/mesurada. Mesurar especialment angles de forward scattering.

## B4

Afegir `GasAbsorptionModel` LUT. Comparar contra integració espectral fina de fixture. Mesurar lookup/vectorització i error de `T_eff`.

## B5

Activar watershed fixture ja segmentat i quadtree adaptatiu. Escombrar `ε_patch`; reportar patches efectius, errors, oclusions parcials i cost.

## B6

Afegir núvol single-scattering amb una capa òpticament prima/moderada. No usar aquest benchmark per validar multiple scattering.

## B7 FULL

Configuració candidata completa, AD OFF/ON i propagació d'incertesa OFF/ON. Incloure cache cold, warm hit, small-motion hit, atmospheric-tile change i occlusion flip obligatòriament miss.

## Mètriques

`latencyP50Ms`, `latencyP95Ms`, `latencyP99Ms`, `losPerSecond`, `domeSourcesPerSecond`, `losCount`, `segmentCount`, `quadratureNodeCount`, `phaseEvaluationCount`, `gkSubdivisionCount`, `cacheHits`, `cacheMisses`, `adOverhead`, `uncertaintyOverhead`, `cpuTimeMs`, `wallTimeMs`, `peakRssBytes`, `allocationCount` si disponible, `gpuTimeMs` si aplica, `radiometricError`, `angularError`.

## Esquema JSON mínim

~~~json
{"benchmarkId":"B3","scenario":"AEROSOL_GRADIENT","variant":"LEGENDRE_8","seed":"0x544C3344534B5947","iterations":30,"metrics":{"latencyP50Ms":0,"latencyP95Ms":0,"quadratureNodeCount":0},"accuracy":{"referenceId":"phase-hires-v1","relativeMae":0,"p95DeltaMag":0},"runtime":{},"hardware":{}}
~~~

## CSV

Una fila per iteració, no només agregats: `benchmark_id,scenario,variant,iteration,wall_ms,cpu_ms,los,segments,nodes,phase_evals,gk_subdivisions,rss_bytes,cache_hit,relative_error,p95_delta_mag`.

## Plots obligatoris

latència vs error; ordre Legendre vs error; bandes vs temps; bases vs temps; `ε_quad` vs nodes/error; `ε_patch` vs patches/error; AD overhead; uncertainty overhead; cache hit/miss; histograma p50/p95/p99.

## Criteri de selecció

No hi ha «guanyador» per un únic score. Una configuració només és candidata si compleix simultàniament l'error físic acordat, latència p95 acordada, freqüència de recompute acordada i stutter zero. Els llindars es fixen després de mesures i proves perceptuals.