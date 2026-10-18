# Pipeline de desenvolupament Python → TypeScript → Three.js

## Backend / Python

### Ingestió

1. El gestor comú del Pas 24 resol i instal·la VNP46/VJ146/VJ246; `LightPollutionDatasetAdapter` delega a un adaptador científic per producte i retorna observació tipada amb identitat i QA. Avui només el lector VNP46 està contrastat amb HDF5 real.
2. Resol producte, release, data/període d'adquisició, quality mask, nodata, cobertura, geometria i unitat declarada pel producte.
3. Publica `ViirsSourceObservation` immutable conservant `radiancia_observada`; no aplica `max(0,·)` ni confon observació amb emissió.
4. Confirma per producte/release quines correccions ja s'han aplicat; stray light no es corregeix dues vegades.
5. Les sèries de baixa radiància que travessen 2017 queden com a no directament comparables fins que es tanqui la política de punt zero.

### Preprocessament i fonts

`SourceModelBuilder` consumeix l'observació VNP46 junt amb el model de mesura DNB. Aplica el prior espectral i el model angular d'emissió seleccionat, amb incertesa explícita. VNP46 no es tracta com a flux hemisfèric ni imposa Lambert.

El segmentador treballa sobre `radiancia_artificial_estimada` o equivalent físicament admissible, no sobre valors crus clipats. Després executa log-radiance, denoise conservador, llindar, màxims/prominence, watershed i merge. `EmissionRegionBuilder` conserva geometria, moments radiomètrics i patches. `RadiancePatchTree` refina segons error físic i valida l'aproximació puntual contra integració d'àrea independent en fixtures de control.

### Espectre

`SpectralBasisLibrary` conté formes normalitzades i metadades. `ViirsSpectralResponseRepository` resol RSR per plataforma/producte/release/guany/data/aplicació; les corbes NOAA de prelanzament són diagnòstiques fins a demostrar-ne la transferència al producte. L'operador `BAND_INTEGRATED` calcula TOA `nW·cm⁻²·sr⁻¹`; la correcció Black Marble L3 és un model diferent documentat a la [User Guide C2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) i contrastat amb [grànuls VJ146 reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md). 7.3 ha completat el contracte de mesura; l'admissibilitat espectral i la inferència L3→font queden per a 7.5/7.16/7.17. Vegeu també [RSR SNPP](../evidencies/pas7.3/recerca-rsr-2026.md) i [revisió J1/J2](../evidencies/pas7.3/revisio-multisatel-lit.md).

`SpectralSourceModel` produeix `SpectralSourceEstimate` i ensemble. VNP46 continua sent una observació panchromàtica: el kernel rep `BandRadiance` per `SpectralBandSet` i no un únic flux acromàtic.

### Atmosfera

`AtmosphericOpticsProvider.resolve(position, altitude, time)` compon camps per variable. Cada `OpticalParameter` conserva valor, sigma/model d'incertesa, font, temps de validesa i qualitat. `OpticalFieldBuilder` materialitza tiles/capes versionats. Rayleigh es deriva de P/T/composició; aerosols de AOD/composició/RH i biblioteca òptica; gasos via LUT; núvols només quan la parametrització estigui disponible.

### Kernel

El `PropagationKernel` rep `SourceSet`, `Observer`, `OpticalField`, `TerrainVisibility`, `DirectionSet` i `PropagationOptions`. Recorre LOS, segmenta per tiles, aplica GK 7/15, vectoritza bandes/bases, registra dependències durant la quadratura i retorna radiància, error numèric, comptadors i sensibilitats opcionals.

### Reference solver

Ha d'existir un camí offline independent per validar el transport. La decisió S1 continua oberta: pot ser un `SG-REF` propi de skyglow o una dependència creuada amb el Pas 7.65. Si es quantifica el biaix single-scattering, l'oracle ha d'incloure multiple scattering segons F5. El gate 7.20 valida transport donat el mateix `SourceModel`; no valida empíricament la inferència VNP46→emissió.

### Projeccions fotomètriques i composició

Després del kernel, `PhotometricProjectionService` calcula projeccions fotòpiques o de sensor amb pesos espectrals/FOV precomputables i versionats. Aquesta etapa no repeteix LOS ni scattering.

`SkyRadianceComposer` combina en radiància lineal canals compatibles: artificial, natural sense Lluna, lunar i crepuscular. Manté simultàniament un estat `reference` i un estat `instantaneous`.

### Serialització

El bridge no envia nodes de quadratura. Envia `PropagationResultSummary` i `DomeProfile[]` amb esquema versionat. Els vectors de radiància han d'indicar `bandSetId` i unitats. Els buffers grans es poden transportar binàriament amb el port existent si el benchmark ho justifica.

## TypeScript

### Contractes

Els DTO TypeScript reflecteixen exactament els contractes serialitzats Python, no les dataclasses internes. Tots els enums versionats són unions literals. Radiàncies i angles tenen sufix d'unitat o wrappers; no hi ha `number[]` sense identificador de banda.

### Runtime

`SkyglowRuntime` manté `requestedRevision`, `acceptedRevision`, estat de càlcul, cache de presentació i doble buffer. Cada resultat tardà es descarta. Els canvis ràpids d'observador es coalescen; el frontend **no força mai una integral del kernel per frame**. El scheduler pot demanar precàrrega segons posició, velocitat i direcció de moviment, però una resposta prefetched només s'accepta després de validar clau, versions, topologia i error.

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

`VNP46 observation → DNB measurement model/RSR → SourceModel spectrum+angular emission → spectral propagation radiance → dome compression → bridge → linear artificial field → + natural moonless + moon + twilight → camera/exposure → tone mapping → display transform → pixel`.

En paral·lel, el resultat físic pot passar per `PhotometricProjectionService` per obtenir luminància, SQM/TESS simulats i `BortleEquivalent`; aquestes projeccions no són la font del kernel.

Qualsevol comparació científica s'atura abans de camera/exposure/tone mapping.
## Cel físic astral separat

La [vertical 7.51+](../cel-fisic/README.md) calcula fonts solars/lunars i transport Hillaire de visualització amb LUT GPU, i manté una ruta espectral independent per a sensors. No comparteix integrador ni pipeline VIIRS amb el skyglow artificial; la composició es fa abans de l'exposició.


### Acceleració offline

Es poden precalcular LUT o kernels i, quan les hipòtesis de simetria ho permetin, usar convolució FFT. Aquesta ruta és un backend del mateix operador físic: ha de conservar bandes, model de font, atmosfera i terreny dins el domini declarat i comparar-se contra la ruta directa. Si la invariància translacional no es compleix, la FFT no és aplicable.
