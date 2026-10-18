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

El component offline [verificat a 7.4](../tasques/completat/pas7.4-spectral-bandset-validation.md) afegeix `inputSignature`: SHA-256 d'identitat, unitats, suport, nusos i valors de SPD i respostes. `bandSetId` identifica estratègia i límits; **tots dos** han de participar en la identitat d'una futura cache o d'un resultat que reutilitzi aquesta discretització. El contracte serialitzable i la integració amb el kernel continuen pendents; 7.10/7.14 revaliden qualsevol domini espectral ampliat.

### Qualificació del SourceModel per domini S/C/H

El [`SourceModel` implementat a 7.5](../../backend/src/terralab3d/domain/light_pollution/source_model.py) declara `sourceModelId`, `sourceMode=DEFINED_SOURCE`, SPD relativa tabulada normalitzada per nm, geometria puntual o rectangle uniforme, emissió angular axial o separable azimutal normalitzada, amplitud absoluta definida/mesurada o paramètrica, `absoluteCalibrationStatus`, `uncertaintyStatus=not_quantified` i procedència. `spectral_flux`, `spectral_radiant_intensity`, `surface_spectral_exitance` i `surface_spectral_radiance` retornen magnituds amb unitat. Aquesta font **S** es construeix sense RSR ni VIIRS i no és una estimació de ciutat. `CONDITIONAL_L3` (C) està implementat a 7.5.1 i només admet amplitud relativa; `ConditionalScenario` conserva observació L3, RSR de referència, font base, configuració, hipòtesis i ràtio DNB predita. `OBSERVATION_VALIDATED` (H) continua planificat i exigeix contrast empíric independent. No promocionar C a H per QA 0 o RSR de prelanzament. [Política](20-politica-rsr-i-validacio-per-dominis.md) i [evidència S](../evidencies/pas7.5/validacio-source-model-s-v1.md).

## ViirsSourceObservation

