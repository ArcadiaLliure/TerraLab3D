# Technical Design Document — sistema físic de skyglow

## Context

El Pas 7 actual resol una necessitat visual i de visibilitat amb Bortle/magnitud límit, però no propaga fonts VIIRS a través d'una atmosfera física. El nou sistema substitueix progressivament aquesta autoritat sense trencar els modes manuals existents.

## Goals

Radiància artificial direccional físicament traçable; zenit i cúpules amb un únic kernel; fonts VIIRS segmentades; terreny/curvatura; espectre i RSR; atmosfera extensible; cache error-based; renderer sense stutter; validació científica reproduïble.

## Non-goals v1

Dispersió múltiple general en runtime, inversió espectral única a partir de DNB, meteorologia perfecta, núvols òpticament gruixuts exactes, 60 FPS del kernel, substitució immediata de tots els controls legacy.

## API de domini

`PropagationKernel.evaluate(request: PropagationRequest) -> PropagationResult`.

`AtmosphericOpticsProvider.resolve(query: OpticalQuery) -> OpticalState`.

`SourceModelBuilder.build(observation, spectralHint, emissionModel) -> EmissionRegionSet`.

`DomeCompressor.compress(directionSamples) -> DomeProfile`.

## Errors

Errors tipats: `DatasetUnavailable`, `DatasetQualityInsufficient`, `SpectralPriorUnavailable`, `OpticalFieldIncomplete`, `TerrainCoverageMissing`, `NumericalConvergenceFailure`, `UnsupportedSchemaVersion`, `Cancelled`, `StaleRevision`. Els fallbacks científics són resultats amb procedència, no excepcions amagades.

## Observabilitat

Cada càlcul publica `correlationId`, `revision`, `sourceCount`, `patchCount`, `losCount`, `segmentCount`, `quadratureNodeCount`, `phaseEvalCount`, `cacheDecision`, `latencyMs`, `numericErrorEstimate`, `opticalDependencyCount`, `bandSetId`, `phaseModelId` i flags de fallback.

## Rendiment

No es fixa SLO abans de B0–B7. El render thread no espera el kernel. Les actualitzacions són revisionades i coalescibles. El cache conserva `observerAnchor`, `validityEnvelope`, dependències de tiles i sensibilitats només si el cost/benefici es demostra.

## Recuperació

Si un càlcul falla, es manté l'últim resultat físic vàlid amb indicador `stale` o es torna al fallback legacy segons política explícita. Mai es mostra un resultat parcial com si fos vigent. Restart reconstrueix des de recursos versionats i snapshots, no des de memòria implícita.

## Testing

Unitari: fórmules, unitats, RSR, espectre, fase, quadratura, PCHIP, geometria. Integració: VIIRS→font→kernel→DTO. Contract tests Python/TS. Golden tests amb reference solver. Property tests: positivitat, linealitat en intensitat de font, invariància d'unitats, monotonia de transmissió amb τ, suma commutativa de fonts.

## Alternatives descartades

- un solver zenital i un solver de cúpules: descartat per divergència física;
- gaussianes artístiques: descartades perquè imposen forma no derivada;
- suma en magnitud/log/RGB: descartada perquè viola linealitat radiomètrica;
- ciutat administrativa = font: descartat per manca de base radiomètrica;
- `β_abs=0`: descartat;
- HG com a única representació: descartat; només fallback;
- invalidació per distància fixa: descartada a favor de pressupost d'error;
- segon ray-march per dependències: descartat; es registren durant quadratura;
- HITRAN line-by-line runtime: descartat per cost.

## Migració

Shadow mode obligatori. El sistema legacy i el físic conviuen fins que la validació i el benchmark compleixin criteris. La retirada del legacy requereix evidència i actualització del manual.

## Seguretat de canvis

Cap pas nou pot marcar el Pas 7 com a «físic» retrospectivament. El Pas 7 continua completat per l'abast històric; el dossier documenta una nova vertical que l'amplia.