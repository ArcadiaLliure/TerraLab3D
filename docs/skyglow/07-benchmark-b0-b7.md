# Benchmark executable B0–B7

## Objectiu

Mesurar la frontera precisió↔cost de la configuració de runtime **ja escollida** i, quan existeixi, comparar qualsevol backend accelerat amb la ruta directa del mateix operador. El benchmark és determinista i no depèn del renderer visual. El nombre de bandes és configurable i **no es fan benchmarks ni sweeps per triar-lo**.

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

Els valors exploratoris es poden escombrar i reportar, però un PASS/FAIL de producció exigeix la política d'acceptació preregistrada segons V1 i un valor justificat, congelat abans del resultat del candidat. La referència numèrica ha de demostrar convergència i quantificar la incertesa; cap llindar de producció es fixa després de veure els resultats. Els passos 7.9–7.11 poden comparar diagnòsticament amb SG-REF; el primer PASS/FAIL numèric de transport és 7.12.

## Checkpoint Z — gate zenital obligatori

Abans de promoure `DomeProfile`, preregistrar a 7.12 la tolerància runtime↔SG-REF amb l'evidència d'incertesa/convergència de 7.6, sense mirar el residual del runtime candidat. Executar el mateix kernel només a 90° en fixtures sintètiques i almenys una fixture VNP46/model de font/atmosfera/DEM reproduïble. Comparar runtime contra SG-REF en radiància física per banda. Runtime i oracle reben el mateix `SourceModel`; el checkpoint no valida la inferència d'emissió. Reportar error, `coldMs`, `warmMs`, peak RSS i dependències tocades. El checkpoint falla si necessita un factor de calibratge opac o si 90° segueix una ruta diferent.

## B0 — infraestructura

Geometria esfèrica, segmentació per tiles, GK 7/15 i integrand trivial. AD OFF. Mesura overhead pur, nodes/LOS, segments/LOS i subdivisions.

## B1a/B1b

B1a: Rayleigh + aerosol HG, 1 banda, 1 base, AD OFF. B1b idèntic amb forward AD `(B,dBx,dBy,dBz)`. `AD_overhead=t_B1b/t_B1a`.

## B2a — proves espectrals de la configuració activa

Validar el `SpectralBandSet` seleccionat per configuració: longituds, límits nm, pesos, unitats, `bandSetId`, vectorització correcta i compartició de geometria. **No** comparar temps entre valors de N, ni escollir N amb benchmark. Els comptadors de nodes i la telemetria general del runtime poden continuar registrant-se per la configuració activa.

## B2b

Usar el nombre de bandes configurat i bases SPD `1,2,3,5`. Reportar increments marginals de bases i memòria, sense comparar ni seleccionar nombres de bandes.

## B3

HG, Legendre 4/8/12/20. Per cada variant: cost i error radiomètric/angular contra fase de referència d'ordre alt o taula Mie/mesurada. Mesurar especialment angles de forward scattering.

## B4

Afegir `GasAbsorptionModel` LUT. Comparar contra integració espectral fina de fixture. Mesurar lookup/vectorització i error de `T_eff`.

## B5

Activar watershed fixture ja segmentat i quadtree adaptatiu. Escombrar `ε_patch`; reportar patches efectius, errors, oclusions parcials i cost.

## B6

Afegir núvol single-scattering amb una capa òpticament prima/moderada. No usar aquest benchmark per validar multiple scattering.

## B7 FULL

Configuració candidata completa, AD OFF/ON i propagació d'incertesa OFF/ON. Incloure cache cold, warm hit, small-motion hit, moviment continu 3D, precàrrega predictiva ON/OFF, teleport, atmospheric-tile change i occlusion flip obligatòriament miss. Si existeix backend LUT/FFT/precomputat, B7 executa també `directe vs accelerat` en el domini declarat i mesura l'error de l'acceleració. El moviment ràpid ha de demostrar coalescing/cancel·lació i absència d'integració per frame.

## Mètriques

`latencyP50Ms`, `latencyP95Ms`, `latencyP99Ms`, `timeToFirstValidMs`, `recomputeHz`, `losPerSecond`, `domeSourcesPerSecond`, `losCount`, `segmentCount`, `quadratureNodeCount`, `phaseEvaluationCount`, `gkSubdivisionCount`, `cacheHits`, `cacheMisses`, `prefetchHits`, `prefetchMisses`, `cancelledJobs`, `staleResultsDiscarded`, `queueDepthMax`, `bridgeBytes`, `adOverhead`, `uncertaintyOverhead`, `cpuTimeMs`, `wallTimeMs`, `peakRssBytes`, `allocationCount` si disponible, `gpuTimeMs` si aplica, `radiometricError`, `angularError`.

## Esquema JSON mínim

~~~json
{"benchmarkId":"B3","scenario":"AEROSOL_GRADIENT","variant":"LEGENDRE_8","seed":"0x544C3344534B5947","iterations":30,"metrics":{"latencyP50Ms":0,"latencyP95Ms":0,"quadratureNodeCount":0},"accuracy":{"referenceId":"phase-hires-v1","relativeMae":0,"p95DeltaMag":0},"runtime":{},"hardware":{}}
~~~

## CSV

Una fila per iteració, no només agregats: `benchmark_id,scenario,variant,iteration,wall_ms,cpu_ms,los,segments,nodes,phase_evals,gk_subdivisions,rss_bytes,cache_hit,relative_error,p95_delta_mag`.

## Plots obligatoris

latència vs error; ordre Legendre vs error; bases vs temps; `ε_quad` vs nodes/error; `ε_patch` vs patches/error; AD overhead; uncertainty overhead; cache hit/miss; histograma p50/p95/p99.

## Criteri de selecció

No hi ha «guanyador» per un únic score. El nombre de bandes no forma part de la selecció per benchmark. La configuració activa només és candidata si compleix l'error físic congelat al gate pertinent i els SLO de producte aprovats a 7.22. Els llindars de PASS/FAIL es fixen **abans** de la campanya de decisió, amb origen declarat segons V1; els SLO inclouen les mètriques, plataforma i condicions que el requisit aprovat estableixi, sense presumir una constant de stutter. Les mesures exploratòries poden servir per dissenyar el sistema, però no per reescriure retrospectivament el criteri d'acceptació.
