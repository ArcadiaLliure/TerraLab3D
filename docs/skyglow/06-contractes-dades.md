# Contractes de dades

## Regles comunes

Tots els contractes serialitzables tenen `schemaVersion`, unitats explícites, identificadors estables i `Provenance`. Python pot usar dataclasses/Pydantic en implementació; TypeScript usa interfaces readonly. Els arrays espectrals sempre porten `bandSetId` o `basisSetId`.

## Provenance

~~~json
{"provider":"NOAA-NCC","product":"NOAA20_VIIRS_DNB_RSR","releaseId":"final-prelaunch","sourceUrl":"...","retrievedAt":"ISO-8601","sha256":"hex","accessMode":"public-download","redistributionStatus":"UNVERIFIED","transformations":[]}
~~~

### Integritat i adquisició de recursos

Per a assets gestionats pel [Pas 24](../tasques/pendent/pas24-cataleg-recursos-descarregues.md), la provenance pot conservar dues evidències d'integritat amb semàntica diferent:

- `sourceChecksum = {algorithm, value, origin}`: checksum publicat o verificable contra el proveïdor/catàleg. L'algoritme no s'assumeix que sigui SHA-256.
- `localSha256`: SHA-256 calculat per TerraLab3D sobre els bytes finals instal·lats, utilitzat com a fingerprint intern reproduïble.

`localSha256` no pot substituir silenciosament un `sourceChecksum` absent ni presentar-se com a verificació externa. Les credencials d'un proveïdor autenticat no formen part de `Provenance`: només s'hi pot registrar el mode/proveïdor d'accés i una referència no secreta a la resolució de l'asset.

Els recursos dinàmics es documenten amb selectors estables i amb la identitat immutable final resolta. Per VNP46A2.002, el resolver del gestor de descàrregues transforma producte/collection/data/tile o AOI en un grànul concret; `ViirsSourceObservation` consumeix després el fitxer local verificat i no coneix tokens ni implementa transferències.

## EmissionRegion

Python conceptual: `EmissionRegion(id, polygon_wgs84, total_dnb_radiance, radiance_centroid, covariance, patches, source_estimate, provenance)`.

TypeScript DTO només si la UI/debug el necessita; el renderer normalment rep `DomeProfile`, no el quadtree complet.

## RadiancePatch

`id`, `regionId`, `centroidEcefM`, `footprint`, `areaM2`, `upwardEmissionModelId`, `spectralSourceEstimateId`, `childrenIds?`, `errorBound`. La magnitud VNP46 observada no es duplica dins el patch; queda a l'observació/procedència que origina l'estimació de font.

## SpectralBasis / SpectrumHint / SpectralSourceEstimate

`SpectralBasis`: `basisId`, mostres `(wavelengthNm,valuePerNm)`, integral normalitzada, tecnologia, font, llicència.

`SpectrumHint`: observació/prior extern amb `priorId`, pesos inicials, confiança i àmbit espacial/temporal.

`SpectralSourceEstimate`: `basisSetId`, `weights`, `normalizationScale`, `directConstraint=DIRECT_DNB`, `indirectConstraint=INDIRECT_PRIOR`, ensemble, uncertainty.

## SpectralBandSet / BandRadiance

`SpectralBandSet`: `id`, llista ordenada de bandes amb límits nm i funció de ponderació. `BandRadiance`: `bandSetId`, `values`, `unit`. `SpectralConfiguration`: `spectralBandCount` (enter positiu), `bandSetId`, rang, regla determinista de partició o límits explícits i revisió; el nombre d'elements ha de coincidir. No s'accepta `double[8]`/`number[8]` a la frontera ni un N fix. Canviar N invalida caches i projeccions dependents; no es fan benchmarks per seleccionar-lo.

## ViirsSourceObservation

`productId`, `releaseId`, `acquisitionDate`, `radianciaObservada`, `radianceUnit`, `measurementOperatorId=BAND_INTEGRATED`, `qualityFlags`, `provenance`.

`radianciaObservada` no equival a `radianciaArtificialEstimada`; aquesta segona pertany a `SourceModel`. El valor original no es trunca silenciosament a zero.

### Vnp46Observation local (Pas 7.2)

