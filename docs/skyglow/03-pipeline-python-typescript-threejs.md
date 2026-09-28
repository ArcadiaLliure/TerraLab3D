# Pipeline de desenvolupament Python → TypeScript → Three.js

## Backend / Python

### Ingestió

1. `LightPollutionDatasetAdapter` resol el producte i la versió.
2. Aplica quality mask, nodata, cobertura, geometria i unitats.
3. Converteix a un `ViirsSourceObservation` immutable amb `productId`, `acquisitionPeriod`, `radianceUnit`, `processingLevel`, `sourceUrl`, checksum i qualitat.
4. No interpreta encara la radiància com a emissió terrestre isotropa.

### Preprocessament i fonts

`SourceModelBuilder` aplica el model angular d'emissió i el prior espectral. El segmentador executa log-radiance, denoise conservador, llindar, màxims/prominence, watershed i merge. `EmissionRegionBuilder` conserva geometria, moments radiomètrics i patches. `RadiancePatchTree` refina segons error físic, no segons un nombre objectiu de nodes.

### Espectre

`SpectralBasisLibrary` conté formes normalitzades i metadades. `ViirsSpectralResponseRepository` proporciona la RSR exacta. `SpectralSourceModel` produeix `SpectralSourceEstimate` i ensemble. La normalització DNB es fa a resolució espectral suficient; el kernel rep només `BandRadiance` per `SpectralBandSet`.

### Atmosfera

`AtmosphericOpticsProvider.resolve(position, altitude, time)` compon camps per variable. Cada `OpticalParameter` conserva valor, sigma/model d'incertesa, font, temps de validesa i qualitat. `OpticalFieldBuilder` materialitza tiles/capes versionats. Rayleigh es deriva de P/T/composició; aerosols de AOD/composició/RH i biblioteca òptica; gasos via LUT; núvols només quan la parametrització estigui disponible.

### Kernel

El `PropagationKernel` rep `SourceSet`, `Observer`, `OpticalField`, `TerrainVisibility`, `DirectionSet` i `PropagationOptions`. Recorre LOS, segmenta per tiles, aplica GK 7/15, vectoritza bandes/bases, registra dependències durant la quadratura i retorna radiància, error numèric, comptadors i sensibilitats opcionals.

### Reference solver

Ha d'existir un camí offline més lent amb toleràncies estretes, malla angular densa i espectre fi. No és el mateix que la v1 runtime. Serveix per validar discretització espectral, compressió de cúpules, ordre de fase, H_TOA i quadratura.

### Serialització

El bridge no envia nodes de quadratura. Envia `PropagationResultSummary` i `DomeProfile[]` amb esquema versionat. Els vectors de radiància han d'indicar `bandSetId` i unitats. Els buffers grans es poden transportar binàriament amb el port existent si el benchmark ho justifica.

## TypeScript

### Contractes

Els DTO TypeScript reflecteixen exactament els contractes serialitzats Python, no les dataclasses internes. Tots els enums versionats són unions literals. Radiàncies i angles tenen sufix d'unitat o wrappers; no hi ha `number[]` sense identificador de banda.

### Runtime

`SkyglowRuntime` manté `requestedRevision`, `acceptedRevision`, estat de càlcul, cache de presentació i doble buffer. Cada resultat tardà es descarta. Els canvis ràpids d'observador es coalescen; el frontend no força un càlcul per frame.

### Interpolació

Si el backend envia les 9 mostres verticals, TypeScript reconstrueix PCHIP en `log(B+ε)`. La implementació ha de tenir golden tests compartits amb Python per evitar divergència. Alternativa: backend envia una LUT ja mostrejada; s'ha de benchmarkar cost de bridge vs duplicació numèrica.

### Observabilitat

Registrar revisió, causa de recompute, cache hit/miss, bytes de bridge, latència backend, upload GPU, temps de swap i stutter. No logar rasters ni vectors massius.

## Three.js / GPU

`DomeSkyglowRenderer` és un renderer retingut propietari de buffers/textures. La representació recomanada és una textura o SSBO-equivalent WebGL-friendly amb paràmetres per cúpula: azimut central, amplada, mostres/LUT verticals i radiància espectral o tristímul lineal segons la fase del pipeline.

El shader calcula només distribució angular i suma lineal. El tone mapping global, exposició i transformació a display venen després. El shader no converteix Bortle a brillantor, no calcula extinció atmosfèrica i no consulta DEM.

### Doble buffer

1. resultat N arriba fora del render loop;
2. es valida i es prepara buffer inactiu;
3. upload asíncron/compacte;
4. al següent frame es canvia la referència;
5. el buffer anterior es recicla o disposa segons propietat.

### LOD

LOD de renderer i LOD físic són independents. El renderer pot reduir resolució de LUT o nombre de cúpules molt febles només amb una cota d'error visual/radiomètric. No pot fusionar fonts físicament diferents si això altera el resultat científic que la UI declara.

## Píxel final

`VIIRS radiance → source spectrum/geometry → propagation radiance → dome compression → bridge → linear sky radiance field → natural+artificial linear composition → camera/exposure → tone mapping → display transform → pixel`.

Qualsevol comparació científica s'atura abans de camera/exposure/tone mapping.