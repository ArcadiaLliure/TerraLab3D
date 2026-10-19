# Benchmark executable B0–B7

## Objectiu

Mesurar la frontera precisió↔cost de la configuració de runtime **ja escollida** i, quan existeixi, comparar qualsevol backend accelerat amb la ruta directa del mateix operador. El benchmark és determinista i no depèn del renderer visual. El nombre de bandes és configurable i **no es fan benchmarks ni sweeps per triar-lo**.

## Metadades obligatòries

`gitCommit`, `modelVersion`, `datasetFixtureVersion`, `os`, `cpuModel`, `cpuCores`, `ramBytes`, `pythonVersion`, `numpyVersion`, `compilerFlags`, `gpuModel` si aplica, `timestampUtc`, `seed`.

Seed canònica inicial: `0x544C3344534B5947` (ASCII-like «TL3DSKYG»). No té significat científic; només reproductibilitat.

## Benchmark prospectiu d'interactivitat i paral·lelisme (7.18–7.22)

Cal registrar quatre famílies de canvis amb semàntica diferent: **Kelvin/SPD o mescla amb geometria fixa; petit moviment/teleport; canvi d'atmosfera; canvi de DEM i flip d'oclusió**, i distingir inicialització freda, primera resposta vàlida, refinament complet i renderer. Una visualització objectiu de 60 FPS no obliga a recomputar radiància cada frame. Les metes orientatives de 1–3 s i 10–30 s no són SLO; el gate de 7.22 n'ha d'aprovar formalment els llindars i la plataforma abans del PASS/FAIL.

Al 7.18 comparar serial, vectoritzat/compilat si és admissible i CPU multicore **1/2/4/6 nuclis quan l'equip ho permeti**, per a punts, fonts extenses/oclusions i atmosfera variable, reportant P50/P95/P99 amb mida mostral declarada, throughput LOS/s, wall/CPU, sobrecàrrega d'inici/IPC, RAM/RSS i error. Al 7.21 repetir amb workers persistents, cache i càrrega de moviments/kelvins; al 7.22 avaluar opcions GPU/LUT/FFT contra la mateixa referència quan els SLO no es compleixin. No usar el nombre de bandes com a variable d'optimització ni acceptar divergències radiomètriques ocultes.

Referència conceptual, límits de costs històrics i responsabilitats: [estratègia de rendiment interactiu](21-estrategia-rendiment-interactiu.md).

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

Abans de promoure `DomeProfile`, preregistrar a 7.12 la tolerància runtime↔SG-REF amb l'evidència d'incertesa/convergència de 7.6, sense mirar el residual del runtime candidat. Executar el mateix kernel a 90° amb [fonts S definides](../evidencies/pas7.5/validacio-source-model-s-v1.md), atmosfera i DEM reproduïbles. Comparar runtime contra SG-REF en radiància física per banda; tots dos consumeixen el mateix `SourceModel` S. Aquest checkpoint **no exigeix** una font Black Marble C/H admissible ni valida inferència d'emissió urbana. Les fonts C relatives de 7.5.1 s’inclouen en el transport compartit conservant plataforma/producte/període, hipòtesis i escala; l’homologació empírica H continua separada. Reportar error, `coldMs`, `warmMs`, peak RSS i dependències tocades. El checkpoint falla si necessita un factor de calibratge opac o si 90° segueix una ruta diferent.

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

## B0 executat a 7.7

La [campanya B0](../evidencies/pas7.7/validacio-b0.md) aplica el [protocol congelat](../evidencies/pas7.7/protocol-b0-v1.json): seed canònica, nou elevacions, cinc warm-ups i trenta passades per N=1/10/25/50/100/200. Els 100 rectangles SourceModel S de la sèrie principal són les fixtures geomètriques equivalents a regions sintètiques; encara no existeix EmissionRegion de producte. Només els ancoratges orienten els LOS i no s’integra emissió ni se n’aproxima l’àrea al centre.

Es mesura `FLAT_CLEAR_NEAR_GEOMETRY_ONLY` amb esfera ECEF/ENU i cel·les cartesianes/altures definides, no OpticalTiles reals. El CSV conté una fila per passada i `run_id` compartit amb el JSON. Errors radiomètrics/magnituds són null/buits, no zeros ficticis. RSS és working set i peak de vida del procés; flags del compilador, temperatura o throttling desconeguts queden null amb causa. Els gràfics d’escalat i distribució de latència són observacions de B0, sense SLO ni selecció de bandes. Plots de Legendre/AD/cache/òptica i els altres escenaris continuen als benchmarks posteriors.

## B1a executat a 7.9

La [campanya B1](../evidencies/pas7.9/validacio-b1.md) aplica un [protocol prospectiu](../evidencies/pas7.9/protocol-b1-v1.json) monocromàtic de 550 nm. Fonts S puntuals definides i medi homogeni P/T/aerosol prescrit, amb esfera ECEF/ENU; no s’han col·lapsat àrees al centre. Sèrie N=1/10/25/50/100/200, nou elevacions, cinc escalfaments i 60 passades mesurades en total; desviació temporal registrada al JSON si escau. La sèrie principal té 100 fonts/900 LOS.

Els set diagnòstics revaliden la referència per Rayleigh, HG explícit de fallback, fase tabulada vs definició analítica, gradient lateral, perfil vertical, rectangle directe i escala relativa C. El CSV conserva cada mesura i comptadors de transmissió/fase; els residuals runtime↔SG-REF no tenen gate de transport. Plots de fase/residuals i escalat/histograma són actuals. B1b/AD i plots Legendre/cache continuen als seus passos; cap banda, fase comprimida, SLO ni cache no s’ha escollit per aquests temps.

## Estat verificat de 7.10 (2026-10-19)

Campanya 7.10: B0/B1/B2/B4, 100 punts/900 LOS, 5 escalfaments i 10 mesures per configuració segons excepció >600 s. p50 0,391/21,003/27,155/29,493 s. Temps exclusius per etapa, CPU global i RSS raw. SPD B1 històrica i B2/B4 LED-B3 declarades; 400/800 intervals derivats dels nusos, sense sweep de N. La passada final després de la partició T és diagnòstica d'una sola mesura; els perfils variables 0–50 km es documenten separadament i no són SLO. [Evidències i límits](../evidencies/pas7.10/validacio-espectral-i-gasos.md).

## Resultat del checkpoint7.12

[Gate verificat](../evidencies/pas7.12/validacio-gate-transport.md) en domini registrat:9 S PASS,6 contrasts addicionals al sostre75km i42 passades verticals. Cua superior positiva condicionada, sense factor de calibratge ni branca zenital. Les dues passades actuals per mode900LOS i les àrees d'1LOS no substitueixen els percentils històrics ni fixen SLO; els temps de gate amb concurrència s'etiqueten separadament.7.13 pendent/no iniciat.