El [lector implementat](../../backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py) retorna un DTO immutable per píxel amb `schemaVersion`, `profileId`, `productId`, `collection`, `acquisitionDate`, fila/columna, latitud/longitud, `rawRadiance`, `radianceUnit`, `qualityFlag`, `qfCloudMask`, `snowFlag`, `latestHighQualityRetrieval`, `isFill`, `classification` i `sourceInferenceCandidate`. La procedència inclou identificador i SHA-256 del grànul, URL d'origen si es coneix, DOI, versions d'algorisme/PGE, temps de producció, període, identificadors de tile, referències d'entrada de processament i atributs autoritatius de la capa. El lector no aplica escala, offset, correcció de punt zero, gap-fill ni inferència d'emissió. El contracte s'ha provat amb fixtures HDF5 i un [grànul binari real aportat localment](../evidencies/pas7.2/validacio-adaptador.md); aquest tile no conté QA 0.

## ViirsSpectralResponse

`sensor`, `platform`, `band=DNB`, `detectorMode=band-averaged|detector-specific`, vector λ/RSR, `releaseId`, `measurementOperatorId=BAND_INTEGRATED`, `sourceUrl`, `retrievedAt`, `sha256`, `accessMode`, `redistributionStatus`, `provenance`.

La selecció de RSR utilitza també `acquisitionDate` de `ViirsSourceObservation`; no es duplica la data al recurs. Si no es pot establir la correspondència release/data, la RSR és `unavailable`.

**Unitat DNB exacta pendent de verificació contra l'ATBD.**

## OpticalParameter<T>

`value`, `sigma?`, `uncertaintyModelId?`, `provenance`, `validTime`, `qualityFlags`. `sigma` no es deriva d'una etiqueta de confiança.

## OpticalState

`position`, `altitudeM`, `time`, `pressurePa`, `temperatureK`, `relativeHumidity`, `gasState`, `aerosolState`, `cloudLayers`, `fieldsProvenance`.

## OpticalTile / OpticalTileBand

`OpticalTile`: `tileId`, `version`, bounds 3D/temps, `bands`, `dependencyHash`.

`OpticalTileBand`: `betaRayleighScaM1`, `betaAerosolExtM1`, `aerosolSingleScatteringAlbedo`, `aerosolPhaseFunctionId`, `gasTransmissionModelRef`, `betaCloudExtM1`, `cloudSingleScatteringAlbedo`, `cloudPhaseFunctionId`.

## PhaseFunction

`phaseFunctionId`, `representation=LEGENDRE`, `coefficients`, `normalization=INTEGRAL_4PI_ONE`, `sourceModel=MIE|MEASURED|TABULATED|DOUBLE_HG|HG_FALLBACK`, `confidence`, `provenance`. Per convenció `a0=1`.

## GasState

`pressurePa`, `temperatureK`, columnes o perfils d'`H2O`, `O3`, `O2`, trace gas profile id i referència de LUT.

## CloudLayer / CloudOptics

`baseAltitudeM`, `topAltitudeM`, `opticalDepth?`, `liquidWaterPath?`, `iceWaterPath?`, `effectiveRadiusUm?`, `betaExt`, `omega0`, `phaseFunctionId`, `provenance`. Camps absents no s'inventen.

## PhotometricProjection

`projectionId`, `sourceRevision`, `kind=PHOTOPIC_LUMINANCE|SQM|TESS_W|CUSTOM_SENSOR`, `value`, `unit`, `spectralResponseId`, `fovModelId?`, `zeroPointId?`, `predictionUncertainty`, `provenance`. Sense resposta/calibratge identificable, la projecció és `unavailable`. Per SQM/TESS, `predictionUncertainty` inclou l'efecte del prior/ensemble espectral quan sigui material; no s'afegeix un camp duplicat d'ensemble.

## SkyRadianceComponents

`bandSetId`, `directions`, components `artificial`, `naturalMoonless`, `moon`, `twilight`, estat `available|unavailable|not_applicable`, versions i provenance. La composició autoritzada és suma lineal només entre camps compatibles; els ports de la vertical 7.51+ poden afegir `solarScattered`/`twilight` i `lunarScattered`, sense reconstruir espectres des de SkyView RGB.

## SkyBrightnessDiagnostics