`platform`, `instrument`, `productId`, `collection`, `releaseId`, `acquisitionDate`, `granuleId`, `radianciaObservada`, `radianceUnit`, `observationStage=L3_BRDF_CORRECTED`, `measurementModelId`, `qualityFlags`, `provenance`. El model TOA declara separadament `measurementOperatorId=BAND_INTEGRATED`. La [User Guide Black Marble C2, §2.2, equació (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta la transformació de radiància `L_DNB` TOA en radiància nocturna ascendent de superfície `L_NTL`, incloent trajecte atmosfèric, transmissions, albedo/retrodispersió, component lunar i escapament pel dosser. La capa `DNB_BRDF-Corrected_NTL` és aquesta observació L3 corregida; els seus atributs no proporcionen tots els auxiliars per reproduir la correcció píxel a píxel. La caracterització condicionada L3→font C s’implementa a 7.5.1; la inferència absoluta i homologació H continuen a 7.16–7.24. 7.5 conserva S. [Contrast amb grànuls reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md).

`radianciaObservada` no equival a `radianciaArtificialEstimada`; aquesta segona pertany a `SourceModel`. El valor original no es trunca silenciosament a zero.

### Vnp46Observation local (Pas 7.2)

El [lector implementat](../../backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py) retorna un DTO immutable per píxel amb `schemaVersion`, `profileId`, `productId`, `collection`, `acquisitionDate`, fila/columna, latitud/longitud, `rawRadiance`, `radianceUnit`, `qualityFlag`, `qfCloudMask`, `snowFlag`, `latestHighQualityRetrieval`, `isFill`, `classification` i `sourceInferenceCandidate`. La procedència inclou identificador i SHA-256 del grànul, URL d'origen si es coneix, DOI, versions d'algorisme/PGE, temps de producció, període, identificadors de tile, referències d'entrada de processament i atributs autoritatius de la capa. El lector no aplica escala, offset, correcció de punt zero, gap-fill ni inferència d'emissió. El contracte s'ha provat amb fixtures HDF5 i un [grànul binari real aportat localment](../evidencies/pas7.2/validacio-adaptador.md); aquest tile no conté QA 0.

## ViirsSpectralResponse

`sensor`, `platform`, `band=DNB`, `gainStage`, `application`, `productId`, `collection`, `releaseId`, `validFrom`, `validThrough`, vector λ/RSR, `measurementOperatorId=BAND_INTEGRATED`, `evidenceClass`, `gainMappingEvidence?`, `l3LinkStatus`, `spectralUncertaintyStatus`, `sourceUrl`, `retrievedAt`, `localSha256`, `sourceChecksum?`, `redistributionStatus`, `provenance`. El lector local de 7.3 exigeix les claus de selecció, SHA-256 local i unitats `nm`/adimensional; no presenta el fingerprint com a checksum de font. La classe d'evidència distingeix RSR directa, reconstruïda, proxy oficial, històrica/experimental, família incerta i indisponible. Cap etiqueta de RSR implica vincle L3 ni cota d'error.

La selecció de RSR utilitza `acquisitionDate`; el recurs declara l'interval de validesa. `gainStage` identifica guany o resposta efectiva **només amb evidència**; el lector no l'infereix del fitxer L3. Absència, ambigüitat o model no homologat són estats separats. Les corbes NOAA de prelanzament estan registrades sota `VIIRS_DNB_TOA`/`at_launch_reference` i no es resolen com a `VJ146A2.002` o `VJ246A2.002` L3 de 2026; la LGS SNPP de 2013 tampoc és fallback. [Evidència](../evidencies/pas7.3/revisio-multisatel-lit.md).

El [gate estricte H conservat](../../backend/src/terralab3d/domain/light_pollution/source_model.py) distingeix `validated_l3_basis_candidate` —condicions **necessàries** de RSR/guany/vincle L3 per inferència observacional, sense crear cap font— de `product_homologation_candidate`, que demana addicionalment incertesa espectral quantificada. L'[auditoria real](../evidencies/pas7.5/estat-inferencia-font-2026.md) retorna indisponibilitat per a les fonts Black Marble instal·lades del 2026. Això no limita els escenaris C relatius de 7.5.1 ni les [fonts S verificades](../evidencies/pas7.5/validacio-source-model-s-v1.md): els perfils angulars declarats no acrediten una ciutat ni resolen l'operador L3→font.

**Unitat DNB verificada:** l'[ATBD VIIRS SDR](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf) especifica radiància integrada `W cm⁻² sr⁻¹` i RSR energètica amb `λ` incorporat. El [model local](../../backend/src/terralab3d/domain/light_pollution/dnb_measurement.py) integra radiància espectral TOA en `nW cm⁻² sr⁻¹ nm⁻¹` amb RSR adimensional i retorna `nW cm⁻² sr⁻¹`, etiquetat `at_sensor_toa`; no torna a multiplicar per `λ`. Black Marble L3 és la radiància corregida de superfície de la mateixa dimensió, però no la mateixa magnitud física. La correcció és documentada per NASA; [SNPP anual](../evidencies/pas7.3/recerca-rsr-2026.md) i [J1/J2](../evidencies/pas7.3/revisio-multisatel-lit.md) no aporten encara una RSR operativa de 2026 amb incertesa per inferir la font.

`DnbBandMeasurement.to_dict()` serialitza `schemaVersion=1`, `physicalStage=at_sensor_toa`, radiància/unitat, identitat de plataforma/producte/col·lecció, dia quan es facilita `MeasurementTarget`, release/guany/aplicació/finestra de la RSR, URL, data de recuperació, SHA-256 local, checksum de font opcional, arxiu/membre d'origen i els seus fingerprints si consten al manifest, redistribució, classe/referència d'evidència, mapping de guany i estats/evidències separats de vincle L3 i incertesa. Aquest DTO és diagnòstic; no afirma que el resultat TOA sigui una observació L3 ni que un text d'evidència o un hash local siguin verificació externa suficient.

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

Els DTO d’escena utilitzen camelCase. La configuració científica `SkyglowConfiguration` manté explícitament les claus snake_case del mateix objecte immutable Python al JSON i a TypeScript, sense dos esquemes competidors. La validació de schema s'executa als dos costats. Qualsevol canvi incompatible incrementa `schemaVersion`; no es reutilitza un camp canviant-ne la unitat.
## Selector visual independent

`skyRenderingMode=simulated|physical` és un contracte de presentació persistent, ortogonal a `lightPollutionMode` i `atmosphereEnabled`. `skyPhysicalAvailability=initializing|available|unavailable` incorpora causa i revisió. Les respostes SQM/TESS provenen de radiància espectral i respostes instrumentals, no del mode visual. Vegeu [contractes del cel físic](../cel-fisic/04-contractes-validacio.md).


## Restriccions de producte VNP46

`VNP46A2.002` és el contracte inicial congelat al [perfil v1](skyglow-v1-profile.json) i verificat a 7.2; el [perfil v2](skyglow-v2-profile.json) afegeix `VJ146A2.002` i `VJ246A2.002` com a candidates. Dos grànuls VJ146 reals comparteixen l'estructura de les nou capes i la semàntica QA 0–5 de la guia amb VNP46, i el lector compartit admet VJ146 només amb una política NOAA-20 explícita, DOI/plataforma/versió propis verificats a 7.5.1. La política VNP46 continua rebutjant un grànul VJ146. VJ246 no s'ha contrastat amb HDF5 real. El valor cru i els flags es conserven; fill, negatius i qualitat degradada no s'infereixen com a font. No hi ha correcció de punt zero universal ni doble correcció de stray light. Dia exacte, sense gap-fill/interpolació o substitució de sensor silenciosa. La política `V1` està preregistrada; cap llindar numèric no es fixa aquí sense procedència.


## SkyglowConfiguration i ConditionalScenario (7.5.1)

`configure_skyglow` transporta `configuration` amb `mode=realistic|kelvin`, `kelvin`, `spectral_family=CIE_LED_B1_B5`, `normalization=constant_photopic_flux|constant_radiant_power|constant_dnb_reference|conditional_relative`, `mixture_model` i `revision`. Python valida i calcula l’SPD/CCT efectiva; `skyglow_configuration_snapshot` retorna `schemaVersion=1`, generació, hash de configuració, revisió espectral, SPD efectiva, qualitat i estat. `blackMarble`/`rsr` són null al nivell de configuració fins a seleccionar observacions; el CLI de fonts els resol dins cada escenari. `skyRadiance=null`, `calculationStatus=transport_pending`: el render no rep ni inventa radiància.

L’ancoratge relatiu és `A0=(L3/Lref)*(A/Aref)/(d0*a(0)/sr^-1)`, amb `Lref=1 nW cm^-2 sr^-1`, `Aref=1 m²` i `d0=∫s0 R dλ`. És una convenció paramètrica explícita per a radiància zenital hipotètica, sense inversió BRDF/atmosfera ni watts. El rectangle tangent és de 15 arcsec amb radi esfèric 6371008,8 m i altura definida 0 m. Per canviar SPD, `A=A0*q(s0)/q(s)` amb `q=683∫sV` (fotòpic), `q=1` (radiant), `q=∫sR` (DNB) o escala relativa fixa. `predictedDnbRatio=(A/A0)*d/d0`; no és radiància satel·lital certificada.

Les tres mescles base LED/sodi són alternatives de flux radiant explícites (80/20, 20/80, 95/5 amb LED fred al tercer cas); no estadístiques locals. Dos patrons angulars hipotètics (uniforme i cosinus tabulat cada 5°) donen sis fonts per píxel i modalitat. Mateixa font `SourceModel` S/C per a SG-REF, amb etiqueta C i procedència pròpies.

La clau d’escenari inclou configuració completa, revisions, components i hashes SPD, observació/QA/llinatge/píxel, RSR/guany/release, geometria i patró angular. Canviar modalitat, K, normalització o qualsevol entrada invalida resultats compatibles només amb l’antic hash. 7.25–7.27 consumiran aquestes claus; encara no existeix cache de propagació.


El gate estricte exposa `validated_l3_basis_candidate` i `unavailable_for_validated_l3_inference`; la manca de cadena acreditada H no és una indisponibilitat global de la simulació C. Les evidències històriques conserven els identificadors i estats emesos al seu moment.

## SG-REF offline (7.6)

`ReferenceOptics` declara longituds d’ona, extinció/dispersió en m⁻¹, altura superior, fase i procedència d’un slab homogeni. `ReferenceSettings` controla LOS GK21, error absolut, refinament d’àrea GL i límits de treball. `ReferenceRadiance` retorna longituds d’ona, valors en `W m^-2 sr^-1 nm^-1` o `relative m^-2 sr^-1 nm^-1`, fonts/modes, signatura de totes les entrades, historial espacial i nombre d’avaluacions. `numerical_error_estimate` combina estimació LOS i diferència espacial; no és un interval rigorós ni incertesa de dades/model. `runtimeGate=not_evaluated_step_7.12` i `empiricalValidation=not_evaluated` són explícits.

El CLI embolcalla cada `ConditionalScenario` de 7.5.1 amb `referenceRadiance`, observador, direcció, òptica i `calculationStatus=offline_reference_complete`. El context conserva l’estat original de producte `transport_pending`; són nivells diferents. Sis alternatives per configuració es propaguen separadament. `MultipleScatteringEstimate` registra primer ordre, total truncat, ordres superiors, errors estàndard iid, error aparellat de la ràtio F5, llavor/N i cota de cua; el seu domini exigeix radiància superficial limitada i 0<albedo<1. [Contracte executable i límits](../tasques/completat/pas7.6-sg-ref-reference-solver.md).
