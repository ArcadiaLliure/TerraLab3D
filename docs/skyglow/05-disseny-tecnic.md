# Technical Design Document — sistema físic de skyglow

## Context

El Pas 7 actual resol una necessitat visual i de visibilitat amb Bortle/magnitud límit, però no propaga fonts artificials a través d'una atmosfera física. El [Pas 7.5](../evidencies/pas7.5/validacio-source-model-s-v1.md) ja defineix fonts físiques S independents de satèl·lit per alimentar el futur transport. VNP46/VJ146/VJ246 continuen com a observacions candidates C/H diferenciades, amb model de mesura VIIRS DNB per sensor i C relatiu NOAA-20 executable a 7.5.1 i homologació H pendent.

## Goals

Radiància artificial direccional físicament traçable; selecció d'una font Black Marble admissible per dia/AOI/QA/model sense confondre observació i emissió; model DNB/RSR `BAND_INTEGRATED` TOA separat de la correcció L3; `SourceModel` espectral/angular; zenit i cúpules amb un únic kernel; terreny/curvatura; atmosfera extensible; projeccions de sensor separades; acceleracions offline homologades; cache error-based; renderer sense stutter; validació científica reproduïble.

## Non-goals v1

Dispersió múltiple general en runtime, inferir un SPD únic o una emissió angular única a partir de VNP46/DNB, meteorologia perfecta, núvols òpticament gruixuts exactes, 60 FPS del kernel, substituir la física per una convolució FFT general o eliminar immediatament els controls legacy.

## API de domini

`PropagationKernel.evaluate(request: PropagationRequest) -> PropagationResult`.

`AtmosphericOpticsProvider.resolve(query: OpticalQuery) -> OpticalState`.

`SourceModel(source_model_id, revision, definition_reference, geometry, spectrum, angular, amplitude)` és el contracte de transport S/C implementat. `build_conditional_scenarios(observation, response, library, configuration)` de 7.5.1 construeix fonts C relatives; inferència absoluta i H continuen a 7.16–7.24.

`DomeCompressor.compress(directionSamples) -> DomeProfile`.

## Errors

Errors tipats: `DatasetUnavailable`, `DatasetQualityInsufficient`, `SpectralPriorUnavailable`, `OpticalFieldIncomplete`, `TerrainCoverageMissing`, `NumericalConvergenceFailure`, `UnsupportedSchemaVersion`, `Cancelled`, `StaleRevision`. Els fallbacks científics són resultats amb procedència, no excepcions amagades.

## Observabilitat

Cada càlcul publica `correlationId`, `revision`, `sourceCount`, `patchCount`, `losCount`, `segmentCount`, `quadratureNodeCount`, `phaseEvalCount`, `cacheDecision`, `latencyMs`, `numericErrorEstimate`, `opticalDependencyCount`, `bandSetId`, `phaseModelId` i flags de fallback.

## Rendiment

No es fixa SLO abans de B0–B7. El render thread no espera el kernel i **no hi ha integral LOS per frame**. Les actualitzacions són revisionades, coalescibles i cancel·lables; les obsoletes no es publiquen. El cache conserva `observerAnchor`, `validityEnvelope`, dependències de tiles i sensibilitats només si el cost/benefici es demostra. B7 mesura cold start, warm hit, moviment continu, teleport, canvi atmosfèric, occlusion flip, queue depth, treball cancel·lat i time-to-first-valid.

## Recuperació

Si un càlcul falla, es manté l'últim resultat físic vàlid amb indicador `stale` o es torna al fallback legacy segons política explícita. Mai es mostra un resultat parcial com si fos vigent. Restart reconstrueix des de recursos versionats i snapshots, no des de memòria implícita.

## Testing

Unitari: fórmules, unitats, RSR, `BAND_INTEGRATED`, espectre, fase, quadratura, PCHIP, geometria i baixa radiància. El 7.5 ja prova conservació i unitats de S; 7.6–7.15 han de provar `SourceModel S→SG-REF/kernel→DTO`. La integració NOAA-20→font C relativa està verificada a 7.5.1; H exigeix els gates observacionals de 7.16–7.24. El contracte de configuració Python/TS es verifica amb el bridge real a 7.5.1; golden tests de resultats radiatius amb SG-REF són futurs. Property tests: positivitat, linealitat en intensitat de font, invariància d'unitats, monotonia de transmissió amb τ i suma commutativa de fonts.

## Alternatives descartades

- un solver zenital i un solver de cúpules: descartat per divergència física;
- gaussianes artístiques: descartades perquè imposen forma no derivada;
- suma en magnitud/log/RGB: descartada perquè viola linealitat radiomètrica;
- ciutat administrativa = font: descartat per manca de base radiomètrica;
- `β_abs=0`: descartat;
- HG com a única representació: descartat; només fallback;
- invalidació per distància fixa: descartada a favor de pressupost d'error;
- segon ray-march per dependències: descartat; es registren durant quadratura;
- HITRAN line-by-line runtime: descartat per cost;
- conversió directa VNP46/DNB → SQM amb factor empíric opac: descartada;
- tractar VNP46 com a flux hemisfèric lambertià per defecte: descartat;
- col·lapsar el transport espectral a un únic flux perquè VNP46 sigui panchromàtic: descartat;
- usar FFT/LUT com a física diferent del `PropagationKernel`: descartat; només són acceleracions homologables del mateix operador;
- solver nou per cada frame o moviment submètric: descartat; scheduler + cache error-based;
- usar Lluna/crepuscle per reclassificar el `BortleEquivalent` intrínsec del lloc: descartat.

## Migració

Shadow mode obligatori. El sistema legacy i el físic conviuen fins que la validació i el benchmark compleixin criteris. La retirada del legacy requereix evidència i actualització del manual.

## Seguretat de canvis

Cap pas nou pot marcar el Pas 7 com a «físic» retrospectivament. El Pas 7 continua completat per l'abast històric; el dossier documenta una nova vertical que l'amplia.
## Separació de verticals i configuració espectral

El `PropagationKernel` continua exclusivament artificial; Sol/Lluna i limbe són responsabilitat de [7.51+](../cel-fisic/README.md). La configuració espectral del kernel és variable (`spectralBandCount`, `bandSetId`), sense valor fix ni benchmarks per determinar N. El mode simulat/real és permanent i independent del skyglow; no s'elimina el shader actual.