`reference`: cel nocturn de referència sense Lluna/crepuscle. `instantaneous`: estat real a data/hora. Pot incloure luminància zenital, projeccions SQM/TESS, `bortleEquivalent`, `bortlePolicyId` i incertesa. `bortleEquivalent` de lloc només consumeix `reference`.

## RuntimePerformanceStats

`timeToFirstValidMs`, `kernelLatencyMs`, `cacheDecision`, `recomputeReason`, `prefetchHit`, `cancelledJobs`, `staleResultsDiscarded`, `queueDepth`, `bridgeBytes`, `gpuUploadMs`, `renderThreadStutterMs`. És telemetria, no física.

## PropagationResult

`requestId`, `revision`, `observer`, `directions`, `bandSetId`, `radiance`, `numericError`, `predictionUncertainty`, `cacheValidityUncertainty`, `opticalTileDependencies`, `metrics`, `fallbacks`, `modelVersion`.

## DomeProfile

`sourceRegionId`, `azimuthCenterDeg`, `physicalWidthDeg`, `effectiveWidthDeg`, `elevationSamplesDeg`, `bandRadianceSamples`, `interpolation=PCHIP_LOG`, `epsilonRadiance`, `predictionUncertainty`, `revision`.

## PropagationCacheEntry

`cacheKey`, `observerAnchor`, `validityEnvelope`, `sourceRevision`, `opticalTileDependencies`, `terrainRevision`, `quadtreeRevision`, `result`, `sensitivities?`, `cacheValidityUncertainty`, `createdAt`, `lastValidatedAt`.

## PredictionUncertainty

Components separats: `radiometricRandom`, `radiometricSystematic`, `spectralPriorEnsemble`, `atmospheric`, `numerical`, `modelStructural`, `covarianceRefs`. No hi ha un únic `sigmaTotal` obligatori.

## CacheValidityUncertainty

Descriu incertesa del canvi des de l'entrada cachejada: distribució/quantil de `ΔB`, paràmetres canviats, cota de segon ordre, hipòtesis SPD considerades i decisió hit/miss.

## UncertaintyModel

`provider`, `product`, `variable`, `forecastLeadTime`, `spatialResolution`, `temporalResolution`, `regime`, `bias`, `systematicBiasSigma`, `localRandomSigma`, `correlationModel`, `correlationLength`, `provenance`.

## Exemple DTO de cúpula

~~~json
{"schemaVersion":1,"sourceRegionId":"er-42","azimuthCenterDeg":112.4,"physicalWidthDeg":18.2,"effectiveWidthDeg":11.7,"elevationSamplesDeg":[0.5,2,5,10,20,30,45,60,90],"bandSetId":"VISIBLE_V1_CANDIDATE","radianceUnit":"W m-2 sr-1","interpolation":"PCHIP_LOG","revision":381}
~~~

## Compatibilitat Python/TypeScript

Els noms wire són camelCase. Python tradueix explícitament des de noms interns snake_case. La validació de schema s'executa als dos costats. Qualsevol canvi incompatible incrementa `schemaVersion`; no es reutilitza un camp canviant-ne la unitat.
## Selector visual independent

`skyRenderingMode=simulated|physical` és un contracte de presentació persistent, ortogonal a `lightPollutionMode` i `atmosphereEnabled`. `skyPhysicalAvailability=initializing|available|unavailable` incorpora causa i revisió. Les respostes SQM/TESS provenen de radiància espectral i respostes instrumentals, no del mode visual. Vegeu [contractes del cel físic](../cel-fisic/04-contractes-validacio.md).


## Restriccions de producte VNP46

`VNP46A2.002` és l'entrada operativa congelada al [perfil v1](skyglow-v1-profile.json), amb la capa `DNB_BRDF-Corrected_NTL` i qualitat 0 com a mostra candidata. La comparabilitat de baixa radiància pre/post-2017 no s'assumeix i no s'aplica cap correcció de punt zero universal. El valor cru i els flags es conserven; fill, negatius i qualitat degradada no s'infereixen com a font. Les correccions de producte, inclosa stray light, només s'apliquen a TerraLab3D si el producte/release no les ha aplicat. La política `V1` està preregistrada; cap llindar numèric no es fixa aquí sense procedència.
