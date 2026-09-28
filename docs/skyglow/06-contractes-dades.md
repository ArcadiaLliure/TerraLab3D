# Contractes de dades

## Regles comunes

Tots els contractes serialitzables tenen `schemaVersion`, unitats explícites, identificadors estables i `Provenance`. Python pot usar dataclasses/Pydantic en implementació; TypeScript usa interfaces readonly. Els arrays espectrals sempre porten `bandSetId` o `basisSetId`.

## Provenance

~~~json
{"provider":"NOAA-NCC","product":"NOAA20_VIIRS_DNB_RSR","releaseId":"final-prelaunch","sourceUrl":"...","retrievedAt":"ISO-8601","sha256":"hex","accessMode":"public-download","redistributionStatus":"UNVERIFIED","transformations":[]}
~~~

## EmissionRegion

Python conceptual: `EmissionRegion(id, polygon_wgs84, total_dnb_radiance, radiance_centroid, covariance, patches, source_estimate, provenance)`.

TypeScript DTO només si la UI/debug el necessita; el renderer normalment rep `DomeProfile`, no el quadtree complet.

## RadiancePatch

`id`, `regionId`, `centroidEcefM`, `footprint`, `areaM2`, `dnbRadianceNwCm2Sr`, `upwardEmissionModelId`, `spectralSourceEstimateId`, `childrenIds?`, `errorBound`.

## SpectralBasis / SpectrumHint / SpectralSourceEstimate

`SpectralBasis`: `basisId`, mostres `(wavelengthNm,valuePerNm)`, integral normalitzada, tecnologia, font, llicència.

`SpectrumHint`: observació/prior extern amb `priorId`, pesos inicials, confiança i àmbit espacial/temporal.

`SpectralSourceEstimate`: `basisSetId`, `weights`, `normalizationScale`, `directConstraint=DIRECT_DNB`, `indirectConstraint=INDIRECT_PRIOR`, ensemble, uncertainty.

## SpectralBandSet / BandRadiance

`SpectralBandSet`: `id`, llista ordenada de bandes amb límits nm i funció de ponderació. `BandRadiance`: `bandSetId`, `values`, `unit`. No s'accepta `double[8]`/`number[8]` a la frontera.

## ViirsSpectralResponse

`sensor`, `platform`, `band=DNB`, `detectorMode=band-averaged|detector-specific`, vector λ/RSR, `releaseId`, `sourceUrl`, `retrievedAt`, `sha256`, `accessMode`, `redistributionStatus`, `provenance`.

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